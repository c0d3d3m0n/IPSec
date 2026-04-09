from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class ActiveSAReport(BaseModel):
    spi: str
    src_ip: str
    dst_ip: str
    encryption_algo: str
    integrity_algo: str
    dh_group: str | None = None
    bytes_encrypted: int = 0
    packets_encrypted: int = 0
    sa_expires_in_seconds: int = 0


class ComplianceReportCreate(BaseModel):
    agent_id: int
    timestamp: datetime
    active_sas: List[ActiveSAReport] = Field(default_factory=list)
    encryption_match: bool
    integrity_match: bool
    pfs_active: bool
    strong_crypto_verified: bool
    total_bytes_encrypted: int = 0
    plaintext_leak_detected: bool
    is_compliant: bool


class ComplianceReportResponse(ComplianceReportCreate):
    id: int
    created_at: datetime


class HeartbeatCreate(BaseModel):
    device_id: int
    status: Literal["active", "degraded", "no_policy", "error"]
    policy_version_applied: str
    os_type: str
    timestamp: datetime
