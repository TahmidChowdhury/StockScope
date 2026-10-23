"""
Optimized FastAPI backend for StockScope with caching, proper error handling, efficient data access, and simple authentication
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, status
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
import sys
import os
import asyncio
import json
import math
from datetime import datetime, timedelta, timezone
from time import monotonic
from threading import RLock
from functools import lru_cache
import logging
from enum import Enum
from dotenv import load_dotenv
from backend.core.auth import (
    authenticate_user,
    get_access_token_expire_minutes,
    create_access_token,
    validate_auth_config,
    verify_password_with_role,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate auth-related environment variables at startup
validate_auth_config()

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing functions
from main import run_full_pipeline_async
from scraping.enhanced_news_scraper import fetch_enhanced_news_with_results
from backend.services.research import (
    data_directory, load_evidence, latest_timestamp, freshness,
    sentiment_metrics, source_analyses, filing_events, normalized_symbol, evidence_freshness,
    parse_timestamp, repository, list_saved_symbols, delete_saved_research,
    saved_news, read_records_reference, save_records,
)

# Import fundamentals router
from backend.routers.fundamentals import router as fundamentals_router
from backend.routers.trading import router as trading_router
from backend.routers.sentiment_lab import router as sentiment_lab_router
from backend.routers.valuation import router as valuation_router


def finite_number(value) -> Optional[float]:
    """Keep observed zero distinct from absent or nonfinite provider values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def latest_daily_close(history):
    """Use the latest observed close when a provider appends an incomplete row.

    A change requires the immediately preceding provider row. Do not bridge a
    missing session and label its multi-session move as a daily change.
    """
    if history.empty or "Close" not in history.columns:
        return None, None, None
    for position in range(len(history) - 1, -1, -1):
        current = finite_number(history["Close"].iloc[position])
        if current is not None:
            previous = finite_number(history["Close"].iloc[position - 1]) if position else None
            return current, previous, parse_timestamp(history.index[position])
    return None, None, None


# Add utility functions directly to replace the removed ones
def get_available_tickers():
    """Read the shared watchlist from the configured authoritative storage."""
    return list_saved_symbols()

def validate_stock_symbol(symbol: str) -> tuple[bool, str]:
    """Validate if a stock symbol exists using yfinance"""
    try:
        symbol = normalized_symbol(symbol)
    except ValueError as exc:
        return False, str(exc)
    try:
        import yfinance as yf
        
        # Check with yfinance
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Check if we got valid data back
        if 'symbol' not in info and 'shortName' not in info and 'longName' not in info:
            return False, f"Symbol '{symbol}' not found in market data"
        
        # Additional check - try to get some recent data
        hist = ticker.history(period="5d", timeout=10)
        if hist.empty:
            return False, f"No trading data available for '{symbol}'"
        
        return True, f"Valid symbol: {info.get('longName', info.get('shortName', symbol))}"
        
    except Exception as e:
        return False, f"Error validating symbol: {str(e)}"

def delete_stock_data(symbol: str) -> tuple[bool, str, list]:
    removed = delete_saved_research(symbol)
    return bool(removed), (f"Deleted saved research for {symbol}" if removed else "No saved research found"), removed

def load_dataframes(ticker):
    """Read stored evidence, retaining original dates and excluding SEC template scores."""
    return load_evidence(ticker)

