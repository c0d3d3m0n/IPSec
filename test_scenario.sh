#!/bin/bash

ORCHESTRATOR_URL="http://127.0.0.1:8000"

echo -e "\033[0;36m1. Fetching enrolled devices...\033[0m"
DEVICES_JSON=$(curl -s "$ORCHESTRATOR_URL/devices/")

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: 'jq' is not installed. Please install it or use the Python script 'test_scenario.py' instead."
    exit 1
fi

DEVICE_ID=$(echo $DEVICES_JSON | jq '.[0].id')
HOSTNAME=$(echo $DEVICES_JSON | jq -r '.[0].hostname')

if [ "$DEVICE_ID" == "null" ]; then
    echo "No devices found! Make sure the Agent is running."
    exit 1
fi

echo -e "\033[0;32mFound Device ID: $DEVICE_ID ($HOSTNAME)\033[0m"

echo -e "\n\033[0;36m2. Creating a Test Policy...\033[0m"
POLICY_NAME="DemoPolicy_$RANDOM"
POLICY_DATA=$(cat <<EOF
{
    "name": "$POLICY_NAME",
    "description": "A test policy created by the Bash script",
    "local_network_cidr": "192.168.10.0/24",
    "remote_network_cidr": "10.10.10.0/24",
    "auth_method": "psk",
    "psk_secret": "SuperSecretKey123!"
}
EOF
)

RESPONSE=$(curl -s -X POST "$ORCHESTRATOR_URL/policies/" -H "Content-Type: application/json" -d "$POLICY_DATA")
POLICY_ID=$(echo $RESPONSE | jq '.id')

if [ "$POLICY_ID" == "null" ]; then
    echo "Failed to create policy (it might exist). Using first available policy..."
    EXISTING_POLICIES=$(curl -s "$ORCHESTRATOR_URL/policies/")
    POLICY_ID=$(echo $EXISTING_POLICIES | jq '.[0].id')
    if [ "$POLICY_ID" == "null" ]; then
        echo "Error: Could not create or find a policy."
        exit 1
    fi
    echo -e "\033[0;33mUsing existing Policy ID: $POLICY_ID\033[0m"
else
    echo -e "\033[0;32mPolicy '$POLICY_NAME' created. ID: $POLICY_ID\033[0m"
fi

echo -e "\n\033[0;36m3. Assigning Policy to Device...\033[0m"
ASSIGN_RESP=$(curl -s -X POST "$ORCHESTRATOR_URL/policies/$POLICY_ID/assign/$DEVICE_ID")

echo -e "\033[0;32mPolicy assigned successfully!\033[0m"
echo -e "\n\033[0;35mDone! Check the Agent terminal window.\033[0m"
