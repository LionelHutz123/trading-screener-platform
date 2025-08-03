#!/usr/bin/env python3
"""
Health check script for production deployment
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def check_database():
    """Check if database files exist and are accessible"""
    try:
        db_path = Path("data/trading_data.duckdb")
        if db_path.exists():
            # Try to get file size
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"Database file size: {size_mb:.2f} MB")
            return True
        else:
            print("Database file not found")
            return False
    except Exception as e:
        print(f"Database check failed: {e}")
        return False

def check_environment():
    """Check environment variables"""
    try:
        required_vars = ['ENV', 'PORT']
        optional_vars = ['ALPACA_API_KEY', 'DATABASE_URL', 'REDIS_URL']
        
        missing_required = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_required.append(var)
        
        if missing_required:
            print(f"Missing required environment variables: {missing_required}")
            return False
        
        print(f"Environment: {os.environ.get('ENV', 'unknown')}")
        print(f"Port: {os.environ.get('PORT', '8080')}")
        
        return True
    except Exception as e:
        print(f"Environment check failed: {e}")
        return False

def check_disk_space():
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        
        print(f"Disk space - Total: {total_gb:.2f}GB, Used: {used_gb:.2f}GB, Free: {free_gb:.2f}GB")
        
        return free_gb > 0.5  # At least 500MB free
    except Exception as e:
        print(f"Disk space check failed: {e}")
        return False

def check_file_structure():
    """Check if required files exist"""
    try:
        required_files = [
            'app_platform_api.py',
            'requirements.txt',
            'Dockerfile'
        ]
        
        required_dirs = [
            'data',
            'logs', 
            'core'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_files or missing_dirs:
            if missing_files:
                print(f"Missing files: {missing_files}")
            if missing_dirs:
                print(f"Missing directories: {missing_dirs}")
            return False
        
        print("All required files and directories present")
        return True
        
    except Exception as e:
        print(f"File structure check failed: {e}")
        return False

def generate_health_response():
    """Generate health response for API"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "environment": os.environ.get("ENV", "development"),
            "uptime": time.time(),
            "checks": {}
        }
        
        # Run all checks
        checks = [
            ("database", check_database),
            ("environment", check_environment),
            ("disk_space", check_disk_space),
            ("file_structure", check_file_structure)
        ]
        
        all_passed = True
        for name, check_func in checks:
            try:
                result = check_func()
                health_data["checks"][name] = {"status": "pass" if result else "fail"}
                if not result:
                    all_passed = False
            except Exception as e:
                health_data["checks"][name] = {"status": "error", "error": str(e)}
                all_passed = False
        
        if not all_passed:
            health_data["status"] = "unhealthy"
        
        return health_data
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

def main():
    """Run all health checks"""
    print("HutzTrades Health Check")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: {os.environ.get('ENV', 'development')}")
    print()
    
    checks = [
        ("Database", check_database),
        ("Environment", check_environment),
        ("Disk Space", check_disk_space),
        ("File Structure", check_file_structure)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"Checking {name}...")
        try:
            if check_func():
                print(f"[OK] {name} check passed")
            else:
                print(f"[ERROR] {name} check failed")
                all_passed = False
        except Exception as e:
            print(f"[ERROR] {name} check failed with exception: {e}")
            all_passed = False
        print()
    
    print("=" * 40)
    if all_passed:
        print("[SUCCESS] All health checks passed")
        
        # Save health status
        health_data = generate_health_response()
        health_file = Path("logs/health_status.json")
        health_file.parent.mkdir(exist_ok=True)
        
        with open(health_file, 'w') as f:
            json.dump(health_data, f, indent=2)
        
        print(f"Health status saved to {health_file}")
        sys.exit(0)
    else:
        print("[FAIL] Some health checks failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
