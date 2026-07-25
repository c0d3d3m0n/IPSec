from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from orchestrator.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    
    # Unified JSON Config
    config_data = Column(Text, nullable=False) # Store the unified JSON object as a text block
    
    # Multi-tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    tenant = relationship("Tenant", back_populates="policies")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    devices = relationship("Device", back_populates="policy")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, index=True, nullable=True)
    os_type = Column(String, nullable=True) # linux, windows, macos
    public_ip = Column(String, nullable=True)
    
    # New Enrollment flow
    enrollment_number = Column(String, unique=True, index=True) # Visible ID like "EP-001"
    enrollment_token = Column(String, unique=True, index=True) # Secret Token
    pre_shared_key = Column(String, nullable=True)
    os_fingerprint = Column(String, nullable=True)
    status = Column(String, default="PENDING") # PENDING, ACTIVE, REVOKED
    
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    # Multi-tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    tenant = relationship("Tenant", back_populates="devices")

    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    policy = relationship("Policy", back_populates="devices")
    compliance_records = relationship("ComplianceRecord", back_populates="device")
    certificates = relationship("DeviceCertificate", back_populates="device")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemSettings(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)
