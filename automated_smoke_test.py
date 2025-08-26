#!/usr/bin/env python3
"""
StockScope Automated Smoke Test
Tests critical functionality and catches common errors.
"""

import sys
import os
import requests
import json
import time
import subprocess
from urllib.parse import quote
from typing import Dict, Any, List, Optional

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SmokeTestRunner:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
        self.password = self._get_password()
        self.test_results = []
        self.failed_tests = []
    
    def _get_password(self) -> str:
        """Get password from environment or .env file"""
        # Try environment variables first
        password = os.environ.get('ADMIN_PASSWORD') or os.environ.get('STOCKSCOPE_PASSWORD')
        if password:
            return password
        
        # Try .env file
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('ADMIN_PASSWORD='):
                        return line.split('=', 1)[1].strip().strip('"\'')
                    elif line.startswith('STOCKSCOPE_PASSWORD='):
                        return line.split('=', 1)[1].strip().strip('"\'')
        
        print("❌ No password found in environment or .env file")
        return "admin123"  # fallback for testing
    
    def log_test(self, test_name: str, passed: bool, details: str = "", error: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        if error:
            print(f"   Error: {error}")
        
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "error": error,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        if not passed:
            self.failed_tests.append(result)
    
    def test_backend_health(self) -> bool:
        """Test if backend is running and responsive"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.log_test("Backend Health Check", True, "Backend is running")
                return True
            else:
                self.log_test("Backend Health Check", False, f"Got status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Backend Health Check", False, error=str(e))
            return False
    
    def test_frontend_health(self) -> bool:
        """Test if frontend is running"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200 and "StockScope" in response.text:
                self.log_test("Frontend Health Check", True, "Frontend is running")
                return True
            else:
                self.log_test("Frontend Health Check", False, f"Got status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Frontend Health Check", False, error=str(e))
            return False
    
    def test_authentication(self) -> bool:
        """Test authentication with correct and incorrect passwords"""
        try:
            # Test with wrong password
            response = requests.get(f"{self.base_url}/api/stocks?password=wrongpassword", timeout=10)
            if response.status_code == 401:
                self.log_test("Auth - Wrong Password", True, "Correctly rejected wrong password")
            else:
                self.log_test("Auth - Wrong Password", False, f"Expected 401, got {response.status_code}")
                return False
            
            # Test with correct password
            encoded_password = quote(self.password)
            response = requests.get(f"{self.base_url}/api/stocks?password={encoded_password}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'count' in data:
                    self.log_test("Auth - Correct Password", True, f"Got {data['count']} stocks")
                    return True
                else:
                    self.log_test("Auth - Correct Password", False, "Invalid response format")
                    return False
            else:
                self.log_test("Auth - Correct Password", False, f"Got status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Auth - Correct Password", False, error=str(e))
            return False
    
    def test_fundamentals_api(self) -> bool:
        """Test fundamentals API endpoints for TTM calculation errors"""
        encoded_password = quote(self.password)
        test_tickers = ["AAPL", "GOOGL", "MSFT", "NVDA"]
        
        all_passed = True
        for ticker in test_tickers:
            try:
                # Test TTM endpoint
                response = requests.get(
                    f"{self.base_url}/api/fundamentals/{ticker}/ttm?password={encoded_password}", 
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        has_data = any(v is not None for v in data.values() if isinstance(v, (int, float)))
                        insufficient_data = data.get('insufficient_data', True)
                        
                        if has_data or not insufficient_data:
                            self.log_test(f"Fundamentals TTM - {ticker}", True, 
                                        f"Revenue TTM: ${data.get('revenue_ttm', 'N/A')}")
                        else:
                            self.log_test(f"Fundamentals TTM - {ticker}", True, 
                                        "No data available (expected for some tickers)")
                    else:
                        self.log_test(f"Fundamentals TTM - {ticker}", False, "Invalid response format")
                        all_passed = False
                else:
                    self.log_test(f"Fundamentals TTM - {ticker}", False, f"Status {response.status_code}")
                    all_passed = False
                
                # Test series endpoint
                response = requests.get(
                    f"{self.base_url}/api/fundamentals/{ticker}/series?password={encoded_password}", 
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and 'revenue_q' in data:
                        self.log_test(f"Fundamentals Series - {ticker}", True, 
                                    f"Got {len(data.get('revenue_q', []))} revenue quarters")
                    else:
                        self.log_test(f"Fundamentals Series - {ticker}", False, "Invalid series format")
                        all_passed = False
                else:
                    self.log_test(f"Fundamentals Series - {ticker}", False, f"Status {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Fundamentals - {ticker}", False, error=str(e))
                all_passed = False
            
            time.sleep(0.5)  # Rate limiting
        
        return all_passed
    
    def test_sentiment_api(self) -> bool:
        """Test sentiment analysis endpoints"""
        encoded_password = quote(self.password)
        test_tickers = ["AAPL", "GOOGL"]
        
        all_passed = True
        for ticker in test_tickers:
            try:
                response = requests.get(
                    f"{self.base_url}/api/sentiment/{ticker}?password={encoded_password}", 
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and 'ticker' in data:
                        sentiment_metrics = data.get('sentiment_metrics', {})
                        avg_sentiment = sentiment_metrics.get('avg_sentiment', 0)
                        self.log_test(f"Sentiment - {ticker}", True, 
                                    f"Avg sentiment: {avg_sentiment:.2f}")
                    else:
                        self.log_test(f"Sentiment - {ticker}", False, "Invalid response format")
                        all_passed = False
                else:
                    self.log_test(f"Sentiment - {ticker}", False, f"Status {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Sentiment - {ticker}", False, error=str(e))
                all_passed = False
        
        return all_passed
    
    def test_direct_ttm_calculation(self) -> bool:
        """Test TTM calculation directly to catch DatetimeIndex errors"""
        try:
            # Import the fundamentals service directly
            from backend.services.fundamentals import get_service
            
            service = get_service()
            test_tickers = ["AAPL", "MSFT"]
            
            all_passed = True
            for ticker in test_tickers:
                try:
                    # This should not raise "DatetimeIndex ambiguous truth value" error
                    data = service.get_fundamentals_data(ticker)
                    ttm_data = data.get('ttm', {})
                    
                    if isinstance(ttm_data, dict):
                        self.log_test(f"Direct TTM Calculation - {ticker}", True, 
                                    f"Revenue: ${ttm_data.get('revenue_ttm', 'N/A')}")
                    else:
                        self.log_test(f"Direct TTM Calculation - {ticker}", False, "Invalid TTM data format")
                        all_passed = False
                        
                except Exception as e:
                    error_msg = str(e)
                    if "ambiguous" in error_msg.lower() and "datetimeindex" in error_msg.lower():
                        self.log_test(f"Direct TTM Calculation - {ticker}", False, 
                                    "DatetimeIndex ambiguous truth value error", error_msg)
                    else:
                        self.log_test(f"Direct TTM Calculation - {ticker}", False, error=error_msg)
                    all_passed = False
            
            return all_passed
            
        except ImportError as e:
            self.log_test("Direct TTM Calculation", False, "Cannot import fundamentals service", str(e))
            return False
        except Exception as e:
            self.log_test("Direct TTM Calculation", False, error=str(e))
            return False
    
    def test_critical_endpoints(self) -> bool:
        """Test other critical endpoints"""
        encoded_password = quote(self.password)
        endpoints_to_test = [
            ("/api/stocks", "Stock list"),
            ("/api/health", "Health check"),
        ]
        
        all_passed = True
        for endpoint, description in endpoints_to_test:
            try:
                url = f"{self.base_url}{endpoint}"
                if "password" not in endpoint:
                    url += f"?password={encoded_password}"
                
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.log_test(f"Endpoint - {description}", True, f"Status 200")
                else:
                    self.log_test(f"Endpoint - {description}", False, f"Status {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Endpoint - {description}", False, error=str(e))
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self) -> bool:
        """Run all smoke tests"""
        print("🧪 StockScope Automated Smoke Test")
        print("=" * 40)
        print(f"Using password: {self.password[:3]}***")
        print()
        
        # Run tests in order of importance
        tests = [
            ("Backend Health", self.test_backend_health),
            ("Frontend Health", self.test_frontend_health),
            ("Authentication", self.test_authentication),
            ("Direct TTM Calculation", self.test_direct_ttm_calculation),
            ("Fundamentals API", self.test_fundamentals_api),
            ("Sentiment API", self.test_sentiment_api),
            ("Critical Endpoints", self.test_critical_endpoints),
        ]
        
        passed_count = 0
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                if test_func():
                    passed_count += 1
            except Exception as e:
                self.log_test(test_name, False, error=str(e))
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['passed']])
        
        print("\n" + "=" * 40)
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 40)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  • {test['test']}: {test['error'] or test['details']}")
        
        # Overall result
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! StockScope is healthy.")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please investigate.")
            return False

def main():
    """Main entry point"""
    runner = SmokeTestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()