from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from orchestrator.database import Base


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_compliant = Column(Boolean, nullable=False, default=False)
    violations = Column(JSON, nullable=False, default=list)
    total_bytes_encrypted = Column(Integer, nullable=False, default=0)
    plaintext_leak_detected = Column(Boolean, nullable=False, default=False)
    active_sa_count = Column(Integer, nullable=False, default=0)
    raw_report = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Multi-tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    device = relationship("Device", back_populates="compliance_records")
