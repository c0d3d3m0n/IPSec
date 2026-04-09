from datetime import datetime, timedelta, timezone
import importlib.util
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import database, models, security, schemas
from orchestrator.auth import get_current_admin_user
from orchestrator.rate_limiter import limiter

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


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
_totp_module = _load_module("orchestrator_security_totp_manager", _BASE_DIR / "security" / "totp_manager.py")
_token_module = _load_module("orchestrator_security_token_manager", _BASE_DIR / "security" / "token_manager.py")
TOTPManager = _totp_module.TOTPManager
TokenManager = _token_module.TokenManager


@router.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    totp_code: str | None = Form(default=None),
    db: Session = Depends(database.get_db),
):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > now:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked due to failed logins")

    if not security.verify_password(form_data.password, user.hashed_password):
        user.failed_attempts = int(user.failed_attempts or 0) + 1
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.totp_enabled:
        if not totp_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="totp_code is required")
        if not TOTPManager().verify_code(user.totp_secret or "", str(totp_code)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    
    manager = TokenManager()
    identity = {"sub": user.username, "admin_id": user.id}
    access_token = manager.create_access_token(identity)
    refresh_token = manager.create_refresh_token(identity, db)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@router.post("/totp/setup", response_model=schemas.TOTPSetupResponse)
def setup_totp(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    manager = TOTPManager()
    secret = manager.generate_secret()
    provisioning_uri = manager.get_provisioning_uri(secret, current_user.username)
    qr_code_png_base64 = manager.qr_png_base64(provisioning_uri)

    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.commit()

    return {
        "qr_code_png_base64": qr_code_png_base64,
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }


@router.post("/totp/verify", response_model=schemas.TOTPVerifyResponse)
def verify_totp(
    body: schemas.TOTPVerifyRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not initialized")

    if not TOTPManager().verify_code(current_user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    current_user.totp_enabled = True
    db.commit()
    return {"verified": True}
