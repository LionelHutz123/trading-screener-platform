# Check deployment status and logs
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

Write-Host "Checking deployment status and logs..." -ForegroundColor Cyan

try {
    # Get app info
    $appResponse = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId" -Headers $headers
    Write-Host "App Phase: $($appResponse.app.phase)" -ForegroundColor Yellow
    
    if ($appResponse.app.active_deployment) {
        Write-Host "Active Deployment:" -ForegroundColor Green
        Write-Host "  ID: $($appResponse.app.active_deployment.id)" -ForegroundColor White
        Write-Host "  Phase: $($appResponse.app.active_deployment.phase)" -ForegroundColor White
        Write-Host "  Created: $($appResponse.app.active_deployment.created_at)" -ForegroundColor Gray
        
        # Get deployment details
        $deploymentId = $appResponse.app.active_deployment.id
        $deploymentResponse = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId/deployments/$deploymentId" -Headers $headers
        
        Write-Host ""
        Write-Host "Deployment Details:" -ForegroundColor Cyan
        Write-Host "  Phase: $($deploymentResponse.deployment.phase)" -ForegroundColor Yellow
        Write-Host "  Progress: $($deploymentResponse.deployment.progress.total_steps) total steps" -ForegroundColor White
        
        if ($deploymentResponse.deployment.progress.steps) {
            Write-Host "  Recent Steps:" -ForegroundColor White
            $deploymentResponse.deployment.progress.steps | Select-Object -Last 5 | ForEach-Object {
                $status = if ($_.status -eq "SUCCESS") { "✓" } elseif ($_.status -eq "RUNNING") { "⏳" } else { "❌" }
                Write-Host "    $status $($_.name): $($_.status)" -ForegroundColor $(if ($_.status -eq "SUCCESS") { "Green" } elseif ($_.status -eq "RUNNING") { "Yellow" } else { "Red" })
            }
        }
    }
    
    # Check if there are any recent deployments
    Write-Host ""
    Write-Host "Recent Deployments:" -ForegroundColor Cyan
    $deploymentsResponse = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId/deployments" -Headers $headers
    $deploymentsResponse.deployments | Select-Object -First 3 | ForEach-Object {
        Write-Host "  $($_.created_at): $($_.phase) (ID: $($_.id))" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}