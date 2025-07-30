# Deployment Status Check
# Check if trading screener deployment is complete

Write-Host "DEPLOYMENT STATUS CHECK" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green
Write-Host ""

Write-Host "This script will check your trading screener deployment status." -ForegroundColor Yellow
Write-Host "When prompted for SSH passphrase, enter: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

# Check if we can connect to the server
Write-Host "1. Testing SSH connection..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'echo Connection test successful'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "echo 'Connection test successful'" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ SSH connection successful!" -ForegroundColor Green
} else {
    Write-Host "❌ SSH connection failed. Please check your SSH key setup." -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Checking trading screener directory..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'ls -la /opt/trading-screener/'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "ls -la /opt/trading-screener/" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Trading screener directory exists" -ForegroundColor Green
    Write-Host "Directory contents:" -ForegroundColor Cyan
    Write-Host $result -ForegroundColor Gray
} else {
    Write-Host "❌ Trading screener directory not found" -ForegroundColor Red
}

Write-Host "`n3. Checking Docker containers..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'docker ps'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "docker ps" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker is running" -ForegroundColor Green
    Write-Host "Running containers:" -ForegroundColor Cyan
    Write-Host $result -ForegroundColor Gray
} else {
    Write-Host "❌ Docker not available or not running" -ForegroundColor Red
}

Write-Host "`n4. Checking trading screener services..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'cd /opt/trading-screener && docker-compose ps'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "cd /opt/trading-screener && docker-compose ps" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker Compose services found" -ForegroundColor Green
    Write-Host "Service status:" -ForegroundColor Cyan
    Write-Host $result -ForegroundColor Gray
} else {
    Write-Host "❌ Docker Compose services not found or not running" -ForegroundColor Red
}

Write-Host "`n5. Checking health endpoints..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'curl -f http://localhost:8080/health'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "curl -f http://localhost:8080/health" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Trading screener health endpoint responding" -ForegroundColor Green
    Write-Host "Response: $result" -ForegroundColor Gray
} else {
    Write-Host "❌ Trading screener health endpoint not responding" -ForegroundColor Red
}

Write-Host "`n6. Checking Grafana monitoring..." -ForegroundColor Yellow
Write-Host "   Running: ssh root@159.203.131.140 'curl -f http://localhost:3000'" -ForegroundColor Gray
Write-Host "   Enter passphrase when prompted: mcoveney@gmail.com" -ForegroundColor Cyan
Write-Host ""

$result = ssh root@159.203.131.140 "curl -f http://localhost:3000" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Grafana monitoring responding" -ForegroundColor Green
} else {
    Write-Host "❌ Grafana monitoring not responding" -ForegroundColor Red
}

Write-Host "`n" + "=" * 50 -ForegroundColor Green
Write-Host "DEPLOYMENT SUMMARY" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "`nNEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. If services are not running:" -ForegroundColor White
Write-Host "   ssh root@159.203.131.140" -ForegroundColor Gray
Write-Host "   cd /opt/trading-screener" -ForegroundColor Gray
Write-Host "   docker-compose up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "2. If files are missing:" -ForegroundColor White
Write-Host "   Upload missing files using scp commands" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Access your trading screener:" -ForegroundColor White
Write-Host "   http://159.203.131.140:8080" -ForegroundColor Gray
Write-Host "   http://159.203.131.140:3000 (Grafana)" -ForegroundColor Gray

Write-Host "`nCheck completed!" -ForegroundColor Green 