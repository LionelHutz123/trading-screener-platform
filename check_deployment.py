#!/usr/bin/env python3
"""
Simple deployment checker for HutzTrades
"""

import requests
import time
import json

def check_deployment():
    """Check if the streaming deployment is working"""
    app_url = "https://trading-screener-lerd2.ondigitalocean.app"
    
    print("🔍 Checking HutzTrades Deployment Status...")
    print(f"🌐 URL: {app_url}")
    
    endpoints_to_test = [
        ("/", "Dashboard"),
        ("/health", "Health Check"),
        ("/api/status", "API Status"),
        ("/api/stream/status", "Stream Status"),
        ("/docs", "API Documentation")
    ]
    
    results = {}
    
    for endpoint, name in endpoints_to_test:
        url = f"{app_url}{endpoint}"
        try:
            response = requests.get(url, timeout=10)
            status = response.status_code
            content = response.text[:100] + "..." if len(response.text) > 100 else response.text
            
            results[name] = {
                "status": status,
                "content": content,
                "success": status == 200
            }
            
            print(f"{'✅' if status == 200 else '❌'} {name}: {status}")
            if status != 200:
                print(f"   Content: {content}")
            
        except requests.exceptions.RequestException as e:
            results[name] = {
                "status": "error",
                "content": str(e),
                "success": False
            }
            print(f"❌ {name}: Connection failed - {str(e)}")
    
    # Check if it's the full API or simple response
    health_content = results.get("Health Check", {}).get("content", "")
    if "Hello! you requested" in health_content:
        print("\n⚠️  Deployment Status: SIMPLE RESPONSE MODE")
        print("   The deployment is running but showing simple responses.")
        print("   This might mean:")
        print("   - Deployment is still in progress")
        print("   - Build failed and reverted to simple version")
        print("   - Environment variables not set correctly")
    elif "status" in health_content.lower():
        print("\n✅ Deployment Status: FULL API ACTIVE")
        print("   The complete streaming API is deployed and running!")
    else:
        print("\n❓ Deployment Status: UNKNOWN")
        print("   Unable to determine deployment status")
    
    return results

def wait_for_deployment():
    """Wait for deployment to complete"""
    print("\n⏳ Waiting for deployment to complete...")
    
    for attempt in range(10):  # 10 attempts, 30 seconds each = 5 minutes
        print(f"   Attempt {attempt + 1}/10...")
        
        try:
            response = requests.get("https://trading-screener-lerd2.ondigitalocean.app/health", timeout=10)
            if "status" in response.text.lower() and "Hello!" not in response.text:
                print("✅ Full API is now active!")
                return True
        except:
            pass
        
        time.sleep(30)
    
    print("⏱️  Timeout waiting for deployment")
    return False

if __name__ == "__main__":
    results = check_deployment()
    
    # If simple responses, wait for full deployment
    health_result = results.get("Health Check", {})
    if health_result.get("success") and "Hello!" in health_result.get("content", ""):
        if wait_for_deployment():
            print("\n🎉 Deployment completed successfully!")
            check_deployment()  # Check again
        else:
            print("\n💡 Manual check recommended:")
            print("   Visit: https://cloud.digitalocean.com/apps")
            print("   Check your app deployment logs")
    
    print("\n🚀 HutzTrades deployment check complete!")