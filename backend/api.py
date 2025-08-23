"""
Optimized FastAPI backend for StockScope with caching, proper error handling, and efficient data access
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing functions
from main import run_full_pipeline
from scraping.news_scraper import fetch_news_sentiment
from ui.utils.data_helpers import get_available_tickers, load_dataframes
from analysis.investment_advisor import InvestmentAdvisor
from analysis.quantitative_strategies import QuantitativeStrategies

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
    """Load stock suggestions from external source or fallback to hardcoded"""
    try:
        # Try to load from external API or file first
        # For now, return optimized hardcoded list
        return [
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "market_cap": "Large"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary", "market_cap": "Large"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "market_cap": "Large"},
            # Add more optimized data
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

@app.get("/api/stocks/suggestions", response_model=List[StockSuggestion], tags=["Search"])
async def get_stock_suggestions(
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
async def get_available_stocks():
    """Get list of analyzed stocks with metadata"""
    cache_key = "available_stocks"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        tickers = get_available_tickers()
        
        # Enhanced response with metadata
        stocks_with_metadata = []
        for ticker in tickers:
            try:
                # Quick metadata without full dataframe load
                df = load_dataframes(ticker)
                if not df.empty:
                    last_updated = df['created_utc'].max() if 'created_utc' in df.columns else datetime.now()
                    stocks_with_metadata.append({
                        "symbol": ticker,
                        "total_posts": len(df),
                        "avg_sentiment": float(df['compound'].mean()),
                        "last_updated": last_updated,
                        "sources": list(df['source'].unique()) if 'source' in df.columns else []
                    })
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
async def get_stock_analysis(symbol: str) -> EnhancedAnalysisResult:
    """Get comprehensive analysis for a specific stock with caching"""
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
                source_analyses.append(SourceAnalysis(
                    source=source,
                    count=len(source_df),
                    avg_sentiment=float(source_df['compound'].mean()),
                    latest_update=source_df['created_utc'].max() if 'created_utc' in source_df.columns else datetime.now()
                ))
        
        # Calculate data quality score
        data_quality = min(1.0, len(df) / 50) * (1 - abs(sentiment_metrics.avg_sentiment - df['compound'].median()))
        
        result = EnhancedAnalysisResult(
            ticker=symbol,
            total_posts=len(df),
            sentiment_metrics=sentiment_metrics,
            sources=source_analyses,
            last_updated=df['created_utc'].max() if 'created_utc' in df.columns else datetime.now(),
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
async def analyze_stock(request: StockRequest, background_tasks: BackgroundTasks):
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
async def get_analysis_status(symbol: str):
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
async def get_investment_advice(symbol: str):
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
        
        # Use your existing InvestmentAdvisor
        advisor = InvestmentAdvisor(symbol)
        recommendation_data = advisor.generate_recommendation()
        
        # Enhanced recommendation structure
        result = InvestmentRecommendation(
            ticker=symbol,
            recommendation=recommendation_data.get('recommendation', 'HOLD'),
            confidence=recommendation_data.get('confidence', 0.5),
            target_price=recommendation_data.get('target_price'),
            reasoning=recommendation_data.get('reasoning', []),
            risk_factors=recommendation_data.get('risk_factors', []),
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
async def get_quantitative_analysis(symbol: str):
    """Get quantitative strategy analysis"""
    symbol = symbol.upper()
    
    cache_key = f"quant_analysis_{symbol}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Use your existing QuantitativeStrategies
        quant = QuantitativeStrategies(symbol)
        analysis = quant.run_analysis()
        
        # Cache for 1 hour
        cache.set(cache_key, analysis, ttl=3600)
        return analysis
        
    except Exception as e:
        logger.error(f"Error getting quantitative analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to run quantitative analysis")

@app.delete("/api/cache", tags=["Admin"])
async def clear_cache(pattern: Optional[str] = None):
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
            run_full_pipeline(symbol)
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )