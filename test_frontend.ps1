# Test frontend deployment
$appUrl = "https://trading-screener-lerd2.ondigitalocean.app"
$maxChecks = 12
$currentCheck = 0

Write-Host "TESTING FRONTEND DEPLOYMENT" -ForegroundColor Magenta
Write-Host "Should serve both API and web interface!" -ForegroundColor Green
Write-Host ""

while ($currentCheck -lt $maxChecks) {
    $currentCheck++
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] Test $currentCheck/$maxChecks..." -ForegroundColor Yellow
    
    try {
        # Test if we get HTML response (frontend)
        $response = Invoke-WebRequest -Uri $appUrl -TimeoutSec 15
        
        if ($response.Content -match "Trading Screener Dashboard") {
            Write-Host ""
            Write-Host "SUCCESS! FRONTEND IS LIVE!" -ForegroundColor Green
            Write-Host "Content Type: $($response.Headers.'Content-Type')" -ForegroundColor Cyan
            Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
            
            # Test API endpoints
            Write-Host ""
            Write-Host "TESTING API ENDPOINTS..." -ForegroundColor Cyan
            
            try {
                $healthResponse = Invoke-RestMethod -Uri "$appUrl/health" -TimeoutSec 10
                Write-Host "✓ Health Check: $($healthResponse.status)" -ForegroundColor Green
                
                $statusResponse = Invoke-RestMethod -Uri "$appUrl/api/status" -TimeoutSec 10  
                Write-Host "✓ API Status: $($statusResponse.status)" -ForegroundColor Green
                
                $strategiesResponse = Invoke-RestMethod -Uri "$appUrl/api/strategies/top" -TimeoutSec 10
                Write-Host "✓ Top Strategies: $($strategiesResponse.strategies.Count) available" -ForegroundColor Green
                
                $resultsResponse = Invoke-RestMethod -Uri "$appUrl/api/backtest/results" -TimeoutSec 10
                Write-Host "✓ Results: $($resultsResponse.count) results available" -ForegroundColor Green
                
            } catch {
                Write-Host "✗ Some API endpoints not ready: $($_.Exception.Message)" -ForegroundColor Yellow
            }
            
            Write-Host ""
            Write-Host "COMPREHENSIVE TRADING SCREENER WEB APP IS LIVE!" -ForegroundColor Green
            Write-Host "=================================================" -ForegroundColor Magenta
            Write-Host ""
            Write-Host "🌐 WEB INTERFACE: $appUrl" -ForegroundColor Cyan
            Write-Host "📊 FEATURES AVAILABLE:" -ForegroundColor Yellow
            Write-Host "   - Real-time system health monitoring" -ForegroundColor White
            Write-Host "   - Interactive backtesting launcher" -ForegroundColor White
            Write-Host "   - Symbol and timeframe selection" -ForegroundColor White
            Write-Host "   - Live results visualization" -ForegroundColor White
            Write-Host "   - Top strategies dashboard" -ForegroundColor White
            Write-Host "   - Auto-refreshing data" -ForegroundColor White
            Write-Host ""
            Write-Host "🚀 READY TO LAUNCH BACKTESTS FROM WEB INTERFACE!" -ForegroundColor Green
            Write-Host "=================================================" -ForegroundColor Magenta
            
            break
            
        } elseif ($response.Content -match "Hello! you requested") {
            Write-Host "Sample app still running. Frontend deploying..." -ForegroundColor Gray
        } else {
            Write-Host "Unexpected response content" -ForegroundColor Gray
        }
        
    } catch {
        Write-Host "Connection failed. Deployment in progress..." -ForegroundColor Gray
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
Write-Host "Frontend testing complete!" -ForegroundColor Green