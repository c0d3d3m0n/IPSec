from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import inspect, text
from orchestrator.database import engine, Base
from orchestrator.routers import devices, policies, auth
from orchestrator.routers.compliance import router as compliance_router
from orchestrator.routers.master_admin import router as master_admin_router
from orchestrator.routers.users import router as users_router
from orchestrator.config import get_settings
from orchestrator.rate_limiter import limiter
from orchestrator.middleware.zero_trust import ZeroTrustMiddleware
from orchestrator.middleware.csrf_guard import CSRFMiddleware





def _get_allowed_origins() -> list[str]:
    # Keep the production allowlist deterministic so a stale env var cannot
    # remove the browser origins the dashboard depends on.
    return [
        "https://www.ipsecvault.tech",
        "https://ipsecvault.tech",
        "https://api.ipsecvault.tech",
        "https://ip-sec.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]


def _normalize_host(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc or parsed.path
    return host.split(":")[0].strip().lower()


def _get_allowed_hosts() -> list[str]:
    default_hosts = [
        "ipsec-lcir.onrender.com",
        "api.ipsecvault.tech",
        "ipsecvault.tech",
        "www.ipsecvault.tech",
        "localhost",
        "127.0.0.1",
    ]

    configured = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]
    merged: list[str] = []

    for host in [*default_hosts, *configured]:
        normalized = _normalize_host(host)
        if normalized and normalized not in merged:
            merged.append(normalized)

    return merged


def _get_csrf_trusted_origins(allowed_origins: list[str]) -> list[str]:
    configured = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
    trusted: list[str] = []
    for origin in [*allowed_origins, *configured]:
        normalized = origin.rstrip("/")
        if normalized and normalized not in trusted:
            trusted.append(normalized)
    return trusted


def _ensure_ca_keypair() -> tuple[str, str]:
    cert_env = os.getenv("CA_CERT_PATH", "keys/ca.crt")
    key_env = os.getenv("CA_KEY_PATH", "keys/ca.key")

    cert_is_pem = "BEGIN CERTIFICATE" in cert_env
    key_is_pem = "BEGIN" in key_env and "PRIVATE KEY" in key_env

    ca_cert_path = os.getenv("CA_CERT_FILE_PATH", "keys/ca.crt") if cert_is_pem else cert_env
    ca_key_path = os.getenv("CA_KEY_FILE_PATH", "keys/ca.key") if key_is_pem else key_env

    cert_file = Path(ca_cert_path)
    key_file = Path(ca_key_path)

    if cert_is_pem or key_is_pem:
        cert_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if cert_is_pem:
            cert_file.write_text(cert_env.replace("\\n", "\n"))
        if key_is_pem:
            key_file.write_text(key_env.replace("\\n", "\n"))
        if cert_file.exists() and key_file.exists():
            print(f"CA keypair loaded from inline env PEM into {ca_cert_path} and {ca_key_path}")
            return ca_cert_path, ca_key_path

    if cert_file.exists() and key_file.exists():
        print(f"CA cert loaded from {ca_cert_path}")
        return ca_cert_path, ca_key_path

    cert_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "IPSec Internal CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IPSec Framework"),
    ])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key=private_key, algorithm=hashes.SHA512())
    )

    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    print("Auto-generated CA keypair at startup — for production, generate offline and mount as secret")
    return ca_cert_path, ca_key_path


