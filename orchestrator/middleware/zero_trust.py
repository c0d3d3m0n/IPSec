from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from orchestrator import models
from orchestrator.database import SessionLocal


from orchestrator.security.certificate_authority import InternalCA
from orchestrator.security.trust_evaluator import TrustEvaluator


logger = logging.getLogger(__name__)


_DEVICE_PATH_RE = re.compile(r"^/api/devices/(\d+)(?:/|$)")


def _extract_device_id_from_path(path: str) -> int | None:
    match = _DEVICE_PATH_RE.match(path)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    _active_instance: "ZeroTrustMiddleware | None" = None
    _configured_ca_cert_path: str | None = None
    _configured_ca_key_path: str | None = None

    EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/totp/setup",
        "/api/auth/totp/verify",
        "/api/devices/enroll",
        "/api/devices/register",
        "/api/ping",
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app):
        super().__init__(app)
        self.allow_token_fallback = os.getenv("ALLOW_DEVICE_TOKEN_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}

        if ZeroTrustMiddleware._configured_ca_cert_path and ZeroTrustMiddleware._configured_ca_key_path:
            ca_cert_path = ZeroTrustMiddleware._configured_ca_cert_path
            ca_key_path = ZeroTrustMiddleware._configured_ca_key_path
        else:
            cert_env = os.getenv("CA_CERT_PATH", "keys/ca.crt")
            key_env = os.getenv("CA_KEY_PATH", "keys/ca.key")
            ca_cert_path = os.getenv("CA_CERT_FILE_PATH", "keys/ca.crt") if "BEGIN CERTIFICATE" in cert_env else cert_env
            ca_key_path = os.getenv("CA_KEY_FILE_PATH", "keys/ca.key") if ("BEGIN" in key_env and "PRIVATE KEY" in key_env) else key_env
        self.ca = None
        self.trust = TrustEvaluator()
        self.zt_enabled = False
        ZeroTrustMiddleware._active_instance = self

        try:
            self.ca = InternalCA(ca_cert_path=ca_cert_path, ca_key_path=ca_key_path)
            self.zt_enabled = True
        except FileNotFoundError:
            logger.warning(
                "WARNING: CA cert not found at '%s' — ZeroTrustMiddleware is DISABLED. Generate CA certs and set CA_CERT_PATH + CA_KEY_PATH env vars on Render.",
                ca_cert_path,
            )

        if ZeroTrustMiddleware._configured_ca_cert_path and ZeroTrustMiddleware._configured_ca_key_path:
            self._reinitialize_ca(
                ZeroTrustMiddleware._configured_ca_cert_path,
                ZeroTrustMiddleware._configured_ca_key_path,
            )

    @classmethod
    def configure_ca(cls, ca_cert_path: str, ca_key_path: str) -> None:
        cls._configured_ca_cert_path = ca_cert_path
        cls._configured_ca_key_path = ca_key_path
        if cls._active_instance is not None:
            cls._active_instance._reinitialize_ca(ca_cert_path, ca_key_path)

    def _reinitialize_ca(self, ca_cert_path: str, ca_key_path: str) -> None:
        self.ca = InternalCA(ca_cert_path=ca_cert_path, ca_key_path=ca_key_path)
        self.zt_enabled = True
        logger.info("ZeroTrustMiddleware CA reinitialized from %s and %s", ca_cert_path, ca_key_path)

    async def dispatch(self, request: Request, call_next):
        if not self.zt_enabled:
            return await call_next(request)

        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer ") and (
            path.startswith("/api/devices") or path.startswith("/api/policies")
        ):
            return await call_next(request)

        cert_obj = request.scope.get("tls_client_cert")
        cert_pem: bytes | None = None
        if isinstance(cert_obj, bytes):
            cert_pem = cert_obj
        elif isinstance(cert_obj, str):
            cert_pem = cert_obj.encode("utf-8")

        if not cert_pem:
            if self.allow_token_fallback and path.startswith("/api/devices/"):
                requested_device_id = _extract_device_id_from_path(path)
                enrollment_token = (request.headers.get("X-Enrollment-Token") or "").strip()
                if requested_device_id is not None and enrollment_token:
                    db: Session = SessionLocal()
                    try:
                        db_device = (
                            db.query(models.Device)
                            .filter(models.Device.id == requested_device_id)
                            .first()
                        )
                        if db_device and (db_device.enrollment_token or "").strip() == enrollment_token:
                            logger.warning(
                                "ZeroTrust token fallback accepted for device_id=%s path=%s",
                                requested_device_id,
                                path,
                            )
                            request.state.device_id = requested_device_id
                            request.state.trust_score = 50
                            request.state.trust_decision = "fallback-token"
                            return await call_next(request)
                    finally:
                        db.close()
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
