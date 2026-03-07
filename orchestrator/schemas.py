from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Policy Schemas
class PolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    ike_version: str = "ikev2"
    encryption_algorithm: str = "aes256"
    integrity_algorithm: str = "sha256"
    dh_group: str = "modp2048"
    local_network_cidr: str
    remote_network_cidr: str
    auth_method: str = "psk"
    psk_secret: Optional[str] = None

class PolicyCreate(PolicyBase):
    pass

class Policy(PolicyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User & Auth Schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Device Schemas
class DeviceBase(BaseModel):
    hostname: Optional[str] = None
    os_type: Optional[str] = None
    public_ip: Optional[str] = None

class DeviceCreate(DeviceBase):
    enrollment_number: str
    enrollment_token: str

class DeviceAdminCreate(BaseModel):
    enrollment_number: str
    enrollment_token: str

class DeviceUpdate(BaseModel):
    public_ip: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

class Device(DeviceBase):
    id: int
    enrollment_number: str
    enrollment_token: str
    status: str
    is_active: bool
    last_seen: Optional[datetime] = None
    policy_id: Optional[int] = None
    policy: Optional[Policy] = None
    created_at: datetime

    class Config:
        from_attributes = True
