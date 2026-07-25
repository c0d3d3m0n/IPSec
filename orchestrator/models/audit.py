from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from orchestrator.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False, index=True)
    actor = Column(String, nullable=False, index=True)
    target = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    payload_hash = Column(String(128), nullable=False)
    ip_address = Column(String, nullable=True)
    chain_hash = Column(String(128), nullable=False)

    # Multi-tenant (nullable — some audit entries are system-level)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
