# Upload Database Files to Digital Ocean Droplet
# This script uploads only the database files to the remote server

param(
    [string]$DropletIP = "159.203.131.140",
    [string]$RemoteUser = "root",
    [string]$RemotePath = "/root/trading-app"
)

Write-Host "💾 Uploading database files to Digital Ocean..." -ForegroundColor Green

# Check if data directory exists
if (-not (Test-Path "data")) {
    Write-Host "❌ Error: data directory not found!" -ForegroundColor Red
    exit 1
}

# Create remote data directory
Write-Host "📁 Creating remote data directory..." -ForegroundColor Yellow
ssh ${RemoteUser}@${DropletIP} "mkdir -p ${RemotePath}/data"

# Upload database files
Write-Host "📤 Uploading database files..." -ForegroundColor Yellow
scp -r data/* ${RemoteUser}@${DropletIP}:${RemotePath}/data/

# Set permissions
Write-Host "🔐 Setting permissions..." -ForegroundColor Yellow
ssh ${RemoteUser}@${DropletIP} "chmod -R 644 ${RemotePath}/data/*"

# Restart containers to pick up new data
Write-Host "🔄 Restarting containers..." -ForegroundColor Yellow
ssh ${RemoteUser}@${DropletIP} "cd ${RemotePath} && docker-compose restart trading-screener"

Write-Host "✅ Database upload completed!" -ForegroundColor Green
Write-Host "📊 Check application at: http://${DropletIP}:8080" -ForegroundColor Cyan 