# 🚀 Production Deployment Guide

This guide covers deploying the Trading Screener to Digital Ocean using Docker containers with full monitoring, alerting, and SSL support.

## 📋 Prerequisites

### Required Tools
- [Docker](https://docs.docker.com/get-docker/) >= 20.10
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.0
- [DigitalOcean CLI (doctl)](https://docs.digitalocean.com/reference/doctl/how-to/install/)
- [Node.js](https://nodejs.org/) >= 18.0 (for frontend build)

### Required Accounts & APIs
- DigitalOcean account with API token
- Alpaca trading account with API keys
- SMTP server for email alerts (optional)
- Domain name for SSL (optional)

## 🔧 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd trading-screener

# Copy environment template
cp .env.example .env.production

# Edit environment variables
nano .env.production
```

### 2. Configure Environment Variables

Create `.env.production` with the following variables:

```bash
# Alpaca API Configuration
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key

# Redis Configuration
REDIS_PASSWORD=secure_redis_password

# Email Alerts (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_password
ALERT_EMAIL=alerts@yourdomain.com

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=secure_grafana_password

# SSL (Optional)
DOMAIN_NAME=yourdomain.com

# DigitalOcean
DIGITAL_OCEAN_TOKEN=your_do_api_token
```

### 3. Automated Deployment

```bash
# Make deployment script executable
chmod +x deploy/digitalocean_deploy.sh

# Deploy to Digital Ocean
./deploy/digitalocean_deploy.sh deploy
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │    Frontend     │    │    Backend      │
│  (Reverse Proxy)│────│   (Next.js)     │────│   (FastAPI)     │
│   Port 80/443   │    │   Port 3000     │    │   Port 8080     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │     Redis       │    │   Prometheus    │    │    Grafana      │
    │  (Cache/Queue)  │    │   (Metrics)     │    │  (Monitoring)   │
    │   Port 6379     │    │   Port 9090     │    │   Port 3001     │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Service Configuration

### Backend Services

#### Trading Screener (Main Service)
- **Port**: 8080
- **Resources**: 2GB RAM, 1 CPU
- **Health Check**: `/health` endpoint
- **Logs**: `/app/logs/`

#### Redis (Cache & Message Queue)
- **Port**: 6379 (internal only)
- **Resources**: 512MB RAM
- **Persistence**: AOF enabled
- **Password**: Set via `REDIS_PASSWORD`

### Frontend Service

#### Next.js Frontend
- **Port**: 3000
- **Resources**: 512MB RAM
- **Build**: Optimized production build
- **Static Assets**: Cached by Nginx

### Monitoring Stack

#### Prometheus (Metrics Collection)
- **Port**: 9090 (internal only)
- **Retention**: 200 hours
- **Storage**: 10GB limit
- **Scrape Interval**: 15s

#### Grafana (Visualization)
- **Port**: 3001
- **Default User**: admin
- **Dashboards**: Pre-configured trading metrics
- **Data Source**: Prometheus

## 🔒 Security Features

- **Non-root containers**: All services run as non-root users
- **Network isolation**: Internal Docker network
- **Resource limits**: Memory and CPU constraints
- **Health checks**: Automatic service recovery
- **SSL/TLS**: Let's Encrypt integration
- **Rate limiting**: API and WebSocket protection

## 📊 Monitoring & Alerts

### Health Monitoring
- Service health checks every 30 seconds
- Automatic restart on failure
- Resource usage monitoring
- Custom trading metrics

### Alert Channels
- Email notifications
- Webhook integrations
- Real-time WebSocket updates
- System status dashboard

### Key Metrics
- Signal generation rate
- Processing latency
- Memory usage
- Database performance
- WebSocket connections

## 🔄 Maintenance Operations

### Updating the Application

```bash
# Update with zero downtime
./deploy/digitalocean_deploy.sh update
```

### Database Backup

```bash
# Manual backup
ssh root@$DROPLET_IP
docker exec trading-backup /usr/local/bin/backup.sh

# Automated backups run daily at 2 AM UTC
```

### Scaling Resources

```bash
# Resize droplet
doctl compute droplet-action resize trading-screener --size s-4vcpu-8gb

# Update resource limits in docker-compose.prod.yml
# Redeploy with updated configuration
```

### Log Management

```bash
# View service logs
ssh root@$DROPLET_IP
docker-compose -f docker-compose.prod.yml logs -f trading-screener

# Log rotation is handled automatically
# Logs are limited to 100MB per service with 3 file rotation
```

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View detailed logs
docker-compose -f docker-compose.prod.yml logs trading-screener

# Check resource usage
docker stats
```

#### Database Connection Issues
```bash
# Check Redis connection
docker exec trading-redis redis-cli ping

# Verify Redis password
docker exec trading-redis redis-cli -a $REDIS_PASSWORD ping
```

#### Frontend Not Loading
```bash
# Check frontend service
docker-compose -f docker-compose.prod.yml logs frontend

# Verify Nginx configuration
docker exec trading-nginx nginx -t

# Check upstream connections
curl -I http://localhost:3000
```

### Performance Tuning

#### Optimize for High Frequency Trading
```bash
# Increase Redis memory
# Edit docker-compose.prod.yml:
redis:
  deploy:
    resources:
      limits:
        memory: 1G

# Tune Nginx worker processes
# Edit nginx.conf:
worker_processes auto;
worker_connections 2048;
```

#### Scale Database Performance
```bash
# Enable Redis clustering (for high load)
# Increase DuckDB buffer sizes
# Consider read replicas for analytics
```

## 📈 Monitoring Dashboard

Access your monitoring dashboard at:
- **Grafana**: `http://your-droplet-ip:3001`
- **Prometheus**: `http://your-droplet-ip:9090`
- **Application**: `http://your-droplet-ip`

### Default Grafana Dashboards
1. **Trading Overview**: Signal counts, win rates, P&L
2. **System Metrics**: CPU, memory, disk usage
3. **Application Performance**: API response times, errors
4. **Real-time Data**: WebSocket connections, data throughput

## 🔐 SSL Certificate Setup

### Automatic SSL with Let's Encrypt

```bash
# Set domain name in environment
export DOMAIN_NAME=yourdomain.com

# Deploy with SSL
./deploy/digitalocean_deploy.sh deploy

# Certificate auto-renewal is configured via cron
```

### Manual SSL Setup

```bash
# Generate certificate manually
ssh root@$DROPLET_IP
certbot --nginx -d yourdomain.com

# Update Nginx configuration
# Uncomment HTTPS server block in nginx.conf
```

## 💾 Backup & Recovery

### Automated Backups
- **Daily**: Full database backup at 2 AM UTC
- **Weekly**: Archive backup every Monday
- **Retention**: 7 days for daily, 4 weeks for weekly

### Manual Recovery
```bash
# List available backups
ssh root@$DROPLET_IP
ls -la /root/backups/daily/

# Restore from backup
docker stop trading-screener
cp /root/backups/daily/backup_YYYYMMDD_HHMMSS.duckdb /root/data/trading_data.duckdb
docker start trading-screener
```

## 🚀 Advanced Configuration

### Custom Indicators
Add custom technical indicators by extending the `TechnicalIndicatorEngine` class in `core/ta_engine/indicators.py`.

### Custom Alert Channels
Implement additional notification channels by extending the `AlertManager` class in `core/alerts/alert_manager.py`.

### Strategy Optimization
Configure strategy parameters in `config/streaming_config.json` for your specific trading requirements.

## 📞 Support

For deployment issues or questions:
1. Check the troubleshooting section above
2. Review service logs for error details
3. Verify all environment variables are set correctly
4. Ensure API credentials are valid and have proper permissions

## 🔄 Updates & Maintenance

The system includes Watchtower for automatic updates. To disable:
```bash
# Comment out watchtower service in docker-compose.prod.yml
# Redeploy the stack
```

For manual updates, use the update command:
```bash
./deploy/digitalocean_deploy.sh update
```

---

**🎯 Your production trading screener is now ready to detect profitable opportunities and send real-time alerts!**