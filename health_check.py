#!/usr/bin/env python3
"""
Health check script for production deployment
"""

import sys
import os
import requests
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def check_database():
    """Check if database is accessible"""
    try:
        from core.data_engine.duckdb_handler import DuckDBHandler
        db = DuckDBHandler("data/trading_data.duckdb")
        db.close()
        return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False

def check_api_connection():
    """Check if Alpaca API is accessible"""
    try:
        from alpaca_fetcher_new import get_latest_quotes
        quotes = get_latest_quotes(["AAPL"])
        return len(quotes) > 0
    except Exception as e:
        print(f"API check failed: {e}")
        return False

def check_disk_space():
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (1024**3)
        return free_gb > 1  # At least 1GB free
    except Exception as e:
        print(f"Disk space check failed: {e}")
        return False

def main():
    """Run all health checks"""
    checks = [
        ("Database", check_database),
        ("API Connection", check_api_connection),
        ("Disk Space", check_disk_space)
    ]
    
    all_passed = True
    for name, check_func in checks:
        if check_func():
            print(f"[OK] {name} check passed")
        else:
            print(f"[ERROR] {name} check failed")
            all_passed = False
    
    if all_passed:
        print("All health checks passed")
        sys.exit(0)
    else:
        print("Some health checks failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
