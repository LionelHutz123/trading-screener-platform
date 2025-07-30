# Manual Remote Server Check
# Provides commands to manually check remote server status

Write-Host "MANUAL REMOTE SERVER CHECK" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host ""

Write-Host "Since automatic SSH with passphrase is complex on Windows," -ForegroundColor Yellow
Write-Host "here are the commands to run manually:" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. CONNECT TO REMOTE SERVER:" -ForegroundColor Cyan
Write-Host "   ssh root@159.203.131.140" -ForegroundColor Gray
Write-Host "   (Enter passphrase: mcoveney@gmail.com)" -ForegroundColor Gray
Write-Host ""

Write-Host "2. CHECK TRADING SCREENER DIRECTORY:" -ForegroundColor Cyan
Write-Host "   ls -la /opt/trading-screener/" -ForegroundColor Gray
Write-Host ""

Write-Host "3. CHECK DOCKER CONTAINERS:" -ForegroundColor Cyan
Write-Host "   docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" -ForegroundColor Gray
Write-Host ""

Write-Host "4. CHECK SERVICE STATUS:" -ForegroundColor Cyan
Write-Host "   cd /opt/trading-screener" -ForegroundColor Gray
Write-Host "   docker-compose ps" -ForegroundColor Gray
Write-Host ""

Write-Host "5. CHECK SYSTEM RESOURCES:" -ForegroundColor Cyan
Write-Host "   df -h" -ForegroundColor Gray
Write-Host "   free -h" -ForegroundColor Gray
Write-Host ""

Write-Host "6. CHECK LOGS:" -ForegroundColor Cyan
Write-Host "   docker-compose logs trading-screener" -ForegroundColor Gray
Write-Host ""

Write-Host "7. RESTART SERVICES IF NEEDED:" -ForegroundColor Cyan
Write-Host "   docker-compose down" -ForegroundColor Gray
Write-Host "   docker-compose up -d" -ForegroundColor Gray
Write-Host ""

Write-Host "8. CHECK HEALTH ENDPOINTS:" -ForegroundColor Cyan
Write-Host "   curl http://localhost:8080/health" -ForegroundColor Gray
Write-Host "   curl http://localhost:3000" -ForegroundColor Gray
Write-Host ""

Write-Host "EXPECTED RESULTS:" -ForegroundColor Yellow
Write-Host "================" -ForegroundColor Yellow
Write-Host "✅ Directory should contain: docker-compose.yml, main.py, core/" -ForegroundColor Green
Write-Host "✅ Docker containers should show: trading-screener, monitoring" -ForegroundColor Green
Write-Host "✅ Services should show: Up (healthy)" -ForegroundColor Green
Write-Host "✅ Health endpoint should return: 200 OK" -ForegroundColor Green
Write-Host ""

Write-Host "IF ISSUES FOUND:" -ForegroundColor Red
Write-Host "===============" -ForegroundColor Red
Write-Host "1. Upload missing files:" -ForegroundColor White
Write-Host "   scp main.py root@159.203.131.140:/opt/trading-screener/" -ForegroundColor Gray
Write-Host "   scp docker-compose.yml root@159.203.131.140:/opt/trading-screener/" -ForegroundColor Gray
Write-Host "   scp Dockerfile root@159.203.131.140:/opt/trading-screener/" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Deploy services:" -ForegroundColor White
Write-Host "   chmod +x deploy_docker.sh" -ForegroundColor Gray
Write-Host "   ./deploy_docker.sh" -ForegroundColor Gray
Write-Host ""

Write-Host "Check completed! Run the commands above manually." -ForegroundColor Green 