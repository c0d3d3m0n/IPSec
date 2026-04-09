import getpass
import json
import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from client import OrchestratorClient
from platforms.base import PlatformManager
from security.device_fingerprint import DeviceFingerprint
from security.mtls_client import MTLSClient
from verification.leak_detector import LeakDetector
from verification.sa_monitor import SAMonitor


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Agent")


def _normalize_algo(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _expected_esp(policy: dict) -> tuple[str, str, bool]:
    config_data = policy.get("config_data", {})
    esp = (((config_data.get("ipsec_policy") or {}).get("crypto") or {}).get("esp") or {})
    compliance = config_data.get("compliance") or {}
    return (
        _normalize_algo(esp.get("encryption")),
        _normalize_algo(esp.get("integrity")),
        bool(compliance.get("require_pfs", False)),
    )


def _extract_protected_subnets(policy: dict) -> list[str]:
    config_data = policy.get("config_data", {})
    connections = ((config_data.get("ipsec_policy") or {}).get("connections") or [])
    subnets: list[str] = []
    for conn in connections:
        if conn.get("local_subnet"):
            subnets.append(conn["local_subnet"])
        if conn.get("remote_subnet"):
            subnets.append(conn["remote_subnet"])
    return subnets


def _save_certificates(enrollment_payload: dict):
    cert_path = Path(config.CLIENT_CERT_PATH)
    key_path = Path(config.CLIENT_KEY_PATH)
    ca_path = Path(config.CA_CERT_PATH)
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    ca_path.parent.mkdir(parents=True, exist_ok=True)

    cert_path.write_text(enrollment_payload["cert_pem"], encoding="utf-8")
    key_path.write_text(enrollment_payload["private_key_pem"], encoding="utf-8")
    ca_path.write_text(enrollment_payload["ca_cert_pem"], encoding="utf-8")


def get_platform_manager() -> PlatformManager:
    if sys.platform == "linux":
        from platforms.linux import LinuxManager

        return LinuxManager()
    if sys.platform == "win32":
        from platforms.windows import WindowsManager

        return WindowsManager()
    raise RuntimeError(f"Unsupported platform: {sys.platform}. Supported platforms are Linux and Windows.")


def _response_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def main():
    orchestrator_url = config.ORCHESTRATOR_URL
    enrollment_token = os.getenv("ENROLLMENT_TOKEN") or getpass.getpass("Enter Secret Enrollment Token: ")
    enrollment_number = os.getenv("ENROLLMENT_NUMBER") or input("Enter Enrollment Number: ")

    pre_shared_key = config.PRE_SHARED_KEY or enrollment_token
    fingerprint = DeviceFingerprint().collect()
    fingerprint_signature = DeviceFingerprint().sign(fingerprint["fingerprint"], pre_shared_key)

    bootstrap = OrchestratorClient(orchestrator_url, enrollment_token)
    platform_mgr = get_platform_manager()
    os_type = platform.system().lower()

    logger.info("Starting Agent bootstrap for %s", enrollment_number)

    enroll_delay = 5
    enrollment_payload = None
    for attempt in range(1, 6):
        enrollment_payload = bootstrap.enroll(
            enrollment_number=enrollment_number,
            os_fingerprint=fingerprint["fingerprint"],
            agent_signature=fingerprint_signature,
        )
        if enrollment_payload:
            break
        logger.warning("Enrollment attempt %s failed, retrying in %s seconds", attempt, enroll_delay)
        time.sleep(enroll_delay)
        enroll_delay = min(enroll_delay * 2, 60)

    if not enrollment_payload:
        logger.error("Enrollment failed after retries")
        return

    _save_certificates(enrollment_payload)

    device_id = enrollment_payload["id"]
    mtls = MTLSClient(
        cert_path=config.CLIENT_CERT_PATH,
        key_path=config.CLIENT_KEY_PATH,
        ca_cert_path=config.CA_CERT_PATH,
    )

    poll_interval = config.POLL_INTERVAL
    current_policy = None
    sa_monitor = SAMonitor(agent_id=device_id)
    protected_subnets = [s.strip() for s in config.PROTECTED_SUBNETS.split(",") if s.strip()]
    leak_detector = LeakDetector(protected_subnets)
    if protected_subnets:
        leak_detector.start(config.LEAK_DETECTION_IFACE)

    headers = {"X-Enrollment-Token": enrollment_token}

    while True:
        try:
            restricted_mode = False

            config_resp = mtls.get(
                f"{orchestrator_url.rstrip('/')}/api/devices/{device_id}/config",
                headers=headers,
                timeout=15,
            )

            if config_resp.status_code == 200:
                policy = config_resp.json()
                platform_mgr.apply_policy(policy)
                current_policy = policy
            elif config_resp.status_code == 404:
                current_policy = None
                logger.info("No policy assigned")
            elif config_resp.status_code == 403:
                payload = _response_json(config_resp)
                if payload.get("reason") in {"zero_trust_restrict", "zero_trust_deny"}:
                    restricted_mode = True
                    logger.warning("Zero Trust restricted config access: %s", payload)
            else:
                logger.warning("Unexpected config status: %s", config_resp.status_code)

            policy_version = "none"
            status_value = "no_policy"
            if current_policy:
                status_value = "active"
                policy_version = str(
                    current_policy.get("config_data", {}).get("version")
                    or current_policy.get("config_data", {}).get("policy_id")
                    or "unknown"
                )

            heartbeat_payload = {
                "device_id": device_id,
                "status": status_value,
                "policy_version_applied": policy_version,
                "os_type": os_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            hb_resp = mtls.post(
                f"{orchestrator_url.rstrip('/')}/api/devices/{device_id}/heartbeat",
                json_payload=heartbeat_payload,
                headers=headers,
                timeout=15,
            )

            if hb_resp.status_code == 200:
                hb_json = hb_resp.json()
                if hb_json.get("action_required") == "repoll_policy":
                    repoll = mtls.get(
                        f"{orchestrator_url.rstrip('/')}/api/devices/{device_id}/config",
                        headers=headers,
                        timeout=15,
                    )
                    if repoll.status_code == 200:
                        current_policy = repoll.json()
                        platform_mgr.apply_policy(current_policy)
            elif hb_resp.status_code == 403:
                payload = _response_json(hb_resp)
                if payload.get("reason") == "zero_trust_restrict":
                    restricted_mode = True
                    logger.warning("Device in restricted mode; skipping non-heartbeat calls")
                elif payload.get("reason") == "zero_trust_deny":
                    logger.error("Zero Trust deny on heartbeat: %s", payload)
                    time.sleep(poll_interval)
                    continue

            if restricted_mode:
                time.sleep(poll_interval)
                continue

            if current_policy:
                if not protected_subnets:
                    dynamic_subnets = _extract_protected_subnets(current_policy)
                    if dynamic_subnets:
                        protected_subnets = dynamic_subnets
                        leak_detector = LeakDetector(protected_subnets)
                        leak_detector.start(config.LEAK_DETECTION_IFACE)

                snapshot = sa_monitor.collect_snapshot()
                expected_enc, expected_integ, require_pfs = _expected_esp(current_policy)
                actual_enc = {_normalize_algo(sa.get("encryption_algo")) for sa in snapshot.get("active_sas", [])}
                actual_integ = {_normalize_algo(sa.get("integrity_algo")) for sa in snapshot.get("active_sas", [])}

                encryption_match = bool(actual_enc) and all(v == expected_enc for v in actual_enc)
                integrity_match = bool(actual_integ) and all(v == expected_integ for v in actual_integ)
                leak_detected = leak_detector.get_leak_status()
                pfs_ok = snapshot.get("pfs_active", False) if require_pfs else True
                strong_ok = snapshot.get("strong_crypto_verified", False)

                snapshot["encryption_match"] = encryption_match
                snapshot["integrity_match"] = integrity_match
                snapshot["plaintext_leak_detected"] = leak_detected
                snapshot["is_compliant"] = encryption_match and integrity_match and pfs_ok and strong_ok and not leak_detected

                comp_resp = mtls.post(
                    f"{orchestrator_url.rstrip('/')}/api/devices/{device_id}/compliance",
                    json_payload=snapshot,
                    headers=headers,
                    timeout=15,
                )
                if comp_resp.status_code == 403:
                    payload = _response_json(comp_resp)
                    if payload.get("reason") == "zero_trust_restrict":
                        logger.warning("Compliance blocked due to restricted mode")
                leak_detector.reset()

            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Stopping Agent")
            break
        except Exception as exc:
            logger.error("Unexpected error: %s", exc)
            time.sleep(poll_interval)


if __name__ == "__main__":
    main()
