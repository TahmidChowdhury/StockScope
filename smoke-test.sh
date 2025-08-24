#!/bin/bash

# StockScope Pro - Manual Smoke Test Script
# This script helps you manually verify all key functionality

echo "🧪 StockScope Pro - Smoke Test Guide"
echo "====================================="
echo ""

# Color codes for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${BLUE}📄 Loaded environment variables from .env${NC}"
else
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please create a .env file with your password configuration"
    exit 1
fi

# Get password from environment variables
if [ -n "$ADMIN_PASSWORD" ]; then
    ENV_PASSWORD="$ADMIN_PASSWORD"
    PASSWORD_TYPE="ADMIN_PASSWORD"
elif [ -n "$STOCKSCOPE_PASSWORD" ]; then
    ENV_PASSWORD="$STOCKSCOPE_PASSWORD"
    PASSWORD_TYPE="STOCKSCOPE_PASSWORD"
else
    echo -e "${RED}❌ No password found in .env file${NC}"
    echo "Please set ADMIN_PASSWORD or STOCKSCOPE_PASSWORD in your .env file"
    exit 1
fi

echo -e "${GREEN}🔑 Using $PASSWORD_TYPE from .env${NC}"
echo ""

echo -e "${BLUE}📋 SMOKE TEST CHECKLIST${NC}"
echo "Follow this checklist to verify all functionality works correctly:"
echo ""

echo -e "${YELLOW}🚀 STEP 1: Environment Setup${NC}"
echo "□ Backend server is running (uvicorn on port 8000)"
echo "□ Frontend is running (Next.js on port 3000)"
echo "□ Virtual environment is activated"
echo ""

echo -e "${YELLOW}🔐 STEP 2: Authentication${NC}"
echo "□ Navigate to http://localhost:3000"
echo "□ Login page appears with password field"
echo "□ Try wrong password - should show error"
echo -e "□ Enter correct password: ${GREEN}'$ENV_PASSWORD'${NC}"
echo "□ Should redirect to main dashboard"
echo "□ Green 'Secure Session Active' indicator visible"
echo ""

echo -e "${YELLOW}🔍 STEP 3: Stock Search${NC}"
echo "□ Search box appears with autocomplete"
echo "□ Type 'APP' - should suggest Apple Inc. (AAPL)"
echo "□ Type 'GOOG' - should suggest Alphabet Inc. (GOOGL)"
echo "□ Try invalid symbol like 'INVALID123' - should handle gracefully"
echo "□ Select a valid stock from suggestions"
echo ""

echo -e "${YELLOW}📊 STEP 4: Portfolio View${NC}"
echo "□ Portfolio section shows analyzed stocks (AAPL, GOOGL, MSFT)"
echo "□ Each stock card shows:"
echo "  - Stock symbol (e.g., AAPL)"
echo "  - Company name (e.g., Apple Inc.)"
echo "  - Current price (e.g., \$150.25)"
echo "  - Price change with arrows (e.g., ↗ +\$2.50 (+1.7%))"
echo "  - Sentiment indicator (📈 Sentiment: 8%)"
echo "□ Price changes show correct colors (green=up, red=down)"
echo "□ Hover effects work on stock cards"
echo ""

echo -e "${YELLOW}📈 STEP 5: Stock Dashboard${NC}"
echo "□ Click on a stock (e.g., GOOGL) to view dashboard"
echo "□ Dashboard loads without infinite API calls"
echo "□ Key metrics display correctly:"
echo "  - Total Posts count"
echo "  - Average Sentiment"
echo "  - Reddit Posts count"
echo "  - News Articles count"
echo "□ Charts render properly:"
echo "  - Pie chart for data sources"
echo "  - Bar chart for source breakdown"
echo "□ Source details table shows data by source"
echo "□ Quick Actions buttons are visible"
echo ""

echo -e "${YELLOW}🤖 STEP 6: AI Features${NC}"
echo "□ Click 'Get Investment Advice' button"
echo "□ Modal opens with recommendation (BUY/SELL/HOLD)"
echo "□ Shows confidence score and reasoning"
echo "□ Click 'View Detailed Analysis' button"
echo "□ Quantitative analysis modal opens"
echo "□ Click 'Recent News & Posts' button"
echo "□ News modal shows aggregated data"
echo ""

