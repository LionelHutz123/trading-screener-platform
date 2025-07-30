#!/usr/bin/env python3
"""
Simple Hang Detector for Trading Screener
Quickly identifies hung processes and provides actionable information
"""

import psutil
import time
import subprocess
import sys
from datetime import datetime

def check_process_hang(process_name, timeout_seconds=300):
    """Check if a specific process is hung"""
    hung_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                # Get process details
                process = psutil.Process(proc.pid)
                cpu_percent = process.cpu_percent(interval=1)
                memory_percent = process.memory_percent()
                
                # Check for hang indicators
                hang_indicators = []
                
                # High CPU usage
                if cpu_percent > 90:
                    hang_indicators.append(f"High CPU: {cpu_percent:.1f}%")
                
                # High memory usage
                if memory_percent > 85:
                    hang_indicators.append(f"High Memory: {memory_percent:.1f}%")
                
                # Process not responding
                if not process.is_running():
                    hang_indicators.append("Not responding")
                
                # Process in uninterruptible sleep
                if process.status() == psutil.STATUS_DISK_SLEEP:
                    hang_indicators.append("Uninterruptible sleep")
                
                if hang_indicators:
                    hung_processes.append({
                        'pid': proc.pid,
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']),
                        'indicators': hang_indicators,
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent
                    })
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return hung_processes

def check_docker_containers():
    """Check Docker containers for issues"""
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            problematic_containers = []
            
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        container_name = parts[0]
                        status = parts[1]
                        
                        # Check for problematic status
                        if any(indicator in status.lower() for indicator in ['restarting', 'exited', 'dead', 'unhealthy']):
                            problematic_containers.append({
                                'name': container_name,
                                'status': status
                            })
            
            return problematic_containers
    except Exception as e:
        print(f"Error checking Docker containers: {e}")
    
    return []

def check_remote_server():
    """Check remote server for hung processes"""
    try:
        # Check if we can connect to the remote server with passphrase
        ssh_cmd = f'echo "mcoveney@gmail.com" | ssh -o StrictHostKeyChecking=no root@159.203.131.140 "echo Connection test"'
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Check Docker containers on remote server with passphrase
            ssh_cmd = f'echo "mcoveney@gmail.com" | ssh -o StrictHostKeyChecking=no root@159.203.131.140 "docker ps --format \\"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\\""'
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                remote_issues = []
                
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            container_name = parts[0]
                            status = parts[1]
                            
                            if any(indicator in status.lower() for indicator in ['restarting', 'exited', 'dead']):
                                remote_issues.append({
                                    'type': 'docker_container',
                                    'name': container_name,
                                    'status': status
                                })
                
                return remote_issues
    except Exception as e:
        print(f"Error checking remote server: {e}")
    
    return []

def main():
    print("🔍 HANG DETECTOR FOR TRADING SCREENER")
    print("=" * 50)
    print(f"Scan started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check local processes
    print("📊 Checking local processes...")
    processes_to_check = ['python', 'docker', 'trading-screener', 'grafana']
    
    local_hung = []
    for process_name in processes_to_check:
        hung = check_process_hang(process_name)
        local_hung.extend(hung)
    
    if local_hung:
        print("❌ Found hung local processes:")
        for proc in local_hung:
            print(f"  - {proc['name']} (PID: {proc['pid']})")
            print(f"    Indicators: {', '.join(proc['indicators'])}")
            print(f"    CPU: {proc['cpu_percent']:.1f}%, Memory: {proc['memory_percent']:.1f}%")
            print()
    else:
        print("✅ No hung local processes detected")
    
    # Check Docker containers
    print("🐳 Checking Docker containers...")
    docker_issues = check_docker_containers()
    
    if docker_issues:
        print("❌ Found problematic Docker containers:")
        for container in docker_issues:
            print(f"  - {container['name']}: {container['status']}")
        print()
    else:
        print("✅ No problematic Docker containers detected")
    
    # Check remote server
    print("🌐 Checking remote server...")
    remote_issues = check_remote_server()
    
    if remote_issues:
        print("❌ Found issues on remote server:")
        for issue in remote_issues:
            print(f"  - {issue['name']}: {issue['status']}")
        print()
    else:
        print("✅ No issues detected on remote server")
    
    # Summary
    total_issues = len(local_hung) + len(docker_issues) + len(remote_issues)
    print("=" * 50)
    print(f"📋 SUMMARY: {total_issues} issues found")
    print("=" * 50)
    
    if total_issues > 0:
        print("\n🔧 RECOMMENDED ACTIONS:")
        if local_hung:
            print("1. Restart hung local processes:")
            for proc in local_hung:
                print(f"   kill -9 {proc['pid']}  # Force kill if needed")
        
        if docker_issues:
            print("2. Restart problematic Docker containers:")
            for container in docker_issues:
                print(f"   docker restart {container['name']}")
        
        if remote_issues:
            print("3. Check remote server:")
            print("   ssh root@159.203.131.140")
            print("   docker-compose restart")
    else:
        print("✅ All systems appear to be running normally!")
    
    print(f"\nScan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 