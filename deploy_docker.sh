#!/bin/bash
# Docker Deployment Script for DigitalOcean
# Run this on your DigitalOcean droplet

set -e

echo "🐳 Deploying Trading Screener to DigitalOcean with Docker"
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root."
    exit 1
fi

print_status "Setting up environment variables..."

# Create .env.production with actual API keys
cat > .env.production << 'EOF'
# Production Environment Configuration
# Alpaca API Configuration
ALPACA_API_KEY=PK463DCZLB0H1M8TG3DN
ALPACA_SECRET_KEY=UNWYjiMmOhCdFIhFvKIXNK0AtdBbFUMDs6w1vVZq
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Database Configuration
DB_PATH=/app/data/trading_data.duckdb

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/trading_screener.log

# Trading Configuration
DEFAULT_TIMEFRAME=1h
DEFAULT_SYMBOLS=AAPL,MSFT,GOOGL,TSLA,AMZN,NVDA,META,AMD,CRM,ADBE

# Backtesting Configuration
BACKTEST_START_DATE=2023-01-01
BACKTEST_END_DATE=2024-01-01
BACKTEST_INITIAL_CAPITAL=10000

# Real-time Streaming Configuration
STREAMING_ENABLED=true
STREAMING_SYMBOLS=AAPL,MSFT,GOOGL,TSLA,NVDA

# Production Configuration
ENVIRONMENT=production
DEBUG=false

# Monitoring Configuration
HEALTH_CHECK_PORT=8080
MONITORING_ENABLED=true

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30

# Security Configuration
SSL_ENABLED=true
CORS_ORIGINS=*
EOF

print_status "Created .env.production with your API keys"

# Create necessary directories
print_status "Creating directories..."
mkdir -p data logs config backups
mkdir -p backups/daily backups/weekly
mkdir -p logs/backtests logs/screening logs/streaming

# Set proper permissions
chmod 600 .env.production
chmod -R 755 data logs config backups

print_status "Building Docker image..."
docker-compose build

print_status "Starting services..."
docker-compose up -d

print_status "Waiting for services to start..."
sleep 10

# Check service status
print_status "Checking service status..."
docker-compose ps

# Test health check
print_status "Testing health check..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_status "✅ Health check passed"
else
    print_warning "⚠ Health check failed (service may still be starting)"
fi

print_status "Setting up monitoring..."
print_status "Grafana will be available at: http://your-droplet-ip:3000"
print_status "Username: admin"
print_status "Password: admin"

print_status "Setting up firewall..."
ufw allow 22/tcp
ufw allow 8080/tcp
ufw allow 3000/tcp
ufw --force enable

print_status "Setting up automatic restarts..."
systemctl enable docker
systemctl start docker

print_status "Creating systemd service..."
cat > /etc/systemd/system/trading-screener.service << 'EOF'
[Unit]
Description=Trading Screener Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/trading-screener
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-screener.service

print_status "Setting up log rotation..."
cat > /etc/logrotate.d/trading-screener << 'EOF'
/opt/trading-screener/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF

print_status "🚀 Deployment complete!"
echo ""
print_status "📊 Service URLs:"
echo "   - Trading Screener: http://your-droplet-ip:8080"
echo "   - Grafana Monitoring: http://your-droplet-ip:3000"
echo ""
print_status "🔧 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Restart services: docker-compose restart"
echo "   - Stop services: docker-compose down"
echo "   - Update and restart: git pull && docker-compose up -d --build"
echo ""
print_status "📈 Monitoring:"
echo "   - Check service status: docker-compose ps"
echo "   - View resource usage: docker stats"
echo "   - Check logs: docker-compose logs trading-screener"
echo ""
print_warning "⚠ Remember to:"
echo "   - Change Grafana admin password"
echo "   - Set up SSL certificates for production"
echo "   - Configure backup retention"
echo "   - Monitor disk space usage" 