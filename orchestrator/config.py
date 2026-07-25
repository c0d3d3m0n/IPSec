from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "Unified IPsec Orchestrator"
    DATABASE_URL: str = "sqlite:///./ipsec_orchestrator.db"  # Default to SQLite for dev
    SECRET_KEY: str = "change_this_in_production_secret_key"
    ALGORITHM: str = "RS512"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # Legacy Admin Credentials (backward compat)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # Master Admin Credentials (Phase 4)
    MASTER_ADMIN_USERNAME: str = ""
    MASTER_ADMIN_EMAIL: str = ""
    MASTER_ADMIN_PASSWORD: str = ""

    class Config:
        env_file = ".env"

    @property
    def effective_master_username(self) -> str:
        return self.MASTER_ADMIN_USERNAME or self.ADMIN_USERNAME

    @property
    def effective_master_password(self) -> str:
        return self.MASTER_ADMIN_PASSWORD or self.ADMIN_PASSWORD

    @property
    def effective_master_email(self) -> str:
        return self.MASTER_ADMIN_EMAIL or f"{self.effective_master_username}@ipsecvault.tech"

    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in {"prod", "production"}

    def get_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_runtime_settings(self) -> None:
        if not self.is_production():
            return

        insecure_values = []
        if self.SECRET_KEY == "change_this_in_production_secret_key":
            insecure_values.append("SECRET_KEY")
        if self.effective_master_username == "admin":
            insecure_values.append("MASTER_ADMIN_USERNAME / ADMIN_USERNAME")
        if self.effective_master_password == "admin123":
            insecure_values.append("MASTER_ADMIN_PASSWORD / ADMIN_PASSWORD")
        if self.DATABASE_URL.startswith("sqlite"):
            insecure_values.append("DATABASE_URL")

        if insecure_values:
            joined = ", ".join(insecure_values)
            raise RuntimeError(f"Production settings are not secure: {joined}")

@lru_cache()
def get_settings():
    return Settings()