echo -e "${YELLOW}🔄 STEP 7: Real-time Features${NC}"
echo "□ Click 'Refresh' button - data updates"
echo "□ Portfolio refreshes every 30 seconds automatically"
echo "□ No infinite API calls in browser dev tools"
echo "□ Backend logs show reasonable API call frequency"
echo ""

echo -e "${YELLOW}🗑️ STEP 8: Management Features${NC}"
echo "□ Click 'Manage Portfolio' button"
echo "□ Selection mode activates"
echo "□ Select multiple stocks"
echo "□ 'Delete Selected' button appears"
echo "□ Cancel selection mode works"
echo "□ Individual delete buttons work on hover"
echo ""

echo -e "${YELLOW}🚪 STEP 9: Logout & Navigation${NC}"
echo "□ Click 'Logout' button"
echo "□ Returns to login screen"
echo "□ Session data cleared"
echo "□ Back button from dashboard works"
echo "□ Navigation between views is smooth"
echo ""

echo -e "${YELLOW}⚡ STEP 10: Performance${NC}"
echo "□ Pages load quickly (< 2 seconds)"
echo "□ No console errors in browser"
echo "□ Backend responds promptly"
echo "□ Memory usage stays reasonable"
echo "□ No memory leaks after navigation"
echo ""

echo ""
echo -e "${GREEN}✅ EXPECTED RESULTS${NC}"
echo "If all checkboxes pass, the smoke test is successful!"
echo ""

echo -e "${RED}❌ COMMON ISSUES TO WATCH FOR${NC}"
echo "• Infinite API calls (check browser network tab)"
echo "• Timezone errors in backend logs"
echo "• Missing price data (should show fallback)"
echo "• Broken authentication flow"
echo "• UI elements not responding"
echo "• Console errors in browser dev tools"
echo ""

echo -e "${BLUE}🐛 DEBUGGING TIPS${NC}"
echo "• Check browser console (F12) for errors"
echo "• Monitor backend logs for API errors"
echo "• Verify network requests in dev tools"
echo "• Check localStorage for auth tokens"
echo "• Ensure all dependencies are installed"
echo ""

echo -e "${GREEN}🎯 QUICK AUTOMATED CHECKS${NC}"
echo "Run these commands to verify setup:"
echo ""

# Backend health check
echo -e "${YELLOW}Backend Health Check:${NC}"
echo "curl -s http://localhost:8000/ | jq ."
echo ""

# API endpoint test  
echo -e "${YELLOW}Test API with Authentication:${NC}"
ENCODED_PASSWORD=$(echo -n "$ENV_PASSWORD" | python3 -c "import urllib.parse; print(urllib.parse.quote(input()))" 2>/dev/null || echo "$ENV_PASSWORD")
echo "curl -s \"http://localhost:8000/api/stocks?password=$ENCODED_PASSWORD\" | jq '.count'"
echo ""

# Frontend check
echo -e "${YELLOW}Frontend Accessibility:${NC}"
echo "curl -s http://localhost:3000 | grep -o '<title>.*</title>'"
echo ""

echo -e "${GREEN}📝 TEST EXECUTION LOG${NC}"
echo "Copy this template to track your test results:"
echo ""
echo "Date: $(date)"
echo "Tester: [Your Name]"
echo "Environment: macOS"
echo "Password Type: $PASSWORD_TYPE"
echo ""
echo "✅ Authentication: PASS/FAIL"
echo "✅ Stock Search: PASS/FAIL"
echo "✅ Portfolio Display: PASS/FAIL"
echo "✅ Dashboard Navigation: PASS/FAIL"
echo "✅ AI Features: PASS/FAIL"
echo "✅ Real-time Updates: PASS/FAIL"
echo "✅ Management Tools: PASS/FAIL"
echo "✅ Performance: PASS/FAIL"
echo ""
echo "Notes:"
echo "- [Any issues found]"
echo "- [Performance observations]"
echo "- [Suggestions for improvement]"
echo ""

echo -e "${BLUE}🚀 Ready to start smoke testing!${NC}"
echo "Open http://localhost:3000 and follow the checklist above."
echo ""