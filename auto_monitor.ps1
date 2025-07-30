# Auto-monitor deployment and start backtesting
$appUrl = "https://trading-screener-lerd2.ondigitalocean.app"
$maxChecks = 10
$currentCheck = 0

Write-Host "🔄 Auto-monitoring Trading Screener deployment..." -ForegroundColor Cyan
Write-Host "Will check every 60 seconds for up to 10 minutes" -ForegroundColor Gray
Write-Host ""

while ($currentCheck -lt $maxChecks) {
    $currentCheck++
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    Write-Host "[$timestamp] Check $currentCheck/$maxChecks - Testing API..." -ForegroundColor Yellow
    
    try {
        # Test health endpoint
        $healthResponse = Invoke-RestMethod -Uri "$appUrl/health" -TimeoutSec 15
        
        # Check if it's our trading API (not the basic sample)
        if ($healthResponse -match "healthy|status|database") {
            Write-Host "✅ TRADING SCREENER DEPLOYED!" -ForegroundColor Green
            Write-Host "Full API is now available!" -ForegroundColor Green
            
            # Test API status endpoint
            try {
                $statusResponse = Invoke-RestMethod -Uri "$appUrl/api/status" -TimeoutSec 10
                Write-Host "API Status: Active" -ForegroundColor Green
                
                # Start comprehensive backtesting
                Write-Host ""
                Write-Host "🚀 STARTING COMPREHENSIVE BACKTESTING..." -ForegroundColor Magenta
                
                $backtestRequest = @{
                    symbols = @("AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA", "LLY", "AVGO")
                    timeframes = @("1h", "4h", "1d") 
                    start_date = "2022-01-01"
                    end_date = "2024-01-01"
                } | ConvertTo-Json
                
                $backtestResponse = Invoke-RestMethod -Uri "$appUrl/api/backtest/run" -Method POST -Body $backtestRequest -ContentType "application/json" -TimeoutSec 30
                
                Write-Host "✅ BACKTESTING STARTED!" -ForegroundColor Green
                Write-Host "Status: $($backtestResponse.status)" -ForegroundColor Cyan
                Write-Host ""
                Write-Host "🎯 Testing these proven strategies:" -ForegroundColor Yellow
                Write-Host "- LLY 4h/15-period (5.42 Sharpe ratio)" -ForegroundColor White
                Write-Host "- TSLA Daily (99.21% return)" -ForegroundColor White
                Write-Host "- NVDA Daily (92.22% return)" -ForegroundColor White
                Write-Host "- GOOGL 4h (2.86 Sharpe ratio)" -ForegroundColor White
                Write-Host ""
                Write-Host "📊 Results will be available at:" -ForegroundColor Cyan
                Write-Host "$appUrl/api/backtest/results" -ForegroundColor White
                Write-Host "$appUrl/api/strategies/top" -ForegroundColor White
                
                break
                
            } catch {
                Write-Host "API endpoints not fully ready yet..." -ForegroundColor Yellow
            }
        } else {
            Write-Host "Still using sample app. Build in progress..." -ForegroundColor Gray
        }
        
    } catch {
        Write-Host "Connection issue. Deployment still in progress..." -ForegroundColor Gray
    }
    
    if ($currentCheck -lt $maxChecks) {
        Write-Host "Waiting 60 seconds..." -ForegroundColor Gray
        Start-Sleep -Seconds 60
    }
}

if ($currentCheck -eq $maxChecks) {
    Write-Host ""
    Write-Host "⏰ Monitoring timeout reached" -ForegroundColor Yellow
    Write-Host "Deployment may still be in progress" -ForegroundColor Yellow
    Write-Host "Check console: https://cloud.digitalocean.com/apps/6cfe845f-1e7a-4c1c-87f4-10400306910e" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "🏁 Monitoring complete!" -ForegroundColor Green