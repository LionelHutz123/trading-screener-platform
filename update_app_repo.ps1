# Update App Platform to use the trading screener repository

Get-Content ".env.production" | ForEach-Object {
    if ($_ -match '^([^#][^=]*?)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

$doToken = [Environment]::GetEnvironmentVariable("DIGITAL_OCEAN_TOKEN", "Process")
$appId = Get-Content ".app_id" -Raw | ForEach-Object { $_.Trim() }

Write-Host "Updating App Platform to use trading screener repository..." -ForegroundColor Green
Write-Host "App ID: $appId" -ForegroundColor Cyan

# Updated app specification with your repository
$appSpec = @{
    name = "trading-screener"
    region = "sfo"
    services = @(
        @{
            name = "web"
            git = @{
                repo_clone_url = "https://github.com/LionelHutz123/trading-screener-platform.git"
                branch = "main"
            }
            build_command = "pip install --upgrade pip && pip install -r requirements.txt"
            run_command = "python app_platform_api.py"
            instance_count = 1
            instance_size_slug = "professional-xs"  # Upgrade for better performance
            http_port = 8080
            health_check = @{
                http_path = "/health"
                initial_delay_seconds = 60
            }
            envs = @(
                @{
                    key = "ALPACA_API_KEY"
                    value = [Environment]::GetEnvironmentVariable("ALPACA_API_KEY", "Process")
                }
                @{
                    key = "ALPACA_SECRET_KEY"
                    value = [Environment]::GetEnvironmentVariable("ALPACA_SECRET_KEY", "Process")
                    type = "SECRET"
                }
                @{
                    key = "ALPACA_BASE_URL"
                    value = "https://paper-api.alpaca.markets"
                }
                @{
                    key = "ENV"
                    value = "production"
                }
                @{
                    key = "PORT"
                    value = "8080"
                }
                @{
                    key = "PYTHONUNBUFFERED"
                    value = "1"
                }
            )
        }
    )
    databases = @(
        @{
            name = "postgres"
            engine = "PG"
            version = "14"
            size = "db-s-1vcpu-1gb"
        }
    )
}

$headers = @{
    "Authorization" = "Bearer $doToken"
    "Content-Type" = "application/json"
}

$requestBody = @{
    spec = $appSpec
} | ConvertTo-Json -Depth 10

try {
    Write-Host "Sending update request..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/apps/$appId" -Method PUT -Headers $headers -Body $requestBody
    
    Write-Host "SUCCESS! App updated with trading screener repository!" -ForegroundColor Green
    Write-Host "Live URL: $($response.app.live_url)" -ForegroundColor Cyan
    Write-Host "Console: https://cloud.digitalocean.com/apps/$appId" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "DEPLOYMENT STATUS:" -ForegroundColor Magenta
    Write-Host "- Repository: https://github.com/LionelHutz123/trading-screener-platform" -ForegroundColor White
    Write-Host "- Branch: main (auto-deploy enabled)" -ForegroundColor White
    Write-Host "- Instance: professional-xs (1 vCPU, 1GB RAM)" -ForegroundColor White
    Write-Host "- Database: PostgreSQL 14 (managed)" -ForegroundColor White
    
    Write-Host ""
    Write-Host "The app is now deploying your trading screener!" -ForegroundColor Green
    Write-Host "Deployment typically takes 5-10 minutes." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Once deployed, you can:" -ForegroundColor Cyan
    Write-Host "- Access API: $($response.app.live_url)/health" -ForegroundColor White
    Write-Host "- Start backtesting: $($response.app.live_url)/api/backtest/run" -ForegroundColor White
    Write-Host "- View results: $($response.app.live_url)/api/strategies/top" -ForegroundColor White
    
}
catch {
    Write-Host "Update failed: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host "Error details: $errorBody" -ForegroundColor Red
        }
        catch {
            Write-Host "Could not read error details" -ForegroundColor Yellow
        }
    }
}