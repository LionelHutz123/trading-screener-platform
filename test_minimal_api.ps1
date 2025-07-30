# Test the minimal API deployment
$appUrl = "https://trading-screener-lerd2.ondigitalocean.app"
$maxChecks = 15
$currentCheck = 0

Write-Host "TESTING MINIMAL API DEPLOYMENT" -ForegroundColor Magenta
Write-Host "This should work with simplified dependencies!" -ForegroundColor Green
Write-Host ""

while ($currentCheck -lt $maxChecks) {
    $currentCheck++
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] Test $currentCheck/$maxChecks..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-RestMethod -Uri "$appUrl/health" -TimeoutSec 15
        
        # Check if we have our trading API response
        if ($response.service -match "trading-screener-api") {
            Write-Host ""
            Write-Host "SUCCESS! TRADING SCREENER API IS LIVE!" -ForegroundColor Green
            Write-Host "Service: $($response.service)" -ForegroundColor Cyan
            Write-Host "Status: $($response.status)" -ForegroundColor Green
            Write-Host "Version: $($response.version)" -ForegroundColor White
            Write-Host "Database: $($response.database)" -ForegroundColor Green
            
            # Test all API endpoints
            Write-Host ""
            Write-Host "TESTING ALL API ENDPOINTS..." -ForegroundColor Cyan
            
            # Test status endpoint
            try {
                $statusResponse = Invoke-RestMethod -Uri "$appUrl/api/status" -TimeoutSec 10
                Write-Host "✓ API Status: $($statusResponse.status)" -ForegroundColor Green
            } catch {
                Write-Host "✗ Status endpoint failed" -ForegroundColor Red
            }
            
            # Test backtest run endpoint
            try {
                $backtestData = @{
                    symbols = @("AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA", "LLY", "AVGO")
                    timeframes = @("1h", "4h", "1d")
                    start_date = "2022-01-01"
                    end_date = "2024-01-01"
                } | ConvertTo-Json
                
                $backtestResponse = Invoke-RestMethod -Uri "$appUrl/api/backtest/run" -Method POST -Body $backtestData -ContentType "application/json" -TimeoutSec 20
                Write-Host "✓ Backtesting: $($backtestResponse.status)" -ForegroundColor Green
                Write-Host "  Message: $($backtestResponse.message)" -ForegroundColor White
                
                # Test results endpoints
                Start-Sleep -Seconds 2
                
                $resultsResponse = Invoke-RestMethod -Uri "$appUrl/api/backtest/results" -TimeoutSec 10
                Write-Host "✓ Results: Found $($resultsResponse.count) results" -ForegroundColor Green
                
                $strategiesResponse = Invoke-RestMethod -Uri "$appUrl/api/strategies/top" -TimeoutSec 10
                Write-Host "✓ Top Strategies: $($strategiesResponse.strategies.Count) strategies" -ForegroundColor Green
                
                Write-Host ""
                Write-Host "COMPREHENSIVE TRADING SCREENER IS OPERATIONAL!" -ForegroundColor Green
                Write-Host "===============================================" -ForegroundColor Magenta
                Write-Host ""
                Write-Host "TOP PERFORMING STRATEGIES:" -ForegroundColor Yellow
                foreach ($strategy in $strategiesResponse.strategies) {
                    Write-Host "  Rank $($strategy.rank): $($strategy.symbol) $($strategy.timeframe) - $($strategy.strategy)" -ForegroundColor White
                    Write-Host "    Sharpe: $($strategy.sharpe_ratio) | Return: $($strategy.return)% | Risk: $($strategy.risk_score)" -ForegroundColor Cyan
                }
                
                Write-Host ""
                Write-Host "API ENDPOINTS READY:" -ForegroundColor Cyan
                Write-Host "- Health: $appUrl/health" -ForegroundColor White
                Write-Host "- Status: $appUrl/api/status" -ForegroundColor White
                Write-Host "- Start Backtest: $appUrl/api/backtest/run" -ForegroundColor White
                Write-Host "- Results: $appUrl/api/backtest/results" -ForegroundColor White
                Write-Host "- Top Strategies: $appUrl/api/strategies/top" -ForegroundColor White
                Write-Host "- API Docs: $appUrl/docs" -ForegroundColor White
                
                Write-Host ""
                Write-Host "TRADING SCREENER DEPLOYMENT COMPLETE!" -ForegroundColor Green
                Write-Host "Ready for live trading strategy analysis!" -ForegroundColor Green
                Write-Host "===============================================" -ForegroundColor Magenta
                
                break
                
            } catch {
                Write-Host "✗ Backtesting endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
            }
        } 
        elseif ($response -match "Hello! you requested") {
            Write-Host "Sample app still active. Build in progress..." -ForegroundColor Gray
        } 
        else {
            Write-Host "Response: $response" -ForegroundColor Gray
        }
        
    } catch {
        Write-Host "Connection failed. Build in progress..." -ForegroundColor Gray
    }
    
    if ($currentCheck -lt $maxChecks) {
        Start-Sleep -Seconds 30
    }
}

if ($currentCheck -eq $maxChecks) {
    Write-Host ""
    Write-Host "Test timeout. Check deployment status:" -ForegroundColor Yellow
    Write-Host "https://cloud.digitalocean.com/apps/6cfe845f-1e7a-4c1c-87f4-10400306910e" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "API testing complete!" -ForegroundColor Green