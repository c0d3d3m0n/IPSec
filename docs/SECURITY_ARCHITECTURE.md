# 🛡️ Security Architecture & Cryptography Reference

Deep technical reference for the security components, cryptographic algorithms, and threat models.

---

## Table of Contents
1. [Security Layers](#security-layers)
2. [Threat Model](#threat-model)
3. [Cryptographic Algorithms](#cryptographic-algorithms)
4. [Key Management](#key-management)
5. [Attack Vectors & Mitigations](#attack-vectors--mitigations)
6. [Security Assumptions](#security-assumptions)
7. [Incident Response](#incident-response)

---

## Security Layers

### Layer 1: Network Transport (TLS/mTLS)

**Purpose**: Confidentiality and integrity of all network communications

**Implementation**:
- TLS 1.3+ (encrypted transport)
- mTLS for device authentication (client certificate required)
- Certificate pinning (CA cert verification on agent)

**Protects Against**:
- Passive eavesdropping
- Man-in-the-middle (MITM) attacks
- Network packet tampering

---

### Layer 2: Authentication

**Purpose**: Verify identity of users and devices

**Methods**:

**For Admins**:
- Username + Password (at least 12 characters)
- TOTP MFA (Time-based One-Time Passwords)
- Rate limiting (10 attempts/minute)
- Account lockout (5 failed attempts → 15 minute lockout)

**For Devices**:
- Device Fingerprint (hostname + OS + MAC address)
- HMAC-SHA512 attestation signature (proof of possession)
- X.509 device certificate (RSA 4096-bit)

**Protects Against**:
- Credential brute-force attacks
- Unauthorized device enrollment
- Device impersonation

**Strength Summary**:
```
Admin Authentication = Password + TOTP
                     = Something you know + Something you have
                     = 2-factor authentication

Device Authentication = Fingerprint + Certificate
                      = Hardware identity + Cryptographic proof
                      = 2-factor authentication (implicit)
```

---

### Layer 3: Authorization & Access Control

**Purpose**: Enforce least-privilege access

**Mechanisms**:

**Token-Based Access**:
- Access tokens expire after 15 minutes
- Refresh tokens tracked in database
- Revocation possible at any time

**Zero Trust Trust Scoring**:
- Continuous evaluation (per request)
- Multi-factor scoring:
  - Certificate validity (mandatory)
  - Device location (IP address consistency)
  - Device behavior (activity recency)
  - System compliance (health checks)
  - Network behavior (leak detection)

**Rate Limiting**:
- 5 requests/min: Device enrollment
- 10 requests/min: Admin login
- 120 requests/min: Heartbeat submissions
- 60 requests/min: Compliance reports

**Protects Against**:
- Privilege escalation
- Lateral movement (microsegmentation)
- DoS attacks (rate limiting)
- Stolen token abuse (short expiry + revocation)

---

### Layer 4: Data Protection

**Purpose**: Confidentiality and integrity of data in transit and at rest

**In Transit**:
- IPsec encryption (AES-GCM-256)
- IPsec integrity (SHA-512)
- TLS encryption (AES-256-GCM)

**At Rest**:
- Database: Encryption defined by DB provider
- Credentials: Hashed with bcrypt (admin passwords)
- Tokens: Hashed with SHA-512 (refresh tokens in DB)
- Private keys: Protected with filesystem permissions (0600)

**Protects Against**:
- Data interception
- Data tampering
- Credential compromise

---

### Layer 5: Audit & Accountability

**Purpose**: Detect breaches and trace activities

**Audit Trail**:
- All events logged with timestamps
- Immutable chain (SHA-512 hashing)
- Cryptographic signatures (RSA)
- Export capability (investigation)

**Compliance Monitoring**:
- Heartbeat checks device is running
- Compliance reports verify policies active
- Leak detection monitors data flows
- SA monitoring verifies encryption active

**Protects Against**:
- Undetected breaches
- Insider threats
- Regulatory non-compliance

---

## Threat Model

### Threat: Unauthorized Device Enrollment

**Attack**: Attacker tries to add rogue device

**Prerequisites**:
- Knowing enrollment number + token
- Network access to orchestrator

**Mitigation**:
1. Enrollment token strong (32 chars, random)
2. HMAC-SHA512 signature required (proof of possession of PSK)
3. Physical device fingerprint included (not replicable)
4. Rate limiting (5 enrollments/min)

**Residual Risk**: LOW (requires stolen PSK + physical device)

---

### Threat: Device Certificate Theft

**Attack**: Attacker steals device.crt and device.key

**Prerequisites**:
- Physical or network access to device
- Root/admin privileges

**Mitigation**:
1. Certificates stored in restricted directory (~/.ipsec, perms 0600)
2. Can be revoked immediately if suspected theft
3. Trust score penalties for IP/behavior anomalies
4. Certificate expiry forces re-enrollment (365 days)

**Residual Risk**: MEDIUM
- Attacker can impersonate device until revocation
- But behavioral/IP mismatches trigger restrictions

**Recovery**:
1. Revoke compromised certificate
2. Re-enroll device (gets new certificate)
3. Review audit logs for unauthorized access

---

### Threat: Token Theft (JWT Access Token)

**Attack**: Attacker intercepts access token (e.g., via MITM)

**Prerequisites**:
- TLS compromise (highly unlikely)
- Token logged in plaintext somewhere

**Mitigation**:
1. Short expiry (15 minutes)
2. HTTPS only (TLS 1.3+)
3. Token stored in memory only (not persisted)
4. Only accessed over secure channels

**Residual Risk**: LOW
- Narrow time window (15 min)
- Requires active MITM (difficult)

**Recovery**:
1. If detected, revoke all tokens for user
2. Force user to re-login
3. Change password if credentials compromised

---

### Threat: Refresh Token Theft

**Attack**: Attacker steals refresh token (stored in DB)

**Prerequisites**:
- Database compromise
- Network breach leaking tokens from transit

**Mitigation**:
1. Refresh tokens hashed with SHA-512 (not plaintext)
2. Tokens rotated on every use (old token revoked)
3. Expiry after 7 days (limits window)
4. Can be revoked immediately if suspected

**Residual Risk**: MEDIUM
- Hash stored in DB (not plaintext)
- But hash can be used if DB hashed with weak algo
- Rotation limits damage window

**Recovery**:
1. Revoke all refresh tokens for affected user/device
2. Force re-login
3. Investigate database breach

---

### Threat: Man-in-the-Middle (MITM) Attack

**Attack**: Attacker intercepts and modifies communication

**Prerequisites**:
- Network position to intercept traffic
- Ability to forge TLS certificates

**Mitigation**:
1. mTLS (both sides authenticate via certificates)
2. Certificate pinning (agent verifies CA cert)
3. Device fingerprint prevents device swapping
4. All traffic encrypted (AES-256-GCM)

**Residual Risk**: VERY LOW
- Both client and server authenticate
- Certificate chain verification
- Fingerprint validation

---

### Threat: Policy Tampering

**Attack**: Attacker modifies assigned policies

**Prerequisites**:
- Database access
- Compromised admin account

**Mitigation**:
1. Audit trail of all policy changes
2. Cryptographic signatures on policies
3. Access control (admin role only)
4. Compliance monitoring detects policy changes daily

**Residual Risk**: MEDIUM
- Requires admin compromise
- But detected within 24 hours via compliance reports

---

### Threat: Lateral Movement

**Attack**: Attacker uses compromised device to access network

**Prerequisites**:
- Device compromise
- Access to corporate network

**Mitigation**:
1. IPsec tunnel mandatory (unencrypted traffic detected)
2. Leak detection (unauthorized flows flagged)
3. Zero trust scoring (behavioral anomalies reduce score)
4. Microsegmentation (each device has isolated policy)

**Residual Risk**: LOW
- Multiple detection vectors
- Leak detection catches unencrypted flows

---

## Cryptographic Algorithms

### Algorithm Selection Rationale

| Algorithm | Purpose | Key Size | Security Level | Notes |
|-----------|---------|----------|---|-------|
| RSA | Device cert signing | 4096-bit | 128-bit | Post-quantum resistant (NIST recommends 2048+ for modern) |
| SHA-512 | Hashing | - | 256-bit | NIST approved, fast on 64-bit CPU |
| HMAC-SHA512 | Fingerprint attestation | 512-bit | 256-bit | Message authentication code |
| AES-GCM | IPsec payload encryption | 256-bit | 128-bit | Authenticated encryption |
| RS256 | JWT signature | 4096-bit | 128-bit | Industry standard for JWTs |
| TOTP | Admin MFA | 128-bit | 64-bit TOTP | Time-based, standard algorithm |
| bcrypt | Admin password hashing | - | Variable | Work factor 12, resistant to GPU attacks |

### Algorithm Strength Analysis

**Strong** (suitable for 10+ year confidentiality):
- RSA-4096 with SHA-512
- AES-256-GCM
- HMAC-SHA512

**Adequate** (suitable for 5-10 year confidentiality):
- TOTP (MFA, not crypto)
- bcrypt (password hashing)

**Weak** (not recommended for new use):
- AES-GCM-128 (only 64-bit security margin)
- SHA-256 (128-bit security, sufficient but not strong)

---

## Key Management

### CA Key Lifecycle

**Storage**:
```
Location: orchestrator/keys/ca.key
Permissions: 0600 (root only)
Backup: Encrypted vault (AWS KMS, Azure Key Vault)
Access: Orchestrator process only
```

**Protection**:
```yaml
At Rest:
  - Filesystem permissions restrict read
  - Optional: Encrypt with TPM or HSM

In Transit:
  - Never transmitted over network
  - Never logged
  - Never backed up unencrypted

In Memory:
  - Loaded once on orchestrator startup
  - Never swapped to disk
  - Cleared on shutdown
```

**Rotation** (every 5 years):
```python
# Generate new CA
new_ca = InternalCA()
new_ca.initialize_ca()  # Creates new ca.key/ca.crt

# Keep old CA active temporarily (grace period)
# Issue transitional certs signed by both old + new

# After migration (6 months):
# Archive old CA key securely
# Delete from production environment
```

### Device Certificate Lifecycle

**Issuance** (on enrollment):
```bash
[Agent]
  1. Collect device fingerprint
  2. Create HMAC signature (proof of possession)
  3. Send to orchestrator with enrollment request

[Orchestrator]
  1. Verify HMAC signature
  2. Check device not already enrolled
  3. Generate RSA 4096-bit keypair
  4. Create X.509 certificate (365 day validity)
  5. Sign with CA key
  6. Return cert + key + CA cert to agent
  7. Store cert reference in database

[Agent]
  1. Persist cert to ~/.ipsec/device.crt (perms 0644)
  2. Persist key to ~/.ipsec/device.key (perms 0600)
```

**Usage** (in mTLS):
```bash
[Agent]
  1. Load cert + key from ~/.ipsec/
  2. Present to orchestrator during TLS handshake
  3. Orchestrator verifies cert chain

[Orchestrator mTLS Middleware]
  1. Extract client certificate from TLS peer
  2. Verify CA signature (cert signed by trusted CA)
  3. Check certificate not revoked
  4. Extract device_id from certificate CN
  5. Attach to request for business logic
```

**Refresh** (before expiry):
```bash
[Agent periodically]
  1. Check certificate expiry
  2. If expires within 30 days:
     POST /api/devices/{id}/refresh-certificate
  3. Orchestrator issues new cert
  4. Agent stores as backup + switches over
```

**Revocation** (on compromise):
```bash
[If certificate suspected compromised]
  POST /api/devices/{id}/revoke-certificate
  {
    "reason": "compromised",
    "timestamp": "2024-04-09T12:00:00Z"
  }

[Orchestrator]
  1. Add cert_serial to revoked_certificates table
  2. Mark in audit log
  3. All future mTLS with this cert → 401

[Agent]
  1. Future enrollments get new certificate
  2. Any in-flight requests fail
  3. Automatic retry with new cert (if re-enrolled)
```

---

## Attack Vectors & Mitigations

### Vector 1: Brute Force Attack (Admin Password)

**Attack Flow**:
```
Attacker
  ↓
[Try] admin / password123
[Rate Limited] 10 attempts/minute
[After 5 fails] Account locked for 15 minutes
[Attacker waits] ...
[Continue] Retry password attempt
[Rate Limited Again] Only 10 attempts available
```

**Mitigation Layers**:
1. Rate limiting (10/min)
2. Account lockout (5 fails → 15 min lock)
3. MFA required (if enabled)
4. Strong password policy recommended

**Residual Time To Crack**: 
- Without MFA: ~480 days (worst case: 5 attempts × 10/min × very weak password)
- With MFA: Impossible in practical time (also need totp code)

---

### Vector 2: Certificate Replay

**Attack Flow**:
```
Attacker steals device.crt + device.key
  ↓
[Impersonate] device-001 to orchest rator
  ↓
[Server verification]
  - Certificate valid? YES
  - Certificate signed by CA? YES
  - Certificate revoked? NO
  - Trust score OK? ... DEPENDS
```

**Mitigation Layers**:
1. Source IP mismatch detection (-40 score if changed)
2. Behavior anomalies (access patterns, off-hours)
3. Leak detection (unencrypted traffic from "device")
4. Certificate expiry (365 days limit)
5. Immediate revocation if detected

**Residual Risk**: MEDIUM
- Attacker can operate for minutes/hours before detected
- But limited by behavioral scoring
- Mitigated by quick revocation

---

### Vector 3: Database Breach (Hashed Tokens Stolen)

**What's in Database**:
```
refresh_tokens table:
├─ token_hash: SHA-512(token)  (not plaintext)
├─ device_id: "device-001"
├─ expires_at: "2024-04-16T08:00:00Z"
└─ is_revoked: false

users table:
├─ password: bcrypt(password, rounds=12)  (not plaintext)
├─ totp_secret: encrypted (not plaintext)
└─ ...
```

**Attacker Gets**:
```
❌ Plaintext tokens (not stored)
❌ Plaintext passwords (hashed with bcrypt)
❌ TOTP secrets (encrypted)
✓ Token hashes (SHA-512)
```

**Mitigation**:
1. Tokens are hashes (not reversible)
2. Attacker can't directly use them
3. Expiration limits window (7 days for refresh tokens)
4. Revocation possible at any time
5. Database encryption at rest (provider feature)

---

### Vector 4: Policy Tempering

**Attack Flow**:
```
Attacker compromises admin account
  ↓
[Modifies] Policy "Production-to-DR"
  └─ Changes dest_subnet  from "192.168.0.0/16" to "10.0.0.0/8"
  └─ Changes encryption from "AES-256" to "AES-128"
  ↓
[Devices receive] Modified policy
  ↓
[Compliance check] Detects policy changed
  └─ Audit log recorded
  └─ Alert generated
```

**Mitigation**:
1. Audit trail (all changes logged)
2. Compliance monitoring (detects changes daily)
3. Alerts triggered
4. Manual review required for policy changes (recommended)

---

## Security Assumptions

### Assumptions We Make (Must Be True)

1. **Authenticator app is secure**
   - TOTP running on trusted device
   - Not compromised by malware
   - If violated: Attacker can forge TOTP codes

2. **Private keys stay private**
   - CA key protected on orchestrator
   - Device keys protected on agents
   - If violated: Can impersonate any device/CA

3. **Filesystem permissions enforced**
   - OS respects 0600 permissions
   - Process can't be accessed by other users
   - If violated: Anyone can steal private keys

4. **TLS is cryptographically strong**
   - TLS 1.3+ implementation is correct
   - No middlebox tampering
   - If violated: MITM attacks possible

5. **Administrator is trusted**
   - Won't abuse privileges
   - Won't create bogus policies
   - If violated: Insider threat possible

### Assumptions We DON'T Make

❌ **Perfect operational security**
- We assume compromise is possible
- Mitigations in place for each component

❌ **Network security**
- We assume network can be compromised
- All traffic encrypted (AES-256-GCM)
- Device authentication required (mTLS)

❌ **Device is not compromised**
- We detect leaks if device is compromised
- Trust score reduced for suspicious behavior
- Revocation possible if detected

---

## Incident Response

### Scenario 1: Admin Password Compromised

**Indicators**:
- Unauthorized policy changes in audit log
- Failed login attempts from unknown IP
- Unexpected device enrollments

**Response**:
1. **Immediate**: Revoke all admin tokens
   ```bash
   # Force all admins to re-login
   DELETE FROM refresh_tokens WHERE user_id = admin_id;
   ```

2. **1 hour**: Reset admin password
   ```bash
   # Force change at next login
   UPDATE users SET password_changed_required = true WHERE id = admin_id;
   ```

3. **2 hours**: Review audit logs
   ```bash
   # Check for unauthorized changes
   SELECT * FROM audit_logs 
   WHERE actor = 'admin' 
   AND timestamp > '2024-04-09T12:00:00Z'
   ```

4. **1 day**: Enable MFA (if not already)
5. **1 week**: Security review of compromised admin account

---

### Scenario 2: Device Certificate Compromised

**Indicators**:
- IP mismatch alerts
- Off-hours access
- Leak detection alerts
- Trust score drops suddenly

**Response**:
1. **Immediate**: Revoke certificate
   ```bash
   POST /api/devices/{device_id}/revoke-certificate
   ```

2. **5 minutes**: Investigate source IPs
   ```bash
   # Where did compromise come from?
   SELECT * FROM audit_logs 
   WHERE resource = 'device-001' 
   AND timestamp BETWEEN now() - interval '1 hour' AND now()
   ```

3. **1 hour**: Isolate device (optional)
   ```bash
   # Temporarily prevent device from accessing policies
   UPDATE devices SET disabled = true WHERE id = 'device-001';
   ```

4. **2 hours**: Re-enroll device with new certificate
   - Agent will automatically request new cert
   - Verify enrollment signature valid

5. **1 day**: Root cause analysis
   - How was cert stolen?
   - Was device actually compromised?
   - Any other devices affected?

---

### Scenario 3: Orchestrator Breached

**Indicators**:
- Unauthorized policy changes
- Multiple device certificates issued
- Tokens exposed
- Database compromise detected

**Response** (CRITICAL):

1. **Immediate**: Isolate orchestrator
   - Stop all network connections
   - Preserve logs for forensics

2. **Take database offline**
   - No new policies issued
   - Devices continue operating (cached policies)
   - Backups preserved

3. **Deploy clean copy**
   - Restore from previous backup (before breach)
   - Rotate all secrets
   - Issue new ca.key/ca.crt

4. **Revoke all certificates**
   - All devices issued certs during compromise
   - Force re-enrollment

5. **Reset all tokens**
   - Delete all JWT tokens
   - Force all admins to re-login
   - Force all devices to re-enroll

---

## Monitoring Security Metrics

### KPIs to Track

| Metric | Target | Alert If |
|--------|--------|----------|
| Failed login attempts | < 5/hour | > 20/hour |
| Accounts locked | 0/day | > 1/day |
| Unauthorized policy changes | 0 | Any detected |
| Data leaks detected | 0 | Any detected |
| Certificate revocations | 0 (normal) | > 1/day |
| Zero trust denials (403) | < 1% | > 5% |
| Average trust score | > 85 | < 70 |
| Audit log tampering | 0 | Any detected |

### Dashboard View (Recommended)

```
Security Dashboard
├─ [Authentication]
│  ├─ Failed logins (24h): 3
│  ├─ Locked accounts: 0
│  └─ MFA enabled: 75%
│
├─ [Devices]
│  ├─ Active devices: 47
│  ├─ Offline devices: 2
│  ├─ Low trust score: 1
│  └─ Revoked certs: 0
│
├─ [Data Protection]
│  ├─ Leaks detected (24h): 0
│  ├─ SAs established: 47
│  ├─ Average SA lifetime: 98%
│  └─ Encryption algorithm: AES-256-GCM
│
├─ [Audit Trail]
│  ├─ Events (24h): 1247
│  ├─ Chain integrity: VERIFIED
│  ├─ Tampering detected: NO
│  └─ Policy changes: 3
│
└─ [Alerts]
   ├─ Critical: 0
   ├─ High: 0
   ├─ Medium: 1
   └─ Low: 2
```

