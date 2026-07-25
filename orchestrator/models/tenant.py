from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from orchestrator.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="free")  # free | pro | enterprise
    is_active = Column(Boolean, default=True)
    max_devices = Column(Integer, default=5)
    max_users = Column(Integer, default=2)
    contact_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="tenant")
    devices = relationship("Device", back_populates="tenant")
    policies = relationship("Policy", back_populates="tenant")
