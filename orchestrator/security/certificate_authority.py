from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


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


class InternalCA:
    def __init__(self, ca_cert_path: str, ca_key_path: str):
        cert_bytes = Path(ca_cert_path).read_bytes()
        key_bytes = Path(ca_key_path).read_bytes()

        self.ca_cert = x509.load_pem_x509_certificate(cert_bytes)
        self.ca_key = serialization.load_pem_private_key(key_bytes, password=None)

        if not isinstance(self.ca_key, rsa.RSAPrivateKey):
            raise RuntimeError("CA key must be an RSA private key")

    def issue_device_certificate(
        self,
        device_id: int,
        enrollment_number: str,
        os_type: str,
        valid_days: int = 90,
    ) -> tuple[bytes, bytes]:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, f"device-{device_id}"),
                x509.NameAttribute(NameOID.SERIAL_NUMBER, enrollment_number),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, os_type or "unknown"),
            ]
        )

        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=valid_days))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(f"device-{device_id}.agents.internal")]),
                critical=False,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .sign(private_key=self.ca_key, algorithm=hashes.SHA512())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cert_pem, private_key_pem

    def revoke_certificate(self, cert_serial: str, reason: str, db):
        models_module = _load_certificate_model_module()
        RevokedCertificate = models_module.RevokedCertificate

        existing = db.query(RevokedCertificate).filter(RevokedCertificate.cert_serial == cert_serial).first()
        if existing:
            return existing

        revoked = RevokedCertificate(cert_serial=cert_serial, reason=reason)
        db.add(revoked)
        db.commit()
        db.refresh(revoked)
        return revoked

    def verify_certificate(self, cert_pem: bytes, db) -> dict[str, Any]:
        models_module = _load_certificate_model_module()
        RevokedCertificate = models_module.RevokedCertificate

        try:
            cert = x509.load_pem_x509_certificate(cert_pem)
            ca_public_key = self.ca_cert.public_key()
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )

            serial = str(cert.serial_number)
            revoked = db.query(RevokedCertificate).filter(RevokedCertificate.cert_serial == serial).first()
            if revoked:
                return {"valid": False, "device_id": None, "enrollment_number": None, "expires_at": cert.not_valid_after}

            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            serial_attr = cert.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)[0].value
            if not cn.startswith("device-"):
                return {"valid": False, "device_id": None, "enrollment_number": serial_attr, "expires_at": cert.not_valid_after}

            device_id = int(cn.replace("device-", "", 1))
            if datetime.now(timezone.utc) > cert.not_valid_after.replace(tzinfo=timezone.utc):
                return {"valid": False, "device_id": device_id, "enrollment_number": serial_attr, "expires_at": cert.not_valid_after}

            return {
                "valid": True,
                "device_id": device_id,
                "enrollment_number": serial_attr,
                "expires_at": cert.not_valid_after,
                "cert_serial": serial,
                "cn": cn,
            }
        except Exception:
            return {"valid": False, "device_id": None, "enrollment_number": None, "expires_at": None}
