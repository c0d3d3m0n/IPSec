# Unified Cross-Platform IPsec Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

A professional, enterprise-grade framework designed to standardize, automate, and orchestrate IPsec tunnel configurations across heterogeneous operating systems (Windows, Linux, and macOS).

---

## 🏗 Architecture & Flow

```mermaid
graph TD
    subgraph "External Control"
        Admin[System Admin] --> Swagger[Swagger UI / API Docs]
    end

    subgraph "Cloud Infrastructure (Render/Docker)"
        Swagger --> Orchestrator[FastAPI Orchestrator]
        Orchestrator --> DB[(PostgreSQL)]
    end

    subgraph "Local Endpoints"
        AgentWin[Windows Agent] -- "Polls Policy (REST)" --> Orchestrator
        AgentLin[Linux Agent] -- "Polls Policy (REST)" --> Orchestrator
        
        AgentWin --> DriverWin[Windows Driver]
        DriverWin --> WFP[Windows Filtering Platform]
        
        AgentLin --> DriverLin[strongSwan Driver]
        DriverLin --> IPsec[Linux IPsec Stack]
    end

    style Orchestrator fill:#f9f,stroke:#333,stroke-width:2px
    style DB fill:#66f,stroke:#333,stroke-width:2px
    style Swagger fill:#dfd,stroke:#333,stroke-width:2px
```

## 📋 Project Status
- [x] **Core Orchestrator**: FastAPI backend with Swagger docs.
- [x] **Persistence**: PostgreSQL integration for cloud deployment.
- [x] **Containerization**: Full Docker support for the Orchestrator.
- [x] **Platform Drivers**: Native support for Windows (PowerShell) and Linux (strongSwan).
- [ ] **macOS Support**: Upcoming integration.

---

## 🚀 Quick Start

### 1. Cloud Deployment (The "Brain")
Deploy the Central Orchestrator to **Render** in minutes using the provided Blueprint:
- **Guide**: [Render Deployment Guide](.gemini/antigravity/brain/98ab75a3-4827-40e4-8942-4410cf362c23/DEPLOYMENT_GUIDE_RENDER.md)
- **Interactive Docs**: Access `/docs` on your deployed URL to manage policies via Swagger UI.

### 2. Local Setup (The "Hands")
To startEstablishing tunnels on your local machines:
- **Windows**: [Windows Agent Setup](.gemini/antigravity/brain/98ab75a3-4827-40e4-8942-4410cf362c23/AGENT_SETUP_GUIDE.md#windows-setup)
- **Linux**: [Linux Agent Setup](.gemini/antigravity/brain/98ab75a3-4827-40e4-8942-4410cf362c23/AGENT_SETUP_GUIDE.md#linux-setup)

---

## 💻 Tech Stack
*   **Orchestrator**: Python 3.10+, FastAPI, SQLAlchemy, PostgreSQL.
*   **Agent**: Lightweight Python residents with OS-native drivers.
*   **Infrastructure**: Docker, Render Blueprints.
*   **Security**: IKEv2 (IKEv2 Focused), AES-GCM, SHA-2.

---

## 📂 Directory Structure
```text
├── agent/                  # Device Agent logic
├── orchestrator/           # Central Orchestrator service
├── .dockerignore           # Optimized Docker build context
├── Dockerfile              # Container definition for Orchestrator
├── render.yaml             # Render infrastructure-as-code
└── README.md               # Overview and status
```

---

## 🤝 Contributing
Contributions are welcome! Please follow the standard fork/PR workflow.

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
