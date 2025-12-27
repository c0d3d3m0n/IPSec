# cleanup.ps1
# Removes all IPsec rules created by the test scenarios

$prefix = "DemoPolicy_*"

Write-Host "Searching for rules matching '$prefix'..." -ForegroundColor Cyan
$rules = Get-NetIPsecRule -DisplayName $prefix -ErrorAction SilentlyContinue

if ($rules) {
    foreach ($rule in $rules) {
        Write-Host "Removing rule: $($rule.DisplayName)" -ForegroundColor Yellow
        Remove-NetIPsecRule -DisplayName $rule.DisplayName -ErrorAction Stop
    }
    Write-Host "Cleanup complete! All test rules removed." -ForegroundColor Green
} else {
    Write-Host "No test rules found." -ForegroundColor Green
}
