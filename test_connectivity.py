#!/usr/bin/env python3
"""
API Connectivity Test Script
Tests connection to HutzTrades backend API
"""

import requests
import json
import time
from datetime import datetime

API_BASE_URL = "https://trading-screener-lerd2.ondigitalocean.app"

class APITester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'HutzTrades-Test-Client/1.0'
        })
        
    def log(self, message, status="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m", 
            "ERROR": "\033[91m",
            "WARNING": "\033[93m"
        }
        color = status_colors.get(status, "\033[0m")
        print(f"{color}[{timestamp}] {status}: {message}\033[0m")
        
    def test_health(self):
        """Test the health endpoint"""
        self.log("Testing health endpoint...", "INFO")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Health check passed! Status: {data.get('status')}", "SUCCESS")
                self.log(f"   - Data points: {data.get('data_points', 'N/A')}")
                self.log(f"   - Version: {data.get('version', 'N/A')}")
                self.log(f"   - Database: {data.get('database', 'N/A')}")
                return True
            else:
                self.log(f"Health check failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Health check failed: {str(e)}", "ERROR")
            return False
    
    def test_strategies(self):
        """Test the strategies endpoint"""
        self.log("Testing strategies endpoint...", "INFO")
        
        try:
            response = self.session.get(f"{self.base_url}/api/strategies/top?limit=5", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                strategies_count = len(data.get('strategies', []))
                self.log(f"Strategies endpoint working! Found {strategies_count} strategies", "SUCCESS")
                
                if strategies_count > 0:
                    strategy = data['strategies'][0]
                    self.log(f"   - Top strategy: {strategy.get('symbol')} {strategy.get('timeframe')} (Return: {strategy.get('total_return', 'N/A')}%)")
                
                return True
            else:
                self.log(f"Strategies test failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Strategies test failed: {str(e)}", "ERROR")
            return False
    
    def test_backtest_submit(self):
        """Test submitting a backtest job"""
        self.log("Testing backtest submission...", "INFO")
        
        test_payload = {
            "symbols": ["AAPL"],
            "timeframes": ["1h"],
            "start_date": "2024-01-01",
            "end_date": "2024-02-01"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/backtest/run",
                json=test_payload,
                timeout=20
            )
            
            if response.status_code in [200, 202]:
                data = response.json()
                self.log(f"Backtest submission successful!", "SUCCESS")
                self.log(f"   - Job ID: {data.get('job_id', 'N/A')}")
                self.log(f"   - Status: {data.get('status', 'N/A')}")
                return True
            else:
                self.log(f"Backtest submission failed: HTTP {response.status_code}", "ERROR")
                if response.text:
                    self.log(f"   Response: {response.text[:200]}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Backtest submission failed: {str(e)}", "ERROR")
            return False
    
    def test_results(self):
        """Test the results endpoint"""
        self.log("Testing results endpoint...", "INFO")
        
        try:
            response = self.session.get(f"{self.base_url}/api/backtest/results?limit=5", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results_count = len(data.get('results', []))
                self.log(f"Results endpoint working! Found {results_count} results", "SUCCESS")
                return True
            else:
                self.log(f"Results test failed: HTTP {response.status_code}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"Results test failed: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all connectivity tests"""
        self.log(f"Starting API connectivity tests for {self.base_url}", "INFO")
        self.log("=" * 60)
        
        tests = [
            ("Health Check", self.test_health),
            ("Strategies Endpoint", self.test_strategies),
            ("Backtest Submission", self.test_backtest_submit),
            ("Results Endpoint", self.test_results)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            self.log(f"\nRunning {test_name}...")
            results[test_name] = test_func()
            time.sleep(1)  # Brief pause between tests
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("Test Summary:", "INFO")
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, test_passed in results.items():
            status = "PASS" if test_passed else "FAIL"
            self.log(f"   {test_name}: {status}")
        
        self.log(f"\nOverall Result: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("All tests passed! API is fully functional.", "SUCCESS")
        else:
            self.log("Some tests failed. Check the logs above.", "WARNING")
        
        return passed == total

if __name__ == "__main__":
    print("HutzTrades API Connectivity Test")
    print("=" * 50)
    
    tester = APITester(API_BASE_URL)
    success = tester.run_all_tests()
    
    exit(0 if success else 1)