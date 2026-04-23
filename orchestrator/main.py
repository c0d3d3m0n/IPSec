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
from orchestrator.seed_admin import seed_admin as run_seed
from orchestrator.config import get_settings
from orchestrator.rate_limiter import limiter
from orchestrator.middleware.zero_trust import ZeroTrustMiddleware
from orchestrator.middleware.csrf_guard import CSRFMiddleware


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


_BASE_DIR = Path(__file__).resolve().parent
_load_module("orchestrator_models_compliance", _BASE_DIR / "models" / "compliance.py")
_load_module("orchestrator_models_audit", _BASE_DIR / "models" / "audit.py")
_load_module("orchestrator_models_certificate", _BASE_DIR / "models" / "certificate.py")


def _get_allowed_origins() -> list[str]:
    default_origins = [
        "https://api.ipsecvault.tech",
        "https://ip-sec.vercel.app",
        "https://ipsecvault.tech",
        "https://www.ipsecvault.tech",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    configured_origins = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    settings_origins = get_settings().get_cors_origins()

    merged_origins: list[str] = []
    for origin in [*default_origins, *settings_origins, *configured_origins]:
        if origin not in merged_origins:
            merged_origins.append(origin)

    return merged_origins


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

    if not statements:
        return

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


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
    try:
        run_seed(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    except Exception as e:
        print(f"Auto-seeding failed: {e}")
    yield

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Unified IPsec Orchestrator",
    description="Central management server for cross-platform IPsec tunnels",
    version="0.1.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = _get_allowed_origins()
allowed_hosts = _get_allowed_hosts()
csrf_trusted_origins = _get_csrf_trusted_origins(allowed_origins)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# CORS must be registered before auth middleware and before routers so preflight
# requests receive the headers the browser requires.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# CSRF-style origin checks for browser unsafe methods while allowing non-browser clients.
app.add_middleware(CSRFMiddleware, trusted_origins=csrf_trusted_origins)

# Zero Trust must wrap routes before downstream middleware behavior.
app.add_middleware(ZeroTrustMiddleware)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(policies.router, prefix="/api")
app.include_router(compliance_router, prefix="/api")

@app.get("/api/ping")
async def ping():
    return {"status": "ok", "message": "Backend is reachable and /api prefix is working"}

@app.get("/")
async def root():
    return {"message": "Unified IPsec Orchestrator Running"}

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
