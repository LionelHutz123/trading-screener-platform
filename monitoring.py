#!/usr/bin/env python3
"""
Production monitoring script
"""

import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import requests

class ProductionMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_file = Path("logs/metrics.json")
        self.alert_thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90,
            "error_rate": 0.1
        }
    
    def collect_system_metrics(self):
        """Collect system performance metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "network_io": psutil.net_io_counters()._asdict()
        }
    
    def check_application_health(self):
        """Check application health"""
        try:
            # Check if main process is running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'python' in proc.info['name'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def check_database_size(self):
        """Check database file size"""
        try:
            db_file = Path("data/trading_data.duckdb")
            if db_file.exists():
                return db_file.stat().st_size
            return 0
        except Exception as e:
            self.logger.error(f"Database size check failed: {e}")
            return 0
    
    def save_metrics(self, metrics):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")
    
    def check_alerts(self, metrics):
        """Check for alert conditions"""
        alerts = []
        
        if metrics['cpu_percent'] > self.alert_thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {metrics['cpu_percent']}%")
        
        if metrics['memory_percent'] > self.alert_thresholds['memory_percent']:
            alerts.append(f"High memory usage: {metrics['memory_percent']}%")
        
        if metrics['disk_percent'] > self.alert_thresholds['disk_percent']:
            alerts.append(f"High disk usage: {metrics['disk_percent']}%")
        
        if alerts:
            self.logger.warning(f"ALERTS triggered: {alerts}")
        
        return alerts
    
    def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        metrics = self.collect_system_metrics()
        metrics['app_healthy'] = self.check_application_health()
        metrics['db_size_bytes'] = self.check_database_size()
        
        self.save_metrics(metrics)
        self.check_alerts(metrics)
        
        return metrics

def main():
    """Main monitoring loop"""
    monitor = ProductionMonitor()
    
    print("Starting production monitoring...")
    
    while True:
        try:
            metrics = monitor.run_monitoring_cycle()
            print(f"Monitoring cycle completed: {metrics['timestamp']}")
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
            break
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
