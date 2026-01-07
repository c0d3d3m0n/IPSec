import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json"
}

def print_result(name, response, expected_status=[200, 201]):
    try:
        if response.status_code in expected_status:
            print(f"✅ [PASS] {name} - Status: {response.status_code}")
            return True, response.json() if response.content else None
        else:
            print(f"❌ [FAIL] {name} - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, response.json() if response.content else None
    except Exception as e:
        print(f"❌ [FAIL] {name} - Exception: {e}")
        return False, None

def run_tests():
    print(f"Starting API Test Suite against {BASE_URL}...\n")
    
    # 1. Health Check
    try:
        response = requests.get(f"{BASE_URL}/health")
        success, _ = print_result("Health Check", response)
        if not success:
            print("Critical: Server is not healthy or unreachable. Exiting.")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ [FAIL] Connection Error: Is the server running at {BASE_URL}?")
        sys.exit(1)

    # 2. Root Endpoint
    print_result("Root Endpoint", requests.get(f"{BASE_URL}/"))

    # 3. Create a Policy
    policy_data = {
        "name": f"Test-Policy-{int(time.time())}",
        "description": "Automated test policy",
        "ike_version": "ikev2",
        "encryption_algorithm": "aes256",
        "integrity_algorithm": "sha256",
        "dh_group": "modp2048",
        "local_network_cidr": "10.0.0.0/24",
        "remote_network_cidr": "192.168.1.0/24",
        "auth_method": "psk",
        "psk_secret": "test_secret_key"
    }
    success, policy = print_result("Create Policy", requests.post(f"{BASE_URL}/policies/", json=policy_data, headers=HEADERS))
    policy_id = policy['id'] if success else None

    # 4. List Policies
    print_result("List Policies", requests.get(f"{BASE_URL}/policies/"))

    # 5. Get Policy Details
    if policy_id:
        print_result(f"Get Policy {policy_id}", requests.get(f"{BASE_URL}/policies/{policy_id}"))

    # 6. Enroll a Device
    device_data = {
        "hostname": f"test-device-{int(time.time())}",
        "os_type": "linux",
        "public_ip": "1.2.3.4",
        "enrollment_token": f"token-{int(time.time())}"
    }
    success, device = print_result("Enroll Device", requests.post(f"{BASE_URL}/devices/enroll", json=device_data, headers=HEADERS))
    device_id = device['id'] if success else None

    # 7. List Devices
    print_result("List Devices", requests.get(f"{BASE_URL}/devices/"))

    # 8. Get Device Details
    if device_id:
        print_result(f"Get Device {device_id}", requests.get(f"{BASE_URL}/devices/{device_id}"))

    # 9. Assign Policy to Device
    if device_id and policy_id:
        print_result("Assign Policy to Device", requests.post(f"{BASE_URL}/policies/{policy_id}/assign/{device_id}"))

    # 10. Get Device Config (Verify Policy Assignment)
    if device_id:
        print_result(f"Get Device {device_id} Config", requests.get(f"{BASE_URL}/devices/{device_id}/config"))

    print("\nTest Suite Completed.")

if __name__ == "__main__":
    run_tests()
