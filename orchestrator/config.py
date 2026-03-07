from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Unified IPsec Orchestrator"
    DATABASE_URL: str = "sqlite:///./ipsec_orchestrator.db"  # Default to SQLite for dev
    SECRET_KEY: str = "change_this_in_production_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Admin Credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
