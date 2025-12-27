# Unified Cross-Platform IPsec Solution

A Python-based framework to standardize and automate IPsec tunnel configuration across heterogeneous environments (Windows, Linux, macOS).

## 📌 Overview

This project solves the problem of inconsistent IPsec management by providing a **Central Orchestrator** that defines policies and **Lightweight Agents** that enforce them on endpoints.

### Key Features
*   **Centralized Management**: Define policies (Networks, Encryption, Auth) in one place.
*   **Cross-Platform**:
    *   **Windows**: Uses PowerShell (`NetSecurity` module).
    *   **Linux**: Generates `strongSwan` configurations.
    *   **macOS**: (Planned) Uses System Configuration APIs.
*   **Automated**: Agents automatically pull and apply policies.
*   **Secure**: Supports IKEv2, AES-256, and PSK/Certificate authentication.

## 🏗 Architecture

```mermaid
graph TD
    subgraph Server
    Orchestrator[Python Orchestrator (FastAPI)]
    DB[(Database)]
    Orchestrator --> DB
    end

    subgraph Clients
    WinAgent[Windows Agent]
    LinAgent[Linux Agent]
    end

    Orchestrator -- REST API (JSON) --> WinAgent
    Orchestrator -- REST API (JSON) --> LinAgent

    WinAgent -- PowerShell --> WinIPsec[Windows IPsec Stack]
    LinAgent -- ipsec.conf --> StrongSwan[strongSwan Daemon]
```

## 🚀 Getting Started

### Prerequisites
*   **Python 3.10+**
*   **Windows**: Administrator privileges (for Agent).
*   **Linux**: Root privileges and `strongSwan` installed.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd IPSec_Framework
    ```

2.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\Activate.ps1
    # Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r orchestrator/requirements.txt
    pip install -r agent/requirements.txt
    ```

## 🛠 Usage

You need to run the **Orchestrator** and the **Agent** in separate terminals.

### 1. Start the Orchestrator (Server)
```bash
python -m orchestrator.main
```
*   Server runs at: `http://127.0.0.1:8000`
*   Docs available at: `http://127.0.0.1:8000/docs`

### 2. Start the Agent (Client)
> **Note**: Must be run as **Administrator** (Windows) or **Root** (Linux) to modify network rules.

```bash
python -m agent.main
```

## 🧪 Testing

We provide automated scripts to simulate an Admin creating and assigning a policy.

1.  Ensure Server and Agent are running.
2.  Run the test script:

    **Cross-Platform (Python)**:
    ```bash
    python test_scenario.py
    ```

    **Windows (PowerShell)**:
    ```powershell
    .\test_scenario.ps1
    ```

    **Linux/macOS (Bash)**:
    ```bash
    ./test_scenario.sh
    ```

3.  **Verify**:
    *   Check Agent logs for `Applying policy...`.
    *   **Windows**: `Get-NetIPsecRule -DisplayName "DemoPolicy_*"`
    *   **Linux**: `ipsec status`

## 📂 Project Structure

*   `orchestrator/`: FastAPI backend (API, DB, Models).
*   `agent/`: Client application.
    *   `platforms/`: OS-specific logic (`windows.py`, `linux.py`).
*   `shared/`: Shared utilities.

## 🧹 Cleanup

To remove test policies:
```powershell
# Windows
.\cleanup.ps1
```
