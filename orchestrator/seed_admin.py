from sqlalchemy.orm import Session
from orchestrator.database import SessionLocal, engine, Base
from orchestrator import models, security
from orchestrator.config import get_settings
import sys

def seed_admin(username, password):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user:
            existing_user.hashed_password = security.get_password_hash(password)
            existing_user.is_admin = True
            db.commit()
            print(f"User {username} already exists. Password updated.")
            return

        # Create new admin user
        hashed_password = security.get_password_hash(password)
        new_user = models.User(
            username=username,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"Admin user {username} created successfully.")
    except Exception as e:
        print(f"Error seeding admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    settings = get_settings()
    if len(sys.argv) == 3:
        seed_admin(sys.argv[1], sys.argv[2])
    else:
        seed_admin(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
