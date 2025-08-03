#!/usr/bin/env python3
"""
Simple deployment monitor for HutzTrades
"""

import requests
import time
from datetime import datetime

def check_deployment():
    """Check if deployment is ready"""
    try:
        response = requests.get("https://trading-screener-lerd2.ondigitalocean.app/health", timeout=10)
        
        # Check if it's full API (not simple response)
        if "Hello! you requested" in response.text:
            return False, "Building..."
        elif response.status_code == 200:
            try:
                data = response.json()
                if "status" in data:
                    return True, "Ready!"
            except:
                pass
        return False, f"Status: {response.status_code}"
    except Exception as e:
        return False, "Connecting..."

def test_endpoints():
    """Test key endpoints"""
    base_url = "https://trading-screener-lerd2.ondigitalocean.app"
    endpoints = ["/health", "/api/status", "/api/stream/status"]
    
    working = 0
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200 and "Hello!" not in response.text:
                working += 1
        except:
            pass
    
    return working, len(endpoints)

def main():
    print("Monitoring HutzTrades Deployment...")
    print("URL: https://trading-screener-lerd2.ondigitalocean.app")
    print("Started:", datetime.now().strftime("%H:%M:%S"))
    print("-" * 50)
    
    for attempt in range(20):  # 20 minutes max
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"[{current_time}] Check {attempt + 1}/20...", end=" ")
        
        is_ready, status = check_deployment()
        print(status)
        
        if is_ready:
            print("\n*** DEPLOYMENT COMPLETE! ***")
            
            # Test endpoints
            working, total = test_endpoints()
            print(f"Endpoints working: {working}/{total}")
            
            if working >= 2:
                print("\nYour HutzTrades platform is LIVE!")
                print("Features available:")
                print("- Real-time data streaming")
                print("- Pattern recognition")
                print("- Live trading signals")
                print("- WebSocket connections")
                
                print("\nAccess your platform:")
                print("Dashboard: https://trading-screener-lerd2.ondigitalocean.app")
                print("API Docs: https://trading-screener-lerd2.ondigitalocean.app/docs")
                print("Stream Status: https://trading-screener-lerd2.ondigitalocean.app/api/stream/status")
                
                print("\nTo start streaming:")
                print("curl -X POST https://trading-screener-lerd2.ondigitalocean.app/api/stream/start")
                
                return True
        
        if attempt < 19:
            time.sleep(60)  # Wait 1 minute
    
    print("\nMonitoring timeout - deployment may still be in progress")
    print("Check manually: https://trading-screener-lerd2.ondigitalocean.app/health")
    return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    except Exception as e:
        print(f"Error: {e}")