# 🐧 IPsec Agent: Linux Deployment Guide

This guide describes how to deploy and run the IPsec Agent on a Linux machine to connect to the central Orchestrator (on Render).

---

## 🏗 Understanding the Flow

- **The Brain**: Central Orchestrator (FastAPI/Docker) deployed on **Render**.
- **The Hands**: Local Agent (Python) running on your **Linux** machine.
- **The Connection**: The Agent polls the Orchestrator for encryption policies and applies them locally using **strongSwan**.

---

## 🛠 Prerequisites

- **OS**: Ubuntu 20.04+, Debian 11+, or RHEL 8+.
- **Software**: **strongSwan** must be installed.
- **Permissions**: Root or `sudo` privileges are **mandatory** to modify IPsec configurations.

---

## 🚀 Step-by-Step Setup

### 1. Install strongSwan
Install the necessary IPsec components:
```bash
sudo apt update && sudo apt install strongswan -y
```

### 2. Prepare the Environment
Clone the repository and set up a Python virtual environment:
```bash
git clone https://github.com/c0d3d3m0n/IPSec.git
cd IPSec
python3 -m venv venv
source venv/bin/activate
pip install -r agent/requirements.txt
```

### 3. Configure and Launch
Run the agent as root. It will automatically point to the deployed Orchestrator and prompt you for the enrollment token:
```bash
sudo venv/bin/python3 -m agent.main
```

---

## 🔍 Verification & Logs

- **Interactive Setup**: When prompted, paste your **Enrollment Token** (characters will be hidden for security).
- **Check Enrollment**: Once started, you should see "Device enrolled successfully" in the console.
- **Check Status**: Run `sudo ipsec statusall` to see established security associations.
- **Troubleshooting**:
  - *Permission Denied*: Ensure you are running with `sudo`.
  - *No policy assigned*: Go to your Orchestrator Swagger UI (`/docs`) and assign a policy to this device ID.
