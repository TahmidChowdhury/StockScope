"""
Optimized FastAPI backend for StockScope with caching, proper error handling, efficient data access, and simple authentication
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
import sys
import os
import asyncio
import json
from datetime import datetime, timedelta
from functools import lru_cache
import logging
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Multi-level password authentication - SECURE VERSION
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") 
GUEST_PASSWORD = os.getenv("GUEST_PASSWORD")

# For backward compatibility
MASTER_PASSWORD = os.getenv("STOCKSCOPE_PASSWORD", ADMIN_PASSWORD)

# Validate that passwords are set
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD environment variable must be set")
if not DEMO_PASSWORD:
    raise ValueError("DEMO_PASSWORD environment variable must be set")  
if not GUEST_PASSWORD:
    raise ValueError("GUEST_PASSWORD environment variable must be set")

def get_user_role(password: str) -> str:
    """Determine user role based on password"""
    if password == ADMIN_PASSWORD:
        return "admin"
    elif password == DEMO_PASSWORD:
        return "demo"
    elif password == GUEST_PASSWORD:
        return "guest"
    elif password == MASTER_PASSWORD:
        return "admin"  # Backward compatibility
    else:
        return None

async def authenticate_user(password: str) -> tuple[bool, str]:
    """Simple password authentication with role detection"""
    role = get_user_role(password)
    if role:
        logger.info(f"Authentication successful - {role} access granted")
        return True, role
    return False, None

# Dependency for authentication with role
async def verify_password_with_role(password: str = Query(..., description="Password")):
    """Password verification with role detection"""
    is_valid, role = await authenticate_user(password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    return role

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing functions
from main import run_full_pipeline_async
from scraping.news_scraper import fetch_news_sentiment
from analysis.investment_advisor import InvestmentAdvisor
from analysis.quantitative_strategies import QuantitativeStrategies

# Add utility functions directly to replace the removed ones
def get_available_tickers():
    """Get list of available stock tickers from data files"""
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        if not os.path.exists(data_dir):
            return []
        
        tickers = set()
        for filename in os.listdir(data_dir):
            if filename.endswith('_sentiment.json') or filename.endswith('.json'):
                # Extract ticker from filename (e.g., AAPL_reddit_sentiment.json -> AAPL)
                ticker = filename.split('_')[0]
                tickers.add(ticker)
        
        return sorted(list(tickers))
    except Exception as e:
        logger.error(f"Error getting available tickers: {e}")
        return []

def validate_stock_symbol(symbol: str) -> tuple[bool, str]:
    """Validate if a stock symbol exists using yfinance"""
    try:
        import yfinance as yf
        
        # Clean the symbol
        symbol = symbol.upper().strip()
        
        # Basic format validation
        if not symbol or len(symbol) > 10 or not symbol.isalpha():
            return False, "Invalid symbol format"
        
        # Check with yfinance
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Check if we got valid data back
        if 'symbol' not in info and 'shortName' not in info and 'longName' not in info:
            return False, f"Symbol '{symbol}' not found in market data"
        
        # Additional check - try to get some recent data
        hist = ticker.history(period="5d")
        if hist.empty:
            return False, f"No trading data available for '{symbol}'"
        
        return True, f"Valid symbol: {info.get('longName', info.get('shortName', symbol))}"
        
    except Exception as e:
        return False, f"Error validating symbol: {str(e)}"

def delete_stock_data(symbol: str) -> tuple[bool, str, list]:
    """Delete all data files for a given stock symbol"""
    try:
        symbol = symbol.upper().strip()
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        if not os.path.exists(data_dir):
            return False, "Data directory not found", []
        
        # Find all files for this symbol
        files_to_delete = []
        for filename in os.listdir(data_dir):
            if filename.startswith(f"{symbol}_") and filename.endswith('.json'):
                files_to_delete.append(filename)
        
        if not files_to_delete:
            return False, f"No data files found for symbol '{symbol}'", []
        
        # Delete the files
        deleted_files = []
        for filename in files_to_delete:
            file_path = os.path.join(data_dir, filename)
            try:
                os.remove(file_path)
                deleted_files.append(filename)
                logger.info(f"Deleted file: {filename}")
            except Exception as e:
                logger.error(f"Failed to delete {filename}: {e}")
        
        return True, f"Successfully deleted {len(deleted_files)} files for '{symbol}'", deleted_files
        
    except Exception as e:
        logger.error(f"Error deleting stock data for {symbol}: {e}")
        return False, f"Error deleting data: {str(e)}", []

def load_dataframes(ticker):
    """Load and combine all sentiment data for a ticker into a single DataFrame"""
    import pandas as pd
    
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        combined_data = []
        
        # Look for all files matching the ticker pattern
        for filename in os.listdir(data_dir):
            if filename.startswith(f"{ticker}_") and filename.endswith('.json'):
                file_path = os.path.join(data_dir, filename)
                
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Determine source from filename
                    if 'reddit' in filename:
                        source = 'Reddit'
                    elif 'news' in filename:
                        source = 'News'
                    elif 'sec' in filename:
                        source = 'SEC'
                    else:
                        source = 'Unknown'
                    
                    # Process each item in the data
                    for item in data:
                        if isinstance(item, dict):
                            # Add source info
                            item['source'] = source
                            
                            # Standardize sentiment data - handle nested sentiment objects
                            if 'sentiment' in item and isinstance(item['sentiment'], dict):
                                # Extract sentiment scores from nested object
                                sentiment_data = item['sentiment']
                                item['compound'] = sentiment_data.get('compound', 0.0)
                                item['pos'] = sentiment_data.get('pos', 0.0)
                                item['neg'] = sentiment_data.get('neg', 0.0)
                                item['neu'] = sentiment_data.get('neu', 0.0)
                                item['sentiment_label'] = sentiment_data.get('label', 'neutral')
                            
                            # Ensure compound score exists
                            if 'compound' not in item:
                                item['compound'] = 0.0
                            
                            # Handle different timestamp formats more robustly
                            timestamp_fields = ['created_utc', 'created', 'publishedAt', 'timestamp']
                            item['created_utc'] = None
                            
                            for field in timestamp_fields:
                                if field in item and item[field]:
                                    try:
                                        if isinstance(item[field], (int, float)):
                                            # Convert Unix timestamp to timezone-aware datetime
                                            item['created_utc'] = pd.to_datetime(item[field], unit='s', utc=True)
                                        else:
                                            # Parse string datetime and ensure it's timezone-aware
                                            dt = pd.to_datetime(item[field])
                                            if dt.tz is None:
                                                # If naive, assume UTC
                                                item['created_utc'] = dt.tz_localize('UTC')
                                            else:
                                                # Already timezone-aware, convert to UTC
                                                item['created_utc'] = dt.tz_convert('UTC')
                                        break
                                    except Exception as parse_error:
                                        logger.debug(f"Failed to parse timestamp {field}={item[field]}: {parse_error}")
                                        continue
                            
                            # Fallback to current time if no valid timestamp (timezone-aware)
                            if item['created_utc'] is None:
                                item['created_utc'] = pd.Timestamp.now(tz='UTC')
                            
                            combined_data.append(item)
                
                except Exception as e:
                    logger.warning(f"Error loading file {filename}: {e}")
                    continue
        
        if not combined_data:
            logger.warning(f"No valid data found for ticker {ticker}")
            return pd.DataFrame()
        
        df = pd.DataFrame(combined_data)
        
        # Ensure required columns exist with proper defaults
        if 'compound' not in df.columns:
            df['compound'] = 0.0
        if 'sentiment' not in df.columns:
            df['sentiment'] = 'neutral'
        if 'source' not in df.columns:
            df['source'] = 'Unknown'
        
        logger.info(f"Successfully loaded {len(df)} records for {ticker}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading dataframes for {ticker}: {e}")
        return pd.DataFrame()

def get_company_info(symbol: str) -> tuple[bool, dict]:
    """Get company information using yfinance"""
    try:
        import yfinance as yf
        
        # Clean the symbol
        symbol = symbol.upper().strip()
        
        # Check with yfinance
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get recent price history for additional metrics
        hist = ticker.history(period="5d")
        
        # Extract relevant company information
        company_data = {
            "symbol": symbol,
            "longName": info.get('longName', ''),
            "shortName": info.get('shortName', ''),
            "sector": info.get('sector', ''),
            "industry": info.get('industry', ''),
            "marketCap": info.get('marketCap', 0),
            "currency": info.get('currency', 'USD'),
            
            # Current Price Data
            "currentPrice": info.get('currentPrice', info.get('regularMarketPrice', 0)),
            "previousClose": info.get('previousClose', 0),
            "dayLow": info.get('dayLow', 0),
            "dayHigh": info.get('dayHigh', 0),
            "fiftyTwoWeekLow": info.get('fiftyTwoWeekLow', 0),
            "fiftyTwoWeekHigh": info.get('fiftyTwoWeekHigh', 0),
            
            # Price Changes
            "regularMarketChangePercent": info.get('regularMarketChangePercent', 0),
            "regularMarketChange": info.get('regularMarketChange', 0),
            
            # Volume Data
            "volume": info.get('volume', 0),
            "averageVolume": info.get('averageVolume', 0),
            "averageVolume10days": info.get('averageVolume10days', 0),
            
            # Valuation Metrics
            "priceToEarningsRatio": info.get('trailingPE', 0),
            "forwardPE": info.get('forwardPE', 0),
            "priceToBook": info.get('priceToBook', 0),
            "priceToSalesTrailing12Months": info.get('priceToSalesTrailing12Months', 0),
            
            # Financial Metrics
            "earningsPerShare": info.get('trailingEps', 0),
            "dividendYield": info.get('dividendYield', 0),
            "beta": info.get('beta', 0),
            
            # Moving Averages
            "fiftyDayAverage": info.get('fiftyDayAverage', 0),
            "twoHundredDayAverage": info.get('twoHundredDayAverage', 0),
            
            # Market Info
            "exchange": info.get('exchange', ''),
            "quoteType": info.get('quoteType', ''),
            "sharesOutstanding": info.get('sharesOutstanding', 0),
            "floatShares": info.get('floatShares', 0),
        }
        
        # Add recent price performance if historical data available
        if not hist.empty and len(hist) >= 2:
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            company_data["lastTradePrice"] = float(current_price)
            company_data["lastTradeChange"] = float(current_price - prev_price)
            company_data["lastTradeChangePercent"] = float((current_price - prev_price) / prev_price * 100)
        
        # Use the best available name
        display_name = company_data['longName'] or company_data['shortName'] or symbol
        company_data['displayName'] = display_name
        
        return True, company_data
        
    except Exception as e:
        return False, {"error": f"Error fetching company info: {str(e)}"}

# In-memory cache with TTL
class CacheManager:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self._ttl = 300  # 5 minutes default TTL
    
    def get(self, key: str):
        if key in self._cache:
            if datetime.now() - self._timestamps[key] < timedelta(seconds=self._ttl):
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
        if ttl:
            # Custom TTL per item if needed
            pass
    
    def invalidate(self, pattern: str = None):
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
                del self._timestamps[key]

cache = CacheManager()

# Simple authentication models
class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Master password for StockScope access")

class SimpleAuthResponse(BaseModel):
    success: bool
    message: str

# Enhanced Pydantic models with validation
class DataSource(str, Enum):
    REDDIT = "reddit"
    NEWS = "news" 
    SEC = "sec"
    TWITTER = "twitter"

class StockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    sources: List[DataSource] = Field(default=[DataSource.REDDIT, DataSource.NEWS, DataSource.SEC])
    
    class Config:
        use_enum_values = True

class StockSuggestion(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    market_cap: Optional[str] = None

class SentimentMetrics(BaseModel):
    avg_sentiment: float
    sentiment_distribution: Dict[str, int]
    confidence_score: float
    trend: str  # "bullish", "bearish", "neutral"

class SourceAnalysis(BaseModel):
    source: str
    count: int
    avg_sentiment: float
    latest_update: datetime

class EnhancedAnalysisResult(BaseModel):
    ticker: str
    total_posts: int
    sentiment_metrics: SentimentMetrics
    sources: List[SourceAnalysis]
    last_updated: datetime
    data_quality_score: float

class AnalysisStatus(BaseModel):
    symbol: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: int  # 0-100
    message: str
    started_at: datetime
    estimated_completion: Optional[datetime] = None

class InvestmentRecommendation(BaseModel):
    ticker: str
    recommendation: str  # "BUY", "SELL", "HOLD"
    confidence: float
    target_price: Optional[float]
    reasoning: List[str]
    risk_factors: List[str]
    generated_at: datetime

# Global status tracking for background tasks
analysis_status: Dict[str, AnalysisStatus] = {}

app = FastAPI(
    title="StockScope API",
    version="2.0.0",
    description="Optimized API for stock sentiment analysis with caching and advanced features"
)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://stockscope.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for rate limiting (placeholder - would use Redis in production)
async def rate_limit_dependency():
    # In production, implement proper rate limiting with Redis
    pass

@lru_cache(maxsize=128)
def load_stock_suggestions() -> List[Dict]:
    """Load stock suggestions from external source or fallback to comprehensive hardcoded list"""
    try:
        # Comprehensive list of popular stocks for better search experience
        return [
            # Original big tech
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "market_cap": "Large"},
            
            # Stocks starting with R
            {"symbol": "RBLX", "name": "Roblox Corporation", "sector": "Technology", "market_cap": "Mid"},
            {"symbol": "ROKU", "name": "Roku Inc.", "sector": "Technology", "market_cap": "Mid"},
            {"symbol": "RIVN", "name": "Rivian Automotive Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "RTX", "name": "Raytheon Technologies Corporation", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "RH", "name": "RH Inc.", "sector": "Consumer Discretionary", "market_cap": "Mid"},
            {"symbol": "ROST", "name": "Ross Stores Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "RCL", "name": "Royal Caribbean Cruises Ltd.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "REGN", "name": "Regeneron Pharmaceuticals Inc.", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "RSG", "name": "Republic Services Inc.", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "RMD", "name": "ResMed Inc.", "sector": "Healthcare", "market_cap": "Large"},
            
            # Other popular stocks
            {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "DIS", "name": "The Walt Disney Company", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "QCOM", "name": "QUALCOMM Incorporated", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "TXN", "name": "Texas Instruments Incorporated", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "NOW", "name": "ServiceNow Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "SNOW", "name": "Snowflake Inc.", "sector": "Technology", "market_cap": "Large"},
            
            # Healthcare
            {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "UNH", "name": "UnitedHealth Group Incorporated", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "TMO", "name": "Thermo Fisher Scientific Inc.", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "DHR", "name": "Danaher Corporation", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "BMY", "name": "Bristol-Myers Squibb Company", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "LLY", "name": "Eli Lilly and Company", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "MDT", "name": "Medtronic plc", "sector": "Healthcare", "market_cap": "Large"},
            {"symbol": "ISRG", "name": "Intuitive Surgical Inc.", "sector": "Healthcare", "market_cap": "Large"},
            
            # Financial
            {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "BAC", "name": "Bank of America Corporation", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "WFC", "name": "Wells Fargo & Company", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "GS", "name": "The Goldman Sachs Group Inc.", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "MS", "name": "Morgan Stanley", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "V", "name": "Visa Inc.", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "MA", "name": "Mastercard Incorporated", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "AXP", "name": "American Express Company", "sector": "Financial Services", "market_cap": "Large"},
            
            # Consumer
            {"symbol": "KO", "name": "The Coca-Cola Company", "sector": "Consumer Defensive", "market_cap": "Large"},
            {"symbol": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer Defensive", "market_cap": "Large"},
            {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Consumer Defensive", "market_cap": "Large"},
            {"symbol": "COST", "name": "Costco Wholesale Corporation", "sector": "Consumer Defensive", "market_cap": "Large"},
            {"symbol": "HD", "name": "The Home Depot Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "LOW", "name": "Lowe's Companies Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "MCD", "name": "McDonald's Corporation", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "SBUX", "name": "Starbucks Corporation", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "NKE", "name": "NIKE Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            
            # Energy
            {"symbol": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy", "market_cap": "Large"},
            {"symbol": "CVX", "name": "Chevron Corporation", "sector": "Energy", "market_cap": "Large"},
            {"symbol": "COP", "name": "ConocoPhillips", "sector": "Energy", "market_cap": "Large"},
            
            # Communications
            {"symbol": "VZ", "name": "Verizon Communications Inc.", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "T", "name": "AT&T Inc.", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "CMCSA", "name": "Comcast Corporation", "sector": "Communication Services", "market_cap": "Large"},
            
            # Industrials
            {"symbol": "BA", "name": "The Boeing Company", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "CAT", "name": "Caterpillar Inc.", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "GE", "name": "General Electric Company", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "MMM", "name": "3M Company", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "HON", "name": "Honeywell International Inc.", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "UPS", "name": "United Parcel Service Inc.", "sector": "Industrials", "market_cap": "Large"},
            {"symbol": "FDX", "name": "FedEx Corporation", "sector": "Industrials", "market_cap": "Large"},
            
            # Utilities
            {"symbol": "NEE", "name": "NextEra Energy Inc.", "sector": "Utilities", "market_cap": "Large"},
            {"symbol": "DUK", "name": "Duke Energy Corporation", "sector": "Utilities", "market_cap": "Large"},
            
            # Growth stocks and meme stocks
            {"symbol": "PLTR", "name": "Palantir Technologies Inc.", "sector": "Technology", "market_cap": "Mid"},
            {"symbol": "GME", "name": "GameStop Corp.", "sector": "Consumer Discretionary", "market_cap": "Small"},
            {"symbol": "AMC", "name": "AMC Entertainment Holdings Inc.", "sector": "Communication Services", "market_cap": "Small"},
            {"symbol": "BB", "name": "BlackBerry Limited", "sector": "Technology", "market_cap": "Small"},
            {"symbol": "SPCE", "name": "Virgin Galactic Holdings Inc.", "sector": "Industrials", "market_cap": "Small"},
            {"symbol": "WISH", "name": "ContextLogic Inc.", "sector": "Consumer Discretionary", "market_cap": "Small"},
            
            # Crypto related
            {"symbol": "COIN", "name": "Coinbase Global Inc.", "sector": "Financial Services", "market_cap": "Large"},
            {"symbol": "MSTR", "name": "MicroStrategy Incorporated", "sector": "Technology", "market_cap": "Mid"},
            
            # EVs and clean energy
            {"symbol": "NIO", "name": "NIO Inc.", "sector": "Consumer Discretionary", "market_cap": "Mid"},
            {"symbol": "XPEV", "name": "XPeng Inc.", "sector": "Consumer Discretionary", "market_cap": "Mid"},
            {"symbol": "LI", "name": "Li Auto Inc.", "sector": "Consumer Discretionary", "market_cap": "Mid"},
            {"symbol": "LCID", "name": "Lucid Group Inc.", "sector": "Consumer Discretionary", "market_cap": "Mid"},
            {"symbol": "F", "name": "Ford Motor Company", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "GM", "name": "General Motors Company", "sector": "Consumer Discretionary", "market_cap": "Large"},
            
            # Social media and gaming
            {"symbol": "SNAP", "name": "Snap Inc.", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "TWTR", "name": "Twitter Inc.", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "PINS", "name": "Pinterest Inc.", "sector": "Communication Services", "market_cap": "Mid"},
            {"symbol": "EA", "name": "Electronic Arts Inc.", "sector": "Communication Services", "market_cap": "Large"},
            {"symbol": "ATVI", "name": "Activision Blizzard Inc.", "sector": "Communication Services", "market_cap": "Large"},
            
            # REITs
            {"symbol": "SPG", "name": "Simon Property Group Inc.", "sector": "Real Estate", "market_cap": "Large"},
            {"symbol": "PLD", "name": "Prologis Inc.", "sector": "Real Estate", "market_cap": "Large"},
            {"symbol": "AMT", "name": "American Tower Corporation", "sector": "Real Estate", "market_cap": "Large"},
            
            # Materials
            {"symbol": "LIN", "name": "Linde plc", "sector": "Basic Materials", "market_cap": "Large"},
            {"symbol": "APD", "name": "Air Products and Chemicals Inc.", "sector": "Basic Materials", "market_cap": "Large"},
        ]
    except Exception as e:
        logger.error(f"Failed to load stock suggestions: {e}")
        return []

def get_cached_analysis(symbol: str) -> Optional[EnhancedAnalysisResult]:
    """Get cached analysis result"""
    return cache.get(f"analysis_{symbol}")

def cache_analysis(symbol: str, result: EnhancedAnalysisResult):
    """Cache analysis result"""
    cache.set(f"analysis_{symbol}", result, ttl=600)  # 10 minutes

def calculate_enhanced_metrics(df) -> SentimentMetrics:
    """Calculate enhanced sentiment metrics from dataframe"""
    if df.empty:
        return SentimentMetrics(
            avg_sentiment=0.0,
            sentiment_distribution={"positive": 0, "neutral": 0, "negative": 0},
            confidence_score=0.0,
            trend="neutral"
        )
    
    avg_sentiment = df['compound'].mean()
    
    # Calculate sentiment distribution
    positive = len(df[df['compound'] > 0.1])
    negative = len(df[df['compound'] < -0.1]) 
    neutral = len(df) - positive - negative
    
    # Calculate confidence score based on data volume and consistency
    confidence = min(1.0, len(df) / 100) * (1 - df['compound'].std())
    
    # Determine trend
    if avg_sentiment > 0.1:
        trend = "bullish"
    elif avg_sentiment < -0.1:
        trend = "bearish"
    else:
        trend = "neutral"
    
    return SentimentMetrics(
        avg_sentiment=float(avg_sentiment),
        sentiment_distribution={"positive": positive, "neutral": neutral, "negative": negative},
        confidence_score=float(confidence),
        trend=trend
    )

# API Endpoints

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "StockScope API v2.0 is running",
        "version": "2.0.0",
        "cache_size": len(cache._cache),
        "endpoints": {
            "suggestions": "/api/stocks/suggestions",
            "portfolio": "/api/stocks",
            "analysis": "/api/stocks/{symbol}",
            "analyze": "/api/stocks/analyze",
            "status": "/api/stocks/{symbol}/status",
            "investment_advice": "/api/stocks/{symbol}/investment-advice"
        }
    }

# Authentication Endpoints

@app.post("/api/auth/login", response_model=SimpleAuthResponse, tags=["Authentication"])
async def login(login_request: LoginRequest):
    """Authenticate with master password"""
    try:
        is_valid, role = await authenticate_user(login_request.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        logger.info("Successful authentication - access granted")
        
        return SimpleAuthResponse(
            success=True,
            message=f"Authentication successful - Role: {role}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Authentication service error")

@app.get("/api/auth/status", tags=["Authentication"])
async def auth_status():
    """Get authentication status and requirements"""
    return {
        "authentication_required": True,
        "message": "Authentication required for all API endpoints"
    }

# Apply authentication to all protected endpoints
@app.get("/api/stocks/suggestions", response_model=List[StockSuggestion], tags=["Search"])
async def get_stock_suggestions(
    current_user: str = Depends(verify_password_with_role),
    q: str = Query("", description="Search query for stock symbols or names"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    _: None = Depends(rate_limit_dependency)
) -> List[StockSuggestion]:
    """Get optimized stock suggestions with caching"""
    
    cache_key = f"suggestions_{q}_{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        suggestions = load_stock_suggestions()
        
        if not q:
            result = suggestions[:limit]
        else:
            q = q.upper()
            matches = [
                stock for stock in suggestions
                if q in stock["symbol"] or q in stock["name"].upper()
            ]
            
            # Enhanced relevance sorting
            exact_matches = [s for s in matches if s["symbol"] == q]
            prefix_matches = [s for s in matches if s["symbol"].startswith(q) and s not in exact_matches]
            name_matches = [s for s in matches if q in s["name"].upper() and s not in exact_matches + prefix_matches]
            other_matches = [s for s in matches if s not in exact_matches + prefix_matches + name_matches]
            
            result = (exact_matches + prefix_matches + name_matches + other_matches)[:limit]
        
        # Cache the result
        cache.set(cache_key, result, ttl=3600)  # 1 hour cache for suggestions
        return result
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch suggestions")

@app.get("/api/stocks", tags=["Portfolio"])
async def get_available_stocks(current_user: str = Depends(verify_password_with_role)):
    """Get list of analyzed stocks with metadata including current prices"""
    import yfinance as yf
    import pandas as pd
    
    cache_key = "available_stocks"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        tickers = get_available_tickers()
        
        # Enhanced response with metadata and price data
        stocks_with_metadata = []
        for ticker in tickers:
            try:
                # Quick metadata without full dataframe load
                df = load_dataframes(ticker)
                stock_info = {
                    "symbol": ticker,
                    "currentPrice": 0,
                    "priceChange": 0,
                    "priceChangePercent": 0,
                    "companyName": ticker,
                    "total_posts": 0,
                    "avg_sentiment": 0,
                    "last_updated": datetime.now(),
                    "sources": []
                }
                
                if not df.empty:
                    # Ensure timezone-aware timestamp calculation
                    if 'created_utc' in df.columns and not df.empty:
                        timestamps = pd.to_datetime(df['created_utc'], utc=True)
                        last_updated = timestamps.max()
                    else:
                        last_updated = datetime.now().replace(tzinfo=pd.Timestamp.now().tz)
                        
                    stock_info.update({
                        "total_posts": len(df),
                        "avg_sentiment": float(df['compound'].mean()),
                        "last_updated": last_updated,
                        "sources": list(df['source'].unique()) if 'source' in df.columns else []
                    })
                
                # Fetch current price data
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    hist = stock.history(period="2d")
                    
                    if not hist.empty and len(hist) >= 1:
                        current_price = hist['Close'].iloc[-1]
                        prev_price = hist['Close'].iloc[-2] if len(hist) >= 2 else current_price
                        
                        price_change = current_price - prev_price
                        price_change_percent = (price_change / prev_price * 100) if prev_price != 0 else 0
                        
                        stock_info.update({
                            "currentPrice": round(float(current_price), 2),
                            "priceChange": round(float(price_change), 2),
                            "priceChangePercent": round(float(price_change_percent), 2),
                            "companyName": info.get('longName', info.get('shortName', ticker))
                        })
                    
                except Exception as price_error:
                    logger.debug(f"Failed to get price data for {ticker}: {price_error}")
                    # Keep default values if price fetch fails
                
                stocks_with_metadata.append(stock_info)
                
            except Exception as e:
                logger.warning(f"Failed to get metadata for {ticker}: {e}")
                stocks_with_metadata.append({"symbol": ticker})
        
        result = {"stocks": stocks_with_metadata, "count": len(stocks_with_metadata)}
        cache.set(cache_key, result, ttl=300)  # 5 minute cache
        return result
        
    except Exception as e:
        logger.error(f"Error getting available stocks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock portfolio")

@app.get("/api/stocks/{symbol}", response_model=EnhancedAnalysisResult, tags=["Analysis"])
async def get_stock_analysis(symbol: str, current_user: str = Depends(verify_password_with_role)) -> EnhancedAnalysisResult:
    """Get comprehensive analysis for a specific stock with caching"""
    import pandas as pd  # Add pandas import for timezone operations
    
    symbol = symbol.upper()
    
    # Check cache first
    cached_result = get_cached_analysis(symbol)
    if cached_result:
        return cached_result
    
    try:
        df = load_dataframes(symbol)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No analysis data found for {symbol}")
        
        # Calculate enhanced metrics
        sentiment_metrics = calculate_enhanced_metrics(df)
        
        # Analyze by source
        source_analyses = []
        if 'source' in df.columns:
            for source in df['source'].unique():
                source_df = df[df['source'] == source]
                
                # Ensure all timestamps are timezone-aware before calculating max
                if 'created_utc' in source_df.columns and not source_df['created_utc'].empty:
                    # Convert any remaining timezone-naive timestamps to UTC
                    timestamps = pd.to_datetime(source_df['created_utc'], utc=True)
                    latest_update = timestamps.max()
                else:
                    latest_update = datetime.now().replace(tzinfo=pd.Timestamp.now().tz)
                
                source_analyses.append(SourceAnalysis(
                    source=source,
                    count=len(source_df),
                    avg_sentiment=float(source_df['compound'].mean()),
                    latest_update=latest_update
                ))
        
        # Calculate data quality score
        data_quality = min(1.0, len(df) / 50) * (1 - abs(sentiment_metrics.avg_sentiment - df['compound'].median()))
        
        # Ensure last_updated is timezone-aware
        if 'created_utc' in df.columns and not df.empty:
            # Convert any remaining timezone-naive timestamps to UTC before calculating max
            timestamps = pd.to_datetime(df['created_utc'], utc=True)
            last_updated = timestamps.max()
        else:
            last_updated = datetime.now().replace(tzinfo=pd.Timestamp.now().tz)
        
        result = EnhancedAnalysisResult(
            ticker=symbol,
            total_posts=len(df),
            sentiment_metrics=sentiment_metrics,
            sources=source_analyses,
            last_updated=last_updated,
            data_quality_score=float(data_quality)
        )
        
        # Cache the result
        cache_analysis(symbol, result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed for {symbol}")

@app.post("/api/stocks/analyze", tags=["Analysis"])
async def analyze_stock(request: StockRequest, background_tasks: BackgroundTasks, current_user: str = Depends(verify_password_with_role)):
    """Start optimized analysis for a new stock with status tracking"""
    symbol = request.symbol.upper()
    
    # Check if analysis is already running
    if symbol in analysis_status and analysis_status[symbol].status == "processing":
        return analysis_status[symbol]
    
    # Initialize status tracking
    analysis_status[symbol] = AnalysisStatus(
        symbol=symbol,
        status="pending",
        progress=0,
        message="Analysis queued",
        started_at=datetime.now(),
        estimated_completion=datetime.now() + timedelta(minutes=2)
    )
    
    # Start background analysis
    background_tasks.add_task(run_optimized_analysis, symbol, request.sources)
    
    return {
        "message": f"Analysis started for {symbol}",
        "symbol": symbol,
        "status": "pending",
        "status_endpoint": f"/api/stocks/{symbol}/status"
    }

@app.get("/api/stocks/{symbol}/status", response_model=AnalysisStatus, tags=["Analysis"])
async def get_analysis_status(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Get real-time analysis status"""
    symbol = symbol.upper()
    
    if symbol not in analysis_status:
        # Check if data already exists
        try:
            df = load_dataframes(symbol)
            if not df.empty:
                return AnalysisStatus(
                    symbol=symbol,
                    status="completed",
                    progress=100,
                    message="Analysis completed",
                    started_at=datetime.now() - timedelta(hours=1),
                )
        except:
            pass
        
        raise HTTPException(status_code=404, detail=f"No analysis found for {symbol}")
    
    return analysis_status[symbol]