def get_company_info(symbol: str) -> tuple[bool, dict]:
    """Return observed provider metrics without inventing values or quote dates."""
    try:
        import yfinance as yf

        symbol = symbol.upper().strip()
        ticker = yf.Ticker(symbol)
        info = ticker.info
        numeric_fields = {
            "marketCap": "marketCap",
            "previousClose": "previousClose",
            "dayLow": "dayLow",
            "dayHigh": "dayHigh",
            "fiftyTwoWeekLow": "fiftyTwoWeekLow",
            "fiftyTwoWeekHigh": "fiftyTwoWeekHigh",
            "regularMarketChangePercent": "regularMarketChangePercent",
            "regularMarketChange": "regularMarketChange",
            "volume": "volume",
            "averageVolume": "averageVolume",
            "averageVolume10days": "averageVolume10days",
            "priceToEarningsRatio": "trailingPE",
            "forwardPE": "forwardPE",
            "priceToBook": "priceToBook",
            "priceToSalesTrailing12Months": "priceToSalesTrailing12Months",
            "earningsPerShare": "trailingEps",
            "beta": "beta",
            "fiftyDayAverage": "fiftyDayAverage",
            "twoHundredDayAverage": "twoHundredDayAverage",
            "sharesOutstanding": "sharesOutstanding",
            "floatShares": "floatShares",
        }
        company_data = {
            "symbol": symbol,
            **{key: info.get(key) for key in (
                "longName", "shortName", "sector", "industry", "currency", "exchange", "quoteType",
            )},
            **{key: finite_number(info.get(source)) for key, source in numeric_fields.items()},
            "currentPrice": finite_number(info.get("currentPrice")),
            "lastTradePrice": None,
            "lastTradeChange": None,
            "lastTradeChangePercent": None,
            "history_as_of": None,
        }
        if company_data["currentPrice"] is None:
            company_data["currentPrice"] = finite_number(info.get("regularMarketPrice"))

        # Yahoo's generic dividendYield can be percentage points (e.g. 0.31
        # for 0.31%). Use explicit trailing annual observations, expressed as
        # a decimal, rather than guessing units from their magnitude.
        annual_dividend = finite_number(info.get("trailingAnnualDividendRate"))
        trailing_yield = finite_number(info.get("trailingAnnualDividendYield"))
        quote_price = company_data["currentPrice"]
        company_data["dividendYield"] = None
        company_data["dividendYieldBasis"] = None
        if annual_dividend is not None and annual_dividend >= 0 and quote_price is not None and quote_price > 0:
            company_data["dividendYield"] = finite_number(annual_dividend / quote_price)
            if company_data["dividendYield"] is not None:
                company_data["dividendYieldBasis"] = "trailing_annual_rate_over_quote"
        elif trailing_yield is not None and trailing_yield >= 0:
            company_data["dividendYield"] = trailing_yield
            company_data["dividendYieldBasis"] = "provider_trailing_annual"

        # Quote time is supplied by the provider; fetching now does not make it current.
        quote_time = finite_number(info.get("regularMarketTime"))
        quote_as_of = parse_timestamp(quote_time) if quote_time is not None and quote_time > 0 else None
        company_data["quote_as_of"] = quote_as_of.isoformat() if quote_as_of else None
        company_data["retrieved_at"] = datetime.now(timezone.utc).isoformat()

        # Optional historical closes are separate from the latest quote. A history
        # failure should not discard available company metrics.
        try:
            hist = ticker.history(period="5d", timeout=10)
            current_price, previous_price, history_as_of = latest_daily_close(hist)
            if current_price is not None:
                company_data["lastTradePrice"] = current_price
                company_data["history_as_of"] = history_as_of.isoformat() if history_as_of else None
                if previous_price is not None:
                    change = finite_number(current_price - previous_price)
                    company_data["lastTradeChange"] = change
                    if change is not None and previous_price != 0:
                        company_data["lastTradeChangePercent"] = finite_number(change / previous_price * 100)
        except Exception:
            logger.warning("Historical company metrics unavailable for %s", symbol)

        company_data["displayName"] = company_data["longName"] or company_data["shortName"] or symbol
        return True, company_data
    except Exception as exc:
        return False, {"error": f"Error fetching company info: {str(exc)}"}

# In-memory cache with TTL
class CacheManager:
    def __init__(self):
        self._cache = {}
        self._expires = {}
        self._ttl = 300
        self._lock = RLock()

    def get(self, key: str):
        with self._lock:
            if key in self._cache and monotonic() < self._expires[key]:
                return self._cache[key]
            self._cache.pop(key, None)
            self._expires.pop(key, None)
            return None

    def set(self, key: str, value: Any, ttl: int = None):
        with self._lock:
            if len(self._cache) >= 512 and key not in self._cache:
                oldest = min(self._expires, key=self._expires.get)
                self._cache.pop(oldest, None)
                self._expires.pop(oldest, None)
            self._cache[key] = value
            self._expires[key] = monotonic() + (self._ttl if ttl is None else max(0, ttl))

    def invalidate(self, pattern: str = None):
        with self._lock:
            for key in list(self._cache):
                if pattern is None or pattern in key:
                    self._cache.pop(key, None)
                    self._expires.pop(key, None)

cache = CacheManager()

# Simple authentication models
class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Master password for StockScope access")

class SimpleAuthResponse(BaseModel):
    success: bool
    message: str
    role: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in_seconds: Optional[int] = None

