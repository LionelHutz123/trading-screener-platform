# Monitor HutzTrades deployment progress
$appUrl = "https://trading-screener-lerd2.ondigitalocean.app"

Write-Host "Monitoring HutzTrades Deployment..." -ForegroundColor Cyan
Write-Host "URL: $appUrl" -ForegroundColor Yellow

$deploymentReady = $false
$attempts = 0
$maxAttempts = 20

while (-not $deploymentReady -and $attempts -lt $maxAttempts) {
    $attempts++
    Write-Host "`nAttempt $attempts/$maxAttempts..." -ForegroundColor White
    
    try {
        # Test health endpoint
        $healthResponse = Invoke-RestMethod -Uri "$appUrl/health" -Method Get -TimeoutSec 10
        Write-Host "Health Status: $($healthResponse.status)" -ForegroundColor Green
        
        # Test if streaming endpoints are available
        try {
            $streamResponse = Invoke-RestMethod -Uri "$appUrl/api/stream/status" -Method Get -TimeoutSec 10
            Write-Host "Stream Status: $($streamResponse.stream_status)" -ForegroundColor Green
            $deploymentReady = $true
        } catch {
            Write-Host "Streaming endpoints not yet available..." -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "Deployment still in progress..." -ForegroundColor Yellow
    }
    
    if (-not $deploymentReady) {
        Start-Sleep -Seconds 30
    }
}

if ($deploymentReady) {
    Write-Host "`n✅ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host "🎉 HutzTrades Live Streaming Platform is LIVE!" -ForegroundColor Cyan
    
    Write-Host "`n📡 Testing Live Streaming Endpoints:" -ForegroundColor Yellow
    
    # Test health
    try {
        $health = Invoke-RestMethod -Uri "$appUrl/health" -Method Get
        Write-Host "✅ Health: $($health.status)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Health check failed" -ForegroundColor Red
    }
    
    # Test stream status
    try {
        $streamStatus = Invoke-RestMethod -Uri "$appUrl/api/stream/status" -Method Get
        Write-Host "✅ Stream Status: $($streamStatus.stream_status)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Stream status failed" -ForegroundColor Red
    }
    
    # Test API status
    try {
        $apiStatus = Invoke-RestMethod -Uri "$appUrl/api/status" -Method Get
        Write-Host "✅ API Status: $($apiStatus.api)" -ForegroundColor Green
    } catch {
        Write-Host "❌ API status failed" -ForegroundColor Red
    }
    
    Write-Host "`n🌐 Your Live Platform:" -ForegroundColor Cyan
    Write-Host "   Dashboard: $appUrl" -ForegroundColor White
    Write-Host "   API Docs: $appUrl/docs" -ForegroundColor White
    Write-Host "   Stream Status: $appUrl/api/stream/status" -ForegroundColor White
    Write-Host "   Live Signals: $appUrl/api/stream/signals" -ForegroundColor White
    
    Write-Host "`n🎯 Pattern Recognition Features:" -ForegroundColor Yellow
    Write-Host "   ✅ Flag patterns (bullish/bearish)" -ForegroundColor Green
    Write-Host "   ✅ Order block detection" -ForegroundColor Green
    Write-Host "   ✅ Fair value gaps (FVG)" -ForegroundColor Green
    Write-Host "   ✅ Change of character (CHoCH)" -ForegroundColor Green
    Write-Host "   ✅ Swing high/low detection" -ForegroundColor Green
    Write-Host "   ✅ Real-time confluence signals" -ForegroundColor Green
    
    Write-Host "`n💡 Next Steps:" -ForegroundColor Yellow
    Write-Host "   1. Start streaming: curl -X POST $appUrl/api/stream/start" -ForegroundColor White
    Write-Host "   2. Monitor signals: curl $appUrl/api/stream/signals" -ForegroundColor White
    Write-Host "   3. Connect via WebSocket: wss://trading-screener-lerd2.ondigitalocean.app/ws/stream" -ForegroundColor White
    
} else {
    Write-Host "`n⏱️ Deployment timed out or failed" -ForegroundColor Red
    Write-Host "Check DigitalOcean dashboard for deployment status" -ForegroundColor Yellow
}

Write-Host "`n🚀 HutzTrades monitoring complete!" -ForegroundColor Cyan