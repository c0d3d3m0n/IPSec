from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import hmac
import hashlib
import importlib.util
import os
import sys
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from .. import models, schemas, database
from datetime import datetime
from orchestrator.rate_limiter import limiter

router = APIRouter(
    prefix="/devices",
    tags=["devices"]
)

from ..auth import get_current_user, get_current_admin_user, get_tenant_filter, require_tenant_admin


def _load_module(module_name: str, file_path: Path):
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_BASE_DIR = Path(__file__).resolve().parents[1]
_ca_module = _load_module("orchestrator_security_certificate_authority", _BASE_DIR / "security" / "certificate_authority.py")
_cert_models_module = _load_module("orchestrator_models_certificate", _BASE_DIR / "models" / "certificate.py")
InternalCA = _ca_module.InternalCA
DeviceCertificate = _cert_models_module.DeviceCertificate


def _safe_serialize_device(device: models.Device) -> dict:
    return {
        "id": device.id,
        "hostname": device.hostname,
        "os_type": device.os_type,
        "public_ip": device.public_ip,
        "enrollment_number": device.enrollment_number,
        "enrollment_token": device.enrollment_token,
        "os_fingerprint": device.os_fingerprint,
        "status": device.status,
        "is_active": device.is_active,
        "last_seen": device.last_seen,
        "policy_id": device.policy_id,
        "policy": None,
        "tenant_id": device.tenant_id,
        "created_at": device.created_at,
    }

