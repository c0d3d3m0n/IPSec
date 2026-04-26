# 🧭 Policy Routing & Driver Dispatch Guide

This guide covers Phase 3 of the framework: parsing uploaded policy JSON, normalizing crypto names, generating OS-specific configs, and dispatching the correct native driver block on each agent.

---

## What Changed in Phase 3

The policy pipeline now works in two stages:

1. The orchestrator parses the uploaded policy JSON and validates structure, crypto aliases, target OS values, and connection fields.
2. The agent requests an OS-specific config and applies only the native driver block for its platform.

This prevents Windows policy syntax from reaching Linux agents and vice versa.

---

## Policy Upload Flow

### Endpoint

`POST /api/policies/upload`

### Input

The upload endpoint accepts a JSON file with these required top-level keys:

- `policy_id`
- `version`
- `target`
- `ipsec_policy`
- `execution`
- `compliance`

### Parser Behavior

The parser will:

- Reject invalid UTF-8 or malformed JSON.
- Require `target.os` to contain only `linux`, `windows`, or `macos`.
- Normalize encryption, integrity, and DH group aliases to canonical names.
- Warn on weak algorithms unless strong crypto is required.
- Warn when integrity is omitted for non-AEAD encryption.
- Validate every connection entry for required fields.
- Build per-OS config blocks for Linux, Windows, and macOS.

### Stored Data

When validation succeeds, the orchestrator stores:

- The original policy JSON.
- `input_hash` for SHA-512 traceability.
- `parse_warnings` for non-fatal issues.
- `per_os_configs` for platform-specific delivery.

---

## OS-Specific Delivery

### Linux

Linux agents receive a strongSwan-style config structure containing:

- `charon` proposals
- `connections`
- `children`
- `secrets`

The agent writes the generated config to `swanctl.conf` and runs `swanctl --load-all --noprompt`.

### Windows

Windows agents receive a PowerShell command list containing cmdlets such as:

- `New-NetIPsecMainModeRule`
- `New-NetIPsecMainModeCryptoSet`
- `New-NetIPsecQuickModeCryptoSet`

The agent executes each cmdlet with `powershell -NonInteractive -Command`.

Current Windows PSK tunnel flow applied by `agent/drivers/dispatcher.py`:

1. Cleanup existing rule and crypto/auth objects by deterministic names.
2. Step 1/6: Create `Phase1AuthSet` using PSK.
3. Step 2/6: Create `MainModeCryptoSet` with mapped Windows DH group.
4. Step 3/6: Skip `Phase2AuthSet` for PSK IKEv2 tunnels.
5. Step 4/6: Create `QuickModeCryptoSet` with ESP hash and encryption.
6. Step 5/6: Create `NetIPsecRule` in tunnel mode with inbound/outbound security required.
7. Step 6/6: Create `MainModeRule` linking Phase1 auth and MainMode crypto.

Notes:

- `New-NetIPsecQuickModeCryptoProposal` does not use a PFS parameter in this implementation.
- Windows-friendly parser output maps values like `AES_CBC_256 -> AES256` and `HMAC_SHA2_256 -> SHA256`.

### macOS

macOS agents receive a racoon-style remote block structure.
The agent writes `racoon.conf` and reloads the configuration.

---

## Device Config Fetch

### Endpoint

`GET /api/devices/{device_id}/config?os_type=linux|windows|macos`

### Responses

- If no policy is assigned: the orchestrator returns a `404` with `action_required=contact_admin`.
- If the assigned policy does not include the requested OS: the orchestrator returns a `409` and lists the available OS targets.
- If `os_type` is omitted: the orchestrator returns the full stored config for backward compatibility.
- If `os_type` is present and supported: the orchestrator returns the OS-specific config payload.

---

## Example Policies

Two sample policies are included in the repository:

- [examples/policy_all_os.json](../examples/policy_all_os.json)
- [examples/policy_linux_only.json](../examples/policy_linux_only.json)

Use them to verify alias normalization and platform-specific output.

---

## Troubleshooting

- If upload fails with `422`, review the returned `errors` and `warnings` fields.
- If a device receives `409`, update the policy target OS list to include that platform.
- If a driver fails on the agent, the dispatcher logs the native command or file write error and the agent reports the failure back to the orchestrator.

---

## Related Docs

- [USAGE_GUIDE.md](USAGE_GUIDE.md)
- [ZERO_TRUST_SETUP.md](ZERO_TRUST_SETUP.md)
- [COMPLIANCE_AND_MONITORING.md](COMPLIANCE_AND_MONITORING.md)
