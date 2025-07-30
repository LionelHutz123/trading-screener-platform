# Fix Trading Screener Deployment
# Install docker-compose and start services

Write-Host "FIXING TRADING SCREENER DEPLOYMENT" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

Write-Host "Issues found:" -ForegroundColor Yellow
Write-Host "1. docker-compose not installed" -ForegroundColor Red
Write-Host "2. Services not running" -ForegroundColor Red
Write-Host "3. Health endpoints not responding" -ForegroundColor Red
Write-Host ""

Write-Host "FIXING STEPS:" -ForegroundColor Cyan
Write-Host "=============" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Installing docker-compose..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'curl -L \"https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "curl -L 'https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)' -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ docker-compose installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install docker-compose" -ForegroundColor Red
    Write-Host "Error: $result" -ForegroundColor Red
}

Write-Host "`n2. Verifying docker-compose installation..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'docker-compose --version'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "docker-compose --version" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ docker-compose is working: $result" -ForegroundColor Green
} else {
    Write-Host "❌ docker-compose still not working" -ForegroundColor Red
    Write-Host "Error: $result" -ForegroundColor Red
}

Write-Host "`n3. Starting trading screener services..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'cd /opt/trading-screener && docker-compose up -d'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "cd /opt/trading-screener && docker-compose up -d" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Services started successfully" -ForegroundColor Green
    Write-Host "Output: $result" -ForegroundColor Gray
} else {
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    Write-Host "Error: $result" -ForegroundColor Red
}

Write-Host "`n4. Checking service status..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'cd /opt/trading-screener && docker-compose ps'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "cd /opt/trading-screener && docker-compose ps" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Service status:" -ForegroundColor Green
    Write-Host $result -ForegroundColor Gray
} else {
    Write-Host "❌ Could not check service status" -ForegroundColor Red
    Write-Host "Error: $result" -ForegroundColor Red
}

Write-Host "`n5. Checking health endpoints..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'sleep 10 && curl -f http://localhost:8080/health'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "sleep 10 && curl -f http://localhost:8080/health" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Trading screener health endpoint responding" -ForegroundColor Green
    Write-Host "Response: $result" -ForegroundColor Gray
} else {
    Write-Host "❌ Trading screener health endpoint still not responding" -ForegroundColor Red
    Write-Host "Error: $result" -ForegroundColor Red
}

Write-Host "`n6. Checking Grafana..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'curl -f http://localhost:3000'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "curl -f http://localhost:3000" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Grafana monitoring responding" -ForegroundColor Green
} else {
    Write-Host "❌ Grafana monitoring still not responding" -ForegroundColor Red
    Write-Host "Error: $result" -ForegroundColor Red
}

Write-Host "`n" + "=" * 50 -ForegroundColor Green
Write-Host "DEPLOYMENT FIX SUMMARY" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "`n✅ FIXES APPLIED:" -ForegroundColor Green
Write-Host "- Installed docker-compose" -ForegroundColor White
Write-Host "- Started trading screener services" -ForegroundColor White
Write-Host "- Checked service status" -ForegroundColor White
Write-Host "- Verified health endpoints" -ForegroundColor White

Write-Host "`n🌐 ACCESS YOUR TRADING SCREENER:" -ForegroundColor Cyan
Write-Host "http://159.203.131.140:8080" -ForegroundColor White
Write-Host "http://159.203.131.140:3000 (Grafana)" -ForegroundColor White

Write-Host "`n🔧 IF SERVICES STILL NOT WORKING:" -ForegroundColor Yellow
Write-Host "1. Check logs: ssh root@159.203.131.140 'cd /opt/trading-screener && docker-compose logs'" -ForegroundColor Gray
Write-Host "2. Restart services: ssh root@159.203.131.140 'cd /opt/trading-screener && docker-compose restart'" -ForegroundColor Gray
Write-Host "3. Rebuild: ssh root@159.203.131.140 'cd /opt/trading-screener && docker-compose up -d --build'" -ForegroundColor Gray

Write-Host "Fix completed!" -ForegroundColor Green 