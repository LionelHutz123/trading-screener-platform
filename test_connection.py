#!/usr/bin/env python3
"""
Test script to verify localhost connection is working
"""

import requests
import time
import sys

def test_connection():
    """Test connection to localhost server"""
    print("🔍 Testing localhost connection...")
    
    # Wait a moment for server to be ready
    time.sleep(2)
    
    try:
        # Test basic connection
        response = requests.get("http://localhost:8080/", timeout=10)
        print(f"✅ Root endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test health endpoint
        response = requests.get("http://localhost:8080/health", timeout=10)
        print(f"✅ Health endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test API docs
        response = requests.get("http://localhost:8080/docs", timeout=10)
        print(f"✅ Docs endpoint: {response.status_code}")
        
        print("🎉 All connections successful!")
        print("🌐 Your server is accessible at: http://localhost:8080")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused - server may not be running")
        return False
    except requests.exceptions.Timeout:
        print("❌ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)