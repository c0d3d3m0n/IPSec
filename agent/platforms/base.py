from abc import ABC, abstractmethod
from typing import Dict, Any

class PlatformManager(ABC):
    @abstractmethod
    def apply_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Apply the given IPsec policy to the system.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def check_tunnel_status(self) -> bool:
        """
        Check if the tunnel is up and running.
        """
        pass
