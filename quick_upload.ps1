# Quick upload script using existing SSH key
# Run this from your project directory

$DROPLET_IP = "159.203.131.140"
$REMOTE_PATH = "/opt/trading-screener"

Write-Host "🚀 Quick Upload to DigitalOcean Droplet..." -ForegroundColor Green

# Start SSH agent and add key
Write-Host "🔑 Setting up SSH agent..." -ForegroundColor Yellow
Start-Service ssh-agent
ssh-add C:\Users\python\.ssh\id_rsa

Write-Host "📁 Creating directories..." -ForegroundColor Yellow
ssh root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine/indicators"
ssh root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine/patterns"
ssh root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine/divergences"
ssh root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/data_engine"
ssh root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/backtesting"
ssh root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/multiprocessing"

Write-Host "📤 Uploading main files..." -ForegroundColor Yellow

# Upload main files
$mainFiles = @(
    "deploy_docker.sh",
    "docker-compose.yml", 
    "Dockerfile",
    "requirements.txt",
    "main.py",
    "alpaca_fetcher_new.py",
    "config.py",
    "health_check.py",
    "monitoring.py",
    "backup.py"
)

foreach ($file in $mainFiles) {
    if (Test-Path $file) {
        Write-Host "Uploading $file..." -ForegroundColor Cyan
        scp $file root@$DROPLET_IP`:$REMOTE_PATH/
    } else {
        Write-Host "Warning: $file not found" -ForegroundColor Red
    }
}

Write-Host "📤 Uploading core files..." -ForegroundColor Yellow

# Upload core files that exist
$coreFiles = @(
    "core/__init__.py",
    "core/ta_engine/__init__.py",
    "core/ta_engine/unified_strategy_engine.py",
    "core/ta_engine/indicators/__init__.py",
    "core/ta_engine/indicators/indicators.py",
    "core/ta_engine/patterns/__init__.py",
    "core/ta_engine/patterns/base_detector.py",
    "core/ta_engine/patterns/order_blocks.py",
    "core/ta_engine/patterns/fair_value_gaps.py",
    "core/ta_engine/divergences/__init__.py",
    "core/ta_engine/divergences/rsi_divergence.py",
    "core/data_engine/__init__.py",
    "core/data_engine/duckdb_handler.py",
    "core/data_engine/sql_database.py",
    "core/backtesting/__init__.py",
    "core/backtesting/backtest_engine.py",
    "core/multiprocessing/__init__.py",
    "core/multiprocessing/parallel_engine.py"
)

foreach ($file in $coreFiles) {
    if (Test-Path $file) {
        Write-Host "Uploading $file..." -ForegroundColor Cyan
        scp $file root@$DROPLET_IP`:$REMOTE_PATH/$file
    } else {
        Write-Host "Warning: $file not found - $file" -ForegroundColor Red
    }
}

Write-Host "✅ Upload complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 Next steps:" -ForegroundColor Yellow
Write-Host "1. SSH to your droplet: ssh root@$DROPLET_IP" -ForegroundColor White
Write-Host "2. Navigate to directory: cd $REMOTE_PATH" -ForegroundColor White
Write-Host "3. Run deployment: chmod +x deploy_docker.sh && ./deploy_docker.sh" -ForegroundColor White
Write-Host ""
Write-Host "📊 After deployment, access:" -ForegroundColor Yellow
Write-Host "   - Trading Screener: http://$DROPLET_IP:8080" -ForegroundColor White
Write-Host "   - Grafana Monitoring: http://$DROPLET_IP:3000" -ForegroundColor White 