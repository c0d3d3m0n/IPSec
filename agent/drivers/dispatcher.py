from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ApplyResult:
    success: bool
    os: str
    message: str
    detail: str = ""


class DriverDispatcher:
    def __init__(self):
        self.os = self._detect_os()

    def _detect_os(self) -> str:
        current = platform.system()
        if current == "Linux":
            return "linux"
        if current == "Windows":
            return "windows"
        if current == "Darwin":
            return "macos"
        raise RuntimeError(f"Unsupported operating system: {current}")

    def apply(self, config_response: dict[str, Any]) -> ApplyResult:
        driver_block = config_response.get("driver_block") or {}
        if not driver_block:
            return ApplyResult(success=False, os=self.os, message="Empty driver_block")

        try:
            if self.os == "linux":
                return self._apply_linux(driver_block, config_response)
            if self.os == "windows":
                return self._apply_windows(driver_block, config_response)
            return self._apply_macos(driver_block, config_response)
        except Exception as exc:
            logger.exception("Driver application failed")
            return ApplyResult(success=False, os=self.os, message="Driver application failed", detail=str(exc))

    def _apply_linux(self, driver_block: dict[str, Any], config: dict[str, Any]) -> ApplyResult:
        try:
            conf_text = self._render_swanctl_conf(driver_block)
            conf_path = Path("/etc/swanctl/swanctl.conf")
            conf_path.parent.mkdir(parents=True, exist_ok=True)
            conf_path.write_text(conf_text, encoding="utf-8")

            load_result = subprocess.run(["swanctl", "--load-all", "--noprompt"], capture_output=True, text=True, check=False)
            if load_result.returncode != 0:
                return ApplyResult(success=False, os=self.os, message="Failed to load swanctl configuration", detail=(load_result.stderr or load_result.stdout or ""))

            connections = driver_block.get("connections") or {}
            initiated = 0
            for connection_name, connection in connections.items():
                child_name = f"{connection_name}-child"
                start_action = ((connection.get("children") or {}).get(child_name) or {}).get("start_action")
                if start_action == "start":
                    init_result = subprocess.run(["swanctl", "--initiate", f"--child={child_name}"], capture_output=True, text=True, check=False)
                    if init_result.returncode != 0:
                        return ApplyResult(success=False, os=self.os, message=f"Failed to initiate {child_name}", detail=(init_result.stderr or init_result.stdout or ""))
                    initiated += 1

            return ApplyResult(success=True, os=self.os, message=f"{len(connections)} connections loaded")
        except Exception as exc:
            logger.exception("Linux driver application error")
            return ApplyResult(success=False, os=self.os, message="Linux driver application failed", detail=str(exc))

    def _apply_windows(self, driver_block: dict[str, Any], config: dict[str, Any]) -> ApplyResult:
        # Windows NetSecurity cmdlets require an elevated (Administrator) PowerShell session.
        connections = config.get("connections") or []
        ike_enc = config.get("ike_encryption")
        ike_int = config.get("ike_integrity")
        ike_dh = config.get("ike_dh_group")
        esp_enc = config.get("esp_encryption")
        esp_int = config.get("esp_integrity")
        esp_dh = config.get("esp_dh_group")

        auth_secret_ref = str(driver_block.get("auth_secret_ref") or config.get("auth_secret_ref") or "")
        psk = os.environ.get(auth_secret_ref, auth_secret_ref)

        logger.info(f"Windows IPSec policy application started: {len(connections)} connection(s)")
        logger.info(f"IKE crypto: {ike_enc}/{ike_int}/{ike_dh}")
        logger.info(f"ESP crypto: {esp_enc}/{esp_int}/{esp_dh}")

        if not (connections and ike_enc and ike_int and ike_dh and esp_enc and esp_int and esp_dh and psk):
            return ApplyResult(
                success=False,
                os=self.os,
                message="Invalid Windows policy payload",
                detail="Missing connections/crypto/auth values",
            )

        def _run_powershell_step(step_label: str, command_text: str) -> tuple[bool, str]:
            logger.info(step_label)
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command_text],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                logger.error("%s FAILED: %s", step_label, detail)
                return False, detail
            logger.info("%s OK", step_label)
            return True, ""

        try:
            executed = 0
            for connection in connections:
                conn_name = str(connection.get("name") or "ipsec")
                local_ip = connection.get("local_ip")
                remote_ip = connection.get("remote_ip")
                local_subnet = connection.get("local_subnet")
                remote_subnet = connection.get("remote_subnet")
                ike_dh_mapped = self._map_windows_dh_group(ike_dh)
                esp_dh_mapped = self._map_windows_dh_group(esp_dh)

                if not all([local_ip, remote_ip, local_subnet, remote_subnet]):
                    return ApplyResult(
                        success=False,
                        os=self.os,
                        message=f"Invalid connection payload for {conn_name}",
                        detail="local_ip/remote_ip/local_subnet/remote_subnet are required",
                    )

                phase1_auth_name = f"{conn_name}-ph1auth"
                mm_crypto_name = f"{conn_name}-mmcrypto"
                qm_crypto_name = f"{conn_name}-qmcrypto"
                rule_name = f"{conn_name}-rule"
                mm_rule_name = f"{conn_name}-mmrule"

                cleanup_cmd = f"""
Remove-NetIPsecRule -Name {self._render_powershell_value(rule_name)} -ErrorAction SilentlyContinue
Remove-NetIPsecMainModeRule -Name {self._render_powershell_value(mm_rule_name)} -ErrorAction SilentlyContinue
Remove-NetIPsecMainModeCryptoSet -Name {self._render_powershell_value(mm_crypto_name)} -ErrorAction SilentlyContinue
Remove-NetIPsecQuickModeCryptoSet -Name {self._render_powershell_value(qm_crypto_name)} -ErrorAction SilentlyContinue
Remove-NetIPsecPhase1AuthSet -Name {self._render_powershell_value(phase1_auth_name)} -ErrorAction SilentlyContinue
"""
                _run_powershell_step("[Windows driver] Cleanup: Removing previous objects...", cleanup_cmd)

                step1_cmd = f"""
$ErrorActionPreference = "Stop"
New-NetIPsecPhase1AuthSet `
  -Name {self._render_powershell_value(phase1_auth_name)} `
  -DisplayName {self._render_powershell_value(f"{conn_name} IKE Auth")} `
  -Proposal (New-NetIPsecAuthProposal -Machine -PreSharedKey {self._render_powershell_value(psk)}) `
  -ErrorAction Stop
"""
                ok, detail = _run_powershell_step("[Windows driver] Step 1/6: Creating Phase1AuthSet...", step1_cmd)
                if not ok:
                    return ApplyResult(success=False, os=self.os, message=f"Step 1 failed for {conn_name}", detail=detail)

                step2_cmd = f"""
$ErrorActionPreference = "Stop"
New-NetIPsecMainModeCryptoSet `
  -Name {self._render_powershell_value(mm_crypto_name)} `
  -DisplayName {self._render_powershell_value(f"{conn_name} MM Crypto")} `
  -Proposal (New-NetIPsecMainModeCryptoProposal `
      -Encryption {self._render_powershell_value(ike_enc)} `
      -Hash {self._render_powershell_value(ike_int)} `
            -KeyExchange {self._render_powershell_value(ike_dh_mapped)}) `
  -ErrorAction Stop
"""
                ok, detail = _run_powershell_step("[Windows driver] Step 2/6: Creating MainModeCryptoSet...", step2_cmd)
                if not ok:
                    return ApplyResult(success=False, os=self.os, message=f"Step 2 failed for {conn_name}", detail=detail)

                # Step 3 — skipped for PSK IKEv2 tunnels
                # Phase2AuthSet is not required when Phase1 uses PSK.
                logger.info("[Windows driver] Step 3/6: Phase2AuthSet skipped (PSK tunnel)")