# Enhanced Pydantic models with validation
class DataSource(str, Enum):
    REDDIT = "reddit"
    NEWS = "news" 
    SEC = "sec"
    SEC_FACTS = "sec_facts"
    TWITTER = "twitter"

class StockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9.-]{0,9}$", description="Stock symbol")
    sources: List[DataSource] = Field(default=[DataSource.NEWS, DataSource.SEC_FACTS], min_length=1, max_length=5)
    
    class Config:
        use_enum_values = True

class StockSuggestion(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    market_cap: Optional[str] = None

class SentimentMetrics(BaseModel):
    avg_sentiment: Optional[float] = None
    sentiment_distribution: Dict[str, int]
    trend: str
    sample_size: int
    method: str

class SourceAnalysis(BaseModel):
    source: str
    count: int
    avg_sentiment: Optional[float] = None
    latest_update: Optional[datetime] = None
    freshness: str
    unknown_timestamps: int

class EnhancedAnalysisResult(BaseModel):
    ticker: str
    total_posts: int
    sentiment_metrics: SentimentMetrics
    sources: List[SourceAnalysis]
    last_updated: Optional[datetime] = None
    source_as_of: Optional[datetime] = None
    freshness: str
    generated_at: datetime
    filings: List[Dict[str, Any]] = Field(default_factory=list)

class AnalysisStatus(BaseModel):
    symbol: str
    status: str
    progress: int
    message: str
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    run_id: Optional[str] = None

# Global status tracking for background tasks
analysis_status: Dict[str, AnalysisStatus] = {}
# Serialize admission and deletion across awaited storage calls in this worker.
_research_mutation_loop = None
_research_mutation_lock = None


def research_mutation_lock():
    global _research_mutation_loop, _research_mutation_lock
    loop = asyncio.get_running_loop()
    if _research_mutation_loop is not loop:
        _research_mutation_loop = loop
        _research_mutation_lock = asyncio.Lock()
    return _research_mutation_lock

@asynccontextmanager
async def lifespan(app):
    repo = repository()
    if repo is not None:
        await asyncio.to_thread(repo.check_ready)
        # This release supports one API process, not a distributed job queue.
        await asyncio.to_thread(repo.interrupt_active_runs)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="StockScope API",
    version="2.0.0",
    description="Optimized API for stock sentiment analysis with caching and advanced features"
)

@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request, exc):
    logger.error("Database operation failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Research storage is unavailable. Try again later."})


# Include fundamentals router with correct path prefix
app.include_router(fundamentals_router, prefix="/api/fundamentals", tags=["Fundamentals"])
app.include_router(trading_router, prefix="/api/trading", tags=["Paper trading"])
app.include_router(sentiment_lab_router, prefix="/api/sentiment-lab", tags=["Tone research"])
app.include_router(valuation_router, prefix="/api/valuation", tags=["Valuation research"])

# Enhanced CORS configuration with optional env overrides
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "")
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://stockscope.vercel.app",
    "https://stock-scope-green.vercel.app",
    "https://stock-scope-juj13l2pn-tahmids-projects-c2f4375b.vercel.app",
]

if frontend_origins_env:
    allowed_origins.extend([
        origin.strip() for origin in frontend_origins_env.split(",") if origin.strip()
    ])
#   allow_origin_regex=r"https://.*\.vercel\.app",

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicitly include OPTIONS
    allow_headers=["*"],
    expose_headers=["*"],
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
    return SentimentMetrics(**sentiment_metrics(df))

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
    """Authenticate with password and return bearer token."""
    try:
        
        # Additional validation
        if not login_request.password or len(login_request.password.strip()) == 0:
            logger.warning("Empty password provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password cannot be empty"
            )
        
        is_valid, role = await authenticate_user(login_request.password)
        if not is_valid:
            logger.warning("Authentication failed for provided password")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        logger.info(f"Successful authentication - {role} access granted")
        
        access_token = create_access_token(subject="stockscope_user", role=role)

        return SimpleAuthResponse(
            success=True,
            message="Authentication successful",
            role=role,
            access_token=access_token,
            token_type="bearer",
            expires_in_seconds=get_access_token_expire_minutes() * 60,
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
        "message": "Authentication required for all API endpoints",
        "preferred_method": "Authorization: Bearer <token>",
        "token_endpoint": "/api/auth/login",
        "legacy_password_query_supported": False,
    }

