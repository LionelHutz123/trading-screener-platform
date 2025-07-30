#!/usr/bin/env python3
"""
Deployment Status Check for Trading Screener
Checks if the deployment is complete and working
"""

import subprocess
import sys
from datetime import datetime

def run_ssh_command(command, description):
    """Run SSH command and provide clear instructions"""
    print(f"\n🔍 {description}")
    print(f"   Command: ssh root@159.203.131.140 '{command}'")
    print("   When prompted for passphrase, enter: mcoveney@gmail.com")
    print()
    
    try:
        result = subprocess.run(
            ['ssh', 'root@159.203.131.140', command],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print("   Output:")
                print(f"   {result.stdout.strip()}")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT")
        return False, "Command timed out"
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False, str(e)

def main():
    print("🚀 TRADING SCREENER DEPLOYMENT STATUS CHECK")
    print("=" * 55)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This script will check your deployment status.")
    print("You'll need to enter the SSH passphrase: mcoveney@gmail.com")
    print()
    
    # Test SSH connection
    success, output = run_ssh_command(
        "echo 'Connection test successful'",
        "Testing SSH connection"
    )
    
    if not success:
        print("\n❌ Cannot connect to remote server. Please check:")
        print("   1. SSH key is properly configured")
        print("   2. Server is accessible")
        print("   3. Passphrase is correct: mcoveney@gmail.com")
        return
    
    # Check trading screener directory
    success, output = run_ssh_command(
        "ls -la /opt/trading-screener/",
        "Checking trading screener directory"
    )
    
    if success:
        print("✅ Trading screener directory exists")
        if "docker-compose.yml" in output:
            print("✅ docker-compose.yml found")
        if "main.py" in output:
            print("✅ main.py found")
        if "core" in output:
            print("✅ core directory found")
    else:
        print("❌ Trading screener directory not found")
    
    # Check Docker
    success, output = run_ssh_command(
        "docker ps",
        "Checking Docker containers"
    )
    
    if success:
        print("✅ Docker is running")
        if "trading-screener" in output:
            print("✅ Trading screener container found")
        if "grafana" in output or "monitoring" in output:
            print("✅ Monitoring container found")
    else:
        print("❌ Docker not available or not running")
    
    # Check Docker Compose services
    success, output = run_ssh_command(
        "cd /opt/trading-screener && docker-compose ps",
        "Checking Docker Compose services"
    )
    
    if success:
        print("✅ Docker Compose services found")
        if "Up" in output:
            print("✅ Services are running")
        else:
            print("⚠️  Services may not be running properly")
    else:
        print("❌ Docker Compose services not found")
    
    # Check health endpoint
    success, output = run_ssh_command(
        "curl -f http://localhost:8080/health",
        "Checking trading screener health endpoint"
    )
    
    if success:
        print("✅ Trading screener health endpoint responding")
    else:
        print("❌ Trading screener health endpoint not responding")
    
    # Check Grafana
    success, output = run_ssh_command(
        "curl -f http://localhost:3000",
        "Checking Grafana monitoring"
    )
    
    if success:
        print("✅ Grafana monitoring responding")
    else:
        print("❌ Grafana monitoring not responding")
    
    # Summary
    print("\n" + "=" * 55)
    print("📋 DEPLOYMENT SUMMARY")
    print("=" * 55)
    
    print("\n🔧 NEXT STEPS:")
    print("1. If services are not running:")
    print("   ssh root@159.203.131.140")
    print("   cd /opt/trading-screener")
    print("   docker-compose up -d")
    print()
    print("2. If files are missing:")
    print("   Upload missing files using scp commands")
    print()
    print("3. Access your trading screener:")
    print("   http://159.203.131.140:8080")
    print("   http://159.203.131.140:3000 (Grafana)")
    print()
    print("4. Monitor with hang detection:")
    print("   python hang_detector.py")
    print("   python simple_hang_check.ps1")
    
    print(f"\nCheck completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 