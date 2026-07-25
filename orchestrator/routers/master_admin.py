from typing import Any, Optional
import base64
import json

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
import pyotp

from orchestrator import database, models, schemas, security
from orchestrator.config import get_settings
from orchestrator.models.compliance import ComplianceRecord
from orchestrator.models.core import SystemSettings
from orchestrator.security.totp_manager import TOTPManager

router = APIRouter(
    prefix="/_master_admin",
    tags=["master_admin"],
)

security_basic = HTTPBasic()


def get_master_admin_totp_secret(db: Session) -> Optional[str]:
    setting = db.query(SystemSettings).filter(SystemSettings.key == "master_admin_totp_secret").first()
    return setting.value if setting else None


def set_master_admin_totp_secret(db: Session, secret: str):
    setting = db.query(SystemSettings).filter(SystemSettings.key == "master_admin_totp_secret").first()
    if setting:
        setting.value = secret
    else:
        setting = SystemSettings(key="master_admin_totp_secret", value=secret)
        db.add(setting)
    db.commit()


def verify_master_admin(credentials: HTTPBasicCredentials = Depends(security_basic)):
    settings = get_settings()
    correct_username = settings.effective_master_username
    correct_password = settings.effective_master_password
    
    if not (credentials.username == correct_username and credentials.password == correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect master admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def require_totp(request: Request, db: Session = Depends(database.get_db), username: str = Depends(verify_master_admin)):
    """Verifies that the TOTP code was provided in a header (X-TOTP-Code) if TOTP is enabled."""
    secret = get_master_admin_totp_secret(db)
    if not secret:
        # If TOTP not setup yet, just allow (or force them to set it up)
        return username

    totp_code = request.headers.get("X-TOTP-Code")
    if not totp_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TOTP code required via X-TOTP-Code header",
        )
    
    if not TOTPManager().verify_code(secret, totp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )
    
    return username


# ─── TOTP SETUP ─────────────────────────────────────────────────────────────

@router.get("/totp/status")
def get_totp_status(db: Session = Depends(database.get_db), username: str = Depends(verify_master_admin)):
    secret = get_master_admin_totp_secret(db)
    return {"totp_enabled": secret is not None}

@router.post("/totp/setup")
def setup_totp(db: Session = Depends(database.get_db), username: str = Depends(verify_master_admin)):
    # We only allow setup if it's not set up yet
    if get_master_admin_totp_secret(db):
        raise HTTPException(status_code=400, detail="TOTP is already set up.")
        
    manager = TOTPManager()
    secret = manager.generate_secret()
    uri = manager.get_provisioning_uri(secret, username)
    qr_b64 = manager.qr_png_base64(uri)
    
    return {
        "secret": secret,
        "uri": uri,
        "qr_base64": qr_b64
    }

@router.post("/totp/verify")
def verify_setup_totp(body: dict, db: Session = Depends(database.get_db), username: str = Depends(verify_master_admin)):
    code = body.get("code")
    secret = body.get("secret")
    
    if not code or not secret:
        raise HTTPException(status_code=400, detail="Code and secret required")
        
    if not TOTPManager().verify_code(secret, code):
        raise HTTPException(status_code=400, detail="Invalid code")
        
    set_master_admin_totp_secret(db, secret)
    return {"message": "TOTP successfully configured."}


# ─── TENANT MANAGEMENT ──────────────────────────────────────────────────────

@router.post("/tenants/", status_code=status.HTTP_201_CREATED)
def create_tenant(
    body: schemas.TenantCreate,
    db: Session = Depends(database.get_db),
    username: str = Depends(require_totp),
):
    existing = db.query(models.Tenant).filter(models.Tenant.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")

    if db.query(models.User).filter(models.User.username == body.admin_username).first():
        raise HTTPException(status_code=400, detail="Admin username already taken")
    if db.query(models.User).filter(models.User.email == body.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already taken")

    tenant = models.Tenant(
        name=body.name,
        slug=body.slug,
        plan=body.plan,
        max_devices=body.max_devices,
        max_users=body.max_users,
        contact_email=body.contact_email,
    )
    db.add(tenant)
    db.flush() 

    # Create first tenant admin user
    admin_user = models.User(
        username=body.admin_username,
        email=body.admin_email,
        hashed_password=security.get_password_hash(body.admin_password),
        role=models.UserRole.TENANT_ADMIN,
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


@router.get("/tenants/")
def list_tenants(
    db: Session = Depends(database.get_db),
    username: str = Depends(require_totp),
):
    tenants = db.query(models.Tenant).all()
    result = []
    for t in tenants:
        device_count = db.query(func.count(models.Device.id)).filter(models.Device.tenant_id == t.id).scalar() or 0
        user_count = db.query(func.count(models.User.id)).filter(models.User.tenant_id == t.id).scalar() or 0
        policy_count = db.query(func.count(models.Policy.id)).filter(models.Policy.tenant_id == t.id).scalar() or 0

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