@app.get("/api/auth/session", tags=["Authentication"])
async def auth_session(current_user: str = Depends(verify_password_with_role)):
    """Verify a bearer session without modifying state."""
    return {"authenticated": True, "role": current_user}

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
def get_available_stocks(current_user: str = Depends(verify_password_with_role)):
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
                    "currentPrice": None,
                    "priceChange": None,
                    "priceChangePercent": None,
                    "price_as_of": None,
                    "companyName": ticker,
                    "total_posts": 0,
                    "avg_sentiment": None,
                    "last_updated": None,
                    "freshness": "unknown",
                    "sources": []
                }
                
                if not df.empty:
                    as_of = latest_timestamp(df)
                    stock_info.update({
                        "total_posts": len(df), "avg_sentiment": sentiment_metrics(df)["avg_sentiment"],
                        "last_updated": as_of, "freshness": evidence_freshness(df),
                        "sources": list(df['source'].unique()),
                    })

                # Fetch current price data
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    hist = stock.history(period="5d", timeout=10)
                    
                    if not hist.empty and len(hist) >= 1:
                        current_price, prev_price, price_as_of = latest_daily_close(hist)
                        price_change = price_change_percent = None
                        if current_price is not None and prev_price not in (None, 0):
                            price_change = finite_number(current_price - prev_price)
                            price_change_percent = finite_number((current_price / prev_price - 1) * 100)
                        
                        stock_info.update({
                            "currentPrice": round(current_price, 2) if current_price is not None else None,
                            "priceChange": round(price_change, 2) if price_change is not None else None,
                            "priceChangePercent": round(price_change_percent, 2) if price_change_percent is not None else None,
                            "companyName": info.get('longName', info.get('shortName', ticker)),
                            "price_as_of": price_as_of.isoformat() if price_as_of else None,
                            "price_basis": "latest_daily_close",
                        })
                    
                except Exception as price_error:
                    logger.debug(f"Failed to get price data for {ticker}: {price_error}")
                    # Keep default values if price fetch fails
                
                stocks_with_metadata.append(stock_info)
                
            except SQLAlchemyError:
                raise
            except Exception as e:
                logger.warning(f"Failed to get metadata for {ticker}: {e}")
                stocks_with_metadata.append({"symbol": ticker})
        
        result = {"stocks": stocks_with_metadata, "count": len(stocks_with_metadata)}
        cache.set(cache_key, result, ttl=300)  # 5 minute cache
        return result
        
    except SQLAlchemyError:
        raise
    except Exception:
        logger.error("Error getting available stocks")
        raise HTTPException(status_code=500, detail="Failed to fetch stock portfolio")

@app.get("/api/stocks/{symbol}", response_model=EnhancedAnalysisResult, tags=["Analysis"])
async def get_stock_analysis(symbol: str, current_user: str = Depends(verify_password_with_role)) -> EnhancedAnalysisResult:
    symbol = symbol.upper()
    cached_result = get_cached_analysis(symbol)
    if cached_result:
        return cached_result
    df = await asyncio.to_thread(load_dataframes, symbol)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No saved research data found for {symbol}")
    as_of = latest_timestamp(df)
    result = EnhancedAnalysisResult(
        ticker=symbol, total_posts=len(df), sentiment_metrics=calculate_enhanced_metrics(df),
        sources=source_analyses(df), last_updated=as_of, source_as_of=as_of,
        freshness=evidence_freshness(df), generated_at=datetime.now(timezone.utc), filings=filing_events(df),
    )
    cache_analysis(symbol, result)
    return result

async def reconcile_finished_job(symbol, repo):
    """Retry a terminal status write after a temporary database outage."""
    job = analysis_status.get(symbol)
    if repo is not None and job and job.run_id and job.status in {"completed", "partial", "failed"}:
        persisted = await asyncio.to_thread(repo.get_run, job.run_id)
        if persisted and persisted["status"] in {"pending", "processing"}:
            await persist_job(job)


