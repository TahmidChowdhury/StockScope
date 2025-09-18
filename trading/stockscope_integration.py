"""
StockScope Trading Integration - PRIVATE USE ONLY
Bridges StockScope analysis with personal trading engine
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personal_trader import PersonalTradingEngine, TradeSignal
from backend.api import load_dataframes
from analysis.investment_advisor import InvestmentAdvisor
from analysis.quantitative_strategies import QuantitativeStrategies
from datetime import datetime
import requests
import logging

logger = logging.getLogger(__name__)

class StockScopeTradeIntegration:
    """Integrates StockScope analysis with personal trading"""
    
    def __init__(self):
        self.trading_engine = PersonalTradingEngine()
        self.api_base_url = "http://localhost:8000"  # Your StockScope API
        
    def get_personal_recommendations(self, watchlist: list = None) -> list[TradeSignal]:
        """Get trading recommendations from your StockScope analysis"""
        if not watchlist:
            # Use your analyzed stocks
            watchlist = self._get_analyzed_stocks()
        
        signals = []
        
        for symbol in watchlist:
            try:
                # Get StockScope analysis for the symbol
                recommendation = self._get_stockscope_recommendation(symbol)
                
                if recommendation and recommendation.get('recommendation'):
                    signal = TradeSignal(
                        symbol=symbol,
                        action=recommendation['recommendation'],
                        confidence=recommendation.get('confidence', 0.5),
                        target_price=recommendation.get('target_price'),
                        stop_loss=recommendation.get('stop_loss'),
                        reasoning=recommendation.get('signals', []),
                        risk_level=recommendation.get('risk_level', 'Medium'),
                        timestamp=datetime.now()
                    )
                    
                    signals.append(signal)
                    logger.info(f"Generated signal for {symbol}: {signal.action} (confidence: {signal.confidence:.2f})")
                
            except Exception as e:
                logger.error(f"Error getting recommendation for {symbol}: {e}")
                continue
        
        # Filter and sort by confidence
        high_confidence_signals = [s for s in signals if s.confidence >= 0.65]
        high_confidence_signals.sort(key=lambda x: x.confidence, reverse=True)
        
        return high_confidence_signals
    
    def _get_analyzed_stocks(self) -> list:
        """Get list of stocks you've already analyzed"""
        try:
            response = requests.get(f"{self.api_base_url}/api/stocks")
            if response.status_code == 200:
                data = response.json()
                return [stock['symbol'] for stock in data.get('stocks', [])]
            return []
        except:
            # Fallback to your current holdings or a default watchlist
            return ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    
    def _get_stockscope_recommendation(self, symbol: str) -> dict:
        """Get investment recommendation from StockScope API"""
        try:
            # Try to get from your API first
            response = requests.get(f"{self.api_base_url}/api/stocks/{symbol}/investment-advice")
            if response.status_code == 200:
                return response.json()
            
            # Fallback: use local analysis
            return self._generate_local_recommendation(symbol)
            
        except Exception as e:
            logger.error(f"Error getting API recommendation for {symbol}: {e}")
            return self._generate_local_recommendation(symbol)
    
    def _generate_local_recommendation(self, symbol: str) -> dict:
        """Generate recommendation using local StockScope modules"""
        try:
            # Load sentiment data if available
            df = load_dataframes(symbol)
            
            if df.empty:
                logger.warning(f"No sentiment data for {symbol}")
                return None
            
            # Use your InvestmentAdvisor
            advisor = InvestmentAdvisor(symbol)
            
            # Fetch stock data
            if not advisor.fetch_data():
                logger.error(f"Failed to fetch stock data for {symbol}")
                return None
            
            # Get recommendation
            recommendation = advisor.get_investment_recommendation()
            
            # Add quantitative analysis
            quant = QuantitativeStrategies()
            sentiment_data = {symbol: df.to_dict('records')}
            quant_strategy = quant.create_sentiment_momentum_strategy([symbol], sentiment_data)
            
            # Combine analysis
            combined_confidence = (
                recommendation.get('confidence', 0.5) * 0.7 + 
                quant_strategy.get('confidence_level', 0.5) * 0.3
            )
            
            return {
                'recommendation': recommendation.get('recommendation', 'HOLD'),
                'confidence': combined_confidence,
                'target_price': recommendation.get('target_price'),
                'stop_loss': recommendation.get('stop_loss'),
                'signals': recommendation.get('signals', []),
                'risk_level': recommendation.get('risk_level', 'Medium'),
                'quant_score': quant_strategy.get('combined_scores', {}).get(symbol, 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error generating local recommendation for {symbol}: {e}")
            return None
    
    def run_daily_trading_check(self, custom_watchlist: list = None):
        """Run daily trading check and execute high-confidence signals"""
        logger.info("🚀 Running daily StockScope trading check...")
        
        # Authenticate with Robinhood
        if not self.trading_engine.authenticate_robinhood():
            logger.error("Failed to authenticate with Robinhood")
            return
        
        # Get current portfolio
        portfolio = self.trading_engine.get_portfolio_info()
        logger.info(f"💰 Current portfolio value: ${portfolio.get('total_value', 0):,.2f}")
        logger.info(f"💵 Available buying power: ${portfolio.get('buying_power', 0):,.2f}")
        
        # Get recommendations
        signals = self.get_personal_recommendations(custom_watchlist)
        
        if not signals:
            logger.info("No trading signals generated")
            return
        
        logger.info(f"📊 Generated {len(signals)} trading signals")
        
        # Execute top signals
        executed_trades = 0
        for signal in signals[:5]:  # Limit to top 5 signals
            if signal.action in ['BUY', 'SELL'] and signal.confidence >= 0.70:
                logger.info(f"🎯 Executing {signal.action} signal for {signal.symbol} (confidence: {signal.confidence:.2f})")
                
                result = self.trading_engine.execute_trade_signal(signal)
                
                if result.get('status') in ['paper_trade_executed', 'order_placed']:
                    executed_trades += 1
                    logger.info(f"✅ Trade executed: {result}")
                else:
                    logger.warning(f"❌ Trade skipped: {result}")
        
        logger.info(f"📈 Trading session complete. Executed {executed_trades} trades.")
    
    def check_positions_against_analysis(self):
        """Check your current positions against latest StockScope analysis"""
        logger.info("🔍 Checking current positions against latest analysis...")
        
        if not self.trading_engine.authenticate_robinhood():
            return
        
        portfolio = self.trading_engine.get_portfolio_info()
        current_positions = portfolio.get('positions', [])
        
        if not current_positions:
            logger.info("No current positions to analyze")
            return
        
        for position in current_positions:
            symbol = position.symbol
            current_pnl_percent = position.unrealized_pnl_percent
            
            # Get latest analysis
            recommendation = self._get_stockscope_recommendation(symbol)
            
            if recommendation:
                latest_action = recommendation.get('recommendation', 'HOLD')
                confidence = recommendation.get('confidence', 0.5)
                
                logger.info(f"📊 {symbol}: Current P&L: {current_pnl_percent:.1f}%, Latest: {latest_action} ({confidence:.2f} confidence)")
                
                # Alert on significant changes
                if latest_action == 'SELL' and confidence > 0.75 and current_pnl_percent > 0:
                    logger.warning(f"🚨 Consider taking profits on {symbol}: {current_pnl_percent:.1f}% gain, analysis suggests SELL")
                elif latest_action == 'SELL' and confidence > 0.80 and current_pnl_percent < -5:
                    logger.warning(f"🚨 Consider cutting losses on {symbol}: {current_pnl_percent:.1f}% loss, analysis suggests SELL")
    
    def get_personal_watchlist_analysis(self, symbols: list) -> dict:
        """Analyze a custom watchlist for trading opportunities"""
        analysis = {}
        
        for symbol in symbols:
            recommendation = self._get_stockscope_recommendation(symbol)
            if recommendation:
                analysis[symbol] = {
                    'action': recommendation.get('recommendation', 'HOLD'),
                    'confidence': recommendation.get('confidence', 0.5),
                    'risk_level': recommendation.get('risk_level', 'Medium'),
                    'reasoning': recommendation.get('signals', [])[:3],  # Top 3 reasons
                    'quant_score': recommendation.get('quant_score', 0.0)
                }
        
        # Sort by confidence
        sorted_analysis = dict(sorted(analysis.items(), 
                                    key=lambda x: x[1]['confidence'], 
                                    reverse=True))
        
        return sorted_analysis

# CLI for easy usage
if __name__ == "__main__":
    integration = StockScopeTradeIntegration()
    
    import argparse
    parser = argparse.ArgumentParser(description='StockScope Personal Trading Integration')
    parser.add_argument('--mode', choices=['daily', 'check-positions', 'analyze'], 
                       default='daily', help='Trading mode')
    parser.add_argument('--symbols', nargs='+', help='Custom watchlist symbols')
    
    args = parser.parse_args()
    
    if args.mode == 'daily':
        integration.run_daily_trading_check(args.symbols)
    elif args.mode == 'check-positions':
        integration.check_positions_against_analysis()
    elif args.mode == 'analyze':
        if args.symbols:
            analysis = integration.get_personal_watchlist_analysis(args.symbols)
            print("\n📊 Watchlist Analysis:")
            for symbol, data in analysis.items():
                print(f"{symbol}: {data['action']} ({data['confidence']:.2f} confidence) - {data['risk_level']} risk")
        else:
            print("Please provide symbols with --symbols")