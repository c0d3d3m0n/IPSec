# 🔐 Zero Trust Security Implementation Guide

Complete reference for the Zero Trust security model implemented in Phase 2 of the IPSec Framework.

---

## Table of Contents
1. [Zero Trust Principles](#zero-trust-principles)
2. [Architecture Overview](#architecture-overview)
3. [Component Breakdown](#component-breakdown)
4. [Cryptographic Stack](#cryptographic-stack)
5. [Setup & Configuration](#setup--configuration)
6. [Trust Scoring Model](#trust-scoring-model)
7. [Certificate Lifecycle](#certificate-lifecycle)
8. [Token Management](#token-management)
9. [Troubleshooting](#troubleshooting)

---

## Zero Trust Principles

### The 7 Core Principles

1. **Verify Explicitly**
   - Use all available data points (user, device, location, time)
   - Authenticate all requests with cryptographic proof

2. **Secure by Default**
   - Assume breach: verify everything
   - Default deny, grant only when necessary

3. **Least Privilege Access**
   - Grant minimum required permissions
   - Time-limit all access grants

4. **Assume Breach**
   - Monitor all activities
   - Detect lateral movement
   - Respond immediately

5. **Microsegmentation**
   - Break network into small zones
   - Enforce policy per connection
   - Continuous verification

6. **Monitor & Validate**
   - Continuous monitoring of device health
   - Behavioral analytics
   - Policy enforcement

7. **Secure All Access**
   - All users, devices, services secured
   - No implicit trust
   - Cryptographic proof required

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           Admin / External User                 │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼─────────┐
         │  MFA (TOTP)     │ ← Time-based One-Time Passwords
         │  + Dashboard    │
         └───────┬─────────┘
                 │
    ┌────────────▼──────────────┐
    │   Authentication Layer    │
    │ - RS256 JWT Tokens        │
    │ - Token Rotation          │
    │ - Refresh Token Tracking  │
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────────────┐
    │  Zero Trust Middleware            │
    │ - mTLS Certificate Verification   │
    │ - Trust Score Calculation         │
    │ - Threshold-based Access Control  │
    └────────────┬──────────────────────┘
                 │
    ┌────────────▼────────────────────┐
    │   Orchestrator Endpoints        │
    │  (Policies, Devices, Compliance) │
    └────────────┬────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │  Device (Agent)                      │
    │ ┌────────────────────────────────┐  │
    │ │ Device Fingerprint             │  │
    │ │ (Hostname + OS + MAC → HMAC)   │  │
    │ └──────────┬─────────────────────┘  │
    │            │                        │
    │ ┌──────────▼──────────────────────┐ │
    │ │ mTLS Client (Device Cert)       │ │
    │ │ - Persistent Certificate Storage│ │
    │ │ - Automatic Certificate Refresh │ │
    │ │ - Connection Retry Logic        │ │
    │ └──────────┬──────────────────────┘ │
    │            │                        │
    │ ┌──────────▼──────────────────────┐ │
    │ │ IPSec Policy Enforcement        │ │
    │ │ - SA Monitoring                 │ │
    │ │ - Leak Detection                │ │
    │ │ - Compliance Reporting          │ │
    │ └──────────────────────────────────┘ │
    └────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Internal Certificate Authority (CA)

**File**: `orchestrator/security/certificate_authority.py`

**Responsibility**: Issue, verify, and revoke device certificates.

**Key Operations**:

```python
# Initialize CA (one-time setup)
ca = InternalCA()
ca.initialize_ca()  # Generates keys/ca.crt, keys/ca.key

# Issue device certificate (on enrollment)
cert_pem, key_pem = ca.issue_device_certificate(
    device_id="device-001",
    cn="PROD-WIN-01",  # Common Name = device ID
    validity_days=365
)

# Verify certificate (on middleware)
is_valid = ca.verify_certificate(cert_pem)

# Revoke certificate (on compromise)
ca.revoke_certificate(cert_serial, reason="compromised")
```

**Files Used**:
- `keys/ca.crt` - CA public certificate
- `keys/ca.key` - CA private key (KEEP SECURE!)
- Database table `revoked_certificates` - Revocation registry

---

### 2. Token Manager (JWT + Refresh Tokens)

**File**: `orchestrator/security/token_manager.py`

**Responsibility**: Manage JWT access tokens and refresh tokens with secure rotation.

**Key Operations**:

```python
tm = TokenManager()

# Create access token (on login, expires 15 min)
access_token = tm.create_access_token(
    subject="admin",
    expires_delta=timedelta(minutes=15)
)

# Create refresh token (on login, expires 7 days)
refresh_token = tm.create_refresh_token(
    subject="admin",
    expires_delta=timedelta(days=7)
)

# Verify token validity
payload = tm.verify_token(access_token)

# Rotate refresh token (always get new pair)
new_access, new_refresh = tm.rotate_refresh_token(
    old_refresh_token=old_token
)
```

**Token Format**: RS256 (RSA Signature with SHA-256)

**Payload Example**:
```json
{
  "sub": "admin",
  "iat": 1712681400,
  "exp": 1712682300,
  "type": "access"
}
```

---

### 3. TOTP Manager (Admin MFA)

**File**: `orchestrator/security/totp_manager.py`

**Responsibility**: Generate and verify time-based one-time passwords (TOTP).

**Key Operations**:

```python
tm = TOTPManager()

# Generate secret for user (first-time MFA setup)
secret = tm.generate_secret()  # Base32-encoded random

# Get QR code for authenticator app
qr_base64 = tm.qr_png_base64(
    name="admin@ipsec",
    issuer="IPSec Framework"
)

# Verify TOTP code on login
is_valid = tm.verify_code(secret, user_code="123456")
```

**TOTP Algorithm**: HMAC-SHA1, 30-second window, 6-digit codes

**Supported Apps**:
- Google Authenticator
- Microsoft Authenticator
- Authy
- FreeOTP
- 1Password

---

### 4. Device Fingerprint & Attestation

**File**: `agent/security/device_fingerprint.py`

**Responsibility**: Create unique device identity and prove it during enrollment.

**Key Operations**:

```python
fp = DeviceFingerprint()

# Collect fingerprint data
fingerprint_data = fp.collect()  # (hostname, os, mac_addresses)

# Create HMAC signature proof
signature = fp.sign(pre_shared_key="MySecureToken")

# Fingerprint includes:
# - Hostname (system-wide identifier)
# - OS Version (platform specifics)
# - MAC Addresses (physical identity)
```

**Fingerprint Hash**: SHA-512(hostname + os_version + mac)

**Attestation Signature**: HMAC-SHA512(pre_shared_key, fingerprint_hash)

---

### 5. mTLS Client

**File**: `agent/security/mtls_client.py`

**Responsibility**: Secure HTTP client using mTLS for agent→orchestrator communication.

**Key Features**:

```python
client = MTLSClient(
    cert_path="/etc/ipsec/device.crt",
    key_path="/etc/ipsec/device.key",
    ca_cert_path="/etc/ipsec/ca.crt",
    orchestrator_url="https://orchestrator.example.com"
)

# All requests use mTLS automatically
response = client.post("/api/compliance/heartbeat", {...})

# Automatic retry on transient failures
# Rate limiting aware (respects Retry-After headers)
# Zero-trust denial handling (403 → restricted mode)
```

**Connection Features**:
- Automatic certificate verification
- Retry logic: 1s → 2s → 4s delays
- Distinguishes permanent errors (SSL) vs. transient (timeout)
- Graceful degradation on zero-trust denial

---

### 6. Trust Evaluator (Behavioral Scoring)

**File**: `orchestrator/security/trust_evaluator.py`

**Responsibility**: Calculate device trust score based on multiple factors.

**Algorithm**:

```
Initial Score: 100 points

Deductions:
├─ Certificate CN mismatch: -100 (device ID mismatch) → DENY
├─ Certificate revoked: -100 (compromised) → DENY
├─ Last seen > 5 minutes: -30 (offline suspicious)
├─ Source IP changed: -40 (possible compromise)
├─ Off-hours access: -10 (unusual timing)
├─ Compliance failures: -25 (policy violations)
├─ Leak detected: -50 (data exfiltration attempt)
└─ No active SA: -20 (tunnel not established)

Decision:
├─ Score ≥ 70: ALLOW (full access)
├─ 40 ≤ Score < 70: RESTRICT (limited endpoints)
└─ Score < 40: DENY (connection blocked)
```

**Example Calculation**:

```
Device Status:
- Certificate CN: ✓ Matches device ID
- Certificate revoked: ✗ No
- Last seen: 3 minutes ago ✓
- Source IP: Same as previous ✓
- Off-hours: 11 PM (outside 6-18) ✗ weekend
- Compliance: ✓ All checks pass
- Leak detected: ✗ No
- Active SA: ✓ 3 tunnels up

Score Calculation:
100 (base)
-  10 (off-hours) = 90
-  0 (no other deductions)
= 90 ALLOW
```

---

### 7. Zero Trust Middleware

**File**: `orchestrator/middleware/zero_trust.py`

**Responsibility**: Intercept all requests and enforce mTLS + trust verification.

**Request Flow**:

```
HTTP Request
    ↓
[1] Extract client certificate from request
    ├─ No cert? → 401 Unauthenticated
    └─ Has cert?
        ↓
[2] Verify certificate chain (CA signature)
    ├─ Invalid? → 401 Unauthenticated
    └─ Valid?
        ↓
[3] Extract device_id from cert Common Name
        ↓
[4] Calculate trust score
        ├─ Score ≥ 70?
        │  └─ YES: ALLOW (proceed to endpoint)
        │
        ├─ 40 ≤ Score < 70?
        │  └─ YES: RESTRICT
        │     (allow only safe endpoints like heartbeat)
        │
        └─ Score < 40?
           └─ NO: 403 Forbidden (zero-trust denial)
```

**Exempt Endpoints** (no certificate required):
- `POST /api/auth/login` - Admin login
- `POST /api/devices/enroll` - Device enrollment
- `GET /docs` - Swagger documentation
- `GET /openapi.json` - API schema

---

## Cryptographic Stack

### Algorithms & Key Sizes

| Component | Algorithm | Key Size | Purpose |
|-----------|-----------|----------|---------|
| Device Certificates | RSA | 4096-bit | Device identity & mTLS |
| Certificate Signing | SHA-512 | - | CA signature verification |
| Access Tokens | RS256 (RSA+SHA256) | 4096-bit | JWT signature |
| Refresh Tokens | HMAC-SHA512 | 512-bit | Token integrity |
| Fingerprint Attestation | HMAC-SHA512 | 512-bit | Device proof-of-possession |
| Audit Log Chain | SHA-512 | - | Tamper detection |
| TOTP | HMAC-SHA1 | 128-bit | Admin MFA |

### Key Storage

**CA Keys** (Orchestrator):
- `keys/ca.crt` - Public CA certificate (shared with agents)
- `keys/ca.key` - Private CA key (NEVER SHARE! 🔒)
  - Protect with: filesystem permissions (0600), encryption at rest
  - Backup to: Secure vault (AWS KMS, Azure Key Vault)

**Device Keys** (Agent):
- `~/.ipsec/device.crt` - Device certificate
- `~/.ipsec/device.key` - Device private key
  - Protect with: filesystem permissions (0600)
  - Backup to: Secure location with encryption

---

## Setup & Configuration

### Phase 1: Initialize CA

```bash
cd orchestrator

# Ensure keys/ directory exists
mkdir -p keys

# Run CA initialization
python -c "
from security.certificate_authority import InternalCA
ca = InternalCA()
ca.initialize_ca()
print('CA initialized successfully')
print('- keys/ca.crt: CA public certificate')
print('- keys/ca.key: CA private key (keep secure!)')
"
```

**Result**:
- `keys/ca.crt` - CA certificate (share with devices)
- `keys/ca.key` - CA private key (keep on orchestrator only)

### Phase 2: Configure Agent Pre-Shared Keys

Create pre-shared keys for device enrollment attestation:

```bash
# Generate secure pre-shared key for each device
python -c "
import secrets
psk = secrets.token_urlsafe(32)
print(f'Device 1 PSK: {psk}')
"

# Output (example):
# Device 1 PSK: AbCdEfG...
```

**Store in Dashboard**:
1. Dashboard → Devices → Pre-activate Device
2. Enter: Enrollment Number, Secret Activation Token (this is the PSK)
3. Agent will use this same token to sign its fingerprint

### Phase 3: Configure Environment Variables (Agent)

```bash
# On device/agent machine
export ORCHESTRATOR_URL="https://orchestrator.example.com:8000"
export PRE_SHARED_KEY="AbCdEfG..."  # From Phase 2
export POLL_INTERVAL=60             # Heartbeat interval (seconds)
export PROTECTED_SUBNETS="10.0.0.0/8"

# Start agent
python -m agent.main
```

### Phase 4: Configure Middleware Trust Thresholds

Edit `orchestrator/security/trust_evaluator.py`:

```python
# Customize trust score calculation
class TrustEvaluator:
    ALLOW_THRESHOLD = 70       # ≥ this = ALLOW (default)
    RESTRICTED_THRESHOLD = 40  # 40-69 = RESTRICT

    # Deduction amounts
    LAST_SEEN_DEDUCTION = 30       # If > 5 min old
    SOURCE_IP_DEDUCTION = 40       # If IP changed
    OFF_HOURS_DEDUCTION = 10       # If outside 6-18
    COMPLIANCE_DEDUCTION = 25      # If any check failed
    LEAK_DEDUCTION = 50            # If leak detected
    NO_SA_DEDUCTION = 20           # If no active tunnels
```

---

## Trust Scoring Model

### Detailed Scoring Breakdown

#### Factor 1: Certificate Validity (Critical)

**Check**: Certificate CN matches device_id?

```
If mismatch → Score set to 0 (DENY)

Example:
  Device ID: "device-001"
  Certificate CN: "device-002"
  Result: DENY (possible certificate swapping attack)
```

**Protected Against**: Certificate spoofing, device impersonation

#### Factor 2: Last Activity Recency (Moderate)

**Check**: When was last heartbeat/request received?

```
If > 5 minutes ago:
  Score -= 30 points

Timeline:
  0-5 min:   No deduction
  5-10 min:  -30 points
  10+ min:   -30 points (escalate to RESTRICT/DENY)

Rationale: Stale devices might be offline/compromised
```

**Protected Against**: Zombie devices, network outages

#### Factor 3: Source IP Consistency (Major)

**Check**: Is request from same IP as last request?

```
If different:
  Score -= 40 points

Examples:
  ✓ 192.168.1.100 → 192.168.1.100 (same) = OK
  ✗ 192.168.1.100 → 10.0.0.50 (different) = -40

Rationale: IP changes suggest device moved/network change
Note: VPN, mobile clients expected to change IPs
```

**Protected Against**: MITM attacks, device compromise at different location

**Whitelist IPs** (if VPN/mobile expected):

```python
# In trust_evaluator.py
ALLOWED_IP_RANGES = [
    "10.0.0.0/8",          # Corporate VPN
    "203.0.113.0/24",      # Remote office
]

def evaluate_ip_change(source_ip):
    if any(ip_in_range(source_ip, r) for r in ALLOWED_IP_RANGES):
        return 0  # No deduction for whitelisted ranges
    else:
        return 40  # Deduct for unexpected IPs
```

#### Factor 4: Off-Hours Access (Minor)

**Check**: Is request during business hours?

```
If outside 6 AM - 6 PM weekday:
  Score -= 10 points

Examples:
  ✓ Tuesday 10:00 AM = OK
  ✗ Tuesday 11:00 PM = -10 points
  ✗ Sunday 10:00 AM = -10 points (weekend)

Rationale: Off-hours access unusual for most devices
```

**Customize**:

```python
def evaluate_off_hours(timestamp):
    hour = timestamp.hour
    weekday = timestamp.weekday()  # 0=Mon, 6=Sun
    
    WORK_HOURS = (6, 18)  # 6 AM to 6 PM
    WORK_DAYS = (0, 4)    # Mon-Fri
    
    if hour < WORK_HOURS[0] or hour >= WORK_HOURS[1]:
        return 10  # Outside work hours
    if weekday >= 5:  # Saturday or Sunday
        return 10
    return 0
```

#### Factor 5: Compliance Status (Major)

**Check**: Device passes all compliance checks?

```
If ANY compliance check failed:
  Score -= 25 points

Compliance Checks:
  ✓ Firewall enabled
  ✓ Antivirus running
  ✓ Disk encryption enabled
  ✓ Required IPsec SAs active
  ✓ OS patches current
  ✗ Any failed = -25 points
```

#### Factor 6: Data Leak Detection (Critical)

**Check**: Any unauthorized data flows detected?

```
If leak detected:
  Score = 0 (DENY immediately)

Leak = Traffic to protected subnet NOT in IPsec tunnel

Example:
  Policy: 10.0.0.0/8 ↔ 192.168.1.0/24 (must use tunnel)
  
  ✗ Unencrypted packet: 10.0.0.10 → 192.168.1.50
  Result: LEAK DETECTED → Score 0 → DENY
```

#### Factor 7: Active SA Presence (Moderate)

**Check**: Device has at least one active IPsec tunnel?

```
If NO active SA:
  Score -= 20 points

Example:
  Device has policy assigned
  but no IPsec tunnel negotiated
  = Device likely failed to apply policy
  = -20 points deduction
```

---

## Certificate Lifecycle

### Phase 1: Generation (On Enrollment)

```python
# Agent initiates enrollment
device_fp = DeviceFingerprint().collect()
signature = HMAC-SHA512(pre_shared_key, device_fp)

# Send to orchestrator
POST /api/devices/enroll
{
  "device_id": "device-001",
  "os_fingerprint": "...",
  "agent_signature": "..."
}

# Orchestrator verifies signature
if not verify_hmac_sha512(stored_psk, fpdata, signature):
    return 401 Unauthorized

# Issue certificate
cert, key = CA.issue_device_certificate(device_id)
```

### Phase 2: Storage (On Agent)

```python
# Agent persists certificate
cert_path = "~/.ipsec/device.crt"
key_path = "~/.ipsec/device.key"

# Protect with filesystem permissions
chmod 0600 ~/.ipsec/device.key

# On subsequent startups, load existing cert
loaded_cert = load_certificate(cert_path)
```

### Phase 3: Usage (In mTLS Communication)

```
Agent Request:
  POST https://orchestrator/api/...
  [TLS]
    Client Certificate: ~/.ipsec/device.crt
    Client Key: ~/.ipsec/device.key

Orchestrator Verification:
  [1] Verify cert signed by CA
  [2] Extract device_id from cert CN
  [3] Check revocation list
  [4] Calculate trust score
```

### Phase 4: Refresh (On Expiry)

```python
# Monitor certificate expiry
cert = load_certificate(cert_path)
if cert.not_valid_after < now() + timedelta(days=30):
    # Certificate expiring within 30 days
    # Request new certificate
    POST /api/devices/refresh-certificate
    
    # Receive new certificate
    # Store as backup, switch over gracefully
```

### Phase 5: Revocation (On Compromise)

```python
# If device compromised
POST /api/devices/{id}/revoke-certificate
{
  "reason": "compromised",
  "revoke_date": "2024-04-09T12:00:00Z"
}

# Orchestrator:
# [1] Add cert_serial to revoked_certificates table
# [2] Revocation takes effect immediately
# [3] All future mTLS connections from this cert → 403
# [4] Agent must re-enroll to get new certificate
```

---

## Token Management

### Access Token Lifecycle

```
Duration: 15 minutes
Type: RS256 JWT
Used for: API requests
Contains: user/device ID, issue time, expiry

Timeline:
  [T+0] Issue access_token
        └─ User makes API request with token
  [T+10min] Token valid, request succeeds
  [T+15min] Token expires
            └─ 401 Unauthorized response
            └─ Client must refresh
  [T+20min] Token is stale (no longer accepted)
```

### Refresh Token Lifecycle

```
Duration: 7 days
Type: Opaque token (stored in DB as hash)
Used for: Obtaining new access_token pair
Contains: Stored as HMAC-SHA512 hash

Timeline:
  [Day 0] Issue refresh_token
  [Day 3] Device refreshes token
          ├─ Verify refresh_token in database
          ├─ Issue NEW access + refresh pair
          ├─ Rotate old refresh_token (mark revoked)
          └─ Return new pair to device
  [Day 7] Original refresh_token expires
          └─ New refresh must be obtained via login
```

### Token Rotation (Automatic)

```python
# Every time device uses refresh token, it gets new pair
def rotate_tokens(old_refresh_token):
    # [1] Verify old refresh token
    if not verify_refresh_token(old_refresh_token):
        raise 401 Unauthorized
    
    # [2] Mark old token as revoked
    revoke_refresh_token(old_refresh_token)
    
    # [3] Issue new pair
    new_access = create_access_token(device_id)
    new_refresh = create_refresh_token(device_id)
    
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "expires_in": 900  # 15 min
    }
```

**Benefits**:
- Reduces window if token leaked
- Tracks active sessions in database
- Can revoke sessions immediately if needed

---

## Troubleshooting

### Certificate Verification Failures

**Symptom**: `SSL: CERTIFICATE_VERIFY_FAILED` in agent logs

**Causes & Solutions**:

1. **CA certificate path incorrect**
   ```bash
   # Verify CA cert exists
   ls -la keys/ca.crt
   
   # Update agent config
   export CA_CERT_PATH="/full/path/to/keys/ca.crt"
   ```

2. **CA cert outdated on agent**
   ```bash
   # Copy fresh CA cert from orchestrator
   scp orchestrator:/keys/ca.crt ~/.ipsec/ca.crt
   chmod 644 ~/.ipsec/ca.crt
   ```

3. **Certificate not signed by CA**
   ```bash
   # Verify certificate chain
   openssl x509 -in device.crt -text -noout | grep Issuer
   
   # Should show: CN = IPSec Internal CA
   ```

### Trust Score Too Low

**Symptom**: Device gets 403 Forbidden with `Zero Trust: Access Denied`

**Debug Steps**:

```bash
# 1. Check certificate validity
openssl x509 -in device.crt -text -noout
# Look for:
#   Issuer: CN = IPSec Internal CA
#   Subject: CN = device-001
#   Valid from: ... to ...

# 2. Check if certificate revoked
curl -H "Authorization: Bearer $TOKEN" \
  http://orchestrator:8000/api/devices/device-001/certificate-status

# 3. Monitor trust score in real-time
# Add logging to orchestrator/middleware/zero_trust.py
logger.info(f"Device {device_id}: score={score}, factors={factors}")

# 4. Common reasons for low score:
#   - Certificate CN mismatch (typo in device_id?)
#   - Last seen > 5 minutes ago (network timeout?)
#   - Source IP changed (VPN? Mobile?)
#   - Off-hours access (expected? adjust threshold)
#   - Compliance failure (check which check failed)
```

### Token Refresh Failing

**Symptom**: `401 Unauthorized` when refreshing token

**Solutions**:

```bash
# 1. Verify refresh token still valid
curl -X POST http://orchestrator:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'

# Response:
# 401 = Token expired (re-login needed)
# 422 = Malformed token (invalid format)

# 2. If token expired, re-login
curl -X POST http://orchestrator:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "..."}' \
  -d '{"code": "123456"}'  # Include TOTP if enabled

# 3. If still failing, check DB
# SELECT * FROM refresh_tokens WHERE is_revoked = false;
```

### Enrollment Attestation Failing

**Symptom**: Device enrollment returns `400 Bad Request: Invalid signature`

**Causes & Solutions**:

1. **Pre-shared key mismatch**
   ```bash
   # Check agent has correct PSK
   env | grep PRE_SHARED_KEY
   
   # Should match what was entered in Dashboard
   # If different, env var not set correctly:
   export PRE_SHARED_KEY="exact-token-from-dashboard"
   ```

2. **Fingerprint collection issue**
   ```bash
   # Debug fingerprint on device
   python -c "
   from agent.security.device_fingerprint import DeviceFingerprint
   fp = DeviceFingerprint()
   data = fp.collect()
   print(f'Hostname: {data[0]}')
   print(f'OS: {data[1]}')
   print(f'MACs: {data[2]}')
   "
   
   # Ensure output looks reasonable
   ```

3. **Time skew**
   ```bash
   # Ensure device time is accurate within 5 seconds
   date
   ntpdate -u ntp.ubuntu.com  # Sync time
   ```

### mTLS Connection Refused

**Symptom**: Agent logs `Connection refused` or `timed out`

**Troubleshooting**:

```bash
# 1. Verify orchestrator is running
curl -v http://orchestrator:8000/docs

# 2. Verify firewall allows connection
# Windows:
netsh advfirewall firewall add rule name="IPSec" dir=out action=allow protocol=tcp localport=8000

# Linux:
sudo ufw allow 8000/tcp

# 3. Check firewall rules on orchestrator
# Ensure port 8000 is LISTENING
netstat -tlnp | grep 8000
ss -tlnp | grep 8000  # On newer systems

# 4. Verify certificate paths
ls -la ~/.ipsec/device.*
ls -la keys/ca.crt

# 5. Test mTLS connection manually (Linux)
openssl s_client -cert ~/.ipsec/device.crt \
  -key ~/.ipsec/device.key \
  -CAfile keys/ca.crt \
  -connect orchestrator:8000

# If succeeds, shows certificate exchange (verbose)
```

---

## References

- [RFC 6234 - US Secure Hash and SHA-3](https://tools.ietf.org/html/rfc6234)
- [RFC 7519 - JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 5869 - HMAC-based Extract-and-Expand Key Derivation](https://tools.ietf.org/html/rfc5869)
- [TOTPspec](https://tools.ietf.org/html/rfc6238)
- [NIST SP 800-207 - Zero Trust Architecture](https://csrc.nist.gov/publications/detail/sp/800-207/final)
