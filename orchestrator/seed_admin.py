from sqlalchemy.orm import Session
from orchestrator.database import SessionLocal, engine, Base
from orchestrator import models, security
from orchestrator.models.user import UserRole
from orchestrator.config import get_settings
import sys


def seed_admin(username: str = None, password: str = None, email: str = None):
    settings = get_settings()

    username = username or settings.effective_master_username
    password = password or settings.effective_master_password
    email = email or settings.effective_master_email

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if any master_admin already exists
        existing_master = db.query(models.User).filter(
            models.User.role == UserRole.MASTER_ADMIN
        ).first()

        if existing_master:
            print(f"Master admin already exists: {existing_master.username}")
            return

        # Check if username is taken
        existing_user = db.query(models.User).filter(
            models.User.username == username
        ).first()
        if existing_user:
            # Upgrade existing user to master_admin
            existing_user.role = UserRole.MASTER_ADMIN
            existing_user.hashed_password = security.get_password_hash(password)
            existing_user.tenant_id = None
            if not existing_user.email:
                existing_user.email = email
            db.commit()
            print(f"Existing user '{username}' upgraded to master_admin.")
            return

        # Create new master admin user
        hashed_password = security.get_password_hash(password)
        new_user = models.User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.MASTER_ADMIN,
            tenant_id=None,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        print(f"Master admin created: {username}")
    except Exception as e:
        print(f"Error seeding master admin: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    settings = get_settings()
    if len(sys.argv) == 4:
        seed_admin(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3:
        seed_admin(sys.argv[1], sys.argv[2])
    else:
        seed_admin()
