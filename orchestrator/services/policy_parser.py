from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha512
import json
import re
from typing import Any


SUPPORTED_OS = {"linux", "windows", "macos"}
WEAK_ALGOS = {"HMAC_SHA1", "AES_CBC_128", "MODP_2048"}
AEAD_ENCRYPTION = {"AES_GCM_256", "AES_GCM_128", "CHACHA20_POLY1305"}


ENCRYPTION_ALIAS_TABLE = {
    "aes256gcm": "AES_GCM_256",
    "aesgcm256": "AES_GCM_256",
    "aes256gcm16": "AES_GCM_256",
    "aesgcm128": "AES_GCM_128",
    "aes128gcm16": "AES_GCM_128",
    "aes256": "AES_CBC_256",
    "aes256cbc": "AES_CBC_256",
    "aescbc256": "AES_CBC_256",
    "aes128": "AES_CBC_128",
    "aes128cbc": "AES_CBC_128",
    "aescbc128": "AES_CBC_128",
    "chacha20poly1305": "CHACHA20_POLY1305",
}

INTEGRITY_ALIAS_TABLE = {
    "sha2256": "HMAC_SHA2_256",
    "hmacsha2256": "HMAC_SHA2_256",
    "sha256": "HMAC_SHA2_256",
    "hmacsha256": "HMAC_SHA2_256",
    "sha2384": "HMAC_SHA2_384",
    "hmacsha2384": "HMAC_SHA2_384",
    "sha384": "HMAC_SHA2_384",
    "hmacsha384": "HMAC_SHA2_384",
    "sha2512": "HMAC_SHA2_512",
    "hmacsha2512": "HMAC_SHA2_512",
    "sha512": "HMAC_SHA2_512",
    "hmacsha512": "HMAC_SHA2_512",
    "sha1": "HMAC_SHA1",
}

DH_GROUP_ALIAS_TABLE = {
    "modp2048": "MODP_2048",
    "group14": "MODP_2048",
    "modp3072": "MODP_3072",
    "group15": "MODP_3072",
    "modp4096": "MODP_4096",
    "group16": "MODP_4096",
    "ecp256": "ECP_256",
    "group19": "ECP_256",
    "ecp384": "ECP_384",
    "group20": "ECP_384",
    "ecp521": "ECP_521",
    "group21": "ECP_521",
}

LINUX_ALGO_MAP = {
    "AES_GCM_256": "aes256gcm16",
    "AES_GCM_128": "aes128gcm16",
    "AES_CBC_256": "aes256",
    "AES_CBC_128": "aes128",
    "CHACHA20_POLY1305": "chacha20poly1305",
    "HMAC_SHA2_256": "sha256",
    "HMAC_SHA2_384": "sha384",
    "HMAC_SHA2_512": "sha512",
    "HMAC_SHA1": "sha1",
    "MODP_2048": "modp2048",
    "MODP_3072": "modp3072",
    "MODP_4096": "modp4096",
    "ECP_256": "ecp256",
    "ECP_384": "ecp384",
    "ECP_521": "ecp521",
}

WINDOWS_ALGO_MAP: dict[str, str] = {
    # Encryption - exact values Windows accepts
    "AES_GCM_256": "AESGCM256",
    "AES_GCM_128": "AESGCM128",
    "AES_CBC_256": "AES256",
    "AES_CBC_128": "AES128",
    "CHACHA20_POLY1305": "AES256",
    # Integrity - exact values Windows accepts
    "HMAC_SHA2_256": "SHA256",
    "HMAC_SHA2_384": "SHA256",
    "HMAC_SHA2_512": "SHA256",
    "HMAC_SHA1": "SHA1",
    # DH groups (for MainMode only)
    "MODP_2048": "DH14",
    "MODP_3072": "DH14",
    "MODP_4096": "DH14",
    "ECP_256": "DH19",
    "ECP_384": "DH20",
    "ECP_521": "DH24",
}

MACOS_ALGO_MAP = {
    "AES_GCM_256": "aes-256-gcm",
    "AES_GCM_128": "aes-128-gcm",
    "AES_CBC_256": "aes256",
    "AES_CBC_128": "aes128",
    "CHACHA20_POLY1305": "chacha20poly1305",
    "HMAC_SHA2_256": "hmac-sha256",
    "HMAC_SHA2_384": "hmac-sha384",
    "HMAC_SHA2_512": "hmac-sha512",
    "HMAC_SHA1": "hmac-sha1",
    "MODP_2048": "modp2048",
    "MODP_3072": "modp3072",
    "MODP_4096": "modp4096",
    "ECP_256": "ecp256",
    "ECP_384": "ecp384",
    "ECP_521": "ecp521",
}

