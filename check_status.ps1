# Check app deployment status
Get-Content ".env.production" | ForEach-Object {
    if ($_ -match '^([^#][^=]*?)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

$doToken = [Environment]::GetEnvironmentVariable("DIGITAL_OCEAN_TOKEN", "Process")
$appId = Get-Content ".app_id" -Raw | ForEach-Object { $_.Trim() }

$headers = @{
    "Authorization" = "Bearer $doToken"
}

Write-Host "Checking app deployment status..." -ForegroundColor Cyan
Write-Host "App ID: $appId" -ForegroundColor Gray

try {
    $appResponse = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId" -Headers $headers
    Write-Host "App Status: $($appResponse.app.phase)" -ForegroundColor Yellow
    Write-Host "Live URL: $($appResponse.app.live_url)" -ForegroundColor Green
    
    if ($appResponse.app.last_deployment_created_at) {
        Write-Host "Last Deployment: $($appResponse.app.last_deployment_created_at)" -ForegroundColor Gray
    }
    
    # Check latest deployment
    if ($appResponse.app.active_deployment) {
        Write-Host "Active Deployment Phase: $($appResponse.app.active_deployment.phase)" -ForegroundColor Cyan
        if ($appResponse.app.active_deployment.cause) {
            Write-Host "Deployment Cause: $($appResponse.app.active_deployment.cause)" -ForegroundColor Gray
        }
    }
    
} catch {
    Write-Host "Error checking status: $($_.Exception.Message)" -ForegroundColor Red
}