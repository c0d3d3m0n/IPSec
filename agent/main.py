import getpass
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from client import OrchestratorClient
from drivers.dispatcher import DriverDispatcher
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


def _expected_esp(config_data: dict) -> tuple[str, str, bool]:
    compliance = config_data.get("compliance") or {}
    esp = config_data or {}
    return (
        _normalize_algo(esp.get("esp_encryption")),
        _normalize_algo(esp.get("esp_integrity")),
        bool(compliance.get("require_pfs", False)),
    )


def _extract_protected_subnets(config_data: dict) -> list[str]:
    connections = config_data.get("connections") or []
    subnets: list[str] = []
    for conn in connections:
        if conn.get("local_subnet"):
            subnets.append(conn["local_subnet"])
        if conn.get("remote_subnet"):
            subnets.append(conn["remote_subnet"])
    return subnets


def _save_certificates(enrollment_payload: dict):
    cert_path = Path(config.CLIENT_CERT_PATH).absolute()
    key_path = Path(config.CLIENT_KEY_PATH).absolute()
    ca_path = Path(config.CA_CERT_PATH).absolute()
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    ca_path.parent.mkdir(parents=True, exist_ok=True)

    cert_path.write_text(enrollment_payload["cert_pem"], encoding="utf-8")
    key_path.write_text(enrollment_payload["private_key_pem"], encoding="utf-8")
    ca_path.write_text(enrollment_payload["ca_cert_pem"], encoding="utf-8")
    logger.info(f"Certificates saved: cert={cert_path}, key={key_path}, ca={ca_path}")


def _response_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def _mask_secret(value: str, keep: int = 4) -> str:
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]


