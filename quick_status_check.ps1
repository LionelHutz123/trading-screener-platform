# Quick Deployment Status Check
# Simple PowerShell script to check trading screener deployment

$Server = "root@159.203.131.140"
$Passphrase = "mcoveney@gmail.com"

Write-Host "🚀 TRADING SCREENER DEPLOYMENT STATUS" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""

# Function to run SSH command with passphrase
function Invoke-SSHWithPassphrase {
    param([string]$Command)
    
    $sshScript = @"
#!/usr/bin/expect -f
set timeout 30
spawn ssh -o StrictHostKeyChecking=no $Server "$Command"
expect "Enter passphrase for key"
send "$Passphrase\r"
expect eof
"@
    
    $tempFile = [System.IO.Path]::GetTempFileName()
    $sshScript | Out-File -FilePath $tempFile -Encoding ASCII
    
    try {
        $result = & expect $tempFile 2>&1
        return $true, $result
    }
    catch {
        return $false, $_.Exception.Message
    }
    finally {
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }
    }
}

# Check if we can connect to the server
Write-Host "🔍 Testing SSH connection..." -ForegroundColor Yellow
$success, $output = Invoke-SSHWithPassphrase "echo 'Connection test successful'"
if ($success) {
    Write-Host "✅ SSH connection: OK" -ForegroundColor Green
} else {
    Write-Host "❌ SSH connection: FAILED" -ForegroundColor Red
    Write-Host "Error: $output" -ForegroundColor Red
    exit 1
}

# Check Docker services
Write-Host "`n🐳 Checking Docker services..." -ForegroundColor Yellow
$success, $output = Invoke-SSHWithPassphrase "cd /opt/trading-screener; docker-compose ps"
if ($success) {
    Write-Host "✅ Docker services:" -ForegroundColor Green
    Write-Host $output
} else {
    Write-Host "❌ Docker services check failed" -ForegroundColor Red
}

# Check if containers are running
$success, $output = Invoke-SSHWithPassphrase "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
if ($success) {
    Write-Host "📊 Running containers:" -ForegroundColor Green
    Write-Host $output
}

# Check health endpoints
Write-Host "`n🏥 Checking health endpoints..." -ForegroundColor Yellow
$success, $output = Invoke-SSHWithPassphrase "curl -f http://localhost:8080/health 2>/dev/null; if [ `$? -ne 0 ]; then echo 'Health check failed'; fi"
if ($success -and $output -notmatch "Health check failed") {
    Write-Host "✅ Trading screener: OK" -ForegroundColor Green
} else {
    Write-Host "❌ Trading screener: FAILED" -ForegroundColor Red
}

$success, $output = Invoke-SSHWithPassphrase "curl -f http://localhost:3000 2>/dev/null; if [ `$? -ne 0 ]; then echo 'Grafana check failed'; fi"
if ($success -and $output -notmatch "Grafana check failed") {
    Write-Host "✅ Grafana monitoring: OK" -ForegroundColor Green
} else {
    Write-Host "❌ Grafana monitoring: FAILED" -ForegroundColor Red
}

# Check key files
Write-Host "`n📁 Checking key files..." -ForegroundColor Yellow
$files = @(
    "docker-compose.yml",
    "Dockerfile", 
    ".env.production",
    "main.py"
)

foreach ($file in $files) {
    $success, $output = Invoke-SSHWithPassphrase "if [ -f /opt/trading-screener/$file ]; then echo 'EXISTS'; else echo 'MISSING'; fi"
    if ($success -and $output -match "EXISTS") {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file" -ForegroundColor Red
    }
}

# Check system resources
Write-Host "`n💻 Checking system resources..." -ForegroundColor Yellow
$success, $output = Invoke-SSHWithPassphrase "df -h /opt/trading-screener"
if ($success) {
    Write-Host "📊 Disk usage:" -ForegroundColor Green
    Write-Host $output
}

# Check recent logs
Write-Host "`n📋 Checking recent logs..." -ForegroundColor Yellow
$success, $output = Invoke-SSHWithPassphrase "docker-compose logs --tail=5 trading-screener 2>/dev/null || echo 'No logs available'"
if ($success) {
    Write-Host "📝 Recent logs:" -ForegroundColor Green
    Write-Host $output
}

# Summary
Write-Host "`n" + "=" * 50 -ForegroundColor Green
Write-Host "📋 DEPLOYMENT SUMMARY" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "`n🔧 Next Steps:" -ForegroundColor Cyan
Write-Host "1. If services are not running: docker-compose up -d" -ForegroundColor White
Write-Host "2. If health checks fail: check logs and restart services" -ForegroundColor White
Write-Host "3. If files are missing: re-upload missing files" -ForegroundColor White
Write-Host "4. Monitor logs: docker-compose logs -f trading-screener" -ForegroundColor White

Write-Host "`n✅ Status check complete!" -ForegroundColor Green 