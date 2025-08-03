# Test script for live HutzTrades deployment
param(
    [string]$AppUrl = "https://trading-screener-lerd2.ondigitalocean.app"
)

Write-Host "🧪 Testing HutzTrades Live Deployment" -ForegroundColor Cyan
Write-Host "🌐 URL: $AppUrl" -ForegroundColor Yellow

# Test 1: Health Check
Write-Host "`n1️⃣ Testing Health Endpoint..." -ForegroundColor Green
try {
    $health = Invoke-RestMethod -Uri "$AppUrl/health" -Method Get
    Write-Host "✅ Health Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Security: $($health.security.enabled)" -ForegroundColor White
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
}

# Test 2: Stream Status
Write-Host "`n2️⃣ Testing Stream Status..." -ForegroundColor Green
try {
    $streamStatus = Invoke-RestMethod -Uri "$AppUrl/api/stream/status" -Method Get
    Write-Host "✅ Stream Status: $($streamStatus.stream_status)" -ForegroundColor Green
    Write-Host "   WebSocket Connections: $($streamStatus.websocket_connections)" -ForegroundColor White
} catch {
    Write-Host "❌ Stream status check failed: $_" -ForegroundColor Red
}

# Test 3: API Status
Write-Host "`n3️⃣ Testing API Status..." -ForegroundColor Green
try {
    $apiStatus = Invoke-RestMethod -Uri "$AppUrl/api/status" -Method Get
    Write-Host "✅ API Status: $($apiStatus.api)" -ForegroundColor Green
    Write-Host "   Backtesting: $($apiStatus.backtesting)" -ForegroundColor White
    Write-Host "   Strategies: $($apiStatus.strategies)" -ForegroundColor White
} catch {
    Write-Host "❌ API status check failed: $_" -ForegroundColor Red
}

# Test 4: Check Available Endpoints
Write-Host "`n4️⃣ Available Streaming Endpoints:" -ForegroundColor Green
Write-Host "   📊 Dashboard: $AppUrl/" -ForegroundColor White
Write-Host "   🔍 Health: $AppUrl/health" -ForegroundColor White
Write-Host "   📡 Stream Status: $AppUrl/api/stream/status" -ForegroundColor White
Write-Host "   ▶️  Start Stream: POST $AppUrl/api/stream/start" -ForegroundColor White
Write-Host "   📈 Live Signals: $AppUrl/api/stream/signals" -ForegroundColor White
Write-Host "   🔌 WebSocket: wss://$($AppUrl -replace 'https://', '')/ws/stream" -ForegroundColor White
Write-Host "   📚 API Docs: $AppUrl/docs" -ForegroundColor White

# Test 5: Test Starting Stream (optional)
Write-Host "`n5️⃣ Start Streaming? (y/n)" -ForegroundColor Yellow
$startStream = Read-Host
if ($startStream -eq 'y') {
    try {
        $startResult = Invoke-RestMethod -Uri "$AppUrl/api/stream/start" -Method Post
        Write-Host "✅ Streaming Started: $($startResult.status)" -ForegroundColor Green
        Write-Host "   Message: $($startResult.message)" -ForegroundColor White
    } catch {
        Write-Host "❌ Failed to start streaming: $_" -ForegroundColor Red
    }
}

Write-Host "`n✨ Testing Complete!" -ForegroundColor Green