def main():
    orchestrator_url = config.ORCHESTRATOR_URL
    enrollment_token = os.getenv("ENROLLMENT_TOKEN") or getpass.getpass("Enter Secret Enrollment Token: ")
    enrollment_number = os.getenv("ENROLLMENT_NUMBER") or input("Enter Enrollment Number: ")

    pre_shared_key = config.PRE_SHARED_KEY or getpass.getpass(
        "Enter Pre-Shared Key (leave blank to reuse Enrollment Token): "
    )
    if not pre_shared_key:
        pre_shared_key = enrollment_token
    fingerprint = DeviceFingerprint().collect()
    fingerprint_signature = DeviceFingerprint().sign(fingerprint["fingerprint"], pre_shared_key)

    bootstrap = OrchestratorClient(orchestrator_url, enrollment_token)
    driver_dispatcher = DriverDispatcher()
    os_type = driver_dispatcher.os

    logger.info("Starting Agent bootstrap for %s", enrollment_number)
    logger.info("Using orchestrator URL: %s", orchestrator_url)
    logger.info("Enrollment token fingerprint: %s", _mask_secret(enrollment_token))

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
        cert_path=str(Path(config.CLIENT_CERT_PATH).absolute()),
        key_path=str(Path(config.CLIENT_KEY_PATH).absolute()),
        ca_cert_path=str(Path(config.CA_CERT_PATH).absolute()),
    )
    logger.info(
        "mTLS init with cert paths: cert_exists=%s key_exists=%s ca_exists=%s",
        Path(config.CLIENT_CERT_PATH).absolute().exists(),
        Path(config.CLIENT_KEY_PATH).absolute().exists(),
        Path(config.CA_CERT_PATH).absolute().exists(),
    )

    poll_interval = config.POLL_INTERVAL
    last_applied_version: str | None = None
    current_config: dict | None = None
    sa_monitor = SAMonitor(agent_id=device_id, os_type=os_type)
    protected_subnets = [s.strip() for s in config.PROTECTED_SUBNETS.split(",") if s.strip()]
    leak_detector = LeakDetector(protected_subnets)
    if protected_subnets:
        leak_detector.start(config.LEAK_DETECTION_IFACE)

    headers = {"X-Enrollment-Token": enrollment_token}

    def send_heartbeat(status_value: str, policy_version_applied: str) -> str:
        heartbeat_payload = {
            "device_id": device_id,
            "status": status_value,
            "policy_version_applied": policy_version_applied,
            "os_type": os_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        hb_resp = mtls.post(
            f"{orchestrator_url.rstrip('/')}/api/devices/{device_id}/heartbeat",
            json_payload=heartbeat_payload,
            headers=headers,
            timeout=15,
        )
        if hb_resp.status_code == 403:
            payload = _response_json(hb_resp)
            if payload.get("reason") == "zero_trust_restrict":
                logger.warning("Device in restricted mode; skipping non-heartbeat calls")
                return "restrict"
            if payload.get("reason") == "zero_trust_deny":
                logger.error("Zero Trust deny on heartbeat: %s", payload)
                return "deny"
        return "ok"

    while True:
        try:
            config_url = f"{orchestrator_url.rstrip('/')}/api/devices/{device_id}/config?os_type={os_type}"
            logger.info("Requesting config for device_id=%s os_type=%s", device_id, os_type)
            config_resp = mtls.get(
                config_url,
                headers=headers,
                timeout=15,
            )

            if config_resp.status_code == 200:
                current_config = config_resp.json()
                incoming_version = str(current_config.get("version") or "")
                if incoming_version != (last_applied_version or ""):
                    apply_result = driver_dispatcher.apply(current_config)
                    if not apply_result.success:
                        logger.error("Driver application failed: %s", apply_result.detail or apply_result.message)
                        if send_heartbeat("error", str(current_config.get("policy_id") or "")) != "ok":
                            time.sleep(poll_interval)
                            continue
                        time.sleep(poll_interval)
                        continue
                    last_applied_version = incoming_version

                if send_heartbeat("active", str(current_config.get("policy_id") or "")) != "ok":
                    time.sleep(poll_interval)
                    continue

                if not protected_subnets:
                    dynamic_subnets = _extract_protected_subnets(current_config)
                    if dynamic_subnets:
                        protected_subnets = dynamic_subnets
                        leak_detector = LeakDetector(protected_subnets)
                        leak_detector.start(config.LEAK_DETECTION_IFACE)

                try:
                    snapshot = sa_monitor.collect_snapshot()
                except Exception as exc:
                    logger.warning("Skipping compliance submission this cycle: %s", exc)
                    time.sleep(poll_interval)
                    continue

                expected_enc, expected_integ, require_pfs = _expected_esp(current_config)
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
            elif config_resp.status_code == 404:
                payload = _response_json(config_resp)
                logger.warning("No policy assigned: %s", payload)
                if send_heartbeat("no_policy", "") != "ok":
                    time.sleep(poll_interval)
                    continue
            elif config_resp.status_code == 409:
                payload = _response_json(config_resp)
                logger.error("Policy not built for this OS. Available OS targets: %s", payload.get("available_os", []))
                if send_heartbeat("degraded", str(payload.get("policy_id") or "")) != "ok":
                    time.sleep(poll_interval)
                    continue
            elif config_resp.status_code == 403:
                payload = _response_json(config_resp)
                reason = payload.get("reason")
                logger.warning("Zero Trust denied config access: %s", payload)
                if reason == "zero_trust_deny":
                    if send_heartbeat("error", str(payload.get("policy_id") or "")) != "ok":
                        time.sleep(poll_interval)
                        continue
                else:
                    if send_heartbeat("degraded", str(payload.get("policy_id") or "")) != "ok":
                        time.sleep(poll_interval)
                        continue
            else:
                response_excerpt = (config_resp.text or "")[:500]
                logger.warning(
                    "Unexpected config status: %s url=%s body=%s",
                    config_resp.status_code,
                    config_url,
                    response_excerpt,
                )
                if config_resp.status_code == 401:
                    logger.error(
                        "401 details: sent_header_x_enrollment_token=%s token_fingerprint=%s",
                        "X-Enrollment-Token" in headers,
                        _mask_secret(headers.get("X-Enrollment-Token", "")),
                    )
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Stopping Agent")
            break
        except Exception as exc:
            logger.error("Unexpected error: %s", exc)
            time.sleep(poll_interval)


if __name__ == "__main__":
    main()
