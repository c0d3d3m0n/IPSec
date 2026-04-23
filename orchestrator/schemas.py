from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any

# --- Unified Policy Schemas ---
class TargetSchema(BaseModel):
    os: List[str]
    device_groups: Optional[List[str]] = None

class AuthSchema(BaseModel):
    type: str # e.g. psk
    secret_ref: str

class CryptoConfigSchema(BaseModel):
    encryption: str
    integrity: str
    dh_group: Optional[str] = None
    pfs: Optional[bool] = None

class CryptoSchema(BaseModel):
    ike: CryptoConfigSchema
    esp: CryptoConfigSchema

    @field_validator('ike', 'esp')
    def validate_crypto(cls, v: CryptoConfigSchema):
        weak_algos = ['des', 'md5', 'rc4', '3des']
        if v.encryption.lower() in weak_algos or v.integrity.lower() in weak_algos:
            raise ValueError(f"Weak crypto algorithm detected in {v}. Use aes256/sha256 or better.")
        return v

class ConnectionSchema(BaseModel):
    name: str
    local_ip: str
    local_subnet: str
    remote_ip: str
    remote_subnet: str
    auto_start: bool = True

class IPsecPolicySchema(BaseModel):
    mode: str
    key_exchange: str
    authentication: AuthSchema
    crypto: CryptoSchema
    connections: List[ConnectionSchema]

class ExecutionSchema(BaseModel):
    retry_count: int = 3
    timeout_seconds: int = 60
    rollback_on_failure: bool = True

class ComplianceSchema(BaseModel):
    require_strong_crypto: bool = True
    require_pfs: bool = True

class UnifiedPolicyCreate(BaseModel):
    policy_id: str
    version: str
    description: Optional[str] = None
    target: TargetSchema
    ipsec_policy: IPsecPolicySchema
    execution: ExecutionSchema
    compliance: ComplianceSchema

class PolicyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    config_data: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PolicyBulkUpload(BaseModel):
    policies: List[UnifiedPolicyCreate]

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
    refresh_token: Optional[str] = None

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
    os_fingerprint: str
    agent_signature: str

class DeviceAdminCreate(BaseModel):
    enrollment_number: str
    enrollment_token: str
    pre_shared_key: Optional[str] = None

class DeviceUpdate(BaseModel):
    public_ip: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

class Device(DeviceBase):
    id: int
    enrollment_number: str
    enrollment_token: str
    os_fingerprint: Optional[str] = None
    status: str
    is_active: bool
    last_seen: Optional[datetime] = None
    policy_id: Optional[int] = None
    policy: Optional[PolicyResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceEnrollmentResponse(Device):
    cert_pem: str
    private_key_pem: str
    ca_cert_pem: str


class TOTPSetupResponse(BaseModel):
    qr_code_png_base64: str
    secret: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    totp_code: str


class TOTPVerifyResponse(BaseModel):
    verified: bool
