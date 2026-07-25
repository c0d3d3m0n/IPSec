"""Master Admin router — platform-wide tenant management.

All routes require the MASTER_ADMIN role.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from orchestrator import database, models, schemas, security
from orchestrator.auth import require_master_admin, get_current_user
from orchestrator.models.user import UserRole

import importlib.util
import sys
from pathlib import Path


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
_compliance_model = _load_module("orchestrator_models_compliance", _BASE_DIR / "models" / "compliance.py")
_audit_model = _load_module("orchestrator_models_audit", _BASE_DIR / "models" / "audit.py")

ComplianceRecord = _compliance_model.ComplianceRecord
AuditLog = _audit_model.AuditLog

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


# ─── POST /api/admin/tenants/ ───────────────────────────────────────────────
@router.post("/tenants/", status_code=status.HTTP_201_CREATED)
def create_tenant(
    body: schemas.TenantCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_master_admin),
):
    # Check slug uniqueness
    existing = db.query(models.Tenant).filter(models.Tenant.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")

    # Check admin username/email uniqueness
    if db.query(models.User).filter(models.User.username == body.admin_username).first():
        raise HTTPException(status_code=400, detail="Admin username already taken")
    if db.query(models.User).filter(models.User.email == body.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already taken")

    # Create tenant
    tenant = models.Tenant(
        name=body.name,
        slug=body.slug,
        plan=body.plan,
        max_devices=body.max_devices,
        max_users=body.max_users,
        contact_email=body.contact_email,
    )
    db.add(tenant)
    db.flush()  # get tenant.id

    # Create first tenant admin user
    admin_user = models.User(
        username=body.admin_username,
        email=body.admin_email,
        hashed_password=security.get_password_hash(body.admin_password),
        role=UserRole.TENANT_ADMIN,
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(tenant)
    db.refresh(admin_user)

    return {
        "tenant": schemas.TenantResponse.model_validate(tenant).model_dump(mode="json"),
        "admin_user": schemas.UserResponse.model_validate(admin_user).model_dump(mode="json"),
    }


# ─── GET /api/admin/tenants/ ────────────────────────────────────────────────
@router.get("/tenants/")
def list_tenants(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_master_admin),
):
    tenants = db.query(models.Tenant).all()
    result = []
    for t in tenants:
        device_count = db.query(func.count(models.Device.id)).filter(models.Device.tenant_id == t.id).scalar() or 0
        user_count = db.query(func.count(models.User.id)).filter(models.User.tenant_id == t.id).scalar() or 0
        policy_count = db.query(func.count(models.Policy.id)).filter(models.Policy.tenant_id == t.id).scalar() or 0

        # Compliant devices: latest compliance record per device is compliant
        compliant_count = 0
        tenant_devices = db.query(models.Device).filter(models.Device.tenant_id == t.id).all()
        for d in tenant_devices:
            latest = (
                db.query(ComplianceRecord)
                .filter(ComplianceRecord.device_id == d.id)
                .order_by(ComplianceRecord.timestamp.desc())
                .first()
            )
            if latest and latest.is_compliant:
                compliant_count += 1

        # Last activity: most recent last_seen across tenant devices
        last_activity = (
            db.query(func.max(models.Device.last_seen))
            .filter(models.Device.tenant_id == t.id)
            .scalar()
        )

        item = schemas.TenantResponse.model_validate(t).model_dump(mode="json")
        item.update({
            "device_count": device_count,
            "user_count": user_count,
            "policy_count": policy_count,
            "compliant_device_count": compliant_count,
            "last_activity": last_activity.isoformat() if last_activity else None,
        })
        result.append(item)

    return result


# ─── GET /api/admin/tenants/{tenant_id} ─────────────────────────────────────
@router.get("/tenants/{tenant_id}")
def get_tenant_detail(
    tenant_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_master_admin),
):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = db.query(models.User).filter(models.User.tenant_id == tenant_id).all()
    devices = db.query(models.Device).filter(models.Device.tenant_id == tenant_id).all()
    policies = db.query(models.Policy).filter(models.Policy.tenant_id == tenant_id).all()

    # Compliance summary
    total_devices = len(devices)
    compliant = 0
    for d in devices:
        latest = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.device_id == d.id)
            .order_by(ComplianceRecord.timestamp.desc())
            .first()
        )
        if latest and latest.is_compliant:
            compliant += 1

    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    device_ids = [d.id for d in devices]

    violations_24h = 0
    bytes_encrypted_24h = 0
    if device_ids:
        recent_records = (
            db.query(ComplianceRecord)
            .filter(
                ComplianceRecord.device_id.in_(device_ids),
                ComplianceRecord.timestamp >= since_24h,
            )
            .all()
        )
        for r in recent_records:
            if not r.is_compliant:
                violations_24h += 1
            bytes_encrypted_24h += r.total_bytes_encrypted or 0

    # Build device list with latest compliance
    device_list = []
    for d in devices:
        d_dict = {
            "id": d.id,
            "hostname": d.hostname,
            "os_type": d.os_type,
            "public_ip": d.public_ip,
            "enrollment_number": d.enrollment_number,
            "enrollment_token": d.enrollment_token,
            "os_fingerprint": d.os_fingerprint,
            "status": d.status,
            "is_active": d.is_active,
            "last_seen": d.last_seen,
            "policy_id": d.policy_id,
            "tenant_id": d.tenant_id,
            "created_at": d.created_at,
            "policy": None,
            "latest_compliance": None,
        }
        latest = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.device_id == d.id)
            .order_by(ComplianceRecord.timestamp.desc())
            .first()
        )
        if latest:
            d_dict["latest_compliance"] = latest.is_compliant
        device_list.append(d_dict)

    # Safe policy serialization
    import json
    policy_list = []
    for p in policies:
        config = p.config_data
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                config = {}
        policy_list.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "config_data": config if isinstance(config, dict) else {},
            "tenant_id": p.tenant_id,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })

    tenant_data = schemas.TenantResponse.model_validate(tenant).model_dump(mode="json")
    tenant_data.update({
        "users": [schemas.UserResponse.model_validate(u).model_dump(mode="json") for u in users],
        "devices": device_list,
        "policies": policy_list,
        "compliance_summary": {
            "total_devices": total_devices,
            "compliant": compliant,
            "violations_24h": violations_24h,
            "bytes_encrypted_24h": bytes_encrypted_24h,
        },
    })

    return tenant_data


# ─── PUT /api/admin/tenants/{tenant_id} ─────────────────────────────────────
@router.put("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: int,
    body: schemas.TenantUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_master_admin),
):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.plan is not None:
        tenant.plan = body.plan
    if body.max_devices is not None:
        tenant.max_devices = body.max_devices
    if body.max_users is not None:
        tenant.max_users = body.max_users
    if body.contact_email is not None:
        tenant.contact_email = body.contact_email
    if body.is_active is not None:
        tenant.is_active = body.is_active
        if not body.is_active:
            # Deactivate all tenant devices
            db.query(models.Device).filter(
                models.Device.tenant_id == tenant_id
            ).update({"is_active": False})

    db.commit()
    db.refresh(tenant)
    return schemas.TenantResponse.model_validate(tenant).model_dump(mode="json")


# ─── DELETE /api/admin/tenants/{tenant_id} ───────────────────────────────────
@router.delete("/tenants/{tenant_id}")
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_master_admin),
):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Soft delete — never hard delete
    tenant.is_active = False
    db.query(models.Device).filter(
        models.Device.tenant_id == tenant_id
    ).update({"is_active": False})
    db.commit()

    return {"message": f"Tenant '{tenant.name}' deactivated"}


# ─── GET /api/admin/platform/stats ──────────────────────────────────────────
@router.get("/platform/stats")
def platform_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_master_admin),
):
    total_tenants = db.query(func.count(models.Tenant.id)).scalar() or 0
    active_tenants = db.query(func.count(models.Tenant.id)).filter(models.Tenant.is_active == True).scalar() or 0
    total_devices = db.query(func.count(models.Device.id)).scalar() or 0
    active_devices = db.query(func.count(models.Device.id)).filter(models.Device.is_active == True).scalar() or 0
    total_policies = db.query(func.count(models.Policy.id)).scalar() or 0

    # Compliance rate: % of devices whose latest record is compliant
    all_devices = db.query(models.Device).all()
    compliant_count = 0
    for d in all_devices:
        latest = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.device_id == d.id)
            .order_by(ComplianceRecord.timestamp.desc())
            .first()
        )
        if latest and latest.is_compliant:
            compliant_count += 1
    compliance_rate = (compliant_count / total_devices * 100) if total_devices > 0 else 0.0

    since_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    violations_today = (
        db.query(func.count(ComplianceRecord.id))
        .filter(ComplianceRecord.is_compliant == False, ComplianceRecord.timestamp >= since_today)
        .scalar() or 0
    )
    api_calls_today = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= since_today)
        .scalar() or 0
    )

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_devices": total_devices,
        "active_devices": active_devices,
        "total_policies": total_policies,
        "compliance_rate": round(compliance_rate, 1),
        "violations_today": violations_today,
        "api_calls_today": api_calls_today,
    }
