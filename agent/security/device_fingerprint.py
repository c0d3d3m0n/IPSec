import hashlib
import hmac
import platform
import socket
import uuid


class DeviceFingerprint:
    def collect(self) -> dict:
        hostname = socket.gethostname()
        os_version = platform.platform()
        mac_int = uuid.getnode()
        mac_address = ":".join(f"{(mac_int >> ele) & 0xFF:02x}" for ele in range(40, -1, -8))

        digest_input = f"{hostname}{os_version}{mac_address}".encode("utf-8")
        fingerprint = hashlib.sha512(digest_input).hexdigest()

        return {
            "hostname": hostname,
            "os_version": os_version,
            "mac_address": mac_address,
            "fingerprint": fingerprint,
        }

    def sign(self, fingerprint: str, pre_shared_key: str) -> str:
        return hmac.new(pre_shared_key.encode("utf-8"), fingerprint.encode("utf-8"), hashlib.sha512).hexdigest()