@app.post("/api/stocks/analyze", status_code=202, tags=["Analysis"])
async def analyze_stock(request: StockRequest, background_tasks: BackgroundTasks, current_user: str = Depends(verify_password_with_role)):
    async with research_mutation_lock():
        symbol = normalized_symbol(request.symbol)
        existing = analysis_status.get(symbol)
        if existing and existing.status in {"pending", "processing"}:
            return existing
        active = sum(job.status in {"pending", "processing"} for job in analysis_status.values())
        if active >= 4:
            raise HTTPException(status_code=429, detail="Four refreshes are already running. Try again after one finishes.")
        repo = repository()
        await reconcile_finished_job(symbol, repo)
        if len(analysis_status) >= 128:
            finished = [key for key, job in analysis_status.items() if job.status not in {"pending", "processing"}]
            if finished:
                # Never evict the only terminal result before its durable write succeeds.
                await reconcile_finished_job(finished[0], repo)
                del analysis_status[finished[0]]
        if repo is not None:
            persisted = await asyncio.to_thread(repo.create_run, symbol, request.sources)
            job = AnalysisStatus.model_validate(persisted)
            if not persisted["created"]:
                return job
        else:
            job = AnalysisStatus(symbol=symbol, status="pending", progress=0, message="Research refresh queued", started_at=datetime.now(timezone.utc))
        analysis_status[symbol] = job
        background_tasks.add_task(run_optimized_analysis, symbol, request.sources)
        return {"message": f"Refresh started for {symbol}", "symbol": symbol, "status": "pending", "status_endpoint": f"/api/stocks/{symbol}/status"}

@app.get("/api/stocks/{symbol}/status", response_model=AnalysisStatus, tags=["Analysis"])
async def get_analysis_status(symbol: str, current_user: str = Depends(verify_password_with_role)):
    symbol = normalized_symbol(symbol)
    repo = repository()
    await reconcile_finished_job(symbol, repo)
    if repo is not None:
        persisted = await asyncio.to_thread(repo.get_latest_run, symbol)
        job = AnalysisStatus.model_validate(persisted) if persisted else None
    else:
        job = analysis_status.get(symbol)
    if job is None:
        raise HTTPException(status_code=404, detail="No refresh is tracked. Saved evidence does not prove a refresh completed.")
    return job

@app.get("/api/stocks/{symbol}/investment-advice", tags=["Research"])
async def get_investment_advice(symbol: str, current_user: str = Depends(verify_password_with_role)):
    """Compatibility route: provide evidence and research questions, never trade advice."""
    symbol = symbol.upper()
    df = await asyncio.to_thread(load_dataframes, symbol)
    sources = source_analyses(df)
    metrics = sentiment_metrics(df)
    events = filing_events(df)
    observations = [f"{len(df)} saved records across {len(sources)} sources.", f"{len(events)} SEC filings are listed as events; their contents have not been evaluated."]
    if metrics["sample_size"]:
        observations.append(f"Text tone is {metrics['trend']} across {metrics['sample_size']} scored news records.")
    return {
        "ticker": symbol, "status": "research_only",
        "summary": "Review the dated evidence and company fundamentals before forming an investment thesis." if not df.empty else "No saved evidence is available. Refresh this stock to collect research material.",
        "observations": observations,
        "limitations": ["Text sentiment measures wording, not company value or future returns.", "Coverage can be incomplete or stale; unknown publication dates remain unknown.", "SEC filing types alone do not establish positive or negative news.", "No validated strategy backtest, expected return, or probability of profit is available."],
        "sources": sources, "as_of": latest_timestamp(df), "generated_at": datetime.now(timezone.utc), "filings": events,
    }

@app.get("/api/stocks/{symbol}/quantitative", tags=["Analysis"])
async def get_quantitative_analysis(symbol: str, current_user: str = Depends(verify_password_with_role)):
    return {"symbol": symbol.upper(), "status": "unavailable", "reason": "Quantitative results are unavailable until calculations and backtests use verified price history, explicit assumptions, costs, and a benchmark.", "metrics": {}, "signals": {}, "strategies": {}}

@app.get("/api/stocks/{symbol}/info", tags=["Analysis"])
def get_company_info_endpoint(symbol: str, current_user: str = Depends(verify_password_with_role)):
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

@app.get("/api/stocks/{symbol}/news", tags=["Analysis"])
async def get_stock_news(symbol: str, limit: int = Query(default=20, ge=1, le=100), current_user: str = Depends(verify_password_with_role)):
    symbol = normalized_symbol(symbol)
    articles = await asyncio.to_thread(saved_news, symbol, limit)
    return {"ticker": symbol, "count": len(articles), "articles": articles}

@app.get("/api/stocks/{symbol}/price-history", tags=["Analysis"])
def get_price_history(
    symbol: str, 
    period: str = "1y",
    interval: str = "1d",
    current_user: str = Depends(verify_password_with_role)
):
    """Get historical price data for charting"""
    symbol = symbol.upper()
    
    cache_key = f"price_history_{symbol}_{period}_{interval}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        import yfinance as yf
        
        # Create ticker object
        ticker = yf.Ticker(symbol)
        
        # Get historical data
        hist = ticker.history(period=period, interval=interval, timeout=10)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="No historical data found")
        
        # Convert to list of dictionaries for frontend consumption
        price_data = []
        for date, row in hist.iterrows():
            prices = {name.lower(): finite_number(row[name]) for name in ('Open', 'High', 'Low', 'Close')}
            if any(value is None for value in prices.values()):
                continue
            volume = finite_number(row.get('Volume'))
            price_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "timestamp": int(date.timestamp() * 1000),  # JavaScript timestamp
                **{name: round(value, 2) for name, value in prices.items()},
                "volume": int(volume) if volume is not None and volume >= 0 else None
            })
        if not price_data:
            raise HTTPException(status_code=404, detail="No valid historical price data found")
        
        # A failed quote request must not discard independently retrieved history.
        try:
            info = ticker.info or {}
        except Exception:
            logger.debug("Quote unavailable for %s; returning historical bars", symbol)
            info = {}
        current_price = finite_number(info.get('regularMarketPrice'))
        if current_price is None:
            current_price = finite_number(info.get('currentPrice'))
        price_change = finite_number(info.get('regularMarketChange'))
        price_change_percent = finite_number(info.get('regularMarketChangePercent'))
        quote_time = parse_timestamp(info.get('regularMarketTime')) if current_price is not None else None
        historical_close = price_data[-1]['close']
        
        result = {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "currentPrice": current_price,
            "priceChange": price_change,
            "priceChangePercent": price_change_percent,
            "quote_as_of": quote_time.isoformat() if quote_time else None,
            "price_source": "Yahoo Finance",
            "lastHistoricalClose": historical_close,
            "lastHistoricalCloseDate": price_data[-1]['date'],
            "data": price_data
        }
        
        # Cache for 5 minutes (price data changes frequently)
        cache.set(cache_key, result, ttl=300)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch price history")

@app.delete("/api/cache", tags=["Admin"])
async def clear_cache(pattern: Optional[str] = None, current_user: str = Depends(verify_password_with_role)):
    """Clear API cache (admin endpoint)"""
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to clear cache")
    cache.invalidate(pattern)
    return {"message": "Cache cleared"}

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
def validate_symbol(symbol: str, current_user: str = Depends(verify_password_with_role)):
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
    async with research_mutation_lock():
        """Delete all data files for a stock symbol (admin only)"""
        # Check if user has admin permissions
        if current_user not in ["admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to delete stock data"
            )

        # Collectors publish files off the event loop. Deleting their state while they
        # run would allow a late write to silently restore a stock after deletion.
        try:
            symbol = normalized_symbol(symbol)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        active_job = analysis_status.get(symbol)
        repo = repository()
        await reconcile_finished_job(symbol, repo)
        if repo is not None:
            persisted = await asyncio.to_thread(repo.get_latest_run, symbol)
            active_job = AnalysisStatus.model_validate(persisted) if persisted else None
        if active_job and active_job.status in {"pending", "processing"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A refresh is still running for this stock. Wait for it to finish before deleting its data.",
            )
    
        try:
            success, message, deleted_files = await asyncio.to_thread(delete_stock_data, symbol)
        
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
        except SQLAlchemyError:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception:
            logger.error("Error deleting stock data for %s", symbol)
            raise HTTPException(status_code=500, detail="Failed to delete stock data")

def _produced_records(reference) -> int:
    if not reference:
        return 0
    try:
        payload = read_records_reference(reference)
        return sum(isinstance(record, dict) for record in payload)
    except (OSError, TypeError, ValueError):
        return 0


def _collect_news(symbol):
    # Preserve provider outcomes; NewsAPI's free plan is development-only.
    return fetch_enhanced_news_with_results(symbol)


async def persist_job(job):
    if job.run_id:
        repo = repository()
        await asyncio.to_thread(repo.update_run, job.run_id, status=job.status, progress=job.progress, message=job.message, providers=job.providers)


