import subprocess
import logging
import os
from typing import Dict, Any
from .base import PlatformManager

logger = logging.getLogger(__name__)

class LinuxManager(PlatformManager):
    def is_admin(self) -> bool:
        return os.geteuid() == 0

    def _map_crypto(self, algo: str) -> str:
        mapping = {
            'aes256': 'aes256',
            'aes128': 'aes128',
            'sha256': 'sha256',
            'sha1': 'sha1',
            'modp2048': 'modp2048',
            'modp1024': 'modp1024',
            'modp3072': 'modp3072',
            'ecp256': 'ecp256'
        }
        return mapping.get(algo.lower(), algo.lower())

    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        if not self.is_admin():
            logger.error("Root privileges are required to apply Linux IPsec policies.")
            logger.error("Please run the agent with 'sudo'.")
            return False

        logger.info(f"Applying Enterprise Linux IPsec policy: {policy['name']}")
        
        name = policy['name'].replace(" ", "_")
        local_ts = policy.get('local_network_cidr', '0.0.0.0/0')
        remote_ts = policy.get('remote_network_cidr', '0.0.0.0/0')
        psk = policy.get('psk_secret', '')
        
        enc = self._map_crypto(policy.get('encryption_algorithm', 'aes256'))
        integ = self._map_crypto(policy.get('integrity_algorithm', 'sha256'))
        dh = self._map_crypto(policy.get('dh_group', 'modp2048'))
        
        proposal = f"{enc}-{integ}-{dh}"

        # 1. Create swanctl configuration
        conf_content = f"""
connections {{
    {name} {{
        local_addrs  = %any
        remote_addrs = %any
        local {{
            auth = psk
            id = %any
        }}
        remote {{
            auth = psk
            id = %any
        }}
        children {{
            {name} {{
                local_ts  = {local_ts}
                remote_ts = {remote_ts}
                esp_proposals = {enc}-{integ}
                mode = transport
                start_action = trap
            }}
        }}
        proposals = {proposal}
    }}
}}

secrets {{
    ike-{name} {{
        secret = {psk}
    }}
}}
"""
        conf_path = f"/etc/swanctl/conf.d/{name}.conf"
        
        try:
            # Ensure directory exists
            os.makedirs("/etc/swanctl/conf.d", exist_ok=True)
            
            with open(conf_path, "w") as f:
                f.write(conf_content)
            
            # 2. Reload swanctl
            subprocess.run(["swanctl", "--reload"], check=True, capture_output=True)
            logger.info(f"Linux IPsec rule '{policy['name']}' applied via swanctl.")
            return True
        except Exception as e:
            logger.error(f"Failed to apply Linux policy: {str(e)}")
            return False

    def check_tunnel_status(self) -> bool:
        try:
            result = subprocess.run(["swanctl", "--list-sas"], capture_output=True, text=True)
            return name in result.stdout # Simplified check
        except Exception:
            return False
