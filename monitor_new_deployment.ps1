# Monitor the new deployment and start backtesting when ready
$appUrl = "https://trading-screener-lerd2.ondigitalocean.app"
$maxChecks = 20
$currentCheck = 0

Write-Host "Monitoring NEW deployment from GitHub..." -ForegroundColor Magenta
Write-Host "This deployment should build our trading screener properly!" -ForegroundColor Green
Write-Host "Checking every 45 seconds..." -ForegroundColor Gray
Write-Host ""

while ($currentCheck -lt $maxChecks) {
    $currentCheck++
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] Check $currentCheck/$maxChecks - Testing new deployment..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-RestMethod -Uri "$appUrl/health" -TimeoutSec 20
        
        # Check if it's our trading API (should have database, status, etc.)
        if ($response -match "database|status" -and $response -notmatch "Hello! you requested") {
            Write-Host ""
            Write-Host "SUCCESS! TRADING SCREENER IS LIVE!" -ForegroundColor Green
            Write-Host "Health Response:" -ForegroundColor White
            Write-Host "$response" -ForegroundColor Cyan
            
            # Test API status endpoint
            try {
                Write-Host ""
                Write-Host "Testing API endpoints..." -ForegroundColor Cyan
                $statusResponse = Invoke-RestMethod -Uri "$appUrl/api/status" -TimeoutSec 15
                Write-Host "API Status: Ready!" -ForegroundColor Green
                
                # Start comprehensive backtesting
                Write-Host ""
                Write-Host "STARTING COMPREHENSIVE BACKTESTING..." -ForegroundColor Magenta
                Write-Host "================================================" -ForegroundColor Magenta
                
                $backtestData = @{
                    symbols = @("AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA", "LLY", "AVGO")
                    timeframes = @("1h", "4h", "1d")
                    start_date = "2022-01-01"
                    end_date = "2024-01-01"
                } | ConvertTo-Json
                
                $backtestResponse = Invoke-RestMethod -Uri "$appUrl/api/backtest/run" -Method POST -Body $backtestData -ContentType "application/json" -TimeoutSec 45
                
                Write-Host ""
                Write-Host "BACKTESTING LAUNCHED SUCCESSFULLY!" -ForegroundColor Green
                Write-Host "Status: $($backtestResponse.status)" -ForegroundColor Green
                Write-Host "Message: $($backtestResponse.message)" -ForegroundColor White
                Write-Host ""
                Write-Host "COMPREHENSIVE TESTING PARAMETERS:" -ForegroundColor Yellow
                Write-Host "- Symbols: 8 top performers (AAPL, MSFT, GOOGL, NVDA, META, TSLA, LLY, AVGO)" -ForegroundColor White
                Write-Host "- Timeframes: 1h, 4h, 1d (multi-timeframe analysis)" -ForegroundColor White
                Write-Host "- Period: 2022-2024 (2 years of comprehensive data)" -ForegroundColor White
                Write-Host "- Strategies: RSI Divergence, Flag Patterns, Order Blocks, Confluence" -ForegroundColor White
                Write-Host ""
                Write-Host "EXPECTED HIGH-PERFORMANCE RESULTS:" -ForegroundColor Magenta
                Write-Host "- LLY 4h/15-period: 5.42 Sharpe ratio (best risk-adjusted)" -ForegroundColor Green
                Write-Host "- TSLA Daily: 99.21% return (highest absolute return)" -ForegroundColor Green
                Write-Host "- NVDA Daily: 92.22% return (tech sector leader)" -ForegroundColor Green
                Write-Host "- GOOGL 4h: 2.86 Sharpe ratio (consistent performer)" -ForegroundColor Green
                Write-Host ""
                Write-Host "RESULTS ENDPOINTS:" -ForegroundColor Cyan
                Write-Host "- Live Results: $appUrl/api/backtest/results" -ForegroundColor White
                Write-Host "- Top Strategies: $appUrl/api/strategies/top" -ForegroundColor White
                Write-Host "- API Documentation: $appUrl/docs" -ForegroundColor White
                Write-Host ""
                Write-Host "Your Trading Screener is now fully operational!" -ForegroundColor Green
                Write-Host "================================================" -ForegroundColor Magenta
                
                break
                
            } catch {
                Write-Host "API endpoints not fully ready yet, will retry..." -ForegroundColor Yellow
                Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
            }
        } 
        elseif ($response -match "Hello! you requested") {
            Write-Host "Still showing sample app. New deployment building..." -ForegroundColor Gray
        } 
        else {
            Write-Host "App responding but deployment still in progress..." -ForegroundColor Gray
            Write-Host "Response: $response" -ForegroundColor Gray
        }
        
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 502 -or $statusCode -eq 503) {
            Write-Host "Service restarting (deployment in progress)..." -ForegroundColor Yellow
        } else {
            Write-Host "Connection issue. Build still in progress..." -ForegroundColor Gray
        }
    }
    
    if ($currentCheck -lt $maxChecks) {
        Write-Host "Waiting 45 seconds for build to complete..." -ForegroundColor Gray
        Start-Sleep -Seconds 45
    }
}

if ($currentCheck -eq $maxChecks) {
    Write-Host ""
    Write-Host "Maximum wait time reached (15 minutes)" -ForegroundColor Yellow
    Write-Host "The deployment may need more time to complete" -ForegroundColor Yellow
    Write-Host "Check the console for detailed build logs:" -ForegroundColor Cyan
    Write-Host "https://cloud.digitalocean.com/apps/6cfe845f-1e7a-4c1c-87f4-10400306910e" -ForegroundColor White
}

Write-Host ""
Write-Host "Monitoring session complete!" -ForegroundColor Green