#!/usr/bin/env python3
"""
Deployment Status Checker for Trading Screener
Checks the current status of Docker services and deployment on DigitalOcean droplet
"""

import subprocess
import sys
import json
import os
from datetime import datetime

# SSH Configuration
SSH_SERVER = "root@159.203.131.140"
SSH_PASSPHRASE = "mcoveney@gmail.com"

def run_ssh_command(command, server=SSH_SERVER):
    """Run a command on the remote server via SSH with passphrase handling"""
    try:
        # Use expect-style approach with echo to provide passphrase
        ssh_cmd = f'echo "{SSH_PASSPHRASE}" | ssh -o StrictHostKeyChecking=no {server} "{command}"'
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "SSH command timed out"
    except Exception as e:
        return False, "", str(e)

def run_ssh_command_alternative(command, server=SSH_SERVER):
    """Alternative method using sshpass if available"""
    try:
        # Try using sshpass if available
        ssh_cmd = f'sshpass -p "{SSH_PASSPHRASE}" ssh -o StrictHostKeyChecking=no {server} "{command}"'
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except:
        # Fallback to manual SSH
        return run_ssh_command(command, server)

def check_docker_status():
    """Check Docker services status"""
    print("🔍 Checking Docker services status...")
    
    # Check if docker-compose is running
    success, output, error = run_ssh_command("cd /opt/trading-screener && docker-compose ps")
    if success:
        print("✅ Docker services status:")
        print(output)
    else:
        print("❌ Failed to check Docker services:")
        print(error)
        return False
    
    # Check if containers are running
    success, output, error = run_ssh_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    if success:
        print("\n📊 Running containers:")
        print(output)
    else:
        print("❌ Failed to check running containers")
    
    return True

def check_health_endpoints():
    """Check if health endpoints are responding"""
    print("\n🏥 Checking health endpoints...")
    
    # Check trading screener health
    success, output, error = run_ssh_command("curl -f http://localhost:8080/health 2>/dev/null || echo 'Health check failed'")
    if success and "Health check failed" not in output:
        print("✅ Trading screener health endpoint: OK")
    else:
        print("❌ Trading screener health endpoint: FAILED")
    
    # Check Grafana
    success, output, error = run_ssh_command("curl -f http://localhost:3000 2>/dev/null || echo 'Grafana check failed'")
    if success and "Grafana check failed" not in output:
        print("✅ Grafana monitoring: OK")
    else:
        print("❌ Grafana monitoring: FAILED")

def check_file_structure():
    """Check if all necessary files are present"""
    print("\n📁 Checking file structure...")
    
    files_to_check = [
        "/opt/trading-screener/docker-compose.yml",
        "/opt/trading-screener/Dockerfile",
        "/opt/trading-screener/.env.production",
        "/opt/trading-screener/main.py",
        "/opt/trading-screener/core/__init__.py",
        "/opt/trading-screener/core/ta_engine/__init__.py",
        "/opt/trading-screener/core/data_engine/__init__.py",
        "/opt/trading-screener/core/backtesting/__init__.py",
        "/opt/trading-screener/core/multiprocessing/__init__.py"
    ]
    
    for file_path in files_to_check:
        success, output, error = run_ssh_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'")
        if success and "EXISTS" in output:
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")

def check_system_resources():
    """Check system resource usage"""
    print("\n💻 Checking system resources...")
    
    # Check disk usage
    success, output, error = run_ssh_command("df -h /opt/trading-screener")
    if success:
        print("📊 Disk usage:")
        print(output)
    
    # Check memory usage
    success, output, error = run_ssh_command("free -h")
    if success:
        print("🧠 Memory usage:")
        print(output)
    
    # Check Docker disk usage
    success, output, error = run_ssh_command("docker system df")
    if success:
        print("🐳 Docker disk usage:")
        print(output)

def check_logs():
    """Check recent logs for errors"""
    print("\n📋 Checking recent logs...")
    
    # Check trading screener logs
    success, output, error = run_ssh_command("docker-compose logs --tail=20 trading-screener")
    if success:
        print("📝 Recent trading screener logs:")
        print(output)
    
    # Check for errors in logs
    success, output, error = run_ssh_command("docker-compose logs trading-screener | grep -i error | tail -5")
    if success and output.strip():
        print("⚠️  Recent errors:")
        print(output)
    else:
        print("✅ No recent errors found")

def check_network_connectivity():
    """Check network connectivity and ports"""
    print("\n🌐 Checking network connectivity...")
    
    # Check if ports are listening
    success, output, error = run_ssh_command("netstat -tulpn | grep -E ':(8080|3000)'")
    if success:
        print("🔌 Active ports:")
        print(output)
    else:
        print("❌ No expected ports found")
    
    # Check firewall status
    success, output, error = run_ssh_command("ufw status")
    if success:
        print("🛡️  Firewall status:")
        print(output)

def generate_deployment_report():
    """Generate a comprehensive deployment report"""
    print("=" * 60)
    print("🚀 TRADING SCREENER DEPLOYMENT STATUS REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all checks
    docker_ok = check_docker_status()
    check_health_endpoints()
    check_file_structure()
    check_system_resources()
    check_logs()
    check_network_connectivity()
    
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    if docker_ok:
        print("✅ Docker services are running")
    else:
        print("❌ Docker services need attention")
    
    print("\n🔧 Next Steps:")
    print("1. If services are not running: docker-compose up -d")
    print("2. If health checks fail: check logs and restart services")
    print("3. If files are missing: re-upload missing files")
    print("4. If ports are not open: check firewall configuration")
    print("5. Monitor logs: docker-compose logs -f trading-screener")

if __name__ == "__main__":
    try:
        generate_deployment_report()
    except KeyboardInterrupt:
        print("\n❌ Status check interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during status check: {e}")
        sys.exit(1) 