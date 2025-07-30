# Production Deployment Guide

## Prerequisites

1. **Python 3.11+** installed
2. **Docker** (optional, for containerized deployment)
3. **Systemd** (for service management)
4. **Alpaca API Keys** (paper trading recommended for testing)

## Quick Start

### 1. Environment Setup

```bash
# Run the production setup script
python production_setup.py

# Edit the environment file with your API keys
nano .env.production
```

### 2. Docker Deployment (Recommended)

```bash
# Build and start the application
docker-compose up -d

# Check logs
docker-compose logs -f trading-screener

# Stop the application
docker-compose down
```

### 3. Systemd Service Deployment

```bash
# Copy service file to systemd directory
sudo cp trading-screener.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable trading-screener
sudo systemctl start trading-screener

# Check status
sudo systemctl status trading-screener
```

## Configuration

### Environment Variables

Edit `.env.production` with your settings:

- `ALPACA_API_KEY`: Your Alpaca API key
- `ALPACA_SECRET_KEY`: Your Alpaca secret key
- `DATABASE_PATH`: Path to database file
- `MAX_WORKERS`: Number of parallel workers
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

### Production Configuration

Edit `config/production.json` for advanced settings:

- Database configuration
- Risk management parameters
- Monitoring thresholds
- Security settings

## Monitoring

### Health Checks

```bash
# Manual health check
python health_check.py

# Continuous monitoring
python monitoring.py
```

### Logs

```bash
# View application logs
tail -f logs/production.log

# View backtest logs
tail -f logs/backtests/

# View screening logs
tail -f logs/screening/
```

## Backup and Maintenance

### Automated Backups

```bash
# Manual backup
python backup.py

# Setup cron job for daily backups
crontab -e
# Add: 0 2 * * * cd /path/to/app && python backup.py
```

### Database Maintenance

```bash
# Check database size
ls -lh data/trading_data.duckdb

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete
```

## Security Considerations

1. **API Keys**: Store securely, never commit to version control
2. **File Permissions**: Restrict access to configuration files
3. **Network Security**: Use firewalls and VPN if needed
4. **Updates**: Regularly update dependencies and security patches

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify API keys in `.env.production`
   - Check network connectivity
   - Verify Alpaca service status

2. **Database Errors**
   - Check disk space
   - Verify file permissions
   - Restore from backup if needed

3. **Performance Issues**
   - Monitor system resources
   - Adjust `MAX_WORKERS` setting
   - Check for memory leaks

### Log Analysis

```bash
# Search for errors
grep -i error logs/production.log

# Check recent activity
tail -100 logs/production.log

# Monitor real-time
tail -f logs/production.log | grep -E "(ERROR|WARNING)"
```

## Scaling

### Horizontal Scaling

1. **Load Balancing**: Use multiple instances behind a load balancer
2. **Database Sharding**: Split data across multiple database files
3. **Microservices**: Separate screening, backtesting, and streaming services

### Vertical Scaling

1. **Increase Workers**: Adjust `MAX_WORKERS` based on CPU cores
2. **Memory Optimization**: Monitor memory usage and optimize data structures
3. **Storage**: Use SSD storage for better database performance

## Support

For issues and questions:

1. Check the logs first
2. Review this documentation
3. Check the GitHub repository for updates
4. Create an issue with detailed error information

## Updates

To update the application:

```bash
# Stop the service
sudo systemctl stop trading-screener

# Backup current version
cp -r /opt/trading-screener /opt/trading-screener.backup

# Update code
git pull origin main

# Restart the service
sudo systemctl start trading-screener
```
