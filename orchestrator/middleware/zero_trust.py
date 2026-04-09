from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from orchestrator.database import SessionLocal


def _load_module(module_name: str, file_path: Path):
    import importlib.util
    import sys

    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_BASE_DIR = Path(__file__).resolve().parents[1]
_ca_module = _load_module("orchestrator_security_certificate_authority", _BASE_DIR / "security" / "certificate_authority.py")
_trust_module = _load_module("orchestrator_security_trust_evaluator", _BASE_DIR / "security" / "trust_evaluator.py")

InternalCA = _ca_module.InternalCA
TrustEvaluator = _trust_module.TrustEvaluator


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/totp/setup",
        "/api/auth/totp/verify",
        "/api/devices/enroll",
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app):
        super().__init__(app)
        import os

        ca_cert_path = os.getenv("CA_CERT_PATH", "keys/ca.crt")
        ca_key_path = os.getenv("CA_KEY_PATH", "keys/ca.key")
        self.ca = InternalCA(ca_cert_path=ca_cert_path, ca_key_path=ca_key_path)
        self.trust = TrustEvaluator()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        cert_obj = request.scope.get("tls_client_cert")
        cert_pem: bytes | None = None
        if isinstance(cert_obj, bytes):
            cert_pem = cert_obj
        elif isinstance(cert_obj, str):
            cert_pem = cert_obj.encode("utf-8")

        if not cert_pem:
            return JSONResponse(status_code=401, content={"detail": "Client certificate required"})

        db: Session = SessionLocal()
        try:
            verification = self.ca.verify_certificate(cert_pem, db)
            if not verification.get("valid"):
                return JSONResponse(status_code=403, content={"detail": "Certificate invalid or revoked"})

            device_id = int(verification["device_id"])
            cert_cn = verification.get("cn", "")

            context = {
                "path": path,
                "source_ip": request.client.host if request.client else None,
                "cert_cn": cert_cn,
                "cert_serial": verification.get("cert_serial"),
            }
            trust = self.trust.evaluate(device_id, context, db)
            if trust.decision == "deny":
                return JSONResponse(
                    status_code=403,
                    content={
                        "reason": "zero_trust_deny",
                        "detail": "Zero Trust denied request",
                        "score": trust.score,
                        "reasons": trust.reasons,
                    },
                )

            if trust.decision == "restrict":
                allowed_restricted = {f"/api/devices/{device_id}/heartbeat"}
                if path not in allowed_restricted:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "reason": "zero_trust_restrict",
                            "detail": "Device in restricted mode",
                            "score": trust.score,
                            "reasons": trust.reasons,
                        },
                    )

            request.state.device_id = device_id
            request.state.trust_score = trust.score
            request.state.trust_decision = trust.decision
            return await call_next(request)
        finally:
            db.close()
