import subprocess
import logging
from typing import Dict, Any
from .base import PlatformManager

logger = logging.getLogger(__name__)

import ctypes

class WindowsManager(PlatformManager):
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
        return mapping.get(algo.lower(), algo.upper())

    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        if not self.is_admin():
            logger.error("Administrator privileges are required to apply Windows IPsec policies.")
            logger.error("Please run the agent in a PowerShell window started with 'Run as Administrator'.")
            return False

        config = policy.get('config_data', {})
        ipsec = config.get('ipsec_policy', {})
        conn = ipsec.get('connections', [{}])[0] if ipsec.get('connections') else {}
        
        logger.info(f"Applying Detailed Windows IPsec policy: {config.get('policy_id', 'unknown')}")
        
        name = config.get('policy_id', 'default_policy').replace(" ", "_")
        local_net = conn.get('local_subnet', '0.0.0.0/0')
        remote_net = conn.get('remote_subnet', '0.0.0.0/0')
        psk = ipsec.get('authentication', {}).get('secret_ref', '')
        
        ike = ipsec.get('crypto', {}).get('ike', {})
        
        enc = self._map_crypto(ike.get('encryption', 'aes256'))
        integ = self._map_crypto(ike.get('integrity', 'sha256'))
        dh = self._map_crypto(ike.get('dh_group', 'modp2048'))

        ps_command = f"""
        $ErrorActionPreference = "Stop"
        
        # 1. Cleanup existing objects with this prefix
        Remove-NetIPsecRule -DisplayName "{name}" -ErrorAction SilentlyContinue
        Remove-NetIPsecMainModeCryptoSet -Name "{name}_MM_Set" -ErrorAction SilentlyContinue
        Remove-NetIPsecQuickModeCryptoSet -Name "{name}_QM_Set" -ErrorAction SilentlyContinue
        Remove-NetIPsecPhase1AuthSet -Name "{name}_Auth_Set" -ErrorAction SilentlyContinue

        # 2. Define Main Mode (Phase 1)
        $mmProposal = New-NetIPsecMainModeCryptoProposal -Encryption {enc} -Hash {integ} -KeyExchange {dh}
        $mmSet = New-NetIPsecMainModeCryptoSet -Name "{name}_MM_Set" -Proposal $mmProposal

        # 3. Define Auth Set (PSK)
        $authSet = New-NetIPsecPhase1AuthSet -Name "{name}_Auth_Set" -PresharedKey "{psk}"

        # 4. Define Quick Mode (Phase 2)
        $qmProposal = New-NetIPsecQuickModeCryptoProposal -Encryption {enc} -Hash {integ}
        $qmSet = New-NetIPsecQuickModeCryptoSet -Name "{name}_QM_Set" -Proposal $qmProposal

        # 5. Create the Final Rule
        New-NetIPsecRule -DisplayName "{name}" `
            -LocalAddress {local_net} `
            -RemoteAddress {remote_net} `
            -Phase1AuthSet "{name}_Auth_Set" `
            -MainModeCryptoSet "{name}_MM_Set" `
            -QuickModeCryptoSet "{name}_QM_Set" `
            -KeyModule IKEv2 `
            -InboundSecurity Require `
            -OutboundSecurity Require `
            -Enabled True
        """
        
        try:
            # We use subprocess.run with input to avoid potential encoding issues with multiline strings
            process = subprocess.run(["powershell", "-Command", "-"], input=ps_command, capture_output=True, text=True, check=True)
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
