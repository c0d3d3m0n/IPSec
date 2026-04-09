import base64
from io import BytesIO

import pyotp
import qrcode


class TOTPManager:
    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, admin_username: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=admin_username, issuer_name="Unified IPsec Orchestrator")

    def generate_qr_code(self, uri: str) -> bytes:
        image = qrcode.make(uri)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def verify_code(self, secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(code, valid_window=1))

    def qr_png_base64(self, uri: str) -> str:
        return base64.b64encode(self.generate_qr_code(uri)).decode("utf-8")
