from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jose import jwt, JWTError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _load_certificate_model_module():
    import importlib.util
    import sys

    module_name = "orchestrator_models_certificate"
    if module_name in sys.modules:
        return sys.modules[module_name]

    file_path = Path(__file__).resolve().parents[1] / "models" / "certificate.py"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load certificate models module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_server_keys() -> tuple[str, str]:
    import os

    private_key = os.getenv("RSA_PRIVATE_KEY")
    public_key = os.getenv("RSA_PUBLIC_KEY")

    if private_key and public_key:
        return private_key.replace("\\n", "\n"), public_key.replace("\\n", "\n")

    private_path = Path("keys/private_key.pem")
    public_path = Path("keys/public_key.pem")

    if not private_path.exists() or not public_path.exists():
        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)

        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        private_path.write_text(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")
        )
        public_path.write_text(
            key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")
        )
        print("Auto-generated JWT RSA keypair for token manager. Set RSA_PRIVATE_KEY/RSA_PUBLIC_KEY in production.")

    return private_path.read_text(), public_path.read_text()


class TokenManager:
    def __init__(self):
        self.private_key, self.public_key = _load_server_keys()
        self.algorithm = "RS256"

    def create_access_token(self, data: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = data.copy()
        payload.update(
            {
                "type": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=15)).timestamp()),
            }
        )
        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: dict[str, Any], db) -> str:
        models_module = _load_certificate_model_module()
        RefreshToken = models_module.RefreshToken

        now = datetime.now(timezone.utc)
        payload = data.copy()
        payload.update(
            {
                "type": "refresh",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=7)).timestamp()),
            }
        )
        raw_token = jwt.encode(payload, self.private_key, algorithm=self.algorithm)
        token_hash = hashlib.sha512(raw_token.encode("utf-8")).hexdigest()

        record = RefreshToken(
            token_hash=token_hash,
            device_id=payload.get("device_id"),
            user_id=payload.get("user_id") or payload.get("admin_id"),
            expires_at=now + timedelta(days=7),
            is_revoked=False,
        )
        db.add(record)
        db.commit()
        return raw_token

    def verify_access_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm])
        except JWTError as exc:
            raise ValueError("Invalid token") from exc

        if payload.get("type") != "access":
            raise ValueError("Invalid token type")

        exp = int(payload.get("exp", 0))
        if exp < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")
        return payload

    def rotate_refresh_token(self, old_token: str, db) -> tuple[str, str]:
        models_module = _load_certificate_model_module()
        RefreshToken = models_module.RefreshToken

        try:
            payload = jwt.decode(old_token, self.public_key, algorithms=[self.algorithm])
        except JWTError as exc:
            raise ValueError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        old_hash = hashlib.sha512(old_token.encode("utf-8")).hexdigest()
        existing = db.query(RefreshToken).filter(RefreshToken.token_hash == old_hash).first()
        if not existing or existing.is_revoked:
            raise ValueError("Refresh token revoked or missing")
        if existing.expires_at < datetime.now(timezone.utc):
            raise ValueError("Refresh token expired")

        existing.is_revoked = True
        db.commit()

        identity = {
            "sub": payload.get("sub"),
            "user_id": payload.get("user_id") or payload.get("admin_id"),
            "role": payload.get("role"),
            "tenant_id": payload.get("tenant_id"),
            "device_id": payload.get("device_id"),
        }
        identity = {k: v for k, v in identity.items() if v is not None}

        new_access = self.create_access_token(identity)
        new_refresh = self.create_refresh_token(identity, db)
        return new_access, new_refresh
