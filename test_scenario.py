import requests
import json
import sys
import random

ORCHESTRATOR_URL = "http://127.0.0.1:8000"

def log(msg, color="white"):
    print(f"[TEST] {msg}")

def main():
    # 1. Fetch Devices
    log("Fetching enrolled devices...")
    try:
        resp = requests.get(f"{ORCHESTRATOR_URL}/devices/")
        resp.raise_for_status()
        devices = resp.json()
    except Exception as e:
        log(f"Failed to connect to Orchestrator: {e}")
        return

    if not devices:
        log("No devices found! Make sure the Agent is running and enrolled.")
        return

    # Pick the first device
    device = devices[0]
    device_id = device['id']
    log(f"Found Device ID: {device_id} ({device['hostname']} - {device['os_type']})")

    # 2. Create Policy
    log("\nCreating a Test Policy...")
    policy_name = f"DemoPolicy_{random.randint(1000, 9999)}"
    policy_data = {
        "name": policy_name,
        "description": "A test policy created by the Python test script",
        "local_network_cidr": "192.168.10.0/24",
        "remote_network_cidr": "10.10.10.0/24",
        "auth_method": "psk",
        "psk_secret": "SuperSecretKey123!"
    }

    try:
        resp = requests.post(f"{ORCHESTRATOR_URL}/policies/", json=policy_data)
        if resp.status_code == 400:
            log("Policy might already exist, fetching existing policies...")
            # Try to get an existing policy to reuse
            resp = requests.get(f"{ORCHESTRATOR_URL}/policies/")
            policies = resp.json()
            if policies:
                policy = policies[0]
                log(f"Using existing policy: {policy['name']} (ID: {policy['id']})")
            else:
                log("Could not create or find a policy.")
                return
        else:
            resp.raise_for_status()
            policy = resp.json()
            log(f"Policy '{policy['name']}' created. ID: {policy['id']}")
    except Exception as e:
        log(f"Error creating policy: {e}")
        return

    # 3. Assign Policy
    log("\nAssigning Policy to Device...")
    try:
        resp = requests.post(f"{ORCHESTRATOR_URL}/policies/{policy['id']}/assign/{device_id}")
        resp.raise_for_status()
        log("Policy assigned successfully!")
    except Exception as e:
        log(f"Failed to assign policy: {e}")
        return

    log("\nDone! Check the Agent terminal window. It should receive the config within 30 seconds.")

if __name__ == "__main__":
    main()
