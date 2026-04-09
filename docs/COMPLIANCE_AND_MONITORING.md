# 📊 Compliance & Monitoring Guide (Phase 1)

Comprehensive reference for heartbeat, compliance reporting, SA monitoring, leak detection, and audit logging.

---

## Table of Contents
1. [Heartbeat System](#heartbeat-system)
2. [Compliance Reporting](#compliance-reporting)
3. [Security Association (SA) Monitoring](#security-association-monitoring)
4. [Leak Detection](#leak-detection)
5. [Audit Logs](#audit-logs)
6. [API Reference](#api-reference)
7. [Dashboard Views](#dashboard-views)

---

## Heartbeat System

### Purpose
Continuously monitor device connectivity and health status.

### What Gets Sent

Every 60 seconds, agents send a heartbeat containing:

```json
{
  "device_id": "device-001",
  "timestamp": "2024-04-09T12:30:45.123Z",
  "uptime_seconds": 604800,
  "memory_usage_percent": 45.2,
  "cpu_usage_percent": 12.5,
  "adapters_online": 4,
  "system_info": {
    "hostname": "PROD-WIN-01",
    "os_version": "Windows 10 (19045)",
    "ip_address": "192.168.1.100"
  }
}
```

### Configuration

Edit `agent/config.py`:

```python
# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 60

# Number of retries on failure
HEARTBEAT_RETRIES = 3

# Timeout for heartbeat request (seconds)
HEARTBEAT_TIMEOUT = 10
```

### Heartbeat Endpoints

**Submit Heartbeat**:
```bash
POST /api/compliance/heartbeat
Authorization: Bearer <token>
Content-Type: application/json

{
  "uptime_seconds": 604800,
  "memory_usage_percent": 45.2,
  "cpu_usage_percent": 12.5,
  "adapters_online": 4
}

# Response (200 OK):
{
  "received": true,
  "next_interval": 60
}
```

**Retrieve Heartbeat Status**:
```bash
GET /api/compliance/heartbeat
Authorization: Bearer <token>

# Response:
{
  "heartbeats": [
    {
      "device_id": "device-001",
      "last_heartbeat": "2024-04-09T12:30:45Z",
      "status": "online",
      "uptime": "7 days 2 hours",
      "memory_usage": 45.2,
      "cpu_usage": 12.5
    },
    {
      "device_id": "device-002",
      "last_heartbeat": "2024-04-09T11:55:12Z",
      "status": "offline",  # No heartbeat in 60+ seconds
      "uptime": "2 days 14 hours",
      "memory_usage": null,
      "cpu_usage": null
    }
  ]
}
```

### Offline Detection

A device is marked **OFFLINE** when:
- No heartbeat received for > 2 minutes
- Network connectivity lost
- Agent process stopped

**Alert Triggers** (configurable):
- Device offline for > 5 minutes → Send notification
- Device offline for > 30 minutes → Escalate alert
- Device offline for > 24 hours → Quarantine device (restrict policy access)

**Recovery**:
- Agent comes back online → Automatic status update
- Dashboard shows time since last hearbeat

---

## Compliance Reporting

### Purpose
Regular snapshots of device security posture and policy adherence.

### What Gets Reported

Every 5 minutes, agents send a compliance report:

```json
{
  "device_id": "device-001",
  "timestamp": "2024-04-09T12:35:00Z",
  "fingerprint": {
    "hostname": "PROD-WIN-01",
    "os_version": "Windows 10 (19045)",
    "mac_addresses": ["aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"]
  },
  "security_associations": [
    {
      "sa_id": "sa-001",
      "local_subnet": "10.0.0.0/8",
      "remote_subnet": "192.168.0.0/16",
      "encryption_algo": "AES-GCM-256",
      "integrity_algo": "SHA-512",
      "sa_status": "ESTABLISHED",
      "bytes_encrypted": 1048576000,
      "bytes_decrypted": 1024000000,
      "created_at": "2024-04-08T10:00:00Z",
      "rekeyed_at": "2024-04-09T12:00:00Z"
    }
  ],
  "compliance_checks": {
    "firewall_enabled": true,
    "antivirus_running": true,
    "disk_encryption": true,
    "os_patches_current": true,
    "all_policies_applied": true
  },
  "is_compliant": true
}
```

### Compliance Checks

| Check | Purpose | Failure Means |
|-------|---------|--------------|
| `firewall_enabled` | Network protection | Many ports exposed |
| `antivirus_running` | Malware protection | System vulnerable |
| `disk_encryption` | Data protection at rest | Data unprotected if stolen |
| `os_patches_current` | Security updates applied | Known vulnerabilities present |
| `all_policies_applied` | Policies active on device | IPsec tunnels not configured |

### Configuration

Edit `agent/config.py`:

```python
# Compliance report interval
COMPLIANCE_INTERVAL = 300  # 5 minutes

# Checks to run
ENABLE_FIREWALL_CHECK = True
ENABLE_ANTIVIRUS_CHECK = True  # May be slow on Windows
ENABLE_DISK_ENCRYPTION_CHECK = True
ENABLE_OS_PATCH_CHECK = True
ENABLE_POLICY_CHECK = True
```

### Compliance Endpoints

**Submit Compliance Report**:
```bash
POST /api/compliance/report
Authorization: Bearer <token>
Content-Type: application/json

{
  "fingerprint": {...},
  "security_associations": [...],
  "compliance_checks": {...},
  "is_compliant": true
}

# Response (200 OK):
{
  "report_id": "report-12345",
  "compliance_status": "compliant",
  "recommendations": []
}
```

**Get Compliance Status**:
```bash
GET /api/compliance/status
Authorization: Bearer <token>

# Response:
{
  "devices": [
    {
      "device_id": "device-001",
      "compliance_status": "compliant",
      "last_report": "2024-04-09T12:35:00Z",
      "violations": []
    },
    {
      "device_id": "device-002",
      "compliance_status": "non_compliant",
      "last_report": "2024-04-09T12:30:00Z",
      "violations": [
        {
          "check": "firewall_enabled",
          "expected": true,
          "actual": false,
          "severity": "high"
        },
        {
          "check": "os_patches_current",
          "expected": true,
          "actual": false,
          "severity": "critical"
        }
      ]
    }
  ]
}
```

---

## Security Association (SA) Monitoring

### What is an SA?

A **Security Association** is an active IPsec tunnel with negotiated parameters:
- Encryption algorithm (e.g., AES-GCM-256)
- Integrity algorithm (e.g., SHA-512)
- Encryption/decryption counters
- Lifetime (when it expires for rekeying)

### SA Metrics Collected

**Per-SA Data**:
```json
{
  "sa_id": "sa-001",
  "device_id": "device-001",
  "policy_name": "Production-to-DR",
  "local_subnet": "10.0.0.0/8",
  "remote_subnet": "192.168.0.0/16",
  "status": "ESTABLISHED",
  "encryption_algorithm": "AES-GCM-256",
  "integrity_algorithm": "SHA-512",
  "bytes_encrypted": 1048576000,
  "bytes_decrypted": 1024000000,
  "packets_encrypted": 2097152,
  "packets_decrypted": 2048000,
  "created_at": "2024-04-08T10:00:00Z",
  "rekeyed_at": "2024-04-09T12:00:00Z",
  "expires_at": "2024-04-09T12:00:00Z",
  "lifetime_seconds": 3600
}
```

### SA Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| ESTABLISHED | Tunnel active and working | Normal operation |
| REKEYING | SA being refreshed | Wait for completion (usually < 30s) |
| EXPIRED | SA lifetime reached | Manual rekey needed (should be automatic) |
| FAILED | SA creation failed | Debug: Check algorithm support, firewall |
| UNKNOWN | Status cannot be determined | Check agent connectivity |

### SA Lifecycle

```
[1] PENDING
    └─ Device receives policy
    └─ Starts IPsec negotiation

[2] ESTABLISHING
    └─ IKE (Internet Key Exchange) in progress
    └─ Usually completes in 1-5 seconds

[3] ESTABLISHED
    └─ SA active, tunnel ready
    └─ Traffic flows through tunnel

[4] REKEYING (periodic)
    └─ After configured lifetime (default 3600s/1hr)
    └─ New keys negotiated without interrupting traffic
    └─ Old SA removed

[5] EXPIRED
    └─ SA lifetime exceeded
    └─ Should trigger automatic rekey
    └─ If not: manual intervention needed

[6] DELETED
    └─ Policy removed or explicitly deleted
    └─ Tunnel torn down
    └─ Traffic no longer protected
```

### Configuration

Edit `orchestrator/models.py`:

```python
# SA configuration defaults
SA_LIFETIME_SECONDS = 3600          # 1 hour
SA_REKEY_MARGIN_SECONDS = 300       # Rekey 5 min before expiry
SA_MAX_BYTES = 2**32                # Rekey after 4GB transferred
SA_MAX_PACKETS = 2**32              # Rekey after 4B packets
```

### SA Monitoring Endpoints

**Get SAs for Device**:
```bash
GET /api/compliance/sa/{device_id}
Authorization: Bearer <token>

# Response:
{
  "device_id": "device-001",
  "security_associations": [
    {
      "sa_id": "sa-001",
      "policy_name": "Production-to-DR",
      "local_subnet": "10.0.0.0/8",
      "remote_subnet": "192.168.0.0/16",
      "status": "ESTABLISHED",
      "encryption": "AES-GCM-256",
      "integrity": "SHA-512",
      "bytes_encrypted": 1048576000,
      "lifetime_remaining": "45 minutes"
    }
  ]
}
```

**Monitor SA Health**:
```bash
GET /api/compliance/sa-health
Authorization: Bearer <token>

# Response:
{
  "summary": {
    "total_sas": 12,
    "established": 11,
    "rekeying": 1,
    "failed": 0,
    "expired": 0
  },
  "devices": [
    {
      "device_id": "device-001",
      "sa_count": 3,
      "status": "healthy"
    },
    {
      "device_id": "device-002",
      "sa_count": 0,
      "status": "no_tunnels",
      "recommendation": "Policy not applied or failed to establish"
    }
  ]
}
```

---

## Leak Detection

### Purpose
Identify unauthorized data flows outside IPsec tunnels to protected networks.

### How Leak Detection Works

**Agent monitors network traffic for**:
1. Destination IP in protected subnets
2. Traffic NOT encrypted (not in IPsec tunnel)
3. Non-whitelisted cases

**When Detected**:
1. Capture packet details (src, dst, protocol, port)
2. Create LEAK alert
3. Send to orchestrator immediately
4. Subject device to trust score penalty (-50 points → DENY)

### Configuration

Edit `agent/config.py`:

```python
# Enable/disable leak detection
ENABLE_LEAK_DETECTION = True

# Network interface to monitor
LEAK_DETECTION_IFACE = "eth0"  # Auto-detect if not set

# Protected subnets (traffic to these must be encrypted)
PROTECTED_SUBNETS = [
    "10.0.0.0/8",           # Corporate network
    "192.168.0.0/16",       # Remote office
    "172.16.0.0/12",        # Data center
]

# Whitelisted destinations (allowed unencrypted)
LEAK_WHITELIST = [
    "8.8.8.8",              # Public DNS
    "1.1.1.1",              # Cloudflare DNS
    "169.254.169.254",      # AWS metadata
]

# Protocols to ignore
IGNORED_PROTOCOLS = ["ICMP", "UDP:53"]  # DNS, ICMP don't need tunnel
```

### Leak Alert Data

```json
{
  "leak_id": "leak-12345",
  "device_id": "device-001",
  "timestamp": "2024-04-09T12:30:15.456Z",
  "source_ip": "192.168.1.100",
  "source_port": 54321,
  "destination_ip": "10.5.2.3",
  "destination_port": 443,
  "protocol": "TCP",
  "detected_packets": 5,
  "total_bytes": 2048,
  "severity": "high",
  "expected_protection": "AES-GCM-256 over IPsec",
  "remediation": [
    "Check VPN client status",
    "Verify policy is assigned",
    "Restart agent",
    "Review firewall rules"
  ]
}
```

### Responding to Leaks

**Low Severity** (e.g., DNS query to public resolver):
```bash
# Add to whitelist and re-run agent
# File: agent/config.py
LEAK_WHITELIST.append("8.8.8.8:53")
```

**High Severity** (unencrypted traffic to protected network):
```bash
# [STEP 1] Investigate on device
ssh admin@device-001
  
  # Is IPsec client running?
  systemctl status ipsec
  
  # Is policy in effect?
  ip xfrm state  # Linux
  netsh ipsec show all  # Windows
  
  # Is traffic going through tunnel?
  tcpdump -i eth0 "host 10.5.2.3"

# [STEP 2] Restart agent
python -m agent.main

# [STEP 3] Verify tunnel re-established
# Check in dashboard → SA monitoring page
```

### Leak Detection Endpoints

**Get Recent Leaks**:
```bash
GET /api/compliance/leaks?limit=50
Authorization: Bearer <token>

# Response:
{
  "leaks": [
    {
      "leak_id": "leak-12345",
      "device_id": "device-001",
      "timestamp": "2024-04-09T12:30:15Z",
      "source_ip": "192.168.1.100",
      "destination_ip": "10.5.2.3",
      "protocol": "TCP",
      "severity": "high",
      "status": "active"  # or "resolved" or "investigated"
    }
  ]
}
```

**Get Leaks for Device**:
```bash
GET /api/compliance/leaks/device/{device_id}
Authorization: Bearer <token>

# Response:
{
  "device_id": "device-001",
  "leak_count": 3,
  "recent_leaks": [...]
}
```

---

## Audit Logs

### Purpose
Immutable record of all security-relevant events.

### What Gets Logged

| Event | Logged When | Contains |
|-------|------------|----------|
| LOGIN | User logs in | Username, IP, timestamp, success/failure, MFA code |
| LOGOUT | User logs out | Username, IP, timestamp |
| POLICY_CREATED | Admin creates policy | Policy ID, name, source/dest, algorithm selection, admin ID |
| POLICY_ASSIGNED | Policy assigned to device | Policy ID, device ID, admin ID, timestamp |
| DEVICE_ENROLLED | Device enrolls | Device ID, hostname, OS, IP, certificate serial |
| DEVICE_UNENROLL | Device removed | Device ID, reason, admin ID |
| CERT_ISSUED | Certificate issued | Device ID, cert serial, validity period |
| CERT_REVOKED | Certificate revoked | Device ID, cert serial, reason, revoker ID |
| TOKEN_REFRESHED | Token rotated | User/device ID, old token hash, new token issued |
| ACCESS_DENIED | Trust score < 40 | Device ID, score, factors, denied endpoint |
| COMPLIANCE_VIOLATION | Check failed | Device ID, check name, expected vs. actual |

### Chain Integrity

Each audit log entry includes:

```python
{
  "log_id": "audit-12345",
  "timestamp": "2024-04-09T12:30:00Z",
  "event_type": "policy_assigned",
  "actor": "admin",
  "action": "ASSIGN",
  "resource": "device-001",
  "status": "success",
  "details": {...},
  
  # Chain integrity fields
  "hash": "sha512(entry_data)",                    # Current entry hash
  "previous_hash": "sha512(previous_entry)",      # Link to previous entry
  "signature": "RSA-sign(hash, orchestrator_key)" # Tamper detection
}
```

**Verification**:
```python
# Check entry hasn't been tampered
current_ok = sha512(entry_data) == entry.hash

# Check chain hasn't been broken
chain_ok = previous_entry.hash == entry.previous_hash

# Check orchestrator signed it
sig_ok = RSA_verify(entry.signature, entry.hash, orchestrator_pubkey)

if current_ok and chain_ok and sig_ok:
    print("Audit log verified - no tampering detected")
else:
    print("ALERT: Audit log tampering detected!")
```

### Audit Log Endpoints

**Get Audit Logs** (paginated):
```bash
GET /api/audit/logs?limit=100&offset=0&filter=event_type:POLICY_ASSIGNED
Authorization: Bearer <token>

# Response:
{
  "total_count": 1243,
  "logs": [
    {
      "log_id": "audit-12345",
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

**Verify Audit Chain**:
```bash
GET /api/audit/logs/{log_id}/verify
Authorization: Bearer <token>

# Response:
{
  "log_id": "audit-12345",
  "verified": true,
  "checks": {
    "hash_valid": true,
    "chain_valid": true,
    "signature_valid": true,
    "tampering_detected": false
  }
}
```

**Export Audit Trail**:
```bash
GET /api/audit/export?format=csv&from=2024-04-01&to=2024-04-09
Authorization: Bearer <token>

# Response: CSV download
```

---

## API Reference

### Rate Limits

```
Heartbeat:    120 requests/minute
Compliance:    60 requests/minute
Audit logs:   100 requests/minute
General:      200 requests/minute (per API key)
```

### Error Responses

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds.",
  "status": 429
}

{
  "detail": "Device not found",
  "status": 404
}

{
  "detail": "Invalid token",
  "status": 401
}
```

---

## Dashboard Views

### Heartbeat Status Page
- Device name
- Status (Online/Offline)
- Last heartbeat (timestamp + ago in human-readable)
- Uptime percentage (last 24h, 7d, 30d)
- Current system metrics (CPU, memory, network adapters)
- Alert indicators (offline > 5min, memory > 80%, etc.)

### SA Monitoring Page
- Table of all SAs per device
- Status per SA (Established/Rekeying/Failed)
- Algorithm verification (expected vs. actual)
- Data transfer stats (bytes/packets/rate)
- SA lifetime and expiry countdown

### Compliance Dashboard
- Overall compliance score (% devices compliant)
- Compliance violations trending
- Per-device compliance status
- Failed checks breakdown

### Leak Alerts Page
- Recent leaks timeline
- Severity breakdown (critical/high/medium/low)
- Resolved vs. active count
- Leak investigation status

### Audit Log Page
- Searchable event log
- Filter by event type, actor, timestamp range
- Verify chain integrity for any log entry
- Export functionality (CSV/JSON)