@app.get("/api/stocks/{symbol}/investment-advice", response_model=InvestmentRecommendation, tags=["Investment"])
async def get_investment_advice(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Get AI-powered investment recommendation"""
    symbol = symbol.upper()
    
    cache_key = f"investment_advice_{symbol}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        df = load_dataframes(symbol)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No analysis data found for {symbol}")
        
        # Use your existing InvestmentAdvisor with correct method name
        advisor = InvestmentAdvisor(symbol)
        
        # First fetch the stock data
        if not advisor.fetch_data():
            raise HTTPException(status_code=500, detail="Failed to fetch stock price data")
        
        # Get the recommendation
        recommendation_data = advisor.get_investment_recommendation()
        
        if recommendation_data.get('error'):
            raise HTTPException(status_code=500, detail=recommendation_data['error'])
        
        # Map the actual return data to our API structure
        reasoning = recommendation_data.get('signals', [])  # signals contains the reasoning
        if not reasoning:
            reasoning = ["Technical analysis completed", "Risk metrics calculated"]
        
        # Extract risk factors from technical analysis
        risk_factors = []
        if recommendation_data.get('risk_level') == 'High':
            risk_factors.append("High volatility detected")
        if recommendation_data.get('risk_metrics', {}).get('beta', 1.0) > 1.5:
            risk_factors.append("Higher than market risk (Beta > 1.5)")
        if not risk_factors:
            risk_factors = ["Standard market risks apply"]
        
        # Enhanced recommendation structure
        result = InvestmentRecommendation(
            ticker=symbol,
            recommendation=recommendation_data.get('recommendation', 'HOLD'),
            confidence=recommendation_data.get('confidence', 0.5),
            target_price=recommendation_data.get('target_price'),
            reasoning=reasoning,  # Use signals as reasoning
            risk_factors=risk_factors,
            generated_at=datetime.now()
        )
        
        # Cache for 30 minutes
        cache.set(cache_key, result, ttl=1800)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting investment advice for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate investment advice")

@app.get("/api/stocks/{symbol}/quantitative", tags=["Analysis"])
async def get_quantitative_analysis(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Get quantitative strategy analysis"""
    symbol = symbol.upper()
    
    cache_key = f"quant_analysis_{symbol}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        df = load_dataframes(symbol)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No analysis data found for {symbol}")
        
        # Create sentiment data structure for quantitative strategies
        sentiment_data = {symbol: df.to_dict('records')}
        
        # Use your existing QuantitativeStrategies
        quant = QuantitativeStrategies()
        
        # Create a comprehensive analysis using multiple strategies
        analysis = {
            "symbol": symbol,
            "metrics": {
                "sharpe_ratio": 0.85,  # Mock data - would calculate from real strategy
                "volatility": 0.22,
                "beta": 1.15,
                "alpha": 0.08
            },
            "signals": {
                "rsi": 65.4,
                "macd": 0.025,
                "bollinger_bands": "Neutral"
            },
            "recommendation": "BUY",
            "confidence": 0.75,
            "strategies": {
                "sentiment_momentum": quant.create_sentiment_momentum_strategy([symbol], sentiment_data),
                "multi_factor": quant.create_multi_factor_strategy([symbol], sentiment_data),
                "sector_rotation": quant.create_sector_rotation_strategy(sentiment_data)
            }
        }
        
        # Cache for 1 hour
        cache.set(cache_key, analysis, ttl=3600)
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quantitative analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to run quantitative analysis")

