"""
Personal Trading Module - PRIVATE USE ONLY
Integrates StockScope analysis with Robinhood for automated trading
"""

import os
import logging
import pyotp
import robin_stocks.robinhood as rh
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
import pandas as pd
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load personal trading environment
load_dotenv('.env.trading')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    reasoning: List[str]
    risk_level: str
    timestamp: datetime

@dataclass
class Position:
    symbol: str
    quantity: float
    average_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float

class PersonalTradingEngine:
    """Personal trading engine that connects StockScope analysis to Robinhood execution"""
    
    def __init__(self):
        self.is_authenticated = False
        self.trading_mode = os.getenv('TRADING_MODE', 'paper')
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', 0.05))
        self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', 0.08))
        self.take_profit_percent = float(os.getenv('TAKE_PROFIT_PERCENT', 0.15))
        self.min_confidence = float(os.getenv('MIN_CONFIDENCE_THRESHOLD', 0.70))
        self.max_positions = int(os.getenv('MAX_CONCURRENT_POSITIONS', 10))
        self.daily_loss_limit = float(os.getenv('DAILY_LOSS_LIMIT', 0.02))
        
        # Notification setup
        self.enable_notifications = os.getenv('ENABLE_TRADE_NOTIFICATIONS', 'false').lower() == 'true'
        self.slack_client = None
        if os.getenv('SLACK_WEBHOOK_URL'):
            self.slack_client = WebClient(token=os.getenv('SLACK_WEBHOOK_URL'))
        
        # Trading log
        self.trade_log = []
        self.daily_pnl = 0.0
        
    def authenticate_robinhood(self) -> bool:
        """Authenticate with Robinhood using stored credentials"""
        try:
            username = os.getenv('ROBINHOOD_USERNAME')
            password = os.getenv('ROBINHOOD_PASSWORD')
            mfa_code = os.getenv('ROBINHOOD_MFA_CODE')
            
            if not username or not password:
                logger.error("Robinhood credentials not found in .env.trading")
                return False
            
            # Login with MFA if provided
            if mfa_code:
                totp = pyotp.TOTP(mfa_code)
                current_mfa = totp.now()
                login_result = rh.login(username, password, mfa_code=current_mfa)
            else:
                login_result = rh.login(username, password)
            
            if login_result:
                self.is_authenticated = True
                logger.info(f"Successfully authenticated with Robinhood (Mode: {self.trading_mode})")
                return True
            else:
                logger.error("Failed to authenticate with Robinhood")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Robinhood: {e}")
            return False
    
    def get_portfolio_info(self) -> Dict:
        """Get current portfolio information"""
        if not self.is_authenticated:
            return {"error": "Not authenticated"}
        
        try:
            # Get account info
            account = rh.profiles.load_account_profile()
            portfolio = rh.profiles.load_portfolio_profile()
            positions = rh.account.get_open_stock_positions()
            
            # Calculate portfolio metrics
            total_value = float(portfolio['total_return_today'])
            buying_power = float(account['buying_power'])
            day_change = float(portfolio['total_return_today'])
            
            # Get positions
            current_positions = []
            for pos in positions:
                instrument = rh.stocks.get_instrument_by_url(pos['instrument'])
                symbol = instrument['symbol']
                
                position_data = Position(
                    symbol=symbol,
                    quantity=float(pos['quantity']),
                    average_cost=float(pos['average_buy_price']) if pos['average_buy_price'] else 0,
                    current_price=float(rh.stocks.get_latest_price(symbol)[0]),
                    market_value=float(pos['market_value']) if pos['market_value'] else 0,
                    unrealized_pnl=float(pos['total_return_today']) if pos['total_return_today'] else 0,
                    unrealized_pnl_percent=0.0  # Calculate this
                )
                
                if position_data.average_cost > 0:
                    position_data.unrealized_pnl_percent = (
                        (position_data.current_price - position_data.average_cost) / position_data.average_cost
                    ) * 100
                
                current_positions.append(position_data)
            
            return {
                "total_value": total_value,
                "buying_power": buying_power,
                "day_change": day_change,
                "positions": current_positions,
                "position_count": len(current_positions),
                "trading_mode": self.trading_mode
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio info: {e}")
            return {"error": str(e)}
    
    def execute_trade_signal(self, signal: TradeSignal) -> Dict:
        """Execute a trade based on StockScope analysis"""
        if not self.is_authenticated:
            return {"error": "Not authenticated with Robinhood"}
        
        # Check if signal meets our criteria
        if signal.confidence < self.min_confidence:
            logger.info(f"Signal for {signal.symbol} below confidence threshold: {signal.confidence}")
            return {"status": "skipped", "reason": "Low confidence"}
        
        # Check daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            logger.warning(f"Daily loss limit reached: {self.daily_pnl}")
            return {"status": "skipped", "reason": "Daily loss limit reached"}
        
        # Get portfolio info for position sizing
        portfolio = self.get_portfolio_info()
        if "error" in portfolio:
            return portfolio
        
        # Calculate position size
        available_cash = portfolio["buying_power"]
        max_position_value = available_cash * self.max_position_size
        
        try:
            current_price = float(rh.stocks.get_latest_price(signal.symbol)[0])
            shares_to_trade = int(max_position_value / current_price)
            
            if shares_to_trade == 0:
                return {"status": "skipped", "reason": "Position size too small"}
            
            # Execute the trade
            trade_result = self._execute_order(signal, shares_to_trade, current_price)
            
            # Log the trade
            trade_log_entry = {
                "timestamp": datetime.now().isoformat(),
                "symbol": signal.symbol,
                "action": signal.action,
                "shares": shares_to_trade,
                "price": current_price,
                "confidence": signal.confidence,
                "reasoning": signal.reasoning,
                "result": trade_result
            }
            
            self.trade_log.append(trade_log_entry)
            self._save_trade_log()
            
            # Send notification
            if self.enable_notifications:
                self._send_trade_notification(trade_log_entry)
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error executing trade for {signal.symbol}: {e}")
            return {"error": str(e)}
    
    def _execute_order(self, signal: TradeSignal, shares: int, current_price: float) -> Dict:
        """Execute the actual order with Robinhood"""
        if self.trading_mode == 'paper':
            # Paper trading - just log the trade
            logger.info(f"PAPER TRADE: {signal.action} {shares} shares of {signal.symbol} at ${current_price}")
            return {
                "status": "paper_trade_executed",
                "symbol": signal.symbol,
                "action": signal.action,
                "shares": shares,
                "price": current_price,
                "mode": "paper"
            }
        
        # Live trading
        try:
            if signal.action == "BUY":
                order = rh.orders.order_buy_market(
                    instrument=signal.symbol,
                    quantity=shares,
                    timeInForce='gfd'  # Good for day
                )
                
                # Set stop loss if specified
                if signal.stop_loss:
                    stop_order = rh.orders.order_sell_stop_loss(
                        instrument=signal.symbol,
                        quantity=shares,
                        stopPrice=signal.stop_loss,
                        timeInForce='gtc'  # Good till canceled
                    )
                
            elif signal.action == "SELL":
                order = rh.orders.order_sell_market(
                    instrument=signal.symbol,
                    quantity=shares,
                    timeInForce='gfd'
                )
            
            return {
                "status": "order_placed",
                "order_id": order.get('id'),
                "symbol": signal.symbol,
                "action": signal.action,
                "shares": shares,
                "price": current_price,
                "mode": "live"
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"error": f"Order failed: {str(e)}"}
    
    def _save_trade_log(self):
        """Save trade log to file"""
        log_file = f"trading_log_{datetime.now().strftime('%Y%m')}.json"
        try:
            with open(log_file, 'w') as f:
                json.dump(self.trade_log, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trade log: {e}")
    
    def _send_trade_notification(self, trade_entry: Dict):
        """Send trade notification via Slack"""
        if not self.slack_client:
            return
        
        try:
            message = (
                f"🤖 StockScope Trade Executed\n"
                f"Symbol: {trade_entry['symbol']}\n"
                f"Action: {trade_entry['action']}\n"
                f"Shares: {trade_entry['shares']}\n"
                f"Price: ${trade_entry['price']:.2f}\n"
                f"Confidence: {trade_entry['confidence']:.1%}\n"
                f"Mode: {trade_entry['result'].get('mode', 'unknown')}\n"
                f"Reasoning: {', '.join(trade_entry['reasoning'][:2])}"
            )
            
            self.slack_client.chat_postMessage(
                channel="#trading",
                text=message
            )
            
        except SlackApiError as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    def get_stockscope_recommendations(self) -> List[TradeSignal]:
        """Get recommendations from StockScope analysis"""
        # This would integrate with your existing API
        # For now, return a sample structure
        return []
    
    def run_trading_session(self):
        """Run a complete trading session"""
        logger.info("Starting personal trading session...")
        
        if not self.authenticate_robinhood():
            logger.error("Failed to authenticate - aborting trading session")
            return
        
        # Get portfolio status
        portfolio = self.get_portfolio_info()
        logger.info(f"Portfolio value: ${portfolio.get('total_value', 0):,.2f}")
        logger.info(f"Available cash: ${portfolio.get('buying_power', 0):,.2f}")
        logger.info(f"Current positions: {portfolio.get('position_count', 0)}")
        
        # Get StockScope recommendations
        recommendations = self.get_stockscope_recommendations()
        
        if not recommendations:
            logger.info("No trading signals from StockScope")
            return
        
        # Execute high-confidence signals
        for signal in recommendations:
            if signal.confidence >= self.min_confidence:
                result = self.execute_trade_signal(signal)
                logger.info(f"Trade result for {signal.symbol}: {result}")
        
        logger.info("Trading session completed")

# Usage example
if __name__ == "__main__":
    # Initialize personal trading engine
    trading_engine = PersonalTradingEngine()
    
    # Run trading session (set up as scheduled job)
    trading_engine.run_trading_session()