#                 step4_cmd = f"""
# $ErrorActionPreference = "Stop"
# New-NetIPsecQuickModeCryptoSet `
#   -Name {self._render_powershell_value(qm_crypto_name)} `
#   -DisplayName {self._render_powershell_value(f"{conn_name} QM Crypto")} `
#   -Proposal (New-NetIPsecQuickModeCryptoProposal `
#       -Encapsulation Tunnel `
#       -ESPHash {self._render_powershell_value(esp_int)} `
#       -Encryption {self._render_powershell_value(esp_enc)} `
#             -DHGroup {self._render_powershell_value(esp_dh_mapped)}) `
#   -ErrorAction Stop
# """
#                 step4_cmd = f"""
# $ErrorActionPreference = "Stop"
# New-NetIPsecQuickModeCryptoSet `
#   -Name        {self._render_powershell_value(qm_crypto_name)} `
#   -DisplayName {self._render_powershell_value(f"{conn_name} QM Crypto")} `
#   -Proposal    (New-NetIPsecQuickModeCryptoProposal `
#                   -Encapsulation ESP `
#                   -ESPHash    {self._render_powershell_value(esp_int)} `
#                   -Encryption {self._render_powershell_value(esp_enc)} `
#                   -DHGroup    {self._render_powershell_value(esp_dh_mapped)}) `
#   -ErrorAction Stop
# """
                step4_cmd = f"""
$ErrorActionPreference = "Stop"
New-NetIPsecQuickModeCryptoSet `
  -Name        {self._render_powershell_value(qm_crypto_name)} `
  -DisplayName {self._render_powershell_value(f"{conn_name} QM Crypto")} `
  -Proposal    (New-NetIPsecQuickModeCryptoProposal `
                  -Encapsulation ESP `
                  -ESPHash    {self._render_powershell_value(esp_int)} `
                  -Encryption {self._render_powershell_value(esp_enc)} `
                  -PfsGroup   {self._render_powershell_value(esp_dh_mapped)}) `
  -ErrorAction Stop
"""
                ok, detail = _run_powershell_step("[Windows driver] Step 4/6: Creating QuickModeCryptoSet...", step4_cmd)
                if not ok:
                    return ApplyResult(success=False, os=self.os, message=f"Step 4 failed for {conn_name}", detail=detail)

                step5_cmd = f"""
$ErrorActionPreference = "Stop"
New-NetIPsecRule `
    -Name                 {self._render_powershell_value(rule_name)} `
    -DisplayName          {self._render_powershell_value(f"{conn_name} IPsec Tunnel")} `
    -Mode                 Tunnel `
    -LocalAddress         {self._render_powershell_value(local_subnet)} `
    -RemoteAddress        {self._render_powershell_value(remote_subnet)} `
    -LocalTunnelEndpoint  {self._render_powershell_value(local_ip)} `
    -RemoteTunnelEndpoint {self._render_powershell_value(remote_ip)} `
    -Phase1AuthSet        {self._render_powershell_value(phase1_auth_name)} `
    -QuickModeCryptoSet   {self._render_powershell_value(qm_crypto_name)} `
    -KeyModule            IKEv2 `
    -InboundSecurity      Require `
    -OutboundSecurity     Require `
    -ErrorAction          Stop
"""
                ok, detail = _run_powershell_step("[Windows driver] Step 5/6: Creating NetIPsecRule...", step5_cmd)
                if not ok:
                    return ApplyResult(success=False, os=self.os, message=f"Step 5 failed for {conn_name}", detail=detail)

                step6_cmd = f"""
$ErrorActionPreference = "Stop"
New-NetIPsecMainModeRule `
  -Name {self._render_powershell_value(mm_rule_name)} `
  -DisplayName {self._render_powershell_value(f"{conn_name} Main Mode Rule")} `
  -LocalAddress {self._render_powershell_value(local_ip)} `
  -RemoteAddress {self._render_powershell_value(remote_ip)} `
  -Phase1AuthSet {self._render_powershell_value(phase1_auth_name)} `
  -MainModeCryptoSet {self._render_powershell_value(mm_crypto_name)} `
  -ErrorAction Stop
"""
                ok, detail = _run_powershell_step("[Windows driver] Step 6/6: Creating MainModeRule...", step6_cmd)
                if not ok:
                    return ApplyResult(success=False, os=self.os, message=f"Step 6 failed for {conn_name}", detail=detail)

                logger.info("Applied Windows tunnel policy for connection '%s'", conn_name)
                executed += 1

            return ApplyResult(success=True, os=self.os, message=f"{executed} Windows IPsec rule(s) applied")
        except Exception as exc:
            logger.exception("Windows driver application error")
            return ApplyResult(success=False, os=self.os, message="Windows driver application failed", detail=str(exc))

        commands = driver_block.get("commands") or []
        try:
            executed = 0
            for command in commands:
                cmdlet = command.get("cmdlet")
                params = command.get("params") or {}
                if not cmdlet:
                    return ApplyResult(success=False, os=self.os, message="Invalid Windows driver_block", detail="Missing cmdlet")
                command_line = self._build_powershell_command(cmdlet, params)
                result = subprocess.run(["powershell", "-NonInteractive", "-Command", command_line], capture_output=True, text=True, check=False)
                if result.returncode != 0:
                    return ApplyResult(success=False, os=self.os, message=f"Failed to execute {cmdlet}", detail=(result.stderr or result.stdout or ""))
                executed += 1

            return ApplyResult(success=True, os=self.os, message=f"{executed} cmdlets executed")
        except Exception as exc:
            logger.exception("Windows driver application error")
            return ApplyResult(success=False, os=self.os, message="Windows driver application failed", detail=str(exc))

    def _apply_macos(self, driver_block: dict[str, Any], config: dict[str, Any]) -> ApplyResult:
        try:
            conf_text = self._render_racoon_conf(driver_block)
            conf_path = Path("/etc/racoon/racoon.conf")
            conf_path.parent.mkdir(parents=True, exist_ok=True)
            conf_path.write_text(conf_text, encoding="utf-8")

            reload_result = subprocess.run(["sudo", "racoonctl", "reload-config"], capture_output=True, text=True, check=False)
            if reload_result.returncode != 0:
                return ApplyResult(success=False, os=self.os, message="Failed to reload racoon config", detail=(reload_result.stderr or reload_result.stdout or ""))

            remotes = driver_block.get("remote") or {}
            return ApplyResult(success=True, os=self.os, message=f"{len(remotes)} remotes configured")
        except Exception as exc:
            logger.exception("macOS driver application error")
            return ApplyResult(success=False, os=self.os, message="macOS driver application failed", detail=str(exc))

    def _build_powershell_command(self, cmdlet: str, params: dict[str, Any]) -> str:
        rendered_params = []
        for key, value in params.items():
            rendered_params.append(f"-{key} {self._render_powershell_value(value)}")
        if rendered_params:
            return f"{cmdlet} {' '.join(rendered_params)} -ErrorAction Stop"
        return f"{cmdlet} -ErrorAction Stop"

    def _render_powershell_value(self, value: Any) -> str:
        if value is None:
            return "$null"
        if isinstance(value, bool):
            return "$true" if value else "$false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, dict)):
            return f"'{json.dumps(value)}'"
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def _map_windows_dh_group(self, value: str) -> str:
        mapping = {
            "DHGroup1": "DH1",
            "DHGroup2": "DH2",
            "DHGroup14": "DH14",
            "DHGroup15": "DH14",
            "DHGroup16": "DH14",
            "ECP256": "DH19",
            "ECP384": "DH20",
            "ECP521": "DH24",
            "MODP_2048": "DH14",
            "MODP_3072": "DH14",
            "MODP_4096": "DH14",
            "ECP_256": "DH19",
            "ECP_384": "DH20",
            "ECP_521": "DH24",
        }
        return mapping.get(str(value), "DH14")

    def _render_swanctl_conf(self, driver_block: dict[str, Any]) -> str:
        lines: list[str] = []
        self._append_conf_block(lines, driver_block, 0)
        return "\n".join(lines) + "\n"

    def _render_racoon_conf(self, driver_block: dict[str, Any]) -> str:
        lines: list[str] = []
        remote = driver_block.get("remote") or {}
        lines.append("remote {")
        for remote_name, remote_block in remote.items():
            lines.append(f"  {remote_name} {{")
            self._append_conf_block(lines, remote_block, 2)
            lines.append("  }")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _append_conf_block(self, lines: list[str], value: Any, indent: int) -> None:
        indent_text = " " * indent
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, dict):
                    lines.append(f"{indent_text}{key} {{")
                    self._append_conf_block(lines, item, indent + 2)
                    lines.append(f"{indent_text}}}")
                elif isinstance(item, list):
                    rendered = ", ".join(self._render_conf_scalar(entry) for entry in item)
                    lines.append(f"{indent_text}{key} = [ {rendered} ]")
                else:
                    lines.append(f"{indent_text}{key} = {self._render_conf_scalar(item)}")
        else:
            lines.append(f"{indent_text}{self._render_conf_scalar(value)}")

    def _render_conf_scalar(self, value: Any) -> str:
        if value is None:
            return '""'
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'