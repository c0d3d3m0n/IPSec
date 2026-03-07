from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orchestrator.database import engine, Base
from orchestrator.routers import devices, policies, auth

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Unified IPsec Orchestrator",
    description="Central management server for cross-platform IPsec tunnels",
    version="0.1.0"
)

# CORS (Allow all for now, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(policies.router, prefix="/api")

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
