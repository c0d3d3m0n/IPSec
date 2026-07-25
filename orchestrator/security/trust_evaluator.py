from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


from orchestrator.models.certificate import RevokedCertificate
from orchestrator.models.compliance import ComplianceRecord
from orchestrator.security.audit_logger import AuditLogger


@dataclass
class TrustScore:
    score: int
    decision: str
    reasons: list[str]


class TrustEvaluator:
    def evaluate(self, device_id: int, request_context: dict[str, Any], db) -> TrustScore:
        from orchestrator import models

        score = 100
        reasons: list[str] = []

        cert_cn = request_context.get("cert_cn", "")
        cert_serial = request_context.get("cert_serial", "")
        if cert_cn != f"device-{device_id}":
            score = 0
            reasons.append("CERT_CN_MISMATCH")
            result = TrustScore(score=0, decision="deny", reasons=reasons)
            self._log_decision(device_id, result, request_context, db)
            return result

        revoked = db.query(RevokedCertificate).filter(RevokedCertificate.cert_serial == cert_serial).first()
        if revoked:
            score = 0
            reasons.append("CERTIFICATE_REVOKED")
            result = TrustScore(score=0, decision="deny", reasons=reasons)
            self._log_decision(device_id, result, request_context, db)
            return result

        device = db.query(models.Device).filter(models.Device.id == device_id).first()
        if not device:
            result = TrustScore(score=0, decision="deny", reasons=["DEVICE_NOT_FOUND"])
            self._log_decision(device_id, result, request_context, db)
            return result

        now = datetime.now(timezone.utc)

        if device.last_seen is None or (now - device.last_seen.replace(tzinfo=timezone.utc)) > timedelta(minutes=5):
            score -= 30
            reasons.append("LAST_SEEN_STALE")

        source_ip = request_context.get("source_ip")
        if source_ip and device.public_ip and source_ip != device.public_ip:
            score -= 40
            reasons.append("SOURCE_IP_MISMATCH")

        if now.hour < 6 or now.hour > 22:
            score -= 10
            reasons.append("OUTSIDE_STANDARD_HOURS")

        latest_compliance = (
            db.query(ComplianceRecord)
            .filter(ComplianceRecord.device_id == device_id)
            .order_by(ComplianceRecord.timestamp.desc())
            .first()
        )

        if latest_compliance:
            if not latest_compliance.is_compliant:
                score -= 25
                reasons.append("LATEST_COMPLIANCE_FAILED")
            if latest_compliance.plaintext_leak_detected:
                score -= 50
                reasons.append("PLAINTEXT_LEAK_DETECTED")
            if latest_compliance.active_sa_count == 0:
                score -= 20
                reasons.append("NO_ACTIVE_SA")

        score = max(0, score)
        if score >= 70:
            decision = "allow"
        elif score >= 40:
            decision = "restrict"
        else:
            decision = "deny"

        result = TrustScore(score=score, decision=decision, reasons=reasons)
        self._log_decision(device_id, result, request_context, db)
        return result

    def _log_decision(self, device_id: int, trust: TrustScore, request_context: dict[str, Any], db):
        payload = {
            "device_id": device_id,
            "score": trust.score,
            "decision": trust.decision,
            "reasons": trust.reasons,
            "path": request_context.get("path"),
            "source_ip": request_context.get("source_ip"),
        }
        AuditLogger().log(
            action="trust_evaluation",
            actor=f"device:{device_id}",
            target=f"device:{device_id}",
            payload_dict=payload,
            ip_address=request_context.get("source_ip"),
            db=db,
        )
