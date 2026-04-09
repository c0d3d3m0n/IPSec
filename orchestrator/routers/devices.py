from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from typing import List
import json
import hmac
import hashlib
import importlib.util
import os
import sys
from pathlib import Path
from .. import models, schemas, database
from datetime import datetime
from orchestrator.rate_limiter import limiter

router = APIRouter(
    prefix="/devices",
    tags=["devices"]
)

from ..auth import get_current_active_user, get_current_admin_user


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
    )
    db.add(cert_record)
    db.commit()

    ca_cert_pem = Path(ca_cert_path).read_text()
    return {
        **schemas.Device.model_validate(db_device).model_dump(),
        "cert_pem": cert_pem.decode("utf-8"),
        "private_key_pem": private_key_pem.decode("utf-8"),
        "ca_cert_pem": ca_cert_pem,
    }

@router.get("/", response_model=List[schemas.Device])
def read_devices(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    devices = db.query(models.Device).offset(skip).limit(limit).all()
    return devices

@router.post("/register", response_model=schemas.Device)
def register_device(
    device: schemas.DeviceAdminCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Admin endpoint to pre-register a device."""
    existing = db.query(models.Device).filter(models.Device.enrollment_number == device.enrollment_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Enrollment number already exists")
        
    new_device = models.Device(
        enrollment_number=device.enrollment_number,
        enrollment_token=device.enrollment_token,
        pre_shared_key=device.pre_shared_key or device.enrollment_token,
        status="PENDING"
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.get("/{device_id}", response_model=schemas.Device)
def read_device(
    device_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.get("/{device_id}/config", response_model=schemas.PolicyResponse)
def get_device_config(
    device_id: int,
    device_token: str = Header(..., alias="X-Enrollment-Token"),
    db: Session = Depends(database.get_db),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.enrollment_token != device_token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")
    
    if device.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device enrollment is not active")

    if not device.policy:
        # Update last_seen even if no policy, to act as heartbeat
        device.last_seen = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=404, detail="No policy assigned to this device")
        
    # Update last_seen on every config poll (heartbeat)
    device.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    policy = device.policy
    policy.config_data = json.loads(policy.config_data)
    
    return policy
