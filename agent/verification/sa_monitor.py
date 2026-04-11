import json
import platform
import re
import subprocess
from datetime import datetime, timezone
from typing import Any


class SAMonitor:
    def __init__(self, agent_id: int, os_type: str | None = None):
        self.agent_id = agent_id
        self.os_type = (os_type or platform.system()).lower()

    def _parse_linux_xfrm(self) -> list[dict[str, Any]]:
        result = subprocess.run(["ip", "-s", "xfrm", "state", "show"], capture_output=True, text=True, check=False)
        text = result.stdout or ""

        active_sas: list[dict[str, Any]] = []
        current: dict[str, Any] = {}

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            src_dst = re.match(r"src\s+(\S+)\s+dst\s+(\S+)", line)
            if src_dst:
                if current.get("spi"):
                    active_sas.append(current)
                current = {
                    "src_ip": src_dst.group(1),
                    "dst_ip": src_dst.group(2),
                    "spi": "",
                    "encryption_algo": "unknown",
                    "integrity_algo": "unknown",
                    "dh_group": None,
                    "bytes_encrypted": 0,
                    "packets_encrypted": 0,
                    "sa_expires_in_seconds": 0,
                }
                continue

            spi_match = re.search(r"spi\s+(0x[0-9a-fA-F]+)", line)
            if spi_match:
                current["spi"] = spi_match.group(1)

            enc_match = re.search(r"(?:aead|enc)\s+([^\s]+)", line)
            if enc_match:
                current["encryption_algo"] = enc_match.group(1)

            auth_match = re.search(r"auth\s+([^\s]+)", line)
            if auth_match:
                current["integrity_algo"] = auth_match.group(1)

            bytes_match = re.search(r"bytes\s+(\d+)", line)
            if bytes_match:
                current["bytes_encrypted"] = int(bytes_match.group(1))

            packets_match = re.search(r"packets\s+(\d+)", line)
            if packets_match:
                current["packets_encrypted"] = int(packets_match.group(1))

        if current.get("spi"):
            active_sas.append(current)

        return active_sas

    def _parse_linux_swanctl(self, active_sas: list[dict[str, Any]]) -> tuple[bool, dict[str, str]]:
        result = subprocess.run(["swanctl", "--list-sas"], capture_output=True, text=True, check=False)
        text = result.stdout or ""

        pfs_active = bool(re.search(r"\bPFS\b|\bCHILD_SA\b.*\bINSTALLED\b", text, flags=re.IGNORECASE))
        spi_to_dh: dict[str, str] = {}

        for line in text.splitlines():
            spi_match = re.search(r"spi[:=]\s*(0x[0-9a-fA-F]+)", line)
            dh_match = re.search(r"(modp\d+|ecp\d+|DH\d+)", line, flags=re.IGNORECASE)
            if spi_match and dh_match:
                spi_to_dh[spi_match.group(1).lower()] = dh_match.group(1)

        for sa in active_sas:
            key = str(sa.get("spi", "")).lower()
            if key in spi_to_dh:
                sa["dh_group"] = spi_to_dh[key]

        return pfs_active, spi_to_dh

    def collect_linux_snapshot(self) -> dict[str, Any]:
        active_sas = self._parse_linux_xfrm()
        pfs_active, _ = self._parse_linux_swanctl(active_sas)

        total_bytes = sum(int(sa.get("bytes_encrypted", 0)) for sa in active_sas)
        strong_crypto = all(
            "aes" in str(sa.get("encryption_algo", "")).lower() and "sha" in str(sa.get("integrity_algo", "")).lower()
            for sa in active_sas
        ) if active_sas else False

        return {
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_sas": active_sas,
            "encryption_match": False,
            "integrity_match": False,
            "pfs_active": pfs_active,
            "strong_crypto_verified": strong_crypto,
            "total_bytes_encrypted": total_bytes,
            "plaintext_leak_detected": False,
            "is_compliant": False,
        }

    def collect_windows_snapshot(self) -> dict[str, Any]:
        command = "Get-NetIPsecQuickModeSA | ConvertTo-Json -Depth 4"
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=False)

        data = []
        output = (result.stdout or "").strip()
        if output:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                data = parsed
            elif isinstance(parsed, dict):
                data = [parsed]

        active_sas: list[dict[str, Any]] = []
        for entry in data:
            active_sas.append(
                {
                    "spi": str(entry.get("Spi") or entry.get("InboundSpi") or ""),
                    "src_ip": str(entry.get("LocalAddress") or ""),
                    "dst_ip": str(entry.get("RemoteAddress") or ""),
                    "encryption_algo": str(entry.get("CipherAlgorithm") or entry.get("EncryptionAlgorithm") or "unknown"),
                    "integrity_algo": str(entry.get("IntegrityAlgorithm") or entry.get("HashAlgorithm") or "unknown"),
                    "dh_group": str(entry.get("PfsGroup") or entry.get("DHGroup") or "") or None,
                    "bytes_encrypted": int(entry.get("NumBytes") or entry.get("InboundByteCount") or 0),
                    "packets_encrypted": int(entry.get("NumPackets") or entry.get("InboundPacketCount") or 0),
                    "sa_expires_in_seconds": int(entry.get("LifetimeSeconds") or 0),
                }
            )

        total_bytes = sum(int(sa.get("bytes_encrypted", 0)) for sa in active_sas)
        pfs_active = any(sa.get("dh_group") for sa in active_sas)
        strong_crypto = all(
            "aes" in str(sa.get("encryption_algo", "")).lower() and "sha" in str(sa.get("integrity_algo", "")).lower()
            for sa in active_sas
        ) if active_sas else False

        return {
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_sas": active_sas,
            "encryption_match": False,
            "integrity_match": False,
            "pfs_active": pfs_active,
            "strong_crypto_verified": strong_crypto,
            "total_bytes_encrypted": total_bytes,
            "plaintext_leak_detected": False,
            "is_compliant": False,
        }

    def collect_snapshot(self) -> dict[str, Any]:
        current = self.os_type
        if current == "linux":
            return self.collect_linux_snapshot()
        if current == "windows":
            return self.collect_windows_snapshot()
        raise RuntimeError(f"Unsupported platform for SA monitoring: {current}")
