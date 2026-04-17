from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, trusted_origins: list[str]):
        super().__init__(app)
        self.trusted_origins = [origin.rstrip("/") for origin in trusted_origins]

    @staticmethod
    def _is_unsafe_method(method: str) -> bool:
        return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}

    def _is_trusted_referer(self, referer: str | None) -> bool:
        if not referer:
            return False
        normalized = referer.rstrip("/")
        return any(
            normalized == origin or normalized.startswith(f"{origin}/")
            for origin in self.trusted_origins
        )

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() == "OPTIONS" or not self._is_unsafe_method(request.method):
            return await call_next(request)

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        # Non-browser clients (agents, scripts, internal services) usually do not send Origin.
        if not origin and not referer:
            return await call_next(request)

        if origin and origin.rstrip("/") in self.trusted_origins:
            return await call_next(request)

        if self._is_trusted_referer(referer):
            return await call_next(request)

        return JSONResponse(status_code=403, content={"detail": "CSRF protection: untrusted origin"})
