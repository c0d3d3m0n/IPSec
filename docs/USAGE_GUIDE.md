# 📖 Comprehensive Usage Guide

Complete walkthrough for using the IPSec Framework with all Phase 1 (Compliance & Telemetry) and Phase 2 (Zero Trust) features.

---

## Table of Contents
1. [Initial Setup](#initial-setup)
2. [Admin Dashboard & MFA Setup](#admin-dashboard--mfa-setup)
3. [Device Enrollment](#device-enrollment)
4. [Zero Trust Configuration](#zero-trust-configuration)
5. [Policy Management](#policy-management)
6. [Policy Routing & Driver Dispatch](#policy-routing--driver-dispatch)
7. [Compliance & Monitoring](#compliance--monitoring)
8. [Audit Logs & Compliance Reports](#audit-logs--compliance-reports)
9. [Troubleshooting](#troubleshooting)

---

## Initial Setup

### Prerequisites
- Python 3.10+
- PostgreSQL database (local or cloud)
- Docker (optional, for containerization)
- pip dependencies installed

### 1. Set Up the Orchestrator

```bash
# Navigate to orchestrator directory
cd orchestrator

# Install dependencies
pip install -r requirements.txt

# Initialize database (if first time)
# Update DATABASE_URL in config
export DATABASE_URL="postgresql://user:password@localhost/ipsec_db"

# Run database migrations (if using Alembic)
# alembic upgrade head

# Seed admin user
python seed_admin.py

# Start the orchestrator
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Verify Orchestrator is Running

```bash
# In another terminal, test API
curl -s http://localhost:8000/docs

# Should open interactive Swagger UI
```

---

## Admin Dashboard & MFA Setup

### Step 1: Access the Dashboard

1. Open browser: `http://localhost:3000` (frontend URL)
2. Default credentials:
   - **Username**: `admin`
   - **Password**: `admin123`

### Step 2: Set Up Admin TOTP MFA (Multi-Factor Authentication)

**Why**: Protects your admin account with time-based one-time passwords (TOTP).

1. After login, navigate to **Settings** → **Security**
2. Click **"Enable Two-Factor Authentication"**
3. Two options appear:
   - **QR Code**: Scan with authenticator app (Google Authenticator, Microsoft Authenticator, Authy, etc.)
   - **Manual Entry**: Type the secret key manually if scanning doesn't work

**Authenticator Apps to Use:**
- Google Authenticator
- Microsoft Authenticator
- Authy
- 1Password
- FreeOTP

4. Add the code to your authenticator app
5. Enter the **6-digit code** from your authenticator app in the prompt
6. Click **"Verify & Enable"**

**Important**: Save the **backup codes** provided. These allow account recovery if you lose access to your authenticator.

### Step 3: Login with TOTP

Next time you log in:
1. Enter username and password
2. When prompted, enter the **6-digit code** from your authenticator app
3. You're now logged in

---

## Device Enrollment

### Pre-Activation via Dashboard (Admin)

1. Log in to dashboard with admin credentials
2. Navigate to **Devices** → **Pre-activate Device**
3. Fill in:
   - **Enrollment Number**: Unique identifier (e.g., `PROD-WIN-01`, `DEV-LINUX-02`)
   - **Secret Activation Token**: Strong password (e.g., `MySecureToken123!@#`)

4. Click **Create**

**Note**: The device appears with status **PENDING** until the agent activates it.

### Device Activation (Agent Side)

#### On Windows (Administrator required)

Use the full runbook for a fresh terminal session:
- [AGENT_WINDOWS_RUNBOOK.txt](AGENT_WINDOWS_RUNBOOK.txt)

Quick sequence:

```powershell
# 1) Open PowerShell as Administrator
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# 2) Go to repo root and activate venv
cd E:\PROJECTS\IPSec_Framework
.\.venv\Scripts\Activate.ps1

# 3) Agent runtime environment
$env:ORCHESTRATOR_URL = "https://api.ipsecvault.tech"
$env:POLL_INTERVAL = "30"

# Optional: suppress interface fallback warning on Windows
$env:LEAK_DETECTION_IFACE = ""

# 4) Run agent
cd agent
python .\main.py
```

Prompts:

```
Enter Secret Enrollment Token: <your enrollment token>
Enter Enrollment Number: PROD-WIN-01
Enter Pre-Shared Key (leave blank to reuse Enrollment Token):
```

Expected output includes:

```
[INFO] Device enrolled successfully
[INFO] New policy version detected
[INFO] Applying IPSec policy to windows
[Windows driver] Step 1/6 ... OK
[Windows driver] Step 2/6 ... OK
[Windows driver] Step 3/6: Phase2AuthSet skipped (PSK tunnel)
[Windows driver] Step 4/6 ... OK
[Windows driver] Step 5/6 ... OK
[Windows driver] Step 6/6 ... OK
```

#### On Linux

```bash
# No special privileges needed for enrollment, but root may be needed for IPsec config
cd agent

# Set environment variables
export ORCHESTRATOR_URL="http://orchestrator.example.com:8000"
export PRE_SHARED_KEY="MySecureToken123!@#"

# Run the agent
python -m agent.main
```

**Expected Output:**
```
[INFO] Device enrolled successfully
[INFO] Certificate issued and saved
[INFO] Starting polling loop
```

### Verification in Dashboard

1. Go back to **Devices**
2. Refresh the page
3. Device status should now be **ACTIVE**
4. You'll see:
   - Hostname
   - OS Type (Windows/Linux)
   - Public IP
   - Last Activity timestamp

---

## Zero Trust Configuration

### What is Zero Trust?

The framework implements a **zero-trust security model**:
- **Every connection must be authenticated** with cryptographic certificates
- **Every request is verified** for trust score and compliance status
- **Least privilege access** based on device behavior and policy

### How Zero Trust Works in This Framework

1. **Device Bootstrap**
   - Agent collects device fingerprint (hostname, OS, MAC address)
   - Signs fingerprint with pre-shared key
   - Sends to orchestrator for enrollment

2. **Certificate Issuance**
   - Orchestrator issues device certificate (RSA 4096-bit)
   - Certificate contains device ID in subject CN
   - Agent stores certificate locally

3. **mTLS Communication**
   - All subsequent agent→orchestrator communication uses mTLS
   - Agent presents device certificate
   - Orchestrator verifies certificate chain

4. **Trust Scoring**
   - Each request is scored (0-100 scale)
   - Factors:
     - Certificate validity
     - Last activity recency (>5 min = -30)
     - Source IP consistency (-40 if changed)
     - Off-hours access (-10 if outside work hours)
     - Compliance status (-25 if violations detected)
     - Active SA presence (-20 if missing)
   - **Allow**: Score ≥ 70
   - **Restricted**: Score 40-69 (limited endpoint access)
   - **Deny**: Score < 40 (connection blocked)

### Configuring Zero Trust Parameters

Edit `orchestrator/security/trust_evaluator.py` to customize trust scoring:

```python
# Risk deductions
CERT_CN_MISMATCH_DEDUCTION = 100  # Critical: Device ID doesn't match cert
REVOKED_CERT_DEDUCTION = 100       # Critical: Certificate revoked
LAST_SEEN_THRESHOLD = 5            # Minutes
LAST_SEEN_DEDUCTION = 30           # Points
SOURCE_IP_MISMATCH_DEDUCTION = 40  # Major: Different IP detected
OFF_HOURS_DEDUCTION = 10           # Minor: Access outside work hours
COMPLIANCE_FAILURE_DEDUCTION = 25  # Major: Compliance check failed
LEAK_DETECTED_DEDUCTION = 50       # Critical: Data leak detected
NO_ACTIVE_SA_DEDUCTION = 20        # Moderate: No active IPsec SA

# Trust thresholds
ALLOW_THRESHOLD = 70
RESTRICTED_THRESHOLD = 40
```

---

## Policy Management

### Create a Policy

1. Dashboard → **Policies** → **Create New**
2. Fill in:
   - **Policy Name**: Descriptive name (e.g., `Production-to-DR`)
   - **Source CIDR**: Local network (e.g., `10.0.0.0/8`)
   - **Destination CIDR**: Remote network (e.g., `192.168.0.0/16`)
   - **Encryption Algorithm**: `AES-GCM-256`
   - **Integrity Algorithm**: `SHA-512`
   - **SA Rekey Period**: `3600` seconds
3. Click **Save**

### Assign Policy to Device

1. Dashboard → **Devices**
2. Click on device name
3. **Policies** section → **Assign Policy**
4. Select policy from dropdown
5. Click **Assign**

**Expected Result**: Device establishes IPsec tunnel within 60 seconds

### Monitor Policy Execution

1. Dashboard → **Policies** → Click policy name
2. View:
   - Assigned devices
   - SA (Security Association) status per device
   - Algorithm matching results
   - Last modified timestamp

---

## Policy Routing & Driver Dispatch

Phase 3 adds OS-aware policy delivery. The orchestrator now normalizes policy JSON before storing it and builds a separate config payload for each supported operating system.

### How It Works

1. Upload a policy JSON file through the policy upload endpoint.
2. The orchestrator validates required fields, target OS values, crypto names, and connection definitions.
3. The orchestrator stores the original JSON plus a `per_os_configs` structure.
4. Each agent requests `GET /api/devices/{device_id}/config?os_type=<os>`.
5. The agent applies only the native driver block for its own platform.

### Supported OS Values

- `linux`
- `windows`
- `macos`

### What the Parser Normalizes

- Encryption names such as `aes-gcm-256`, `aes256gcm16`, and `AES-256-GCM`
- Integrity names such as `sha512` and `hmac-sha512`
- DH groups such as `group20` and `ecp384`

### What Agents Receive

- Linux agents receive strongSwan-style connection and secret blocks.
- Windows agents receive PowerShell cmdlet instructions.
- macOS agents receive racoon-style remote blocks.

### Example Policies

Use these files to test routing behavior:

- [policy_all_os.json](../examples/policy_all_os.json)
- [policy_linux_only.json](../examples/policy_linux_only.json)

---

## Compliance & Monitoring

### Heartbeat System (Phase 1)

The heartbeat system provides continuous device connectivity monitoring.

#### How It Works

- Agents send heartbeat every **60 seconds**
- Heartbeat includes:
  - Device ID
  - Current timestamp
  - System uptime
  - Memory usage
  - CPU usage
  - Network adapter status

#### View Heartbeat Status

Dashboard → **Monitoring** → **Heartbeat Status**

Shows:
- Device name
- Last heartbeat time
- Status (Online/Offline)
- Uptime percentage

#### API Endpoint (for programmatic access)

```bash
# Get latest heartbeat from all devices
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/compliance/heartbeat

# Response:
{
  "status": "success",
  "heartbeats": [
    {
      "device_id": "device-001",
      "timestamp": "2024-04-09T12:34:56Z",
      "uptime_seconds": 86400,
      "memory_usage_percent": 45.2,
      "cpu_usage_percent": 12.5,
      "adapters_online": 4
    }
  ]
}
```

### SA (Security Association) Monitoring (Phase 1)

Monitors active IPsec tunnels.

#### What is an SA?

An SA is an active IPsec tunnel with negotiated encryption/integrity algorithms.

#### View SA Status

Dashboard → **Monitoring** → **Security Associations**

Shows per device:
- Source/destination IPs
- Encryption algorithm
- Integrity algorithm
- Bytes encrypted/decrypted
- Last activity time
- Validity remaining (e.g., "Expires in 45 minutes")

#### SA Metrics

The system collects:
- **Algorithm Matching**: Device's configured algorithm vs. actual SA algorithm
- **Tunnel Uptime**: Time since SA created
- **Data Transfer Rate**: Bytes/sec through tunnel
- **Rekeying Events**: Number of times SA has been rekeyed

### Compliance Reports (Phase 1)

Regular compliance snapshots of device state.

#### Send Compliance Report (Automated)

Agents automatically send compliance reports every **5 minutes** containing:
- Device fingerprint (hostname, OS, MAC)
- Active IPsec tunnels (SAs)
- Encryption algorithm verification
- System security status (firewall, antivirus if available)

#### View Compliance Report

Dashboard → **Compliance** → **Reports**

Shows:
- Device name
- Report timestamp
- Compliance status (✓ Compliant / ✗ Non-Compliant)
- Detailed metrics:
  - SAs present
  - Algorithms matching policy
  - System health

#### API Example

```bash
# Get latest compliance report
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/compliance/status

# Response:
{
  "device_id": "device-001",
  "timestamp": "2024-04-09T12:35:00Z",
  "is_compliant": true,
  "sa_count": 3,
  "algorithms_verified": true,
  "fingerprint": {
    "hostname": "PROD-WIN-01",
    "os_version": "Windows 10 (19045)",
    "mac_addresses": ["aa:bb:cc:dd:ee:01"]
  }
}
```

### Leak Detection (Phase 1)

Monitors network traffic for unauthorized data flows outside IPsec tunnels.

#### How Leak Detection Works

1. Agent monitors network interface for traffic
2. Compares traffic destination IPs against protected subnets
3. Flags unencrypted traffic to protected networks as **LEAK**
4. Sends alert to orchestrator with:
   - Source/destination IPs
   - Protocol
   - Port
   - Timestamp

#### Configure Protected Subnets

In `agent/config.py`:

```python
PROTECTED_SUBNETS = [
    "10.0.0.0/8",        # Production network
    "192.168.0.0/16",    # Remote office
    "172.16.0.0/12",     # Data center
]
```

#### View Leak Alerts

Dashboard → **Security** → **Leak Alerts**

Shows:
- Device name
- Leak detection timestamp
- Source IP / Destination IP
- Protocol / Port
- Severity level
- Remediation steps

#### Responding to Leaks

1. **Minor Leak** (e.g., DNS query to 8.8.8.8): Review and whitelist if acceptable
2. **Major Leak** (unencrypted traffic to protected network): 
   - Investigate on device
   - Check VPN client status
   - Review firewall rules
   - Restart agent if needed

---

## Audit Logs & Compliance Reports

### Audit Trail (Phase 1)

All security events are logged with SHA-512 chain integrity.

#### What Gets Logged

- User login/logout (with IP, timestamp, success/failure)
- Policy changes (who changed what, when)
- Device enrollment/unenrollment
- Certificate issuance/revocation
- Token refresh
- Access denials (trust score < 40)

#### Access Audit Logs

Dashboard → **Admin** → **Audit Logs**

Shows:
- Event type
- Actor (user/device ID)
- Action (create/update/delete/access)
- Timestamp
- Status (success/failure)
- Details (what changed)

#### API Access

```bash
# Get audit logs
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/audit/logs?limit=100

# Response:
{
  "logs": [
    {
      "timestamp": "2024-04-09T12:30:00Z",
      "event_type": "policy_assigned",
      "actor": "admin",
      "action": "ASSIGN",
      "resource": "device-001",
      "status": "success",
      "details": {
        "policy_id": "policy-prod-001",
        "policy_name": "Production-to-DR"
      }
    }
  ]
}
```

#### Chain Integrity Verification

Each audit log entry contains:
- Current hash: SHA-512(entry_data)
- Previous hash: SHA-512(previous_entry)

This creates an immutable chain. Any tampering is detected:

```python
# Verify chain integrity
current_chain_ok = (log.hash == sha512(log_data))
previous_chain_ok = (log.previous_hash == previous_log.hash)
```

---

## Rate Limiting & DoS Protection

### Active Rate Limits

```
Device Enrollment:        5 requests / minute
Admin Login:             10 requests / minute
Heartbeat Submission:   120 requests / minute
Compliance Reports:      60 requests / minute
Policy Fetch:           120 requests / minute
```

### Handling Rate Limit Errors

If you hit a rate limit:

```bash
# Response (HTTP 429):
{
  "detail": "Rate limit exceeded. Try again in 12 seconds."
}
```

**Action**: Wait 60 seconds before retrying.

### Configuring Rate Limits

In `orchestrator/main.py`:

```python
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",  # Use Redis for production
    default_limits=["200 per day", "50 per hour"]
)

# Custom per-endpoint:
@limiter.limit("120/minute")
@router.post("/api/compliance/heartbeat")
async def submit_heartbeat(heartbeat: HeartbeatData):
    ...
```

---

## Troubleshooting

### Agent Won't Connect

**Symptom**: `Connection refused` errors in agent logs

**Solutions**:
1. Verify orchestrator is running: `curl http://localhost:8000/docs`
2. Check `ORCHESTRATOR_URL` environment variable
3. Check firewall allows port 8000
4. On Windows, restart agent with Administrator privileges

### Certificate Errors

**Symptom**: `SSL: CERTIFICATE_VERIFY_FAILED` in agent logs

**Solutions**:
1. Verify CA cert exists: `ls keys/ca.crt`
2. Regenerate certs if expired:
   ```bash
   cd orchestrator
   python -c "from security.certificate_authority import InternalCA; ca = InternalCA(); ca.initialize_ca()"
   ```
3. Delete agent cert and re-enroll

### Device Status Shows "Offline" but Agent is Running

**Symptom**: Dashboard shows device as OFFLINE despite agent running

**Solutions**:
1. Check heartbeat wasn't disabled:
   ```bash
   # In agent logs, look for heartbeat submission
   grep "Heartbeat sent" agent.log
   ```
2. Restart agent:
   ```bash
   # Kill current process
   kill <pid>
   # Restart
   python -m agent.main
   ```
3. Check database connection on orchestrator

### "Access Denied" (HTTP 403) on Device Requests

**Symptom**: Devices getting 403 responses to policy fetch

**Solutions**:
1. Check trust score:
   ```bash
   # Add logging to see trust score
   # Edit orchestrator/middleware/zero_trust.py
   logger.info(f"Trust score: {trust_score.score}")
   ```
2. If score < 40:
   - Verify device certificate: `openssl x509 -in device.crt -text`
   - Check device is not in revoked list
   - Verify source IP hasn't changed
3. If score 40-69 (restricted):
   - Check compliance status
   - Send heartbeat to restore good standing

### High Memory Usage on Agent

**Symptom**: Agent process consuming > 500MB RAM

**Solutions**:
1. Reduce polling interval in `agent/config.py`:
   ```python
   POLL_INTERVAL = 120  # seconds, instead of 60
   ```
2. Disable leak detection if not needed:
   ```python
   ENABLE_LEAK_DETECTION = False
   ```
3. Clear old audit logs periodically

### Policy Not Applied to Device

**Symptom**: Device has policy assigned but no SA established

**Solutions**:
1. Check device received policy:
   ```bash
   # In device logs, look for policy fetch
   grep "Policy fetched" agent.log
   ```
2. Verify policy syntax:
   - Source CIDR valid (e.g., `10.0.0.0/8`)
   - Destination CIDR valid
   - Encryption algorithm supported on device
3. Check OS-specific issues:
   - **Windows**: Ensure PowerShell script executed successfully
   - **Linux**: Check strongSwan is installed and running

### MFA Setup Failed

**Symptom**: "Invalid code" when trying to enable TOTP

**Solutions**:
1. Verify time sync on device running authenticator app
   - Clock skew > 30 seconds causes code mismatch
2. Try different authenticator app
3. Generate new secret and retry

---

## Advanced: API Reference

### Authentication

```bash
# Get access token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}

# Use token for authenticated requests
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/devices/
```

### Common Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login` | Get access token |
| GET | `/api/devices/` | List all devices |
| POST | `/api/devices/enroll` | Enroll new device |
| POST | `/api/policies/` | Create policy |
| GET | `/api/policies/{id}` | Get policy details |
| POST | `/api/policies/{id}/assign` | Assign to device |
| GET | `/api/compliance/heartbeat` | Get heartbeats |
| POST | `/api/compliance/report` | Submit compliance |
| GET | `/api/audit/logs` | View audit trail |

---

## Next Steps

- [Zero Trust Architecture Deep Dive](ZERO_TRUST_SETUP.md)
- [Security Features & Cryptography](SECURITY_ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_LINUX.md)
- [Test Plan](../TEST_PLAN.md)
