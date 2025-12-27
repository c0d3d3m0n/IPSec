from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import devices, policies

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

app.include_router(devices.router)
app.include_router(policies.router)

@app.get("/")
async def root():
    return {"message": "Unified IPsec Orchestrator Running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
