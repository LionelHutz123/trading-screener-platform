# Check current app configuration
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

Write-Host "Checking app configuration..." -ForegroundColor Cyan

try {
    $appResponse = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId" -Headers $headers
    
    Write-Host "App Name: $($appResponse.app.spec.name)" -ForegroundColor Green
    Write-Host "Services:" -ForegroundColor Yellow
    
    foreach ($service in $appResponse.app.spec.services) {
        Write-Host "  - Service: $($service.name)" -ForegroundColor White
        if ($service.git) {
            Write-Host "    Git Repo: $($service.git.repo_clone_url)" -ForegroundColor Cyan
            Write-Host "    Branch: $($service.git.branch)" -ForegroundColor Cyan
        }
        if ($service.github) {
            Write-Host "    GitHub Repo: $($service.github.repo)" -ForegroundColor Cyan
            Write-Host "    Branch: $($service.github.branch)" -ForegroundColor Cyan
        }
        Write-Host "    Build Command: $($service.build_command)" -ForegroundColor Gray
        Write-Host "    Run Command: $($service.run_command)" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}