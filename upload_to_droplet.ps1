# PowerShell script to upload trading screener to DigitalOcean droplet
# Run this from your project directory

$DROPLET_IP = "159.203.131.140"
$REMOTE_PATH = "/opt/trading-screener"
$SSH_KEY = "~/.ssh/digitalocean_key"

Write-Host "🚀 Uploading Trading Screener to DigitalOcean Droplet..." -ForegroundColor Green

# Check if SSH key exists
if (-not (Test-Path $SSH_KEY)) {
    Write-Host "🔑 SSH key not found. Creating one..." -ForegroundColor Yellow
    ssh-keygen -t rsa -b 4096 -f $SSH_KEY -N '""'
    Write-Host "📋 Copying SSH key to droplet..." -ForegroundColor Yellow
    ssh-copy-id -i "$SSH_KEY.pub" root@$DROPLET_IP
}

Write-Host "📁 Creating remote directory structure..." -ForegroundColor Yellow
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/data_engine"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/backtesting"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/multiprocessing"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine/indicators"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine/patterns"
ssh -i $SSH_KEY root@$DROPLET_IP "mkdir -p $REMOTE_PATH/core/ta_engine/divergences"

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
        scp -i $SSH_KEY $file root@$DROPLET_IP`:$REMOTE_PATH/
    } else {
        Write-Host "Warning: $file not found" -ForegroundColor Red
    }
}

Write-Host "📤 Uploading core files..." -ForegroundColor Yellow

# Upload core files
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
        scp -i $SSH_KEY $file root@$DROPLET_IP`:$REMOTE_PATH/$file
    } else {
        Write-Host "Warning: $file not found" -ForegroundColor Red
    }
}

Write-Host "✅ Upload complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 Next steps:" -ForegroundColor Yellow
Write-Host "1. SSH to your droplet: ssh -i $SSH_KEY root@$DROPLET_IP" -ForegroundColor White
Write-Host "2. Navigate to directory: cd $REMOTE_PATH" -ForegroundColor White
Write-Host "3. Run deployment: chmod +x deploy_docker.sh && ./deploy_docker.sh" -ForegroundColor White
Write-Host ""
Write-Host "📊 After deployment, access:" -ForegroundColor Yellow
Write-Host "   - Trading Screener: http://$DROPLET_IP:8080" -ForegroundColor White
Write-Host "   - Grafana Monitoring: http://$DROPLET_IP:3000" -ForegroundColor White 