from __future__ import annotations

from dataclasses import dataclass
import json
import logging
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
        connections = config.get("connections") or []
        ike_enc = config.get("ike_encryption")
        ike_int = config.get("ike_integrity")
        ike_dh = config.get("ike_dh_group")
        esp_enc = config.get("esp_encryption")
        esp_int = config.get("esp_integrity")
        esp_dh = config.get("esp_dh_group")
        auth_secret = config.get("auth_secret_ref") or ""

        logger.info(f"Windows IPSec policy application started: {len(connections)} connection(s)")
        logger.info(f"IKE crypto: {ike_enc}/{ike_int}/{ike_dh}")
        logger.info(f"ESP crypto: {esp_enc}/{esp_int}/{esp_dh}")

        # Preferred path: build policy with proposal-based cmdlets in one script.
        # This avoids invalid parameter usage on New-NetIPsecMainModeCryptoSet.
        if connections and ike_enc and esp_enc and auth_secret:
            try:
                executed = 0
                for connection in connections:
                    name = str(connection.get("name") or "ipsec-rule")
                    logger.info(f"Applying rule: {name}")
                    mm_name = f"{name}-mm"
                    qm_name = f"{name}-qm"
                    auth_name = f"{name}-auth"
                    local_address = connection.get("local_subnet") or connection.get("local_ip") or "Any"
                    remote_address = connection.get("remote_subnet") or connection.get("remote_ip") or "Any"

                    key_exchange_value = self._map_windows_dh_group(ike_dh) if ike_dh else None

                    mm_parts = [f"-Encryption {self._render_powershell_value(ike_enc)}"]
                    if ike_int:
                        mm_parts.append(f"-Hash {self._render_powershell_value(ike_int)}")
                    if key_exchange_value:
                        mm_parts.append(f"-KeyExchange {self._render_powershell_value(key_exchange_value)}")

                    qm_parts = [f"-Encapsulation ESP", f"-Encryption {self._render_powershell_value(esp_enc)}"]
                    if esp_int:
                        qm_parts.append(f"-ESPHash {self._render_powershell_value(esp_int)}")

                    script = f"""
$ErrorActionPreference = "Stop"

Remove-NetIPsecRule -DisplayName {self._render_powershell_value(name)} -ErrorAction SilentlyContinue
Remove-NetIPsecMainModeCryptoSet -Name {self._render_powershell_value(mm_name)} -ErrorAction SilentlyContinue
Remove-NetIPsecQuickModeCryptoSet -Name {self._render_powershell_value(qm_name)} -ErrorAction SilentlyContinue
Remove-NetIPsecPhase1AuthSet -Name {self._render_powershell_value(auth_name)} -ErrorAction SilentlyContinue

$mmProposal = New-NetIPsecMainModeCryptoProposal {' '.join(mm_parts)}
New-NetIPsecMainModeCryptoSet -Name {self._render_powershell_value(mm_name)} -Proposal $mmProposal | Out-Null

$qmProposal = New-NetIPsecQuickModeCryptoProposal {' '.join(qm_parts)}
New-NetIPsecQuickModeCryptoSet -Name {self._render_powershell_value(qm_name)} -Proposal $qmProposal | Out-Null

$authProposal = New-NetIPsecAuthProposal -Machine -PreSharedKey {self._render_powershell_value(auth_secret)}
New-NetIPsecPhase1AuthSet -Name {self._render_powershell_value(auth_name)} -DisplayName {self._render_powershell_value(auth_name)} -Proposal $authProposal | Out-Null

New-NetIPsecRule -PolicyStore PersistentStore -DisplayName {self._render_powershell_value(name)} `
  -LocalAddress {self._render_powershell_value(local_address)} `
  -RemoteAddress {self._render_powershell_value(remote_address)} `
  -Phase1AuthSet {self._render_powershell_value(auth_name)} `
  -MainModeCryptoSet {self._render_powershell_value(mm_name)} `
  -QuickModeCryptoSet {self._render_powershell_value(qm_name)} `
  -KeyModule IKEv2 `
  -InboundSecurity Require `
  -OutboundSecurity Require `
  -Enabled True | Out-Null

$createdRule = Get-NetIPsecRule -PolicyStore PersistentStore -DisplayName {self._render_powershell_value(name)} -ErrorAction SilentlyContinue
if (-not $createdRule) {{
    throw "IPSec rule was not found after creation"
}}
"""
                    result = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode != 0:
                        logger.error(f"IPSec rule '{name}' failed: {result.stderr or result.stdout}")
                        return ApplyResult(
                            success=False,
                            os=self.os,
                            message=f"Failed to apply Windows IPsec rule {name}",
                            detail=(result.stderr or result.stdout or ""),
                        )
                    logger.info(f"IPSec rule '{name}' applied successfully")
                    logger.info(f"  Local subnet: {connection.get('local_subnet') or connection.get('local_ip')}")
                    logger.info(f"  Remote subnet: {connection.get('remote_subnet') or connection.get('remote_ip')}")
                    executed += 1

                logger.info(f"✅ Windows IPSec policy application completed: {executed} rule(s) applied")
                return ApplyResult(success=True, os=self.os, message=f"{executed} Windows IPsec rule(s) applied")
            except Exception as exc:
                logger.exception("Windows script-based driver application error")
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
            "MODP_4096": "DH24",
        }
        return mapping.get(str(value), str(value))

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
