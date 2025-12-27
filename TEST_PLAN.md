# Unified IPsec Framework - Comprehensive Test Plan

This document outlines the detailed testing strategy for the Unified IPsec Framework. It covers functional, security, performance, and resilience testing to ensure enterprise-grade reliability.

## Prerequisite: Environment Setup

Before running tests, ensure the Orchestrator and at least two Agents (Linux/Windows) are running.

**1. Start Orchestrator**
```bash
# In terminal 1
cd orchestrator
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Start Agents**
```bash
# In terminal 2 (Linux/Windows Agent 1)
export ORCHESTRATOR_URL="http://127.0.0.1:8000"
export ENROLLMENT_TOKEN="secret-token-123"
python -m agent.main
```

---

# 1. Functional Testing (Core Features)

## 1.1 Agent Enrollment Test
**Objective:** Verify agents can register with the orchestrator.

**Steps:**
1.  Start the agent as shown above.
2.  Check Agent logs for:
    ```text
    Device enrolled successfully. ID: <number>
    ```
3.  Query Orchestrator for devices:
    ```bash
    curl -s http://127.0.0.1:8000/devices/ | jq
    ```

**Expected Result:**
- API returns the new device with correct `hostname`, `os_type`, and `public_ip`.
- Agent ID matches the log.

## 1.2 Policy Delivery Test
**Objective:** Ensure global IPsec policies are pushed to agents.

**Steps:**
1.  Run the automated test scenario script:
    ```bash
    python test_scenario.py
    ```
2.  Observe Agent logs for:
    ```text
    Applying policy: DemoPolicy_<random_id>
    ```

**Expected Result:**
- `test_scenario.py` reports "Policy assigned successfully!".
- Agent parses the JSON policy and initiates configuration (mock or real).

## 1.3 Tunnel Establishment Test
**Objective:** Verify encrypted connectivity.

**Steps:**
1.  **Linux/StrongSwan:**
    ```bash
    sudo ipsec statusall
    ```
2.  **Windows (PowerShell):**
    ```powershell
    Get-NetIPsecMainModeSA
    Get-NetIPsecQuickModeSA
    ```
3.  **Ping Test:**
    ```bash
    ping <remote_tunnel_ip>
    ```

**Expected Result:**
- `ipsec statusall` shows `ESTABLISHED`.
- Ping succeeds.
- `tcpdump -i any esp` shows ESP packets (encrypted traffic).

---

# 2. Cross-Platform Interoperability Testing

**Matrix:**
- **Linux (StrongSwan) ↔ Windows (Native IKEv2)**
- **Linux ↔ macOS (Native)**

**Steps:**
1.  Enroll a Linux agent and a Windows agent.
2.  Assign a generic IKEv2 policy (AES-256-GCM-128, SHA256, DH19).
3.  Trigger traffic from Linux:
    ```bash
    ping <windows_ip>
    ```

**Expected Result:**
- Windows Event Viewer (Security Log) shows Event 4653 (IPsec Main Mode negotiated).
- Linux logs show `IKE_SA` established.

---

# 3. PKI Testing

## 3.1 Certificate Generation & Storage
**Objective:** specific files are strictly secure.

**Steps:**
1.  **Linux:** Check permissions:
    ```bash
    ls -l /etc/ipsec.d/private/
    # Should be 600 or 700 (root only)
    ```
2.  **Windows:** Check Cert Store:
    ```powershell
    Get-ChildItem Cert:\LocalMachine\My
    ```

## 3.2 Certificate Revocation
**Steps:**
1.  Revoke a device in Orchestrator (simulated via DB update or API).
2.  Force re-auth on Agent:
    ```bash
    sudo ipsec restart
    ```

**Expected Result:**
- Connection fails with `CERTIFICATE_REVOKED` or authentication failure.

---

# 4. IKE / SA Negotiation Testing

## 4.1 Debugging Negotiation
**Tools:**
- **Linux:** `sudo journalctl -u strongswan -f`
- **Windows:** EtlTrace or `netsh wfp capture start`

**Verify:**
- **Algorithms:** Ensure matching proposals (e.g., AES_GCM_16_256).
- **Authentication:** RSA Signature / ECDSA.

## 4.2 Dead Peer Detection (DPD)
**Steps:**
1.  Establish tunnel.
2.  Disconnect network on Peer B (simulate cable pull).
3.  Watch Peer A logs.

**Expected Result:**
- Peer A sends DPD probes (R_U_THERE).
- After timeout (e.g., 30s), SA is torn down.

---

# 5. Security Testing

## 5.1 Replay Attack Simulation
**Steps:**
1.  Capture a valid ESP packet using Wireshark/tcpdump.
2.  Replay it using `tcpreplay`:
    ```bash
    tcpreplay -i eth0 captured_esp_packet.pcap
    ```

**Expected Result:**
- Receiver kernel drops duplicates.
- Incrementing "Replay window errors" in `netstat -s` or `ipsec -s`.

## 5.2 Weak Cipher Rejection
**Steps:**
1.  Configure Agent A to propose *only* `3DES-SHA1`.
2.  Configure Agent B (Policy) to accept *only* `AES-GCM`.
3.  Attempt connection.

**Expected Result:**
- `NO_PROPOSAL_CHOSEN` error in IKE logs.

---

# 6. Performance Testing

## 6.1 Throughput (iPerf3)
**Baseline (No Encryption):**
```bash
iperf3 -c <server_ip>
```
**Encrypted:**
```bash
iperf3 -c <server_tunnel_ip>
```

**Metrics:**
- **Throughput Drop:** Should be < 10-15% on modern CPUs (AES-NI).
- **CPU Usage:** Monitor `htop` or Task Manager.

## 6.2 Latency
```bash
ping -c 100 <destination>
```
- Compare average RTT with and without IPsec.

---

# 7. Scalability Testing (Simulation)

**Steps:**
1.  Use `docker-compose` to spin up 50+ lightweight python agents.
    ```bash
    for i in {1..50}; do
       docker run -d -e ORCHESTRATOR_URL=... my-agent-image
    done
    ```
2.  Monitor Orchestrator CPU/RAM.

**Expected Result:**
- Orchestrator handles concurrent POST `/enroll` requests.
- Database (`ipsec_orchestrator.db`) remains responsive.

---

# 8. Resilience Testing

## 8.1 Controller Downtime
**Steps:**
1.  Establish tunnels.
2.  Stop Orchestrator (`Ctrl+C`).
3.  Restart Agents.

**Expected Result:**
- Agents should cache last known valid policy (if implemented) or retry connection with exponential backoff.
- Existing Tunnels (data plane) stay UP if IKE auth is not required immediately.

---

# 9. Logging & Monitoring

**Checklist:**
- [ ] Agent logs clearly show: `Enrolling` -> `Policy Received` -> `Applying`.
- [ ] Error states (e.g., 404 from server) are handled gracefully (retry loop).
- [ ] Orchestrator logs show request source IPs and Device IDs.

---

# 10. Automation

**Run the full suite:**
```powershell
# Windows
./test_scenario.ps1
```
or
```bash
# Linux
python test_scenario.py
```
This script acts as the "Integration Test" verifying the Orchestrator-Agent loop.

---

# 11. Teardown & Cleanup

**Objective:** Reset the environment for a fresh test cycle.

**Steps:**

1.  **Windows Agents:**
    Run the cleanup script to remove IPsec rules:
    ```powershell
    ./cleanup.ps1
    ```

2.  **Linux Agents:**
    Flush StrongSwan configuration:
    ```bash
    sudo ipsec purge
    sudo ipsec restart
    ```

3.  **Orchestrator:**
    To completely reset the database (loss of all device enrollments!):
    ```bash
    rm ipsec_orchestrator.db
    # Restart the service
    ```
