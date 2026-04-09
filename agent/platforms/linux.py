import subprocess
import logging
import os
import ipaddress
import re
from typing import Dict, Any
from .base import PlatformManager

logger = logging.getLogger(__name__)

class LinuxManager(PlatformManager):
    def __init__(self):
        self.last_policy_name: str | None = None

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
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        if not self.is_admin():
            logger.error("Root privileges are required to apply Linux IPsec policies.")
            logger.error("Please run the agent with 'sudo'.")
            return False

        config = policy.get('config_data', {})
        ipsec = config.get('ipsec_policy', {})
        conn = ipsec.get('connections', [{}])[0] if ipsec.get('connections') else {}
        
        logger.info(f"Applying Enterprise Linux IPsec policy: {config.get('policy_id', 'unknown')}")
        
        name = self._sanitize_identifier(config.get('policy_id', 'default_policy'))
        local_ts = self._validate_network(conn.get('local_subnet', '0.0.0.0/0'))
        remote_ts = self._validate_network(conn.get('remote_subnet', '0.0.0.0/0'))
        psk = ipsec.get('authentication', {}).get('secret_ref', '')
        if not psk:
            raise ValueError("Policy is missing a pre-shared key")
        
        ike = ipsec.get('crypto', {}).get('ike', {})
        
        enc = self._map_crypto(ike.get('encryption', 'aes256'))
        integ = self._map_crypto(ike.get('integrity', 'sha256'))
        dh = self._map_crypto(ike.get('dh_group', 'modp2048'))
        
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
                local_ts  = {self._quote(local_ts)}
                remote_ts = {self._quote(remote_ts)}
                esp_proposals = {self._quote(f'{enc}-{integ}')}
                mode = transport
                start_action = trap
            }}
        }}
        proposals = {self._quote(proposal)}
    }}
}}

secrets {{
    ike-{name} {{
        secret = {self._quote(psk)}
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
            self.last_policy_name = name
            logger.info(f"Linux IPsec rule '{name}' applied via swanctl.")
            return True
        except Exception as e:
            logger.error(f"Failed to apply Linux policy: {str(e)}")
            return False

    def check_tunnel_status(self) -> bool:
        try:
            result = subprocess.run(["swanctl", "--list-sas"], capture_output=True, text=True)
            if not result.stdout.strip():
                return False
            if self.last_policy_name:
                return self.last_policy_name in result.stdout
            return True
        except Exception:
            return False
