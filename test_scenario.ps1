# test_scenario.ps1
# This script simulates the "Admin" actions to create a policy and assign it to a device.

$OrchestratorUrl = "http://127.0.0.1:8000"

Write-Host "1. Fetching enrolled devices..." -ForegroundColor Cyan
$devices = Invoke-RestMethod -Method Get -Uri "$OrchestratorUrl/devices/"
if ($devices.Count -eq 0) {
    Write-Error "No devices found! Make sure the Agent is running."
    exit
}
$deviceId = $devices[0].id
Write-Host "Found Device ID: $deviceId ($($devices[0].hostname))" -ForegroundColor Green

Write-Host "`n2. Creating a Test Policy..." -ForegroundColor Cyan
$policyName = "DemoPolicy_$(Get-Random)"
$body = @{
    name = $policyName
    description = "A test policy created by the test script"
    local_network_cidr = "192.168.10.0/24"
    remote_network_cidr = "10.10.10.0/24"
    auth_method = "psk"
    psk_secret = "SuperSecretKey123!"
} | ConvertTo-Json

try {
    $policy = Invoke-RestMethod -Method Post -Uri "$OrchestratorUrl/policies/" -ContentType "application/json" -Body $body
    Write-Host "Policy '$policyName' created. ID: $($policy.id)" -ForegroundColor Green
} catch {
    Write-Error "Failed to create policy. It might already exist."
    $policy = Invoke-RestMethod -Method Get -Uri "$OrchestratorUrl/policies/" | Select-Object -First 1
    Write-Host "Using existing policy ID: $($policy.id)" -ForegroundColor Yellow
}

Write-Host "`n3. Assigning Policy to Device..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Method Post -Uri "$OrchestratorUrl/policies/$($policy.id)/assign/$deviceId"
    Write-Host "Policy assigned successfully!" -ForegroundColor Green
} catch {
    Write-Error "Failed to assign policy: $_"
}

Write-Host "`nDone! Check the Agent terminal window. It should receive the config within 30 seconds." -ForegroundColor Magenta
