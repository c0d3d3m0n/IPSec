import subprocess
import logging
import ipaddress
import re
from typing import Dict, Any
from .base import PlatformManager

logger = logging.getLogger(__name__)

import ctypes

class WindowsManager(PlatformManager):
    def __init__(self):
        self.last_policy_name: str | None = None

    def is_admin(self) -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except AttributeError:
            return False

    def _map_crypto(self, algo: str) -> str:
        mapping = {
            'aes256': 'AES256',
            'aes128': 'AES128',
            'sha256': 'SHA256',
            'sha1': 'SHA1',
            'modp2048': 'DH14',
            'modp1024': 'DH2',
            'modp3072': 'DH15',
            'ecp256': 'ECDHP256'
        }
        normalized = algo.lower()
        if normalized not in mapping:
            raise ValueError(f"Unsupported crypto algorithm: {algo}")
        return mapping[normalized]

    def _sanitize_identifier(self, value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "default_policy")
        sanitized = sanitized.strip("_")
        return sanitized or "default_policy"

    def _validate_network(self, value: str) -> str:
        network = ipaddress.ip_network(value, strict=False)
        return str(network)

    def _quote(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        if not self.is_admin():
            logger.error("Administrator privileges are required to apply Windows IPsec policies.")
            logger.error("Please run the agent in a PowerShell window started with 'Run as Administrator'.")
            return False

        config = policy.get('config_data', {})
        ipsec = config.get('ipsec_policy', {})
        conn = ipsec.get('connections', [{}])[0] if ipsec.get('connections') else {}
        
        logger.info(f"Applying Detailed Windows IPsec policy: {config.get('policy_id', 'unknown')}")
        
        name = self._sanitize_identifier(config.get('policy_id', 'default_policy'))
        local_net = self._validate_network(conn.get('local_subnet', '0.0.0.0/0'))
        remote_net = self._validate_network(conn.get('remote_subnet', '0.0.0.0/0'))
        psk = ipsec.get('authentication', {}).get('secret_ref', '')
        if not psk:
            raise ValueError("Policy is missing a pre-shared key")
        
        ike = ipsec.get('crypto', {}).get('ike', {})
        
        enc = self._map_crypto(ike.get('encryption', 'aes256'))
        integ = self._map_crypto(ike.get('integrity', 'sha256'))
        dh = self._map_crypto(ike.get('dh_group', 'modp2048'))

        ps_command = f"""
        $ErrorActionPreference = "Stop"
        
        # 1. Cleanup existing objects with this prefix
        Remove-NetIPsecRule -DisplayName {self._quote(name)} -ErrorAction SilentlyContinue
        Remove-NetIPsecMainModeCryptoSet -Name {self._quote(f'{name}_MM_Set')} -ErrorAction SilentlyContinue
        Remove-NetIPsecQuickModeCryptoSet -Name {self._quote(f'{name}_QM_Set')} -ErrorAction SilentlyContinue
        Remove-NetIPsecPhase1AuthSet -Name {self._quote(f'{name}_Auth_Set')} -ErrorAction SilentlyContinue

        # 2. Define Main Mode (Phase 1)
        $mmProposal = New-NetIPsecMainModeCryptoProposal -Encryption {enc} -Hash {integ} -KeyExchange {dh}
        $mmSet = New-NetIPsecMainModeCryptoSet -Name {self._quote(f'{name}_MM_Set')} -Proposal $mmProposal

        # 3. Define Auth Set (PSK)
        $authSet = New-NetIPsecPhase1AuthSet -Name {self._quote(f'{name}_Auth_Set')} -PresharedKey {self._quote(psk)}

        # 4. Define Quick Mode (Phase 2)
        $qmProposal = New-NetIPsecQuickModeCryptoProposal -Encryption {enc} -Hash {integ}
        $qmSet = New-NetIPsecQuickModeCryptoSet -Name {self._quote(f'{name}_QM_Set')} -Proposal $qmProposal

        # 5. Create the Final Rule
        New-NetIPsecRule -DisplayName {self._quote(name)} `
            -LocalAddress {self._quote(local_net)} `
            -RemoteAddress {self._quote(remote_net)} `
            -Phase1AuthSet {self._quote(f'{name}_Auth_Set')} `
            -MainModeCryptoSet {self._quote(f'{name}_MM_Set')} `
            -QuickModeCryptoSet {self._quote(f'{name}_QM_Set')} `
            -KeyModule IKEv2 `
            -InboundSecurity Require `
            -OutboundSecurity Require `
            -Enabled True
        """
        
        try:
            # We use subprocess.run with input to avoid potential encoding issues with multiline strings
            process = subprocess.run(["powershell", "-Command", "-"], input=ps_command, capture_output=True, text=True, check=True)
            self.last_policy_name = name
            logger.info(f"Detailed IPsec rule '{name}' applied successfully.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply Windows policy: {e.stderr}")
            return False

    def check_tunnel_status(self) -> bool:
        try:
            # Check if there are any active main mode SAs
            cmd = "Get-NetIPsecMainModeSA | Measure-Object | Select-Object -ExpandProperty Count"
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            count = int(result.stdout.strip())
            return count > 0
        except Exception:
            return False