@router.post("/enroll", response_model=schemas.DeviceEnrollmentResponse)
@limiter.limit("5/minute")
def enroll_device(request: Request, device: schemas.DeviceCreate, db: Session = Depends(database.get_db)):
    # 1. Look for pre-registered device with this number and token
    clean_no = device.enrollment_number.strip()
    clean_token = device.enrollment_token.strip()
    
    db_device = db.query(models.Device).filter(
        models.Device.enrollment_number == clean_no,
        models.Device.enrollment_token == clean_token
    ).first()
    
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid enrollment credentials. Please contact your administrator."
        )
    
    if db_device.status == "REVOKED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This enrollment has been revoked."
        )

    # Verify tenant is active
    if db_device.tenant_id:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == db_device.tenant_id).first()
        if tenant and not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is inactive. Contact your administrator."
            )

    pre_shared_key = (db_device.pre_shared_key or db_device.enrollment_token or "").strip()
    expected_signature = hmac.new(
        pre_shared_key.encode("utf-8"),
        device.os_fingerprint.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, device.agent_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent signature")

    # 2. Update device info and activate
    db_device.hostname = device.hostname
    db_device.os_type = device.os_type
    db_device.public_ip = device.public_ip
    db_device.os_fingerprint = device.os_fingerprint
    db_device.status = "ACTIVE"
    db_device.last_seen = datetime.utcnow()
    
    db.commit()
    db.refresh(db_device)

    ca_cert_path = os.getenv("CA_CERT_PATH", "keys/ca.crt")
    ca_key_path = os.getenv("CA_KEY_PATH", "keys/ca.key")
    ca = InternalCA(ca_cert_path=ca_cert_path, ca_key_path=ca_key_path)
    cert_pem, private_key_pem = ca.issue_device_certificate(
        device_id=db_device.id,
        enrollment_number=db_device.enrollment_number,
        os_type=db_device.os_type or "unknown",
        valid_days=int(os.getenv("DEVICE_CERT_VALID_DAYS", "90")),
    )

    from cryptography import x509

    cert_obj = x509.load_pem_x509_certificate(cert_pem)
    cert_record = DeviceCertificate(
        device_id=db_device.id,
        cert_serial=str(cert_obj.serial_number),
        cert_pem=cert_pem.decode("utf-8"),
        expires_at=cert_obj.not_valid_after,
        is_active=True,
        tenant_id=db_device.tenant_id,
    )
    db.add(cert_record)
    db.commit()

    ca_cert_pem = Path(ca_cert_path).read_text()
    return {
        **_safe_serialize_device(db_device),
        "cert_pem": cert_pem.decode("utf-8"),
        "private_key_pem": private_key_pem.decode("utf-8"),
        "ca_cert_pem": ca_cert_pem,
    }

@router.get("/", response_model=List[schemas.Device])
def read_devices(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    tenant_filter: Optional[int] = Depends(get_tenant_filter),
):
    query = db.query(models.Device)
    if tenant_filter is not None:
        query = query.filter(models.Device.tenant_id == tenant_filter)
    devices = query.offset(skip).limit(limit).all()
    return [_safe_serialize_device(device) for device in devices]

@router.post("/register", response_model=schemas.Device)
def register_device(
    device: schemas.DeviceAdminCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_tenant_admin),
    tenant_filter: Optional[int] = Depends(get_tenant_filter),
):
    """Admin endpoint to pre-register a device."""
    # Determine tenant_id
    tenant_id = tenant_filter or current_user.tenant_id
    
    # Check device limit
    if tenant_id:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if tenant:
            current_count = db.query(models.Device).filter(
                models.Device.tenant_id == tenant_id,
            ).count()
            if current_count >= tenant.max_devices:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Device limit reached ({tenant.max_devices}). Upgrade your plan to add more devices.",
                )

    existing = db.query(models.Device).filter(models.Device.enrollment_number == device.enrollment_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Enrollment number already exists")

    token_exists = db.query(models.Device).filter(models.Device.enrollment_token == device.enrollment_token).first()
    if token_exists:
        raise HTTPException(status_code=400, detail="Enrollment token already exists")
        
    new_device = models.Device(
        enrollment_number=device.enrollment_number,
        enrollment_token=device.enrollment_token,
        pre_shared_key=device.pre_shared_key or device.enrollment_token,
        status="PENDING",
        tenant_id=tenant_id,
    )
    db.add(new_device)
    try:
        db.commit()
        db.refresh(new_device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Device enrollment number or token already exists")
    return _safe_serialize_device(new_device)

@router.get("/{device_id}", response_model=schemas.Device)
def read_device(
    device_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
    tenant_filter: Optional[int] = Depends(get_tenant_filter),
):
    query = db.query(models.Device).filter(models.Device.id == device_id)
    if tenant_filter is not None:
        query = query.filter(models.Device.tenant_id == tenant_filter)
    device = query.first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return _safe_serialize_device(device)

@router.get("/{device_id}/config")
def get_device_config(
    device_id: int,
    device_token: str = Header(..., alias="X-Enrollment-Token"),
    os_type: str | None = Query(default=None),
    db: Session = Depends(database.get_db),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.enrollment_token != device_token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")

    # Check tenant is active
    if device.tenant_id:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == device.tenant_id).first()
        if tenant and not tenant.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")

    # Heartbeat used to write runtime states (NO_POLICY/DEGRADED/ERROR) into
    # device.status; treat those as enrolled and normalize back to ACTIVE.
    status_normalized = (device.status or "").strip().upper()
    if status_normalized in {"NO_POLICY", "DEGRADED", "ERROR"}:
        device.status = "ACTIVE"
        db.commit()
        db.refresh(device)

    if device.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device enrollment is not active")

    if not device.policy:
        # Update last_seen even if no policy, to act as heartbeat
        device.last_seen = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No policy assigned to this device",
                "device_id": device_id,
                "action_required": "contact_admin",
            },
        )

    if os_type is not None:
        normalized_os = os_type.strip().lower()
        if normalized_os not in {"linux", "windows", "macos"}:
            raise HTTPException(status_code=422, detail=f"Unsupported OS type: {os_type}")

    # Update last_seen on every config poll (heartbeat)
    device.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    policy = device.policy
    config_data = json.loads(policy.config_data) if isinstance(policy.config_data, str) else policy.config_data

    if os_type is None:
        return config_data

    normalized_os = os_type.strip().lower()
    per_os_configs = config_data.get("per_os_configs") or {}
    if normalized_os not in per_os_configs:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Assigned policy has no config for OS '{normalized_os}'",
                "device_id": device_id,
                "policy_id": config_data.get("policy_id", policy.name),
                "available_os": list(per_os_configs.keys()),
                "action_required": "ask_admin_to_update_policy_target_os",
            },
        )

    os_config = per_os_configs[normalized_os]
    return {
        "policy_id": config_data.get("policy_id", policy.name),
        "version": config_data.get("version"),
        "description": config_data.get("description"),
        "ike_encryption": os_config.get("ike_encryption"),
        "ike_integrity": os_config.get("ike_integrity"),
        "ike_dh_group": os_config.get("ike_dh_group"),
        "esp_encryption": os_config.get("esp_encryption"),
        "esp_integrity": os_config.get("esp_integrity"),
        "esp_dh_group": os_config.get("esp_dh_group"),
        "key_exchange": os_config.get("key_exchange"),
        "mode": os_config.get("mode"),
        "connections": os_config.get("connections", []),
        "auth_type": os_config.get("auth_type"),
        "auth_secret_ref": os_config.get("auth_secret_ref"),
        "driver_block": os_config.get("driver_block", {}),
        "compliance": config_data.get("compliance", {}),
        "execution": config_data.get("execution", {}),
        "parse_warnings": config_data.get("parse_warnings", []),
    }
