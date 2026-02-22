# Unified Cross-Platform IPsec Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

A professional, enterprise-grade framework designed to standardize, automate, and orchestrate IPsec tunnel configurations across heterogeneous operating systems (Windows, Linux, and macOS).

---

## 📖 Table of Contents
1. [Overiew](#-overview)
2. [Value Proposition](#-value-proposition)
3. [Architecture](#-architecture)
4. [Tech Stack](#-tech-stack)
5. [Prerequisites](#-prerequisites)
6. [Installation](#-installation)
7. [Getting Started](#-getting-started)
8. [Orchestrator API](#-orchestrator-api)
9. [Agent Drivers](#-agent-drivers)
10. [Testing Suite](#-testing-suite)
11. [Deployment](#-deployment)
12. [Directory Structure](#-directory-structure)
13. [Roadmap](#-roadmap)
14. [Security Considerations](#-security-considerations)
15. [Contributing](#-contributing)

---

## 📌 Overview

The **Unified IPsec Framework** solves the critical problem of configuration fragmentation in VPN management. Traditionally, network administrators manually manage separate configurations for Windows (PowerShell), Linux (strongSwan), and macOS. This framework introduces a **Central Orchestrator** (the Hub) which defines consistent security policies and **Lightweight Agents** (the Spokes) that automatically enforce those policies on the endpoints.

### Key Features
*   **Centralized Policy Engine**: Define encryption (AES-GCM), integrity (SHA-2), and DH groups in one JSON-based model.
*   **Automatic Enrollment**: Agents register themselves and retrieve assigned policies securely.
*   **Cross-Platform Driver Abstraction**: OS-specific drivers translate high-level policies into low-level stack commands (WFP on Windows, XFRM on Linux).
*   **Health Monitoring**: Real-time heartbeat and SA status reporting.
*   **IKEv2 Focused**: Built exclusively on modern, secure protocols (RFC 7296).

---

## 💰 Value Proposition

*   **Operational Efficiency**: Reduce configuration time from hours to seconds across multi-OS fleets.
*   **Security Compliance**: Ensure 100% policy alignment across all endpoints. No more "encryption mismatch" errors.
*   **Auditability**: A single database serves as the authoritative record of every VPN tunnel in the infrastructure.
*   **Zero-Touch Provisioning**: Deploy an agent, provide a token, and the tunnel is established automatically.

---

## 🏗 Architecture

The framework uses a **Hub-and-Spoke** architecture communicating over a secure REST API.

    subgraph "Central Orchestrator (FastAPI)"
        API[REST API Layer]
        DB[(SQLAlchemy DB)]
        PolicyEngine[Policy Translation Logic]
        API --> DB
        API --> PolicyEngine
    end

    subgraph "Device Agents (Python)"
        subgraph "Windows Endpoint"
            WinAgent[Agent Core]
            WinDriver[PowerShell Driver]
            WinAgent --> WinDriver
        end

        subgraph "Linux Endpoint"
            LinAgent[Agent Core]
            LinDriver[strongSwan Driver]
            LinAgent --> LinDriver
        end
    end

    API -- "REST / JSON" --- WinAgent
    API -- "REST / JSON" --- LinAgent

    WinDriver -- "NetSecurity" --- WFP[Windows Filtering Platform]
    LinDriver -- "ipsec.conf" --- Charon[strongSwan Charon]
```

### Components
1.  **Orchestrator**: A FastAPI service managing the state of `Devices` and `Policies`.
2.  **Agent**: A resident service on the endpoint that polls the Orchestrator for policy updates.
3.  **Platform Drivers**: OS-specific managers that interface with the local IPsec stack.

---

## 💻 Tech Stack

*   **Backend**: Python 3.10+, FastAPI, Uvicorn.
*   **Database**: SQLAlchemy ORM (SQLite for dev, PostgreSQL ready).
*   **Windows Agent**: PowerShell NetSecurity module, `subprocess` integration.
*   **Linux Agent**: `strongSwan` (Charon daemon), `/etc/ipsec.conf` generation.
*   **Security**: Pydantic for schema validation, IKEv2 for key exchange.

---

## 📋 Prerequisites

### General
*   **Python 3.10** or higher.
*   A network-reachable server for the Orchestrator.

### Windows Agent
*   **Windows 10/11 Pro/Enterprise** or **Windows Server 2016+**.
*   **Execution Policy**: Must allow PowerShell scripts (e.g., `Set-ExecutionPolicy RemoteSigned`).
*   **Privileges**: Must run as **Administrator**.

### Linux Agent
*   **Distribution**: Ubuntu 20.04+, Debian 11+, or RHEL 8+.
*   **Software**: `strongSwan` installed (`sudo apt install strongswan`).
*   **Privileges**: Must run as **root**.

---

## 📥 Installation

### 1. Clone the Archive
```bash
git clone https://github.com/your-org/IPSec_Framework.git
cd IPSec_Framework
```

### 2. Virtual Environment Setup
```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# Linux
source venv/bin/activate
```

### 3. Dependency Installation
```bash
# Orchestrator Dependencies
pip install -r orchestrator/requirements.txt
# Agent Dependencies
pip install -r agent/requirements.txt
```

---

## 🚀 Getting Started

### 1. Launch the Orchestrator
The orchestrator initializes a local SQLite database (`ipsec_orchestrator.db`) on first run.
```bash
python -m orchestrator.main
```
*   **API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
*   **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Configure Environment Variables (Agent)
```powershell
# Windows
$env:ORCHESTRATOR_URL="http://127.0.0.1:8000"
$env:ENROLLMENT_TOKEN="your-secret-token"
```
```bash
# Linux
export ORCHESTRATOR_URL="http://127.0.0.1:8000"
export ENROLLMENT_TOKEN="your-secret-token"
```

### 3. Launch the Agent
```bash
# Run as Admin/Root
python -m agent.main
```

---

## 📡 Orchestrator API

The Orchestrator provides a full CRUD API for managing tunnels.

### Devices
*   `GET /devices/`: List all enrolled devices.
*   `POST /enroll/`: Register a new agent using a token.
*   `GET /devices/{id}/policy`: Retrieve the currently assigned policy for a device.

### Policies
*   `GET /policies/`: List all defined IPsec policies.
*   `POST /policies/`: Create a new policy (Encryption, Networks, PSK).
*   `PUT /devices/{id}/assign-policy/{policy_id}`: Map a policy to a target device.

---

## 🛠 Agent Drivers

### Windows Driver (`agent/platforms/windows.py`)
Uses the `New-NetIPsecRule` PowerShell command to create rules in the Windows Filtering Platform (WFP). It automatically handles rule cleanup and re-creation to prevent stale configurations.

### Linux Driver (`agent/platforms/linux.py`)
Generates standardized `ipsec.conf` and `ipsec.secrets` files for strongSwan. It initiates an `ipsec restart` or `ipsec reload` signal to apply changes without dropping existing unrelated traffic (using `auto=start`).

---

## 🧪 Testing Suite

We provide a comprehensive test suite to validate the entire lifecycle.

### Automated Test Scenario
The `test_scenario.py` script simulates an administrator's actions:
1.  Creates a test policy in the Orchestrator.
2.  Assigns it to the enrolled agent.
3.  Verifies the agent picks up the change.

```bash
python test_scenario.py
```

### Manual Verification
*   **Windows**: `Get-NetIPsecMainModeSA` to see active IKE negotiations.
*   **Linux**: `sudo ipsec statusall` to see established security associations.
*   **Network**: `ping <remote_peer_ip>` should traverse the encrypted tunnel.

---

## 🚀 Deployment

### Local Development
*   Use the default SQLite database.
*   Run the agent with `mock_drivers=True` (if implemented) for testing without changing OS rules.

### Production Production
*   **Database**: Point `DATABASE_URL` to a PostgreSQL instance.
*   **Security**: Use HTTPS for the Orchestrator API.
*   **Authentication**: Use X.509 Certificates instead of PSKs for device enrollment and tunnel auth.

---

## 📂 Directory Structure

```text
├── agent/                  # Agent logic
│   ├── platforms/          # OS-Specific Drivers (Win/Linux)
│   ├── utils/              # Heartbeat and API clients
│   └── main.py             # Agent entry point
├── orchestrator/           # Backend logic
│   ├── routers/            # API Endpoints (FastAPI)
│   ├── models.py           # SQLAlchemy Data Models
│   ├── schemas.py          # Pydantic Schemas
│   └── main.py             # Server entry point
├── shared/                 # Common models and constants
├── test_scenario.py        # Integration test script
├── Project_Synopsis.docx   # Detailed project document
└── README.md               # You are here
```

---

## 🗓 Roadmap

- [x] Core FastAPI Orchestrator.
- [x] Windows & Linux Agent Drivers.
- [ ] **macOS Support**: Integration with NetworkExtension API.
- [ ] **Dashboard**: React-based UI for tunnel visualization.
- [ ] **Certificate Manager**: Automated Let's Encrypt / Internal CA integration.
- [ ] **MFA Integration**: Identity-aware tunnel establishment.

---

## 🔒 Security Considerations

1.  **Credential Storage**: Ensure the `psk_secret` in the database is encrypted using a KMS or Vault.
2.  **API Security**: The enrollment token should be short-lived or single-use in high-security environments.
3.  **Cipher Selection**: Avoid `3DES` and `SHA1`. Refer to [RFC 8221](https://tools.ietf.org/html/rfc8221) for current cryptographic recommendations.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/awesome-feature`).
3.  Commit your changes.
4.  Push to the branch.
5.  Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📚 References
*   [RFC 7296 (IKEv2)](https://tools.ietf.org/html/rfc7296)
*   [strongSwan Documentation](https://docs.strongswan.org/)
*   [Microsoft NetSecurity Docs](https://learn.microsoft.com/en-us/powershell/module/netsecurity/)