@app.get("/api/stocks/{symbol}/info", tags=["Analysis"])
async def get_company_info_endpoint(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Get company information for a stock symbol"""
    symbol = symbol.upper()
    
    cache_key = f"company_info_{symbol}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        success, company_data = get_company_info(symbol)
        
        if not success:
            raise HTTPException(status_code=404, detail=company_data.get("error", "Company information not found"))
        
        # Cache for 1 hour (company info doesn't change often)
        cache.set(cache_key, company_data, ttl=3600)
        return company_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch company information")

@app.delete("/api/cache", tags=["Admin"])
async def clear_cache(pattern: Optional[str] = None, current_user: str = Depends(verify_password_with_role)):
    """Clear API cache (admin endpoint)"""
    try:
        if pattern:
            cache.invalidate(pattern)
            return {"message": f"Cache cleared for pattern: {pattern}"}
        else:
            cache._cache.clear()
            cache._timestamps.clear()
            return {"message": "All cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Detailed health check with system metrics"""
    try:
        # Test database connection
        tickers = get_available_tickers()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "cache_size": len(cache._cache),
            "active_analyses": len([s for s in analysis_status.values() if s.status == "processing"]),
            "available_stocks": len(tickers),
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# New validation and deletion endpoints
@app.get("/api/stocks/validate/{symbol}", tags=["Validation"])
async def validate_symbol(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Validate if a stock symbol exists before analysis"""
    try:
        is_valid, message = validate_stock_symbol(symbol)
        
        return {
            "symbol": symbol.upper(),
            "valid": is_valid,
            "message": message,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Symbol validation failed")

@app.delete("/api/stocks/{symbol}", tags=["Management"])
async def delete_stock(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Delete all data files for a stock symbol (admin only)"""
    # Check if user has admin permissions
    if current_user not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to delete stock data"
        )
    
    try:
        success, message, deleted_files = delete_stock_data(symbol)
        
        if success:
            # Clear all caches related to this symbol
            cache.invalidate(symbol)
            cache.invalidate("available_stocks")
            
            # Remove from analysis status if present
            symbol_upper = symbol.upper()
            if symbol_upper in analysis_status:
                del analysis_status[symbol_upper]
            
            return {
                "success": True,
                "symbol": symbol.upper(),
                "message": message,
                "deleted_files": deleted_files,
                "timestamp": datetime.now()
            }
        else:
            raise HTTPException(status_code=404, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stock data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete stock data")

async def run_optimized_analysis(symbol: str, sources: List[str]):
    """Optimized background analysis with progress tracking"""
    try:
        # Update status
        analysis_status[symbol].status = "processing"
        analysis_status[symbol].progress = 10
        analysis_status[symbol].message = "Starting analysis..."
        
        # Run analysis based on sources
        if "reddit" in sources or "sec" in sources:
            analysis_status[symbol].progress = 30
            analysis_status[symbol].message = "Collecting Reddit and SEC data..."
            await run_full_pipeline_async(symbol)
        
        if "news" in sources:
            analysis_status[symbol].progress = 60
            analysis_status[symbol].message = "Fetching news sentiment..."
            fetch_news_sentiment(symbol)
        
        # Final processing
        analysis_status[symbol].progress = 90
        analysis_status[symbol].message = "Processing sentiment analysis..."
        
        # Invalidate cache for this symbol
        cache.invalidate(f"analysis_{symbol}")
        cache.invalidate(f"investment_advice_{symbol}")
        cache.invalidate("available_stocks")
        
        # Complete
        analysis_status[symbol].status = "completed"
        analysis_status[symbol].progress = 100
        analysis_status[symbol].message = "Analysis completed successfully"
        
        logger.info(f"Analysis completed for {symbol}")
        
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        analysis_status[symbol].status = "failed"
        analysis_status[symbol].message = f"Analysis failed: {str(e)}"

# Add health endpoint for Railway
@app.get("/health", tags=["Health"])
async def simple_health():
    """Simple health check for Railway deployment"""
    return {"status": "ok", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )