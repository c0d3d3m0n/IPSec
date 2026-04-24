from datetime import datetime, timedelta, timezone
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, Header
from sqlalchemy.orm import Session

from orchestrator import database, models
from orchestrator.rate_limiter import limiter
from orchestrator.auth import get_current_admin_user


router = APIRouter(prefix="/devices", tags=["compliance"])


def _load_module(module_name: str, file_path: Path):
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_BASE_DIR = Path(__file__).resolve().parents[1]
_compliance_schema_module = _load_module("orchestrator_schemas_compliance", _BASE_DIR / "schemas" / "compliance.py")
_compliance_model_module = _load_module("orchestrator_models_compliance", _BASE_DIR / "models" / "compliance.py")
_audit_logger_module = _load_module("orchestrator_security_audit_logger", _BASE_DIR / "security" / "audit_logger.py")

ComplianceReportCreate = _compliance_schema_module.ComplianceReportCreate
ComplianceReportResponse = _compliance_schema_module.ComplianceReportResponse
HeartbeatCreate = _compliance_schema_module.HeartbeatCreate
ComplianceRecord = _compliance_model_module.ComplianceRecord
AuditLogger = _audit_logger_module.AuditLogger


def _normalize_algo(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


def _get_policy_payload(device: models.Device) -> dict[str, Any] | None:
    if not device.policy:
        return None

    policy_raw = device.policy.config_data
    if isinstance(policy_raw, str):
        return json.loads(policy_raw)
    if isinstance(policy_raw, dict):
        return policy_raw
    return None


def _check_device_token(device: models.Device, token: str):
    if device.enrollment_token != token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")


@router.post("/{device_id}/heartbeat")
@limiter.limit("120/minute")
def post_heartbeat(
    device_id: int,
    heartbeat: HeartbeatCreate,
    request: Request,
    device_token: str = Header(..., alias="X-Enrollment-Token"),
    db: Session = Depends(database.get_db),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    _check_device_token(device, device_token)

    if heartbeat.device_id != device_id:
        raise HTTPException(status_code=400, detail="device_id mismatch")

    device.last_seen = datetime.now(timezone.utc)
    db.commit()

    policy = _get_policy_payload(device)
    assigned_version = None
    if policy:
        assigned_version = str(policy.get("version") or policy.get("policy_id") or "")

    stale = bool(assigned_version) and heartbeat.policy_version_applied != assigned_version
    response = {
        "acknowledged": True,
        "policy_stale": stale,
        "action_required": "repoll_policy" if stale else None,
    }

    AuditLogger().log(
        action="heartbeat_received",
        actor=f"device:{device_id}",
        target=f"device:{device_id}",
        payload_dict=heartbeat.model_dump(),
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return response


@router.post("/{device_id}/compliance", response_model=ComplianceReportResponse)
@limiter.limit("60/minute")
def post_compliance(
    device_id: int,
    report: ComplianceReportCreate,
    request: Request,
    device_token: str = Header(..., alias="X-Enrollment-Token"),
    db: Session = Depends(database.get_db),
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    _check_device_token(device, device_token)

    if report.agent_id != device_id:
        raise HTTPException(status_code=400, detail="agent_id mismatch")

    policy = _get_policy_payload(device)
    if not policy:
        raise HTTPException(status_code=400, detail="Device has no assigned policy")

    esp = (((policy.get("ipsec_policy") or {}).get("crypto") or {}).get("esp") or {})
    compliance = policy.get("compliance") or {}

    required_encryption = _normalize_algo(esp.get("encryption"))
    required_integrity = _normalize_algo(esp.get("integrity"))

    violations: list[str] = []

    actual_encryption = {_normalize_algo(sa.encryption_algo) for sa in report.active_sas}
    actual_integrity = {_normalize_algo(sa.integrity_algo) for sa in report.active_sas}

    encryption_match = bool(actual_encryption) and all(v == required_encryption for v in actual_encryption)
    integrity_match = bool(actual_integrity) and all(v == required_integrity for v in actual_integrity)

    # Check if in pre-traffic state (policy deployed but no SAs negotiated yet)
    has_active_sas = len(report.active_sas) > 0
    
    if required_encryption and actual_encryption and not encryption_match:
        violations.append(f"ENCRYPTION_MISMATCH: expected {required_encryption}, got {sorted(actual_encryption)}")

    if required_integrity and actual_integrity and not integrity_match:
        violations.append(f"INTEGRITY_MISMATCH: expected {required_integrity}, got {sorted(actual_integrity)}")

    # Only check PFS/crypto requirements if SAs are active
    # Zero SAs is expected in pre-traffic state (policy deployed but no matching traffic yet)
    if has_active_sas:
        if compliance.get("require_pfs", False) and not report.pfs_active:
            violations.append("PFS_REQUIRED_BUT_NOT_ACTIVE")

        strong_required = compliance.get("require_strong_crypto", False)
        if strong_required and not report.strong_crypto_verified:
            violations.append("STRONG_CRYPTO_REQUIRED_BUT_NOT_VERIFIED")

    if report.plaintext_leak_detected:
        violations.append("CRITICAL_PLAINTEXT_LEAK_DETECTED")

    is_compliant = len(violations) == 0

    record = ComplianceRecord(
        device_id=device_id,
        timestamp=report.timestamp,
        is_compliant=is_compliant,
        violations=violations,
        total_bytes_encrypted=report.total_bytes_encrypted,
        plaintext_leak_detected=report.plaintext_leak_detected,
        active_sa_count=len(report.active_sas),
        raw_report=report.model_dump(mode="json"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    AuditLogger().log(
        action="compliance_report_received",
        actor=f"device:{device_id}",
        target=f"device:{device_id}",
        payload_dict=report.model_dump(),
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    return ComplianceReportResponse(
        id=record.id,
        created_at=record.created_at,
        agent_id=report.agent_id,
        timestamp=report.timestamp,
        active_sas=report.active_sas,
        encryption_match=encryption_match,
        integrity_match=integrity_match,
        pfs_active=report.pfs_active,
        strong_crypto_verified=report.strong_crypto_verified,
        total_bytes_encrypted=report.total_bytes_encrypted,
        plaintext_leak_detected=report.plaintext_leak_detected,
        is_compliant=is_compliant,
    )


@router.get("/{device_id}/compliance")
def get_compliance_reports(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    device_token: str | None = Header(default=None, alias="X-Enrollment-Token"),
    db: Session = Depends(database.get_db),
    request: Request = None,
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Check if this is an admin request (has Authorization Bearer header)
    auth_header = (request.headers.get("authorization", "") if request else "").lower()
    is_admin_request = auth_header.startswith("bearer ")
    
    # Allow if called by admin OR has valid device token
    if not is_admin_request and not device_token:
        raise HTTPException(status_code=401, detail="Missing X-Enrollment-Token header or Bearer token")
    
    if device_token:
        # Validate device token
        _check_device_token(device, device_token)
    # If admin request with Bearer token, it will be validated by the middleware before reaching here

    records = (
        db.query(ComplianceRecord)
        .filter(ComplianceRecord.device_id == device_id)
        .order_by(ComplianceRecord.timestamp.desc())
        .limit(limit)
        .all()
    )

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = (
        db.query(ComplianceRecord)
        .filter(ComplianceRecord.device_id == device_id, ComplianceRecord.timestamp >= since)
        .all()
    )

    violations_last_24h: list[str] = []
    for record in recent:
        violations_last_24h.extend(record.violations or [])

    payload_records = []
    for record in records:
        payload_records.append(
            {
                "id": record.id,
                "timestamp": record.timestamp,
                "is_compliant": record.is_compliant,
                "violations": record.violations,
                "total_bytes_encrypted": record.total_bytes_encrypted,
                "plaintext_leak_detected": record.plaintext_leak_detected,
                "active_sa_count": record.active_sa_count,
            }
        )

    return {
        "device_id": device_id,
        "total_records": len(records),
        "latest_compliant": records[0].is_compliant if records else None,
        "violations_last_24h": violations_last_24h,
        "records": payload_records,
    }
