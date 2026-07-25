from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pathlib import Path
import importlib.util
import sys
from .database import get_db
from .models import User
from .models.user import UserRole
from .security import decode_access_token


from orchestrator.security.token_manager import TokenManager


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Extract Bearer token, verify JWT, fetch User from DB, check active."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = None
    try:
        payload = TokenManager().verify_access_token(token)
    except Exception:
        # Backward compatibility for older tokens still signed via legacy security module.
        payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception
    
    # Support both new (user_id in sub) and legacy (username in sub) tokens
    user_id = payload.get("user_id") or payload.get("admin_id")
    username = payload.get("sub")

    user = None
    if user_id:
        user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None and username:
        user = db.query(User).filter(User.username == str(username)).first()

    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Alias for backward compatibility — get_current_user already checks is_active."""
    return current_user


def _get_role_value(role) -> str:
    if hasattr(role, "value"):
        return role.value
    role_str = str(role)
    if role_str.startswith("UserRole."):
        return role_str.split(".")[1].lower()
    return role_str.lower()


def get_tenant_filter(current_user: User = Depends(get_current_user)):
    """Return tenant_id for filtering queries.
    
    - MASTER_ADMIN: returns None (no filter — sees everything)
    - TENANT_ADMIN / TENANT_VIEWER: returns current_user.tenant_id
    - Raises 403 if a non-master user has no tenant_id
    """
    role_val = _get_role_value(current_user.role)
    if role_val == UserRole.MASTER_ADMIN.value:
        return None
    
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any tenant",
        )
    
    return current_user.tenant_id


def require_tenant_admin(current_user: User = Depends(get_current_user)):
    """Require TENANT_ADMIN or MASTER_ADMIN role."""
    role_val = _get_role_value(current_user.role)
    if role_val not in (UserRole.MASTER_ADMIN.value, UserRole.TENANT_ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions — tenant admin or higher required",
        )
    return current_user


def require_master_admin(current_user: User = Depends(get_current_user)):
    """Require MASTER_ADMIN role."""
    if current_user.role != UserRole.MASTER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions — master admin required",
        )
    return current_user


# Backward compatibility alias
get_current_admin_user = require_tenant_admin
