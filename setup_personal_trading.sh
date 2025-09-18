#!/bin/bash

# Personal Trading Setup Script - PRIVATE USE ONLY
# Sets up your dev-trading branch for Robinhood integration

echo "🚀 Setting up StockScope Personal Trading Environment..."

# Check if we're on the right branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "dev-trading" ]; then
    echo "❌ Please switch to dev-trading branch first:"
    echo "   git checkout dev-trading"
    exit 1
fi

# Install trading dependencies
echo "📦 Installing trading dependencies..."
pip install robin-stocks pyotp schedule slack-sdk

# Create trading logs directory
mkdir -p logs/trading

# Set up environment file if it doesn't exist
if [ ! -f ".env.trading" ]; then
    echo "⚙️  Creating .env.trading template..."
    echo "# Please fill in your actual credentials" >> .env.trading
    echo "ROBINHOOD_USERNAME=" >> .env.trading
    echo "ROBINHOOD_PASSWORD=" >> .env.trading
    echo "ROBINHOOD_MFA_CODE=" >> .env.trading
    echo "TRADING_MODE=paper" >> .env.trading
    echo ""
    echo "📝 Please edit .env.trading with your Robinhood credentials"
    echo "   - For MFA_CODE, use your TOTP secret from Robinhood 2FA setup"
    echo "   - Keep TRADING_MODE=paper until you're ready for live trading"
fi

# Create a daily trading script
cat > run_daily_trading.sh << 'EOF'
#!/bin/bash
# Daily Trading Execution Script
cd /Users/tahmid/Projects/StockScope
python3 trading/stockscope_integration.py --mode daily
EOF
chmod +x run_daily_trading.sh

# Create portfolio check script
cat > check_positions.sh << 'EOF'
#!/bin/bash
# Check Current Positions Against Analysis
cd /Users/tahmid/Projects/StockScope
python3 trading/stockscope_integration.py --mode check-positions
EOF
chmod +x check_positions.sh

echo ""
echo "✅ Personal trading environment setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env.trading with your Robinhood credentials"
echo "2. Test paper trading: python3 trading/stockscope_integration.py --mode daily"
echo "3. Check positions: ./check_positions.sh"
echo "4. Analyze custom watchlist: python3 trading/stockscope_integration.py --mode analyze --symbols AAPL TSLA"
echo ""
echo "⚠️  Important Security Notes:"
echo "- .env.trading is gitignored - your credentials won't be committed"
echo "- Always test in paper mode first"
echo "- This branch should remain private"
echo ""
echo "🔄 To set up automated daily trading:"
echo "   crontab -e"
echo "   Add: 0 9 * * 1-5 /Users/tahmid/Projects/StockScope/run_daily_trading.sh"