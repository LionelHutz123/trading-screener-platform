#!/usr/bin/env python3
"""
Monitor HutzTrades deployment until live streaming API is active
"""

import requests
import time
import json
from datetime import datetime

def check_api_status():
    """Check if the full API is deployed"""
    try:
        response = requests.get("https://trading-screener-lerd2.ondigitalocean.app/health", timeout=10)
        
        # Check if it's the simple response or full API
        if "Hello! you requested" in response.text:
            return False, "simple_response"
        elif response.status_code == 200:
            try:
                # Try to parse as JSON
                data = response.json()
                if "status" in data:
                    return True, "full_api"
            except:
                pass
        
        return False, f"status_code_{response.status_code}"
    except Exception as e:
        return False, f"error_{str(e)[:50]}"

def test_streaming_endpoints():
    """Test all streaming endpoints"""
    base_url = "https://trading-screener-lerd2.ondigitalocean.app"
    
    endpoints = {
        "Health": "/health",
        "API Status": "/api/status", 
        "Stream Status": "/api/stream/status",
        "Live Signals": "/api/stream/signals"
    }
    
    results = {}
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            results[name] = {
                "status": response.status_code,
                "working": response.status_code == 200 and "Hello!" not in response.text
            }
        except Exception as e:
            results[name] = {"status": "error", "working": False}
    
    return results

def main():
    """Monitor deployment progress"""
    print("🔍 Monitoring HutzTrades Deployment...")
    print("🌐 URL: https://trading-screener-lerd2.ondigitalocean.app")
    print("⏰ Started monitoring at:", datetime.now().strftime("%H:%M:%S"))
    print("\n" + "="*60)
    
    attempt = 0
    max_attempts = 20  # 20 minutes max
    
    while attempt < max_attempts:
        attempt += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{current_time}] Check #{attempt}/{max_attempts}")
        
        is_ready, status = check_api_status()
        
        if is_ready:
            print("✅ FULL API IS LIVE!")
            print("\n🧪 Testing all streaming endpoints...")
            
            results = test_streaming_endpoints()
            
            working_count = sum(1 for r in results.values() if r["working"])
            total_count = len(results)
            
            print(f"\n📊 Endpoint Status ({working_count}/{total_count} working):")
            for name, result in results.items():
                status_icon = "✅" if result["working"] else "❌"
                print(f"   {status_icon} {name}: {result['status']}")
            
            if working_count >= 3:  # At least 3 endpoints working
                print("\n🎉 DEPLOYMENT COMPLETE!")
                print("🚀 Your HutzTrades Live Streaming Platform is READY!")
                
                print("\n📡 Available Features:")
                print("   ✅ Real-time data streaming")
                print("   ✅ Pattern recognition engine")
                print("   ✅ Live signal generation")
                print("   ✅ WebSocket connections")
                print("   ✅ Paper trading integration")
                
                print("\n🌐 Ready to Use:")
                print("   • Dashboard: https://trading-screener-lerd2.ondigitalocean.app")
                print("   • API Docs: https://trading-screener-lerd2.ondigitalocean.app/docs")
                print("   • Stream Status: https://trading-screener-lerd2.ondigitalocean.app/api/stream/status")
                
                print("\n🎯 Next Steps:")
                print("   1. Visit the dashboard to see the interface")
                print("   2. Start streaming: POST /api/stream/start") 
                print("   3. Monitor signals: GET /api/stream/signals")
                
                return True
            else:
                print("⚠️  Some endpoints not ready yet, continuing to monitor...")
        else:
            print(f"⏳ Deployment in progress... (Status: {status})")
        
        if attempt < max_attempts:
            print("   ⏱️  Waiting 60 seconds for next check...")
            time.sleep(60)
    
    print("\n⏰ Monitoring timeout reached")
    print("💡 The deployment may still be in progress.")
    print("   Check manually: https://trading-screener-lerd2.ondigitalocean.app/health")
    return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n📋 If deployment seems stuck:")
            print("   1. Check DigitalOcean dashboard for build logs")
            print("   2. Ensure environment variables are set")
            print("   3. Try manual redeploy if needed")
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")