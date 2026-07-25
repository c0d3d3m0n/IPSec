from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from orchestrator.database import Base


class DeviceCertificate(Base):
    __tablename__ = "device_certificates"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    cert_serial = Column(String, unique=True, nullable=False, index=True)
    cert_pem = Column(Text, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Multi-tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    device = relationship("Device", back_populates="certificates")


class RevokedCertificate(Base):
    __tablename__ = "revoked_certificates"

    id = Column(Integer, primary_key=True, index=True)
    cert_serial = Column(String, unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reason = Column(String, nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
