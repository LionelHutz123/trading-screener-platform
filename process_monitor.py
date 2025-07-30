#!/usr/bin/env python3
"""
Process Monitor for Trading Screener
Detects hung processes and provides monitoring capabilities
"""

import subprocess
import time
import psutil
import signal
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class ProcessMonitor:
    def __init__(self, config_file: str = "monitor_config.json"):
        self.config_file = config_file
        self.hung_processes = []
        self.process_history = {}
        self.setup_logging()
        self.load_config()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('process_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self):
        """Load monitoring configuration"""
        self.config = {
            "check_interval": 30,  # seconds
            "hung_threshold": 300,  # seconds (5 minutes)
            "cpu_threshold": 90,    # percentage
            "memory_threshold": 85,  # percentage
            "processes_to_monitor": [
                "python",
                "docker",
                "trading-screener",
                "grafana",
                "main.py"
            ],
            "ssh_server": "root@159.203.131.140",
            "ssh_passphrase": "mcoveney@gmail.com"
        }
        
        try:
            with open(self.config_file, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except FileNotFoundError:
            self.logger.info(f"Config file {self.config_file} not found, using defaults")
            self.save_config()
    
    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_process_info(self, pid: int) -> Optional[Dict]:
        """Get detailed information about a process"""
        try:
            process = psutil.Process(pid)
            return {
                'pid': pid,
                'name': process.name(),
                'cmdline': ' '.join(process.cmdline()),
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_info': process.memory_info()._asdict(),
                'status': process.status(),
                'create_time': process.create_time(),
                'num_threads': process.num_threads(),
                'num_connections': len(process.connections()),
                'io_counters': process.io_counters()._asdict() if process.io_counters() else None
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
    
    def detect_hung_processes(self) -> List[Dict]:
        """Detect processes that appear to be hung"""
        hung_processes = []
        current_time = time.time()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                # Check if this is a process we want to monitor
                if not any(monitor_name in proc.info['name'].lower() 
                          for monitor_name in self.config['processes_to_monitor']):
                    continue
                
                # Get detailed process info
                proc_info = self.get_process_info(proc.pid)
                if not proc_info:
                    continue
                
                # Check for hung indicators
                hung_indicators = []
                
                # 1. High CPU usage for extended period
                if proc_info['cpu_percent'] > self.config['cpu_threshold']:
                    hung_indicators.append(f"High CPU: {proc_info['cpu_percent']:.1f}%")
                
                # 2. High memory usage
                if proc_info['memory_percent'] > self.config['memory_threshold']:
                    hung_indicators.append(f"High Memory: {proc_info['memory_percent']:.1f}%")
                
                # 3. Process stuck in same state
                if proc.pid in self.process_history:
                    last_check = self.process_history[proc.pid]
                    time_diff = current_time - last_check['timestamp']
                    
                    if time_diff > self.config['hung_threshold']:
                        # Check if process hasn't changed significantly
                        if (abs(proc_info['cpu_percent'] - last_check['cpu_percent']) < 1 and
                            abs(proc_info['memory_percent'] - last_check['memory_percent']) < 1):
                            hung_indicators.append(f"Stuck for {time_diff:.0f}s")
                
                # 4. Process in uninterruptible sleep (D state)
                if proc_info['status'] == psutil.STATUS_DISK_SLEEP:
                    hung_indicators.append("Uninterruptible sleep (D state)")
                
                # 5. No I/O activity
                if proc_info['io_counters']:
                    if proc.pid in self.process_history:
                        last_io = self.process_history[proc.pid].get('io_counters')
                        if last_io:
                            current_io = proc_info['io_counters']
                            if (current_io['read_bytes'] == last_io['read_bytes'] and
                                current_io['write_bytes'] == last_io['write_bytes']):
                                hung_indicators.append("No I/O activity")
                
                # Update process history
                self.process_history[proc.pid] = {
                    'timestamp': current_time,
                    'cpu_percent': proc_info['cpu_percent'],
                    'memory_percent': proc_info['memory_percent'],
                    'io_counters': proc_info['io_counters']
                }
                
                # If process shows hung indicators, add to list
                if hung_indicators:
                    hung_process = {
                        'pid': proc.pid,
                        'name': proc_info['name'],
                        'cmdline': proc_info['cmdline'],
                        'indicators': hung_indicators,
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent'],
                        'status': proc_info['status'],
                        'detected_at': datetime.now().isoformat()
                    }
                    hung_processes.append(hung_process)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return hung_processes
    
    def check_remote_processes(self) -> List[Dict]:
        """Check processes on remote server via SSH"""
        remote_hung = []
        
        try:
            # Check Docker containers
            cmd = f"ssh {self.config['ssh_server']} 'docker ps --format \"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\"'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            container_name = parts[0]
                            status = parts[1]
                            
                            # Check for hung indicators in container status
                            if any(indicator in status.lower() for indicator in ['restarting', 'exited', 'dead']):
                                remote_hung.append({
                                    'type': 'docker_container',
                                    'name': container_name,
                                    'status': status,
                                    'detected_at': datetime.now().isoformat()
                                })
            
            # Check system processes
            cmd = f"ssh {self.config['ssh_server']} 'ps aux | grep -E \"(python|docker|trading)\" | grep -v grep'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            cpu_percent = float(parts[2])
                            if cpu_percent > self.config['cpu_threshold']:
                                remote_hung.append({
                                    'type': 'system_process',
                                    'pid': parts[1],
                                    'cpu_percent': cpu_percent,
                                    'command': ' '.join(parts[10:]),
                                    'detected_at': datetime.now().isoformat()
                                })
                                
        except subprocess.TimeoutExpired:
            self.logger.warning("SSH command timed out")
        except Exception as e:
            self.logger.error(f"Error checking remote processes: {e}")
        
        return remote_hung
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive monitoring report"""
        local_hung = self.detect_hung_processes()
        remote_hung = self.check_remote_processes()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'local_hung_processes': local_hung,
            'remote_hung_processes': remote_hung,
            'total_hung_processes': len(local_hung) + len(remote_hung),
            'system_info': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        }
        
        return report
    
    def log_report(self, report: Dict):
        """Log the monitoring report"""
        if report['total_hung_processes'] > 0:
            self.logger.warning(f"Found {report['total_hung_processes']} hung processes!")
            
            for proc in report['local_hung_processes']:
                self.logger.warning(f"Local hung process: {proc['name']} (PID: {proc['pid']}) - {proc['indicators']}")
            
            for proc in report['remote_hung_processes']:
                self.logger.warning(f"Remote hung process: {proc}")
        else:
            self.logger.info("No hung processes detected")
        
        # Log system info
        sys_info = report['system_info']
        self.logger.info(f"System: CPU {sys_info['cpu_percent']:.1f}%, "
                        f"Memory {sys_info['memory_percent']:.1f}%, "
                        f"Disk {sys_info['disk_percent']:.1f}%")
    
    def run_monitoring_loop(self):
        """Run the monitoring loop"""
        self.logger.info("Starting process monitor...")
        
        try:
            while True:
                report = self.generate_report()
                self.log_report(report)
                
                # Save report to file
                with open('process_monitor_report.json', 'w') as f:
                    json.dump(report, f, indent=2)
                
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            self.logger.info("Process monitor stopped by user")
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")

def main():
    """Main function"""
    monitor = ProcessMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--report':
        # Generate one-time report
        report = monitor.generate_report()
        print(json.dumps(report, indent=2))
    else:
        # Run continuous monitoring
        monitor.run_monitoring_loop()

if __name__ == "__main__":
    main() 