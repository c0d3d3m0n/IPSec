from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    
    # IPsec Configuration
    ike_version = Column(String, default="ikev2")
    encryption_algorithm = Column(String, default="aes256")
    integrity_algorithm = Column(String, default="sha256")
    dh_group = Column(String, default="modp2048")
    
    # Network Selectors
    local_network_cidr = Column(String) # The network behind the device
    remote_network_cidr = Column(String) # The network the device connects to
    
    # Authentication
    auth_method = Column(String, default="psk") # psk, pubkey
    psk_secret = Column(String, nullable=True) # Encrypted in real app
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    devices = relationship("Device", back_populates="policy")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, index=True)
    os_type = Column(String) # linux, windows, macos
    public_ip = Column(String, nullable=True)
    
    enrollment_token = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    policy = relationship("Policy", back_populates="devices")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
