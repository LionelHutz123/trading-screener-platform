# Deployment Status Checker for Trading Screener
# PowerShell version for Windows

param(
    [string]$Server = "root@159.203.131.140",
    [string]$Passphrase = "mcoveney@gmail.com"
)

Write-Host "🚀 TRADING SCREENER DEPLOYMENT STATUS REPORT" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

# Function to run SSH command
function Invoke-SSHCommand {
    param(
        [string]$Command,
        [string]$Server = $Server,
        [string]$Passphrase = $Passphrase
    )
    
    try {
        # Create a temporary expect script
        $expectScript = @"
#!/usr/bin/expect
set timeout 30
spawn ssh -o StrictHostKeyChecking=no $Server "$Command"
expect "Enter passphrase for key"
send "$Passphrase\r"
expect eof
"@
        
        $tempFile = [System.IO.Path]::GetTempFileName()
        $expectScript | Out-File -FilePath $tempFile -Encoding ASCII
        
        $result = & expect $tempFile 2>&1
        Remove-Item $tempFile -Force
        
        return $true, $result, ""
    }
    catch {
        return $false, "", $_.Exception.Message
    }
}

# Check Docker services
Write-Host "🔍 Checking Docker services status..." -ForegroundColor Yellow
$success, $output, $error = Invoke-SSHCommand "cd /opt/trading-screener && docker-compose ps"
if ($success) {
    Write-Host "✅ Docker services status:" -ForegroundColor Green
    Write-Host $output
} else {
    Write-Host "❌ Failed to check Docker services:" -ForegroundColor Red
    Write-Host $error
}

# Check running containers
$success, $output, $error = Invoke-SSHCommand "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
if ($success) {
    Write-Host "📊 Running containers:" -ForegroundColor Green
    Write-Host $output
}

# Check health endpoints
Write-Host "`n🏥 Checking health endpoints..." -ForegroundColor Yellow
$success, $output, $error = Invoke-SSHCommand "curl -f http://localhost:8080/health 2>/dev/null || echo 'Health check failed'"
if ($success -and $output -notmatch "Health check failed") {
    Write-Host "✅ Trading screener health endpoint: OK" -ForegroundColor Green
} else {
    Write-Host "❌ Trading screener health endpoint: FAILED" -ForegroundColor Red
}

$success, $output, $error = Invoke-SSHCommand "curl -f http://localhost:3000 2>/dev/null || echo 'Grafana check failed'"
if ($success -and $output -notmatch "Grafana check failed") {
    Write-Host "✅ Grafana monitoring: OK" -ForegroundColor Green
} else {
    Write-Host "❌ Grafana monitoring: FAILED" -ForegroundColor Red
}

# Check file structure
Write-Host "`n📁 Checking file structure..." -ForegroundColor Yellow
$files = @(
    "/opt/trading-screener/docker-compose.yml",
    "/opt/trading-screener/Dockerfile",
    "/opt/trading-screener/.env.production",
    "/opt/trading-screener/main.py",
    "/opt/trading-screener/core/__init__.py",
    "/opt/trading-screener/core/ta_engine/__init__.py",
    "/opt/trading-screener/core/data_engine/__init__.py",
    "/opt/trading-screener/core/backtesting/__init__.py",
    "/opt/trading-screener/core/multiprocessing/__init__.py"
)

foreach ($file in $files) {
    $success, $output, $error = Invoke-SSHCommand "test -f $file && echo 'EXISTS' || echo 'MISSING'"
    if ($success -and $output -match "EXISTS") {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file" -ForegroundColor Red
    }
}

# Check system resources
Write-Host "`n💻 Checking system resources..." -ForegroundColor Yellow
$success, $output, $error = Invoke-SSHCommand "df -h /opt/trading-screener"
if ($success) {
    Write-Host "📊 Disk usage:" -ForegroundColor Green
    Write-Host $output
}

$success, $output, $error = Invoke-SSHCommand "free -h"
if ($success) {
    Write-Host "🧠 Memory usage:" -ForegroundColor Green
    Write-Host $output
}

# Check logs
Write-Host "`n📋 Checking recent logs..." -ForegroundColor Yellow
$success, $output, $error = Invoke-SSHCommand "docker-compose logs --tail=10 trading-screener"
if ($success) {
    Write-Host "📝 Recent trading screener logs:" -ForegroundColor Green
    Write-Host $output
}

# Check for errors
$success, $output, $error = Invoke-SSHCommand "docker-compose logs trading-screener | grep -i error | tail -5"
if ($success -and $output.Trim()) {
    Write-Host "⚠️  Recent errors:" -ForegroundColor Yellow
    Write-Host $output
} else {
    Write-Host "✅ No recent errors found" -ForegroundColor Green
}

# Check network connectivity
Write-Host "`n🌐 Checking network connectivity..." -ForegroundColor Yellow
$success, $output, $error = Invoke-SSHCommand "netstat -tulpn | grep -E ':(8080|3000)'"
if ($success) {
    Write-Host "🔌 Active ports:" -ForegroundColor Green
    Write-Host $output
} else {
    Write-Host "❌ No expected ports found" -ForegroundColor Red
}

# Summary
Write-Host "`n" + "=" * 60 -ForegroundColor Green
Write-Host "📋 DEPLOYMENT SUMMARY" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

Write-Host "`n🔧 Next Steps:" -ForegroundColor Cyan
Write-Host "1. If services are not running: docker-compose up -d" -ForegroundColor White
Write-Host "2. If health checks fail: check logs and restart services" -ForegroundColor White
Write-Host "3. If files are missing: re-upload missing files" -ForegroundColor White
Write-Host "4. If ports are not open: check firewall configuration" -ForegroundColor White
Write-Host "5. Monitor logs: docker-compose logs -f trading-screener" -ForegroundColor White

Write-Host "`n✅ Status check complete!" -ForegroundColor Green 