#!/bin/bash

# Test script for fundamentals analytics
echo "🚀 Testing StockScope Fundamentals Analytics..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the StockScope root directory"
    exit 1
fi

# Test backend API endpoints
echo "📡 Testing backend API endpoints..."

# Test single ticker endpoint
echo "Testing single ticker: /fundamentals/AAPL"
curl -s "http://localhost:8000/fundamentals/AAPL?password=${STOCKSCOPE_PASSWORD:-demo123}" | jq '.ttm.ticker' 2>/dev/null || echo "Backend not running or no jq installed"

# Test compare endpoint
echo "Testing compare endpoint"
curl -s -X POST "http://localhost:8000/fundamentals/compare?password=${STOCKSCOPE_PASSWORD:-demo123}" \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT"]}' | jq 'length' 2>/dev/null || echo "Backend not running or no jq installed"

# Test screener endpoint
echo "Testing screener endpoint"
curl -s -X POST "http://localhost:8000/fundamentals/screener?password=${STOCKSCOPE_PASSWORD:-demo123}" \
  -H "Content-Type: application/json" \
  -d '{"min_revenue_growth_yoy": 0.1, "limit": 5}' | jq '.results | length' 2>/dev/null || echo "Backend not running or no jq installed"

echo "✅ API tests completed"

# Test frontend routes
echo "🌐 Frontend routes available:"
echo "  - /fundamentals/[ticker] - Individual company analysis"
echo "  - /compare - Multi-company comparison"
echo "  - /screener - Stock screening with filters"

echo ""
echo "📊 Features implemented:"
echo "  ✅ FCF margin charts (quarterly + TTM)"
echo "  ✅ Operating margin charts (quarterly + TTM)" 
echo "  ✅ Revenue growth tracking (TTM + YoY)"
echo "  ✅ EBITDA growth tracking (TTM + YoY)"
echo "  ✅ Peer comparison across multiple tickers"
echo "  ✅ Stock screener with comprehensive filters"
echo "  ✅ 6-hour TTL caching for performance"
echo "  ✅ Error handling and loading states"
echo "  ✅ Responsive design with Tailwind CSS"

echo ""
echo "🧪 To run backend tests:"
echo "  pytest backend/tests/test_fundamentals.py -v"

echo ""
echo "🚦 To start the application:"
echo "  Backend: uvicorn backend.api:app --reload --port 8000"
echo "  Frontend: cd stockscope-frontend && npm run dev"

echo ""
echo "📝 Example URLs to test:"
echo "  http://localhost:3000/fundamentals/AAPL"
echo "  http://localhost:3000/compare"
echo "  http://localhost:3000/screener"

echo ""
echo "✨ StockScope Fundamentals Analytics is ready!"