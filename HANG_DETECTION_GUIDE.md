# Hang Detection System for Trading Screener

## Overview

This system provides comprehensive monitoring and hang detection for your trading screener deployment. It can identify hung processes both locally and on your remote DigitalOcean droplet.

## Quick Start

### 1. Quick Hang Detection (One-time check)

**Python version:**
```bash
python hang_detector.py
```

**PowerShell version:**
```powershell
.\quick_hang_detector.ps1
```

### 2. Continuous Monitoring

**Python version:**
```bash
python process_monitor.py
```

**PowerShell version:**
```powershell
.\process_monitor.ps1
```

### 3. Generate Report Only

**Python version:**
```bash
python process_monitor.py --report
```

## What Gets Monitored

### Local Processes
- Python processes (trading screener, backtesting, etc.)
- Docker processes
- High CPU usage (>90%)
- High memory usage (>85%)
- Non-responding processes
- Processes stuck in uninterruptible sleep

### Docker Containers
- Container status (restarting, exited, dead, unhealthy)
- Resource usage
- Health checks

### Remote Server (DigitalOcean Droplet)
- Docker containers on remote server
- System processes
- SSH connectivity

### System Resources
- CPU usage
- Memory usage
- Disk usage

## Configuration

Edit `monitor_config.json` to customize:

```json
{
  "check_interval": 30,           // Check every 30 seconds
  "hung_threshold": 300,          // Consider process hung after 5 minutes
  "cpu_threshold": 90,            // High CPU threshold
  "memory_threshold": 85,         // High memory threshold
  "processes_to_monitor": [       // Processes to watch
    "python",
    "docker",
    "trading-screener"
  ]
}
```

## Hang Indicators

A process is considered "hung" if it exhibits any of these behaviors:

1. **High CPU Usage**: Consistently using >90% CPU
2. **High Memory Usage**: Using >85% of available memory
3. **Non-Responding**: Process not responding to system calls
4. **Uninterruptible Sleep**: Process stuck in D state (waiting for I/O)
5. **No Activity**: No CPU or I/O activity for extended period
6. **Container Issues**: Docker containers in restarting/exited/dead state

## Common Issues and Solutions

### Issue: Python process using 100% CPU
**Solution:**
```bash
# Find the process
ps aux | grep python

# Kill if necessary
kill -9 <PID>

# Restart the trading screener
docker-compose restart trading-screener
```

### Issue: Docker container stuck in restarting state
**Solution:**
```bash
# Check container logs
docker logs <container_name>

# Restart container
docker restart <container_name>

# If that doesn't work, remove and recreate
docker-compose down
docker-compose up -d
```

### Issue: Remote server not responding
**Solution:**
```bash
# Check SSH connection
ssh root@159.203.131.140

# Check Docker services
cd /opt/trading-screener
docker-compose ps

# Restart services
docker-compose restart
```

## Monitoring Commands

### Check Current Status
```bash
# Local processes
python hang_detector.py

# Remote server
ssh root@159.203.131.140 "docker ps"
ssh root@159.203.131.140 "docker-compose ps"
```

### Continuous Monitoring
```bash
# Start monitoring
python process_monitor.py

# Check logs
tail -f process_monitor.log
```

### System Health Check
```bash
# Check system resources
top
htop
df -h
free -h

# Check Docker
docker stats
docker system df
```

## Alert System

The monitoring system can be configured to send alerts when:

- More than 3 processes are hung
- System resources exceed thresholds
- Docker containers become unhealthy
- Remote server becomes unreachable

## Log Files

- `process_monitor.log`: Main monitoring log
- `process_monitor_report.json`: Latest monitoring report
- `monitor_config.json`: Configuration file

## Troubleshooting

### Monitor Not Starting
1. Check Python dependencies: `pip install psutil`
2. Check file permissions
3. Verify SSH key setup for remote monitoring

### False Positives
1. Adjust thresholds in `monitor_config.json`
2. Add processes to exclude list
3. Increase check intervals

### Remote Monitoring Issues
1. Verify SSH key authentication
2. Check network connectivity
3. Ensure Docker is running on remote server

## Integration with Trading Screener

The hang detection system works alongside your trading screener to ensure:

1. **Data Fetching**: Monitors Alpaca API connection processes
2. **Backtesting**: Watches backtesting processes for hangs
3. **Real-time Streaming**: Monitors streaming processes
4. **Web Interface**: Ensures web server stays responsive
5. **Database Operations**: Monitors database connection processes

## Best Practices

1. **Regular Monitoring**: Run continuous monitoring in production
2. **Log Rotation**: Configure log rotation to prevent disk space issues
3. **Alert Thresholds**: Set appropriate thresholds for your system
4. **Backup Monitoring**: Monitor backup processes
5. **Resource Limits**: Set Docker resource limits to prevent hangs

## Emergency Procedures

If critical processes are hung:

1. **Immediate Action**: Kill hung processes
2. **Service Restart**: Restart affected services
3. **Data Recovery**: Check for data corruption
4. **System Reboot**: As last resort, reboot the system
5. **Post-Mortem**: Analyze logs to prevent future hangs

## Support

For issues with the hang detection system:

1. Check the logs: `tail -f process_monitor.log`
2. Verify configuration: `cat monitor_config.json`
3. Test connectivity: `ssh root@159.203.131.140`
4. Check system resources: `htop` or `top`

The hang detection system is designed to be lightweight and non-intrusive while providing comprehensive monitoring of your trading screener deployment. 