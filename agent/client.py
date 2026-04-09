import requests
import platform
import socket
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class OrchestratorClient:
    def __init__(self, base_url: str, enrollment_token: str):
        self.base_url = base_url.rstrip('/')
        self.enrollment_token = enrollment_token
        self.device_id: Optional[int] = None
        self.session = requests.Session()
        self.session.headers.update({"X-Enrollment-Token": enrollment_token})

    def enroll(self, enrollment_number: str, os_fingerprint: str, agent_signature: str) -> Optional[Dict[str, Any]]:
        """Register the device with the orchestrator."""
        hostname = socket.gethostname()
        os_type = platform.system().lower()
        
        # Get public IP (simple check)
        try:
            public_ip = requests.get('https://api.ipify.org', timeout=5).text
        except Exception:
            public_ip = "0.0.0.0"

        payload = {
            "hostname": hostname,
            "os_type": os_type,
            "public_ip": public_ip,
            "enrollment_number": enrollment_number,
            "enrollment_token": self.enrollment_token,
            "os_fingerprint": os_fingerprint,
            "agent_signature": agent_signature,
        }

        try:
            response = self.session.post(f"{self.base_url}/devices/enroll", json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            self.device_id = data['id']
            logger.info(f"Device enrolled successfully (Number: {enrollment_number}). ID: {self.device_id}")
            return data
        except Exception as e:
            logger.error(f"Enrollment failed: {e}")
            return None

    def get_policy(self) -> Optional[Dict[str, Any]]:
        """Fetch the assigned IPsec policy."""
        if not self.device_id:
            logger.error("Device not enrolled.")
            return None

        try:
            response = self.session.get(f"{self.base_url}/devices/{self.device_id}/config", timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("No policy assigned yet.")
                return None
            if e.response.status_code == 401:
                raise PermissionError("Device token rejected by orchestrator") from e
            else:
                logger.error(f"Failed to fetch policy: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching policy: {e}")
            raise
