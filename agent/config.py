import os


ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "https://your-orchestrator.onrender.com")
DEVICE_ID = os.getenv("DEVICE_ID", "")
CLIENT_CERT_PATH = os.getenv("CLIENT_CERT_PATH", "./certs/client.crt")
CLIENT_KEY_PATH = os.getenv("CLIENT_KEY_PATH", "./certs/client.key")
CA_CERT_PATH = os.getenv("CA_CERT_PATH", "./certs/ca.crt")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
PROTECTED_SUBNETS = os.getenv("PROTECTED_SUBNETS", "")
LEAK_DETECTION_IFACE = os.getenv("LEAK_DETECTION_IFACE", "eth0")
PRE_SHARED_KEY = os.getenv("PRE_SHARED_KEY", "")