OS_NATIVE_MAPS = {
    "linux": LINUX_ALGO_MAP,
    "windows": WINDOWS_ALGO_MAP,
    "macos": MACOS_ALGO_MAP,
}


@dataclass
class OSConfig:
    os: str
    ike_encryption: str
    ike_integrity: str | None
    ike_dh_group: str | None
    esp_encryption: str
    esp_integrity: str | None
    esp_dh_group: str | None
    key_exchange: str
    mode: str
    connections: list[dict[str, Any]]
    auth_type: str
    auth_secret_ref: str
    raw_driver_block: dict[str, Any]


@dataclass
class ParsedPolicy:
    policy_id: str
    version: str
    description: str | None
    os_configs: dict[str, OSConfig]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    input_hash: str = ""

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class PolicyParser:
    def parse(self, raw_bytes: bytes) -> ParsedPolicy:
        warnings: list[str] = []
        errors: list[str] = []

        input_hash = sha512(raw_bytes).hexdigest()

        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            return ParsedPolicy(
                policy_id="",
                version="",
                description=None,
                os_configs={},
                warnings=warnings,
                errors=[f"Invalid UTF-8: {exc}"],
                input_hash=input_hash,
            )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return ParsedPolicy(
                policy_id="",
                version="",
                description=None,
                os_configs={},
                warnings=warnings,
                errors=[f"Malformed JSON: {exc.msg}"],
                input_hash=input_hash,
            )

        if not isinstance(payload, dict):
            return ParsedPolicy(
                policy_id="",
                version="",
                description=None,
                os_configs={},
                warnings=warnings,
                errors=["Top-level JSON must be an object"],
                input_hash=input_hash,
            )

        required_keys = ["policy_id", "version", "target", "ipsec_policy", "execution", "compliance"]
        missing_keys = [key for key in required_keys if key not in payload]
        if missing_keys:
            errors.append(f"Missing required top-level keys: {', '.join(missing_keys)}")

        target = payload.get("target") or {}
        if not isinstance(target, dict):
            errors.append("target must be an object")
            target = {}

        os_targets = target.get("os")
        if not isinstance(os_targets, list) or not os_targets:
            errors.append("target.os must be a non-empty list")
            os_targets = []

        normalized_os_targets: list[str] = []
        unsupported_os: list[str] = []
        for item in os_targets:
            os_name = str(item).strip().lower()
            if os_name not in SUPPORTED_OS:
                unsupported_os.append(os_name)
            elif os_name not in normalized_os_targets:
                normalized_os_targets.append(os_name)
        if unsupported_os:
            errors.append(f"Unsupported OS targets: {', '.join(sorted(set(unsupported_os)))}")

        ipsec_policy = payload.get("ipsec_policy") or {}
        if not isinstance(ipsec_policy, dict):
            errors.append("ipsec_policy must be an object")
            ipsec_policy = {}

        execution = payload.get("execution") or {}
        if not isinstance(execution, dict):
            errors.append("execution must be an object")
            execution = {}

        compliance = payload.get("compliance") or {}
        if not isinstance(compliance, dict):
            errors.append("compliance must be an object")
            compliance = {}

        auth = ipsec_policy.get("authentication") or {}
        if not isinstance(auth, dict):
            errors.append("ipsec_policy.authentication must be an object")
            auth = {}

        crypto = ipsec_policy.get("crypto") or {}
        if not isinstance(crypto, dict):
            errors.append("ipsec_policy.crypto must be an object")
            crypto = {}

        ike = crypto.get("ike") or {}
        esp = crypto.get("esp") or {}
        if not isinstance(ike, dict):
            errors.append("ipsec_policy.crypto.ike must be an object")
            ike = {}
        if not isinstance(esp, dict):
            errors.append("ipsec_policy.crypto.esp must be an object")
            esp = {}

        connections = ipsec_policy.get("connections") or []
        if not isinstance(connections, list) or len(connections) == 0:
            errors.append("ipsec_policy.connections must be a non-empty list")
            connections = []

        connection_models: list[dict[str, Any]] = []
        required_connection_fields = ["name", "local_ip", "local_subnet", "remote_ip", "remote_subnet"]
        for index, connection in enumerate(connections):
            if not isinstance(connection, dict):
                errors.append(f"Connection entry {index} must be an object")
                continue
            missing = [field for field in required_connection_fields if field not in connection]
            if missing:
                errors.append(
                    f"Connection entry '{connection.get('name', index)}' missing required fields: {', '.join(missing)}"
                )
                continue
            connection_models.append(connection)

        if errors:
            return ParsedPolicy(
                policy_id=str(payload.get("policy_id", "")),
                version=str(payload.get("version", "")),
                description=payload.get("description"),
                os_configs={},
                warnings=warnings,
                errors=errors,
                input_hash=input_hash,
            )

        policy_id = str(payload.get("policy_id"))
        version = str(payload.get("version"))
        description = payload.get("description")

        compliance_require_strong_crypto = bool(compliance.get("require_strong_crypto", False))
        compliance_require_pfs = bool(compliance.get("require_pfs", False))

        ike_enc = self._resolve_alias(ike.get("encryption"), ENCRYPTION_ALIAS_TABLE, errors, "IKE encryption")
        esp_enc = self._resolve_alias(esp.get("encryption"), ENCRYPTION_ALIAS_TABLE, errors, "ESP encryption")
        ike_int = self._resolve_optional_integrity(ike.get("integrity"), warnings, errors, "IKE integrity", ike_enc)
        esp_int = self._resolve_optional_integrity(esp.get("integrity"), warnings, errors, "ESP integrity", esp_enc)
        ike_dh = self._resolve_optional_alias(ike.get("dh_group"), DH_GROUP_ALIAS_TABLE, errors, "IKE DH group")
        esp_dh = self._resolve_optional_alias(esp.get("dh_group"), DH_GROUP_ALIAS_TABLE, errors, "ESP DH group")

        if compliance_require_pfs and not esp_dh:
            warnings.append("PFS required but ESP DH group is missing; IKE group may satisfy policy")

        for algo in [ike_enc, esp_enc, ike_int, esp_int, ike_dh, esp_dh]:
            if not algo:
                continue
            if algo in WEAK_ALGOS:
                message = f"Weak algorithm detected: {algo}"
                if compliance_require_strong_crypto:
                    errors.append(message)
                else:
                    warnings.append(message)

        os_configs: dict[str, OSConfig] = {}
        for os_name in normalized_os_targets:
            native_map = OS_NATIVE_MAPS[os_name]
            os_configs[os_name] = self._build_os_config(
                os_name=os_name,
                policy_id=policy_id,
                version=version,
                description=description,
                ike_enc=ike_enc,
                ike_int=ike_int,
                ike_dh=ike_dh,
                esp_enc=esp_enc,
                esp_int=esp_int,
                esp_dh=esp_dh,
                key_exchange=str(ipsec_policy.get("key_exchange", "ikev2")),
                mode=str(ipsec_policy.get("mode", "tunnel")),
                auth_type=str(auth.get("type", "psk")),
                auth_secret_ref=str(auth.get("secret_ref", "")),
                connections=connection_models,
                native_map=native_map,
            )

        return ParsedPolicy(
            policy_id=policy_id,
            version=version,
            description=description,
            os_configs=os_configs,
            warnings=warnings,
            errors=errors,
            input_hash=input_hash,
        )

    def _resolve_alias(
        self,
        value: Any,
        alias_table: dict[str, str],
        errors: list[str],
        label: str,
    ) -> str:
        if value is None:
            errors.append(f"{label} is missing")
            return ""
        key = self._normalize(value)
        canonical = alias_table.get(key)
        if not canonical:
            errors.append(f"Unsupported {label}: {value}")
            return ""
        return canonical

    def _resolve_optional_alias(
        self,
        value: Any,
        alias_table: dict[str, str],
        errors: list[str],
        label: str,
    ) -> str | None:
        if value in (None, ""):
            return None
        key = self._normalize(value)
        canonical = alias_table.get(key)
        if not canonical:
            errors.append(f"Unsupported {label}: {value}")
            return None
        return canonical

    def _resolve_optional_integrity(
        self,
        value: Any,
        warnings: list[str],
        errors: list[str],
        label: str,
        encryption: str,
    ) -> str | None:
        if value in (None, ""):
            if encryption not in AEAD_ENCRYPTION:
                warnings.append(f"{label} is missing for non-AEAD encryption; review policy")
            return None
        canonical = self._resolve_alias(value, INTEGRITY_ALIAS_TABLE, errors, label)
        return canonical or None

    def _build_os_config(
        self,
        *,
        os_name: str,
        policy_id: str,
        version: str,
        description: str | None,
        ike_enc: str,
        ike_int: str | None,
        ike_dh: str | None,
        esp_enc: str,
        esp_int: str | None,
        esp_dh: str | None,
        key_exchange: str,
        mode: str,
        auth_type: str,
        auth_secret_ref: str,
        connections: list[dict[str, Any]],
        native_map: dict[str, str],
    ) -> OSConfig:
        mapped_ike_enc = native_map[ike_enc]
        mapped_esp_enc = native_map[esp_enc]
        mapped_ike_int = native_map[ike_int] if ike_int else None
        mapped_esp_int = native_map[esp_int] if esp_int else None
        mapped_ike_dh = native_map[ike_dh] if ike_dh else None
        mapped_esp_dh = native_map[esp_dh] if esp_dh else None

        conn_payloads: list[dict[str, Any]] = []
        for connection in connections:
            conn_payloads.append(
                {
                    "name": connection["name"],
                    "local_ip": connection["local_ip"],
                    "local_subnet": connection["local_subnet"],
                    "remote_ip": connection["remote_ip"],
                    "remote_subnet": connection["remote_subnet"],
                    "auto_start": bool(connection.get("auto_start", True)),
                }
            )

        if os_name == "linux":
            raw_driver_block = self._build_linux_driver_block(
                policy_id=policy_id,
                version=version,
                description=description,
                ike_enc=mapped_ike_enc,
                ike_int=mapped_ike_int,
                ike_dh=mapped_ike_dh,
                esp_enc=mapped_esp_enc,
                esp_int=mapped_esp_int,
                esp_dh=mapped_esp_dh,
                key_exchange=key_exchange,
                mode=mode,
                auth_type=auth_type,
                auth_secret_ref=auth_secret_ref,
                connections=conn_payloads,
            )
        elif os_name == "windows":
            raw_driver_block = self._build_windows_driver_block(
                policy_id=policy_id,
                ike_enc=mapped_ike_enc,
                ike_int=mapped_ike_int,
                ike_dh=mapped_ike_dh,
                esp_enc=mapped_esp_enc,
                esp_int=mapped_esp_int,
                esp_dh=mapped_esp_dh,
                key_exchange=key_exchange,
                mode=mode,
                auth_type=auth_type,
                auth_secret_ref=auth_secret_ref,
                connections=conn_payloads,
            )
        else:
            raw_driver_block = self._build_macos_driver_block(
                policy_id=policy_id,
                ike_enc=mapped_ike_enc,
                ike_int=mapped_ike_int,
                ike_dh=mapped_ike_dh,
                esp_enc=mapped_esp_enc,
                esp_int=mapped_esp_int,
                esp_dh=mapped_esp_dh,
                mode=mode,
                auth_type=auth_type,
                auth_secret_ref=auth_secret_ref,
                connections=conn_payloads,
            )

        return OSConfig(
            os=os_name,
            ike_encryption=mapped_ike_enc,
            ike_integrity=mapped_ike_int,
            ike_dh_group=mapped_ike_dh,
            esp_encryption=mapped_esp_enc,
            esp_integrity=mapped_esp_int,
            esp_dh_group=mapped_esp_dh,
            key_exchange=key_exchange,
            mode=mode,
            connections=conn_payloads,
            auth_type=auth_type,
            auth_secret_ref=auth_secret_ref,
            raw_driver_block=raw_driver_block,
        )

    def _proposal(self, *parts: str | None) -> str:
        return "-".join(part for part in parts if part)

    def _build_linux_driver_block(
        self,
        *,
        policy_id: str,
        version: str,
        description: str | None,
        ike_enc: str,
        ike_int: str | None,
        ike_dh: str | None,
        esp_enc: str,
        esp_int: str | None,
        esp_dh: str | None,
        key_exchange: str,
        mode: str,
        auth_type: str,
        auth_secret_ref: str,
        connections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        proposal = self._proposal(ike_enc, ike_int, ike_dh)
        esp_proposal = self._proposal(esp_enc, esp_int, esp_dh)
        connection_blocks: dict[str, Any] = {}
        for connection in connections:
            name = connection["name"]
            connection_blocks[name] = {
                "version": 2,
                "local_addrs": [connection["local_ip"]],
                "remote_addrs": [connection["remote_ip"]],
                "proposals": proposal,
                "children": {
                    f"{name}-child": {
                        "local_ts": [connection["local_subnet"]],
                        "remote_ts": [connection["remote_subnet"]],
                        "esp_proposals": esp_proposal,
                        "mode": mode,
                        "start_action": "start" if connection.get("auto_start", True) else "none",
                    }
                },
                "local": {"auth": auth_type, "id": connection["local_ip"]},
                "remote": {"auth": auth_type, "id": connection["remote_ip"]},
            }

        return {
            "policy_id": policy_id,
            "version": version,
            "description": description,
            "charon": {"proposals": proposal},
            "connections": connection_blocks,
            "secrets": {"ike-secret": {"secret": f"${{{auth_secret_ref}}}"}},
            "key_exchange": key_exchange,
            "mode": mode,
            "auth_type": auth_type,
            "auth_secret_ref": auth_secret_ref,
        }

    def _build_windows_driver_block(
        self,
        *,
        policy_id: str,
        ike_enc: str,
        ike_int: str | None,
        ike_dh: str | None,
        esp_enc: str,
        esp_int: str | None,
        esp_dh: str | None,
        key_exchange: str,
        mode: str,
        auth_type: str,
        auth_secret_ref: str,
        connections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        commands: list[dict[str, Any]] = []
        for connection in connections:
            name = connection["name"]
            commands.append(
                {
                    "cmdlet": "New-NetIPsecMainModeRule",
                    "params": {
                        "DisplayName": name,
                        "LocalAddress": connection["local_ip"],
                        "RemoteAddress": connection["remote_ip"],
                        "PolicyStore": "PersistentStore",
                    },
                }
            )
            commands.append(
                {
                    "cmdlet": "New-NetIPsecMainModeCryptoSet",
                    "params": {
                        "Name": f"{name}-mm",
                        "Encryption": ike_enc,
                        "Integrity": ike_int,
                        "DHGroup": ike_dh,
                        "KeyExchange": key_exchange,
                    },
                }
            )
            commands.append(
                {
                    "cmdlet": "New-NetIPsecQuickModeCryptoSet",
                    "params": {
                        "Name": f"{name}-qm",
                        "Encryption": esp_enc,
                        "Integrity": esp_int,
                        "DHGroup": esp_dh,
                        "Mode": mode,
                        "AuthType": auth_type,
                    },
                }
            )

        return {
            "policy_id": policy_id,
            "commands": commands,
            "mode": mode,
            "key_exchange": key_exchange,
            "auth_type": auth_type,
            "auth_secret_ref": auth_secret_ref,
            "connections": connections,
        }

    def _build_macos_driver_block(
        self,
        *,
        policy_id: str,
        ike_enc: str,
        ike_int: str | None,
        ike_dh: str | None,
        esp_enc: str,
        esp_int: str | None,
        esp_dh: str | None,
        mode: str,
        auth_type: str,
        auth_secret_ref: str,
        connections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        remote: dict[str, Any] = {}
        for connection in connections:
            name = connection["name"]
            remote[name] = {
                "remote_address": connection["remote_ip"],
                "local_address": connection["local_ip"],
                "authentication_method": auth_type,
                "shared_secret": f"${{{auth_secret_ref}}}",
                "proposal": {
                    "encryption_algorithm": ike_enc,
                    "hash_algorithm": ike_int,
                    "dh_group": ike_dh,
                    "lifetime": 28800,
                },
                "phase2": {
                    "my_address": connection["local_subnet"],
                    "peers_address": connection["remote_subnet"],
                    "esp_enc": esp_enc,
                    "esp_auth": esp_int,
                    "pfs_group": esp_dh,
                    "lifetime": 3600,
                    "mode": mode,
                },
            }
        return {"policy_id": policy_id, "remote": remote, "auth_type": auth_type, "auth_secret_ref": auth_secret_ref}

    def _normalize(self, value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())
