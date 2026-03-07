# 🤖 Agent Registration & Activation Guide

This guide explains how to register a new device using the **Unified IPsec Console** and activate the local **Agent**.

---

## 🔐 The Two-Step Process

The framework uses a secure "Pre-activation" flow to ensure only authorized devices can join the network.

### Step 1: Pre-activate in the Dashboard (Admin)
1.  Open the **Admin Dashboard** ([http://localhost:3000](http://localhost:3000)).
2.  Log in (Default: `admin` / `admin123`).
3.  Click the **"Pre-activate Device"** button in the top right.
4.  Enter the following details:
    - **Enrollment Number**: A unique identifier for the machine (e.g., `DELL-XL-01`, `PROD-SRV-Linux`).
    - **Secret Activation Token**: A strong password or token for this specific device.
5.  Click **Register**. The device will now appear in the list with a status of **`PENDING`**.

---

### Step 2: Activate the Agent (Local Machine)

> [!IMPORTANT]
> **Windows Requirement**: You **MUST** run your terminal as **Administrator**. Configuring IPsec policies requires high-level system permissions.

1.  **Open an Elevated Terminal**: Right-click your terminal (PowerShell or CMD) and select **"Run as Administrator"**.
2.  Navigate to the `agent/` directory on your local machine.
2.  Run the Agent:
    ```bash
    python -m agent.main
    ```
3.  The console will prompt you:
    - **Enter Secret Enrollment Token**: Paste the token you created in the dashboard (characters will be hidden).
    - **Enter Enrollment Number**: Type the exact identifier (e.g., `DELL-XL-01`).
4.  If successful, the agent will log: `Device enrolled successfully`.

---

## ✅ Verification
1.  Go back to the **Dashboard**.
2.  The device status should now be **`ACTIVE`**.
3.  You will see the machine's **Hostname**, **OS Type**, and **Public IP** automatically filled in.
4.  You can now assign a **Policy** to this device to establish the IPsec tunnel.

---

## 🔍 Troubleshooting
- **"Invalid credentials"**: Ensure the Enrollment Number and Token match *exactly* what was entered in the Dashboard.
- **Connection Error**: Double-check that your Orchestrator backend (Port 8000) is running and reachable.
