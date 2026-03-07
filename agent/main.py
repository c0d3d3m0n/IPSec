import time
import logging
import sys
import os
import getpass
from client import OrchestratorClient
from platforms.base import PlatformManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Agent")

# Mock platform for now until we implement specific ones
class MockPlatform(PlatformManager):
    def apply_policy(self, policy):
        logger.info(f"Applying policy: {policy['name']}")
        return True
    
    def check_tunnel_status(self):
        return True

def get_platform_manager() -> PlatformManager:
    if sys.platform == "linux":
        from platforms.linux import LinuxManager
        return LinuxManager()
    elif sys.platform == "win32":
        from platforms.windows import WindowsManager
        return WindowsManager()
        # return MockPlatform() # Placeholder
    else:
        logger.warning("Unsupported platform, using mock")
        return MockPlatform()

def main():
    # Hardcoded Orchestrator URL as requested by user
    default_url = "https://ipsec-lcir.onrender.com"
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", default_url)
    
    enrollment_token = os.environ.get("ENROLLMENT_TOKEN")
    
    if not enrollment_token:
        print(f"Connecting to: {orchestrator_url}")
        enrollment_token = getpass.getpass("Enter Secret Enrollment Token: ")
    
    enrollment_number = os.environ.get("ENROLLMENT_NUMBER")
    if not enrollment_number:
        enrollment_number = input("Enter Enrollment Number: ")

    client = OrchestratorClient(orchestrator_url, enrollment_token)
    platform_mgr = get_platform_manager()
    
    logger.info(f"Starting Agent for Device #{enrollment_number}...")
    
    # 1. Enroll
    if not client.enroll(enrollment_number):
        logger.error("Failed to enroll. Exiting.")
        return

    # 2. Main Loop
    while True:
        try:
            policy = client.get_policy()
            if policy:
                platform_mgr.apply_policy(policy)
            else:
                logger.info("No policy assigned.")
            
            time.sleep(30) # Check every 30 seconds
        except KeyboardInterrupt:
            logger.info("Stopping Agent.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
