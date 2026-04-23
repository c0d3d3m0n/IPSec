# 🤖 Agent Registration & Activation Guide

This guide explains the two-part device onboarding flow in the Unified IPsec Console.

---

## 🔐 The Two-Step Process

The system uses a secure pre-registration flow first, then the local agent enrolls itself using that record.

### Step 1: Pre-register the device in the Dashboard (Admin)
1. Open the **Admin Dashboard**.
2. Log in as admin.
3. Click **Pre-register Device**.
4. Fill in only these fields:
    - **Enrollment Number**: A unique device label, for example `OFFICE-01`.
    - **Enrollment Token**: A secret token for that device, for example `my_secret_key`.
    - **Pre-shared Key**: Usually the same value as the enrollment token.
5. Click **Register**.
6. The device record will be created in **PENDING** state.

### Step 2: Run the agent on the device

> [!IMPORTANT]
> On Windows, open PowerShell **as Administrator**.

1. Open an elevated PowerShell window.
2. Go to the agent folder:
    ```powershell
    Set-Location E:\PROJECTS\IPSec_Framework\agent
    ```
3. Install dependencies if needed:
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```
4. Set these environment variables:
    ```powershell
    $env:ORCHESTRATOR_URL = "https://api.ipsecvault.tech/api"
    $env:ENROLLMENT_NUMBER = "OFFICE-01"
    $env:ENROLLMENT_TOKEN = "my_secret_key"
    $env:PRE_SHARED_KEY = "my_secret_key"
    ```
5. Start the agent:
    ```powershell
    python main.py
    ```
6. The agent automatically generates the fingerprint and signature, enrolls, saves certificates, and begins polling the backend.

---

## ✅ Verification
1. Return to the Dashboard.
2. The device should move from **PENDING** to **ACTIVE**.
3. Hostname, OS type, and public IP should appear after the first enrollment/heartbeat.
4. Assign a policy to start VPN/IPsec enforcement.

---

## 🔍 Troubleshooting
- **Invalid credentials**: Check that the enrollment number and token exactly match the pre-registered record.
- **Enrollment rejected**: Make sure `PRE_SHARED_KEY` matches the pre-registered value.
- **Connection error**: Confirm the backend is reachable at `/api`.
