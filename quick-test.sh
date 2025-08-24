#!/bin/bash

# StockScope Pro - Quick Automated Test Script
# Runs basic API tests to verify core functionality

echo "🤖 StockScope Pro - Automated Quick Tests"
echo "========================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${BLUE}📄 Loaded environment variables from .env${NC}"
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Configuration
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

# Use password from environment variables with fallback priority
if [ -n "$ADMIN_PASSWORD" ]; then
    PASSWORD="$ADMIN_PASSWORD"
    echo -e "${GREEN}🔑 Using ADMIN_PASSWORD from .env${NC}"
elif [ -n "$STOCKSCOPE_PASSWORD" ]; then
    PASSWORD="$STOCKSCOPE_PASSWORD"
    echo -e "${GREEN}🔑 Using STOCKSCOPE_PASSWORD from .env${NC}"
else
    echo -e "${RED}❌ No password found in .env file${NC}"
    echo "Please set ADMIN_PASSWORD or STOCKSCOPE_PASSWORD in your .env file"
    exit 1
fi

ENCODED_PASSWORD=$(echo -n "$PASSWORD" | python3 -c "import urllib.parse; print(urllib.parse.quote(input()))")

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run tests
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_pattern="$3"
    
    echo -n "Testing $test_name... "
    
    result=$(eval "$command" 2>/dev/null)
    exit_code=$?
    
    if [ $exit_code -eq 0 ] && echo "$result" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "  Command: $command"
        echo "  Expected: $expected_pattern"
        echo "  Got: $result"
        ((TESTS_FAILED++))
    fi
}

echo -e "${YELLOW}🔧 Running automated tests...${NC}"
echo ""

# Test 1: Backend Health Check
run_test "Backend Health" \
    "curl -s $BACKEND_URL/" \
    "StockScope API"

# Test 2: Authentication
run_test "Authentication" \
    "curl -s \"$BACKEND_URL/api/stocks?password=$ENCODED_PASSWORD\"" \
    "stocks"

# Test 3: Stock Suggestions
run_test "Stock Suggestions" \
    "curl -s \"$BACKEND_URL/api/stocks/suggestions?password=$ENCODED_PASSWORD&q=AAPL\"" \
    "Apple"

# Test 4: Portfolio Endpoint
run_test "Portfolio Data" \
    "curl -s \"$BACKEND_URL/api/stocks?password=$ENCODED_PASSWORD\"" \
    "count"

# Test 5: Stock Analysis (GOOGL)
run_test "Stock Analysis" \
    "curl -s \"$BACKEND_URL/api/stocks/GOOGL?password=$ENCODED_PASSWORD\"" \
    "ticker"

# Test 6: Company Info
run_test "Company Info" \
    "curl -s \"$BACKEND_URL/api/stocks/AAPL/info?password=$ENCODED_PASSWORD\"" \
    "displayName"

# Test 7: Frontend Accessibility
run_test "Frontend Loading" \
    "curl -s $FRONTEND_URL" \
    "StockScope"

# Test 8: Cache Endpoint (Admin only)
echo -n "Testing Cache Management... "
cache_result=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/cache?password=$ENCODED_PASSWORD" -X DELETE)
if [ "$cache_result" = "200" ] || [ "$cache_result" = "403" ]; then
    echo -e "${GREEN}✅ PASS${NC} (Status: $cache_result)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC} (Status: $cache_result)"
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}📊 TEST RESULTS${NC}"
echo "=================="
echo -e "✅ Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "❌ Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "📈 Success Rate: $(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))%"

echo ""
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo "Your StockScope Pro setup is working correctly."
else
    echo -e "${YELLOW}⚠️  SOME TESTS FAILED${NC}"
    echo "Please check the failed tests above and:"
    echo "• Ensure backend is running on port 8000"
    echo "• Ensure frontend is running on port 3000"
    echo "• Check that all dependencies are installed"
    echo "• Verify the password is correct"
fi

echo ""
echo -e "${BLUE}🔍 NEXT STEPS${NC}"
echo "1. Run: ./smoke-test.sh for detailed manual testing"
echo "2. Open http://localhost:3000 to test the UI"
echo "3. Check browser console for any JavaScript errors"
echo ""