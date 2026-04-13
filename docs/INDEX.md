# 📚 Documentation Index & Navigation Guide

Complete guide to all documentation in the IPSec Framework. Start here to find what you need.

---

## 🎯 Get Started Based on Your Role

### I'm a System Administrator Setting Up the Framework

**Start with these in order**:
1. [USAGE_GUIDE.md](USAGE_GUIDE.md) - **Read first** - Complete walkthrough of all features
   - How to set up orchestrator
   - How to enroll devices
   - How to manage policies
   - Troubleshooting common issues

2. [DEPLOYMENT_LINUX.md](DEPLOYMENT_LINUX.md) - Deploy orchestrator on Linux
3. [DEPLOYMENT_VERCEL.md](DEPLOYMENT_VERCEL.md) - Deploy orchestrator on cloud (Render/Vercel)
4. [AGENT_REGISTRATION.md](AGENT_REGISTRATION.md) - Register agents on devices

**Then learn about security**:
- [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md) - Understand Zero Trust model
- [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md) - Security deep dive
- [POLICY_ROUTING_AND_DRIVERS.md](POLICY_ROUTING_AND_DRIVERS.md) - Phase 3 policy parsing and native driver dispatch

---

### I'm a Network Engineer Implementing Policies

**Recommended reading order**:
1. [USAGE_GUIDE.md](USAGE_GUIDE.md#policy-management) - Policy management section
2. [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#security-association-monitoring) - SA monitoring
3. [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#leak-detection) - Leak detection
4. [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md) - For cryptographic details

---

### I'm a Security Officer / Compliance Manager

**Recommended reading order**:
1. [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md) - **Start here**
   - Heartbeat & health monitoring
   - Compliance reporting
   - SA monitoring
   - Leak detection
   - Audit logs

2. [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md) - Deep security review
   - Threat model analysis
   - Attack vector mitigations
   - Cryptographic algorithms
   - Incident response procedures

3. [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#trust-scoring-model) - Trust scoring details

---

### I'm a Developer Debugging or Extending the Framework

**Recommended reading order**:
1. [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#component-breakdown) - Component architecture
2. [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#cryptographic-algorithms) - Algorithms reference
3. [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#troubleshooting) - Troubleshooting guide
4. [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#api-reference) - API reference

---

## 📖 Documentation Files

### [USAGE_GUIDE.md](USAGE_GUIDE.md)
**Length**: ~2,500 lines | **Depth**: Comprehensive | **For**: Everyone

Complete end-to-end guide covering:
- ✅ Initial setup (orchestrator + agents)
- ✅ Admin dashboard & MFA setup
- ✅ Device enrollment & verification
- ✅ Zero Trust configuration
- ✅ Policy management
- ✅ Compliance monitoring
- ✅ Audit logs
- ✅ Rate limiting
- ✅ Troubleshooting section
- ✅ API reference

**Best for**: First-time users, operational guides, day-to-day usage

---

### [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md)
**Length**: ~2,000 lines | **Depth**: Very Deep | **For**: Security architects, developers

Deep technical reference for Zero Trust implementation:
- ✅ Zero Trust principles (7 core principles explained)
- ✅ Architecture overview (with diagram)
- ✅ Component breakdown (CA, Token Manager, TOTP, mTLS Client, Trust Evaluator)
- ✅ Cryptographic stack (algorithms, key sizes, security analysis)
- ✅ Setup & configuration (phase-by-phase)
- ✅ Trust scoring model (detailed algorithm with examples)
- ✅ Certificate lifecycle (generation → storage → usage → refresh → revocation)
- ✅ Token management (access + refresh tokens, rotation)
- ✅ Troubleshooting

**Best for**: Understanding how Zero Trust works, implementing security features, debugging certificate/token issues

---

### [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md)
**Length**: ~1,800 lines | **Depth**: Comprehensive | **For**: Operations, compliance

Complete reference for Phase 1 telemetry & monitoring:
- ✅ Heartbeat system (configuration, endpoints, offline detection)
- ✅ Compliance reporting (what gets reported, checks performed)
- ✅ SA monitoring (metrics, lifecycle, health status)
- ✅ Leak detection (how it works, configuration, alerts, responses)
- ✅ Audit logs (what gets logged, chain integrity, verification)
- ✅ Rate limiting (limits per endpoint, handling errors)
- ✅ API reference (all endpoints, response formats)
- ✅ Dashboard views (what each page shows)

**Best for**: Setting up monitoring, understanding compliance system, incident response

---

### [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md)
**Length**: ~2,200 lines | **Depth**: Expert Level | **For**: Security engineers, auditors, architects

Comprehensive security reference:
- ✅ Security layers (5 layers: Transport, Auth, AuthZ, Data, Audit)
- ✅ Threat model (7 threats analyzed with mitigations)
- ✅ Cryptographic algorithms (with rationale & strength analysis)
- ✅ Key management (lifecycle, storage, rotation, protection)
- ✅ Attack vectors & mitigations (8 vectors with response strategies)
- ✅ Security assumptions (what must be true for security to hold)
- ✅ Incident response (3 scenarios: admin compromise, device compromise, orchestrator breach)
- ✅ Security metrics & KPIs (what to monitor)

**Best for**: Security audit, threat assessment, incident response planning, cryptographic validation

---

### [AGENT_REGISTRATION.md](AGENT_REGISTRATION.md)
**Length**: ~200 lines | **Depth**: Simple | **For**: New users setting up devices

Quick guide to device enrollment:
- ✅ Two-step process (pre-activation + agent activation)
- ✅ Dashboard steps (create device)
- ✅ Agent steps (Windows with admin rights, Linux)
- ✅ Verification (check device is active)
- ✅ Troubleshooting (common enrollment issues)

**Best for**: Quick reference on enrolling first devices

---

### [DEPLOYMENT_LINUX.md](DEPLOYMENT_LINUX.md)
**Length**: ~400 lines | **Depth**: Practical | **For**: Linux operators

Linux deployment guide:
- ✅ System requirements
- ✅ Installation steps
- ✅ Configuration
- ✅ Running orchestrator
- ✅ Systemd integration
- ✅ Docker deployment
- ✅ Troubleshooting

**Best for**: Deploying orchestrator on Linux servers

---

### [DEPLOYMENT_VERCEL.md](DEPLOYMENT_VERCEL.md)
**Length**: ~300 lines | **Depth**: Practical | **For**: Cloud operators

Cloud deployment guide (Vercel/Render):
- ✅ Setup steps
- ✅ Configuration
- ✅ Database setup (PostgreSQL)
- ✅ Environment variables
- ✅ Verification
- ✅ Troubleshooting

**Best for**: Fast cloud deployment in minutes

---

## 🗂️ Documentation Structure by Topic

### Getting Started
| Topic | File | Section |
|-------|------|---------|
| First time setup | [USAGE_GUIDE.md](USAGE_GUIDE.md#initial-setup) | "Initial Setup" |
| Quick deployment | [DEPLOYMENT_VERCEL.md](DEPLOYMENT_VERCEL.md) | Full guide |
| Linux deployment | [DEPLOYMENT_LINUX.md](DEPLOYMENT_LINUX.md) | Full guide |
| Device enrollment | [AGENT_REGISTRATION.md](AGENT_REGISTRATION.md) | Full guide |

### Administration & Operations
| Topic | File | Section |
|-------|------|---------|
| Admin dashboard | [USAGE_GUIDE.md](USAGE_GUIDE.md#admin-dashboard--mfa-setup) | "Admin Dashboard & MFA Setup" |
| MFA setup | [USAGE_GUIDE.md](USAGE_GUIDE.md#step-2-set-up-admin-totp-mfa) | "Set Up Admin TOTP MFA" |
| Device management | [USAGE_GUIDE.md](USAGE_GUIDE.md#device-enrollment) | "Device Enrollment" |
| Policy management | [USAGE_GUIDE.md](USAGE_GUIDE.md#policy-management) | "Policy Management" |
| Policy routing | [POLICY_ROUTING_AND_DRIVERS.md](POLICY_ROUTING_AND_DRIVERS.md) | "Policy Routing & Driver Dispatch" |
| Monitoring | [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md) | All sections |
| Heartbeat | [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#heartbeat-system) | "Heartbeat System" |
| Compliance | [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#compliance-reporting) | "Compliance Reporting" |

### Security & Architecture
| Topic | File | Section |
|-------|------|---------|
| ZT principles | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#zero-trust-principles) | "Zero Trust Principles" |
| ZT architecture | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#architecture-overview) | "Architecture Overview" |
| Components | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#component-breakdown) | "Component Breakdown" |
| Trust scoring | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#trust-scoring-model) | "Trust Scoring Model" |
| Certificates | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#certificate-lifecycle) | "Certificate Lifecycle" |
| Policy parsing | [POLICY_ROUTING_AND_DRIVERS.md](POLICY_ROUTING_AND_DRIVERS.md) | "Policy Routing & Driver Dispatch" |
| Cryptography | [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#cryptographic-algorithms) | "Cryptographic Algorithms" |
| Threat model | [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#threat-model) | "Threat Model" |
| Incident response | [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#incident-response) | "Incident Response" |

### Troubleshooting & Reference
| Topic | File | Section |
|-------|------|---------|
| Common issues | [USAGE_GUIDE.md](USAGE_GUIDE.md#troubleshooting) | "Troubleshooting" |
| API testing | [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md) | Full guide |
| Connection issues | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#troubleshooting) | "Troubleshooting" |
| Certificate issues | [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#troubleshooting) | "Certificate Verification Failures" |
| API reference | [USAGE_GUIDE.md](USAGE_GUIDE.md#advanced-api-reference) | "API Reference" |
| Compliance API | [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#api-reference) | "API Reference" |
| Attack responses | [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#incident-response) | "Incident Response" |

---

## 🔍 Finding Specific Information

### I need to understand...

**Device Trust**
- → [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#trust-scoring-model) | "Trust Scoring Model"

**How Certificates Work**
- → [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#certificate-lifecycle) | "Certificate Lifecycle"

**Encryption Details**
- → [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#cryptographic-algorithms) | "Cryptographic Algorithms"

**Heartbeat System**
- → [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#heartbeat-system) | "Heartbeat System"

**SA Monitoring**
- → [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#security-association-monitoring) | "SA Monitoring"

**Leak Detection**
- → [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#leak-detection) | "Leak Detection"

**Admin MFA**
- → [USAGE_GUIDE.md](USAGE_GUIDE.md#step-2-set-up-admin-totp-mfa) | "Set Up Admin TOTP MFA"

**Device Enrollment**
- → [AGENT_REGISTRATION.md](AGENT_REGISTRATION.md) | Full guide (2 pages)
- → [USAGE_GUIDE.md](USAGE_GUIDE.md#device-enrollment) | Detailed guide

**Policy Routing**
- → [POLICY_ROUTING_AND_DRIVERS.md](POLICY_ROUTING_AND_DRIVERS.md) | "Policy Routing & Driver Dispatch"

**Threat Model**
- → [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#threat-model) | "Threat Model"

**Incident Response**
- → [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#incident-response) | "Incident Response"

**API Endpoints**
- → [USAGE_GUIDE.md](USAGE_GUIDE.md#advanced-api-reference) | "API Reference"
- → [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#api-reference) | "API Reference"

**Rate Limiting**
- → [USAGE_GUIDE.md](USAGE_GUIDE.md#rate-limiting--dos-protection) | "Rate Limiting & DoS Protection"

**Troubleshooting**
- → [USAGE_GUIDE.md](USAGE_GUIDE.md#troubleshooting) | General troubleshooting (50 lines)
- → [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#troubleshooting) | Security troubleshooting (100 lines)

---

## 📊 Documentation Statistics

| Document | Lines | Topics | Diagrams | Tables |
|----------|-------|--------|----------|--------|
| USAGE_GUIDE.md | ~2,500 | 10 major sections | 1 | 8 |
| ZERO_TRUST_SETUP.md | ~2,000 | 9 major sections | 1 | 5 |
| COMPLIANCE_AND_MONITORING.md | ~1,800 | 8 major sections | 2 | 10 |
| SECURITY_ARCHITECTURE.md | ~2,200 | 8 major sections | 1 | 12 |
| AGENT_REGISTRATION.md | ~200 | 2 major sections | 0 | 0 |
| DEPLOYMENT_LINUX.md | ~400 | 5 major sections | 0 | 1 |
| DEPLOYMENT_VERCEL.md | ~300 | 4 major sections | 0 | 0 |
| **TOTAL** | **~9,400** | **46 topics** | **5** | **36** |

---

## 📝 Document Conventions

### Notation Used Across Documentation

**File Paths**:
```
/path/to/file.py          - Absolute path
orchestrator/main.py      - Relative path
~/.ipsec/device.crt       - User home directory
```

**Code Examples**:
```bash
# Bash/shell commands
curl -X GET http://localhost:8000/api/devices/

# Python code
python -m agent.main
```

**JSON Responses**:
```json
{
  "status": "success",
  "data": {...}
}
```

**API Endpoints**:
```
GET /api/devices/
POST /api/policies/
```

**Configuration**:
```python
# Python configuration
VARIABLE_NAME = "value"
```

**Alert Symbols**:
- 🔐 Security-related
- ⚠️ Warning / Important
- ℹ️ Information
- ✅ Completed / Success
- ❌ Failed / Error
- 🔧 Configuration
- 📊 Monitoring
- 🚀 Getting started
- 📚 Documentation

---

## 🤝 Contributing to Documentation

To update documentation:
1. Make changes to relevant `.md` file
2. Ensure formatting is consistent
3. Test all links and code examples
4. Submit PR with documentation changes

---

## ❓ FAQ - Quick Answers

**Q: Where do I start?**
A: If new to the framework, start with [USAGE_GUIDE.md](USAGE_GUIDE.md)

**Q: How do I deploy?**
A: Choose Linux ([DEPLOYMENT_LINUX.md](DEPLOYMENT_LINUX.md)) or Cloud ([DEPLOYMENT_VERCEL.md](DEPLOYMENT_VERCEL.md))

**Q: How do I add a device?**
A: See [AGENT_REGISTRATION.md](AGENT_REGISTRATION.md) or [USAGE_GUIDE.md](USAGE_GUIDE.md#device-enrollment)

**Q: How does Zero Trust work?**
A: Read [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#zero-trust-principles) first, then [Trust Scoring](ZERO_TRUST_SETUP.md#trust-scoring-model)

**Q: What are the security features?**
A: See [USAGE_GUIDE.md](USAGE_GUIDE.md#zero-trust-configuration) and [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md)

**Q: How do I monitor compliance?**
A: Read [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md) (all sections)

**Q: What happens if a device gets hacked?**
A: See [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md#scenario-2-device-certificate-compromised)

**Q: How do I troubleshoot issues?**
A: See [USAGE_GUIDE.md](USAGE_GUIDE.md#troubleshooting) or [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md#troubleshooting)

**Q: Where is the API documentation?**
A: See [USAGE_GUIDE.md](USAGE_GUIDE.md#advanced-api-reference) or [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md#api-reference)

---

## 📞 Need Help?

- **Setup Issues**: → [USAGE_GUIDE.md - Troubleshooting](USAGE_GUIDE.md#troubleshooting)
- **Connection Issues**: → [ZERO_TRUST_SETUP.md - Troubleshooting](ZERO_TRUST_SETUP.md#troubleshooting)
- **Security Questions**: → [SECURITY_ARCHITECTURE.md](SECURITY_ARCHITECTURE.md)
- **API Questions**: → Search the documentation index above or relevant document
