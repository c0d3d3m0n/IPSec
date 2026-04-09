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
    
    # Admin Credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"

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
        if self.ADMIN_USERNAME == "admin":
            insecure_values.append("ADMIN_USERNAME")
        if self.ADMIN_PASSWORD == "admin123":
            insecure_values.append("ADMIN_PASSWORD")
        if self.DATABASE_URL.startswith("sqlite"):
            insecure_values.append("DATABASE_URL")

        if insecure_values:
            joined = ", ".join(insecure_values)
            raise RuntimeError(f"Production settings are not secure: {joined}")

@lru_cache()
def get_settings():
    return Settings()