def _ensure_auth_schema_compatibility() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []

    if "totp_secret" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN totp_secret VARCHAR")
    if "totp_enabled" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE")
    if "failed_attempts" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    if "locked_until" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP")
    if "email" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
    if "role" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN role VARCHAR(50)")
    if "tenant_id" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)")
    if "last_login" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")

    if not statements:
        return

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _ensure_device_policy_schema_compatibility() -> None:
    """Add missing columns for enrollment flow and multi-tenancy."""
    inspector = inspect(engine)
    statements: list[str] = []
    
    # Device table migrations
    if "devices" in inspector.get_table_names():
        device_cols = {col["name"] for col in inspector.get_columns("devices")}
        if "enrollment_number" not in device_cols:
            statements.append("ALTER TABLE devices ADD COLUMN enrollment_number VARCHAR UNIQUE")
        if "enrollment_token" not in device_cols:
            statements.append("ALTER TABLE devices ADD COLUMN enrollment_token VARCHAR UNIQUE")
        if "pre_shared_key" not in device_cols:
            statements.append("ALTER TABLE devices ADD COLUMN pre_shared_key VARCHAR")
        if "os_fingerprint" not in device_cols:
            statements.append("ALTER TABLE devices ADD COLUMN os_fingerprint VARCHAR")
        if "status" not in device_cols:
            statements.append("ALTER TABLE devices ADD COLUMN status VARCHAR DEFAULT 'PENDING'")
        if "tenant_id" not in device_cols:
            statements.append("ALTER TABLE devices ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)")
    
    # Policy table migrations
    if "policies" in inspector.get_table_names():
        policy_cols = {col["name"] for col in inspector.get_columns("policies")}
        if "config_data" not in policy_cols:
            statements.append("ALTER TABLE policies ADD COLUMN config_data TEXT")
        if "tenant_id" not in policy_cols:
            statements.append("ALTER TABLE policies ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)")

    # Compliance records
    if "compliance_records" in inspector.get_table_names():
        comp_cols = {col["name"] for col in inspector.get_columns("compliance_records")}
        if "tenant_id" not in comp_cols:
            statements.append("ALTER TABLE compliance_records ADD COLUMN tenant_id INTEGER")

    # Audit logs
    if "audit_logs" in inspector.get_table_names():
        audit_cols = {col["name"] for col in inspector.get_columns("audit_logs")}
        if "tenant_id" not in audit_cols:
            statements.append("ALTER TABLE audit_logs ADD COLUMN tenant_id INTEGER")

    # Device certificates
    if "device_certificates" in inspector.get_table_names():
        cert_cols = {col["name"] for col in inspector.get_columns("device_certificates")}
        if "tenant_id" not in cert_cols:
            statements.append("ALTER TABLE device_certificates ADD COLUMN tenant_id INTEGER")
    
    if not statements:
        return
    
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                print(f"✅ Migration: {stmt}")
            except Exception as e:
                print(f"⚠️  Migration skipped (may already exist): {stmt} - {e}")


# Resolve CA files before middleware is created so middleware can initialize cleanly.
_INITIAL_CA_CERT_PATH, _INITIAL_CA_KEY_PATH = _ensure_ca_keypair()
ZeroTrustMiddleware.configure_ca(_INITIAL_CA_CERT_PATH, _INITIAL_CA_KEY_PATH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_runtime_settings()
    ca_cert_path, ca_key_path = _ensure_ca_keypair()
    ZeroTrustMiddleware.configure_ca(ca_cert_path, ca_key_path)
    Base.metadata.create_all(bind=engine)
    _ensure_auth_schema_compatibility()
    _ensure_device_policy_schema_compatibility()
    
    # DEBUG: Log CORS configuration
    allowed_origins = _get_allowed_origins()
    yield

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Unified IPsec Orchestrator",
    description="Central management server for cross-platform IPsec tunnels — Multi-Tenant SaaS",
    version="0.4.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = _get_allowed_origins()
allowed_hosts = _get_allowed_hosts()
csrf_trusted_origins = _get_csrf_trusted_origins(allowed_origins)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(ZeroTrustMiddleware)

# CSRF-style origin checks for browser unsafe methods while allowing non-browser clients.
app.add_middleware(CSRFMiddleware, trusted_origins=csrf_trusted_origins)

# CORS must be the outermost middleware so preflight requests and short-circuit
# responses still get the access-control headers browsers require.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(policies.router, prefix="/api")
app.include_router(compliance_router, prefix="/api")
app.include_router(master_admin_router, prefix="/api")
app.include_router(users_router, prefix="/api")

@app.get("/api/ping")
async def ping():
    return {"status": "ok", "message": "Backend is reachable and /api prefix is working"}

@app.get("/")
async def root():
    return {"message": "Unified IPsec Orchestrator Running — Multi-Tenant SaaS v0.4.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path_name: str):
    return {
        "error": "Not Found",
        "path": path_name,
        "message": "The requested path was not found on this API. Check your prefixes."
    }


@app.on_event("startup")
async def bootstrap_zero_trust_ca():
    ca_cert_path, ca_key_path = _ensure_ca_keypair()
    ZeroTrustMiddleware.configure_ca(ca_cert_path, ca_key_path)
