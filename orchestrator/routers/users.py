"""User management router — tenant-scoped user CRUD.

Accessible by TENANT_ADMIN (own tenant) and MASTER_ADMIN (any tenant).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from orchestrator import database, models, schemas, security
from orchestrator.auth import get_current_user, require_tenant_admin, get_tenant_filter
from orchestrator.models.user import UserRole

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


# ─── POST /api/users/ ───────────────────────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    body: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_tenant_admin),
):
    # Validate role — cannot create master_admin via this endpoint
    allowed_roles = {UserRole.TENANT_ADMIN.value, UserRole.TENANT_VIEWER.value}
    if body.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Allowed: {', '.join(allowed_roles)}",
        )

    # Determine target tenant
    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin must specify a tenant context (or it fails)
        if current_user.tenant_id is None:
            raise HTTPException(
                status_code=400,
                detail="Master admin must create users from the tenant admin panel (use POST /api/admin/tenants/ to create tenants with initial admin)",
            )
    
    tenant_id = current_user.tenant_id

    # Check tenant max_users limit
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if tenant:
        current_count = db.query(models.User).filter(
            models.User.tenant_id == tenant_id,
            models.User.is_active == True,
        ).count()
        if current_count >= tenant.max_users:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"User limit reached ({tenant.max_users}). Upgrade your plan to add more users.",
            )

    # Check uniqueness
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already taken")

    new_user = models.User(
        username=body.username,
        email=body.email,
        hashed_password=security.get_password_hash(body.password),
        role=UserRole(body.role),
        tenant_id=tenant_id,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return schemas.UserResponse.model_validate(new_user).model_dump(mode="json")


# ─── GET /api/users/ ────────────────────────────────────────────────────────
@router.get("/")
def list_users(
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_tenant_admin),
):
    query = db.query(models.User)

    if current_user.role == UserRole.MASTER_ADMIN:
        # Master admin can filter by tenant_id param
        if tenant_id is not None:
            query = query.filter(models.User.tenant_id == tenant_id)
    else:
        # Tenant admin sees only own tenant's users
        query = query.filter(models.User.tenant_id == current_user.tenant_id)

    users = query.all()
    return [schemas.UserResponse.model_validate(u).model_dump(mode="json") for u in users]


# ─── PUT /api/users/{user_id}/role ───────────────────────────────────────────
@router.put("/{user_id}/role")
def update_user_role(
    user_id: int,
    body: schemas.UserRoleUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_tenant_admin),
):
    # Cannot change own role
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    allowed_roles = {UserRole.TENANT_ADMIN.value, UserRole.TENANT_VIEWER.value}
    if body.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {', '.join(allowed_roles)}")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Tenant isolation — non-master can only modify own tenant's users
    if current_user.role != UserRole.MASTER_ADMIN and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(body.role)
    db.commit()
    db.refresh(user)
    return schemas.UserResponse.model_validate(user).model_dump(mode="json")


# ─── DELETE /api/users/{user_id} ─────────────────────────────────────────────
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_tenant_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Tenant isolation
    if current_user.role != UserRole.MASTER_ADMIN and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found")

    # Soft delete
    user.is_active = False
    db.commit()
    return {"message": f"User '{user.username}' deactivated"}


# ─── GET /api/users/me ──────────────────────────────────────────────────────
@router.get("/me")
def get_my_profile(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    tenant_name = None
    plan = None
    if current_user.tenant_id:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
        if tenant:
            tenant_name = tenant.name
            plan = tenant.plan

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, "value") else current_user.role,
        "tenant_name": tenant_name,
        "plan": plan,
        "is_active": current_user.is_active,
        "totp_enabled": current_user.totp_enabled or False,
    }