def _collect_sec_facts(symbol):
    from backend.services.sec_facts import collect_sec_facts
    result = collect_sec_facts(symbol)
    facts, filings = result.get("facts", []), result.get("filings", [])
    # Failed collection cannot replace the last successful financial snapshot.
    if facts:
        save_records(symbol, "sec_companyfacts", [result])
    if filings:
        save_records(symbol, "sec_filings", filings)
    return result


async def run_optimized_analysis(symbol: str, sources: List[str]):
    """Collect off the event loop and persist actual outcomes when DB-backed."""
    job = analysis_status[symbol]
    job.status, job.progress, job.message = "processing", 10, "Collecting dated research evidence"
    requested = list(dict.fromkeys(sources))
    try:
        await persist_job(job)
        for index, source in enumerate(requested):
            job.message = f"Collecting {source} evidence"
            await persist_job(job)
            try:
                if source == "sec_facts":
                    result = await asyncio.to_thread(_collect_sec_facts, symbol)
                    count = len(result.get("facts", [])) + len(result.get("filings", []))
                    outcome = result["status"]
                    if outcome == "completed" and not count:
                        outcome = "no_data"
                    job.providers[source] = {
                        "status": outcome, "count": count,
                        "message": "SEC facts and filing events collected; reported periods and revisions are preserved" if count else
                        "Set SEC_USER_AGENT with your actual contact email to collect SEC evidence" if outcome == "not_configured" else
                        "No new SEC facts returned; previously saved evidence remains unchanged",
                    }
                elif source in {"sec", "news"}:
                    if source == "sec":
                        outputs = await run_full_pipeline_async(symbol)
                        result = outputs.get("sec")
                    else:
                        result = await asyncio.to_thread(_collect_news, symbol)
                    count = await asyncio.to_thread(_produced_records, result)
                    outcome = "completed" if count else "no_data"
                    if isinstance(result, dict):
                        provider_outcomes = result.get("providers", {})
                        for name, provider in provider_outcomes.items():
                            raw_status = provider.get("status", "failed")
                            job.providers[f"news.{name}"] = {
                                "status": "completed" if raw_status == "ok" else raw_status,
                                "count": provider.get("count", 0),
                                "message": provider.get("reason") or "Provider collection outcome",
                            }
                        if count and any(p.get("status") in {"failed", "budget_exhausted"} for p in provider_outcomes.values()):
                            outcome = "partial"
                    job.providers[source] = {"status": outcome, "count": count, "message": "Records collected" if count else "No records returned; existing saved evidence may be stale"}
                else:
                    job.providers[source] = {"status": "unavailable", "count": 0, "message": "This collector is disabled"}
            except SQLAlchemyError:
                # A storage failure is not a provider outage; never switch stores.
                raise
            except Exception:
                logger.exception("Research collector failed for %s (%s)", symbol, source)
                job.providers[source] = {"status": "failed", "count": 0, "message": "Provider request failed"}
            job.progress = min(90, 10 + int(80 * (index + 1) / max(1, len(requested))))
            await persist_job(job)
        outcomes = [job.providers[source]["status"] for source in requested]
        successful = sum(value in {"completed", "partial"} for value in outcomes)
        job.status = "completed" if outcomes and all(value == "completed" for value in outcomes) else "partial" if successful else "failed"
        job.message = {"completed": "Requested sources returned evidence", "partial": "Some sources returned no data, are not configured, or failed. Check provider results and dates.", "failed": "No requested source returned usable data. Saved evidence has not been refreshed."}[job.status]
    except Exception:
        logger.error("Research refresh failed for %s", symbol)
        job.status, job.message = "failed", "Research refresh failed; verify source and storage availability"
    finally:
        cache.invalidate(symbol)
        cache.invalidate("available_stocks")
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)
        try:
            await persist_job(job)
        except Exception:
            logger.error("Could not persist final refresh status for %s", symbol)

# Add health endpoint for Railway
@app.get("/health", tags=["Health"])
async def simple_health():
    """Simple health check for Railway deployment"""
    repo = repository()
    if repo is not None:
        try:
            await asyncio.to_thread(repo.check_ready)
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable", "storage": "postgres"})
    return {"status": "ok", "storage": "postgres" if repo is not None else "files", "timestamp": datetime.now(timezone.utc)}

@app.get("/api/sentiment/{symbol}", response_model=EnhancedAnalysisResult, tags=["Sentiment"])
async def get_sentiment_analysis(symbol: str, current_user: str = Depends(verify_password_with_role)):
    return await get_stock_analysis(symbol, current_user)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
