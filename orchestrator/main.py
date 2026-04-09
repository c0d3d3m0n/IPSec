from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import importlib.util
import sys
from pathlib import Path
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from orchestrator.database import engine, Base
from orchestrator.routers import devices, policies, auth
from orchestrator.routers.compliance import router as compliance_router
from orchestrator.seed_admin import seed_admin as run_seed
from orchestrator.config import get_settings
from orchestrator.rate_limiter import limiter
from orchestrator.middleware.zero_trust import ZeroTrustMiddleware


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_runtime_settings()
    Base.metadata.create_all(bind=engine)
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

# Zero Trust must wrap routes before downstream middleware behavior.
app.add_middleware(ZeroTrustMiddleware)
app.add_middleware(SlowAPIMiddleware)

# CORS (Allow all for now, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
