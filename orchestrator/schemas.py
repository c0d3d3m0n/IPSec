from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


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
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PolicyBulkUpload(BaseModel):
    policies: List[UnifiedPolicyCreate]


# --- Tenant Schemas ---
class TenantCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"
    max_devices: int = 5
    max_users: int = 2
    contact_email: Optional[str] = None
    # First admin user for the tenant
    admin_username: str
    admin_email: str
    admin_password: str

class TenantUpdate(BaseModel):
    plan: Optional[str] = None
    max_devices: Optional[int] = None
    max_users: Optional[int] = None
    is_active: Optional[bool] = None
    contact_email: Optional[str] = None

class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    is_active: bool
    max_devices: int
    max_users: int
    contact_email: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TenantListItem(TenantResponse):
    device_count: int = 0
    user_count: int = 0
    policy_count: int = 0
    compliant_device_count: int = 0
    last_activity: Optional[datetime] = None

class TenantDetail(TenantResponse):
    users: List["UserResponse"] = []
    devices: List["DeviceWithCompliance"] = []
    policies: List[PolicyResponse] = []
    compliance_summary: Dict[str, Any] = {}

class PlatformStats(BaseModel):
    total_tenants: int = 0
    active_tenants: int = 0
    total_devices: int = 0
    active_devices: int = 0
    total_policies: int = 0
    compliance_rate: float = 0.0
    violations_today: int = 0
    api_calls_today: int = 0


# --- User & Auth Schemas ---
class UserBase(BaseModel):
    username: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "tenant_viewer"  # tenant_admin | tenant_viewer

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    tenant_id: Optional[int] = None
    is_active: bool
    totp_enabled: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserRoleUpdate(BaseModel):
    role: str  # tenant_admin | tenant_viewer

class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    role: str
    tenant_name: Optional[str] = None
    plan: Optional[str] = None
    is_active: bool
    totp_enabled: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    role: Optional[str] = None
    tenant_name: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None


# --- Device Schemas ---
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
    tenant_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DeviceWithCompliance(Device):
    latest_compliance: Optional[bool] = None

class DeviceEnrollmentResponse(Device):
    cert_pem: str
    private_key_pem: str
    ca_cert_pem: str


# --- TOTP Schemas ---
class TOTPSetupResponse(BaseModel):
    qr_code_png_base64: str
    secret: str
    provisioning_uri: str

class TOTPVerifyRequest(BaseModel):
    totp_code: str

class TOTPVerifyResponse(BaseModel):
    verified: bool
