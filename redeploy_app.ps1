# Trigger a new deployment
Get-Content ".env.production" | ForEach-Object {
    if ($_ -match '^([^#][^=]*?)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

$doToken = [Environment]::GetEnvironmentVariable("DIGITAL_OCEAN_TOKEN", "Process")
$appId = Get-Content ".app_id" -Raw | ForEach-Object { $_.Trim() }

$headers = @{
    "Authorization" = "Bearer $doToken"
    "Content-Type" = "application/json"
}

Write-Host "Triggering new deployment..." -ForegroundColor Cyan

try {
    # Trigger deployment by creating a new deployment
    $deploymentResponse = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId/deployments" -Method POST -Headers $headers -Body "{}"
    
    Write-Host "SUCCESS! New deployment triggered!" -ForegroundColor Green
    Write-Host "Deployment ID: $($deploymentResponse.deployment.id)" -ForegroundColor Cyan
    Write-Host "Phase: $($deploymentResponse.deployment.phase)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This will rebuild from the GitHub repository." -ForegroundColor White
    Write-Host "Monitor at: https://cloud.digitalocean.com/apps/$appId" -ForegroundColor Cyan
    
} catch {
    Write-Host "Error triggering deployment: $($_.Exception.Message)" -ForegroundColor Red
}