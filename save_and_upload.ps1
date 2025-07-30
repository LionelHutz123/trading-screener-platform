# Save Docker Image and Upload to Digital Ocean
# This approach doesn't require a registry account

param(
    [string]$DropletIP = "159.203.131.140",
    [string]$RemoteUser = "root",
    [string]$RemotePath = "/root/trading-app",
    [string]$ImageName = "trading-screener.tar"
)

Write-Host "💾 Saving Docker image..." -ForegroundColor Green

# Save the image as a tar file
docker save untitledfolder-trading-screener:latest -o $ImageName

Write-Host "📤 Uploading image to Digital Ocean..." -ForegroundColor Yellow
scp $ImageName ${RemoteUser}@${DropletIP}:${RemotePath}/

Write-Host "🐳 Loading image on remote server..." -ForegroundColor Yellow
ssh ${RemoteUser}@${DropletIP} "cd ${RemotePath} && docker load -i $ImageName"

Write-Host "🔄 Updating docker-compose.yml..." -ForegroundColor Yellow
# Create a temporary docker-compose file that uses the loaded image
$composeContent = @"
version: '3.8'

services:
  trading-screener:
    image: untitledfolder-trading-screener:latest
    container_name: trading-screener
    restart: unless-stopped
    environment:
      - ENV=production
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
      - ./backups:/app/backups
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "python", "health_check.py"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - trading-network

  monitoring:
    image: grafana/grafana:latest
    container_name: trading-monitoring
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
    networks:
      - trading-network

  database-backup:
    image: alpine:latest
    container_name: trading-backup
    restart: unless-stopped
    volumes:
      - ./data:/data
      - ./backups:/backups
    command: |
      sh -c '
      while true; do
        cp /data/trading_data.duckdb /backups/daily/backup_$(date +%Y%m%d_%H%M%S).duckdb
        sleep 86400
      done
      '
    networks:
      - trading-network

networks:
  trading-network:
    driver: bridge

volumes:
  grafana-storage:
"@

$composeContent | Out-File -FilePath "docker-compose.prod.yml" -Encoding UTF8
scp docker-compose.prod.yml ${RemoteUser}@${DropletIP}:${RemotePath}/docker-compose.yml

Write-Host "🚀 Starting containers..." -ForegroundColor Yellow
ssh ${RemoteUser}@${DropletIP} "cd ${RemotePath} && docker-compose down && docker-compose up -d"

Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host "📊 Application: http://${DropletIP}:8080" -ForegroundColor Cyan
Write-Host "📈 Monitoring: http://${DropletIP}:3000" -ForegroundColor Cyan

# Clean up local tar file
Remove-Item $ImageName -ErrorAction SilentlyContinue
Write-Host "🧹 Cleaned up local tar file" -ForegroundColor Green 