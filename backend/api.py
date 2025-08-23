"""
FastAPI backend to expose StockScope Python functions
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os

# Add the parent directory to the Python path so we can import from the main project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing functions
from main import run_full_pipeline
from scraping.news_scraper import fetch_news_sentiment
from ui.utils.data_helpers import get_available_tickers, load_dataframes
from analysis.investment_advisor import InvestmentAdvisor

app = FastAPI(title="StockScope API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class StockRequest(BaseModel):
    symbol: str
    sources: List[str] = ["reddit", "news", "sec"]

class StockSuggestion(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None

class AnalysisResult(BaseModel):
    ticker: str
    total_posts: int
    avg_sentiment: float
    sources: Dict[str, int]
    recommendation: Optional[str] = None

# Stock suggestions data (expanded list)
STOCK_SUGGESTIONS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial Services"},
    {"symbol": "BAC", "name": "Bank of America Corp", "sector": "Financial Services"},
    {"symbol": "WFC", "name": "Wells Fargo & Company", "sector": "Financial Services"},
    {"symbol": "GS", "name": "Goldman Sachs Group Inc.", "sector": "Financial Services"},
    {"symbol": "MS", "name": "Morgan Stanley", "sector": "Financial Services"},
    {"symbol": "C", "name": "Citigroup Inc.", "sector": "Financial Services"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"symbol": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare"},
    {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Healthcare"},
    {"symbol": "ABT", "name": "Abbott Laboratories", "sector": "Healthcare"},
    {"symbol": "TMO", "name": "Thermo Fisher Scientific", "sector": "Healthcare"},
    {"symbol": "DHR", "name": "Danaher Corporation", "sector": "Healthcare"},
    {"symbol": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer Defensive"},
    {"symbol": "KO", "name": "Coca-Cola Company", "sector": "Consumer Defensive"},
    {"symbol": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer Defensive"},
    {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Consumer Defensive"},
    {"symbol": "HD", "name": "Home Depot Inc.", "sector": "Consumer Cyclical"},
    {"symbol": "MCD", "name": "McDonald's Corporation", "sector": "Consumer Cyclical"},
    {"symbol": "BA", "name": "Boeing Company", "sector": "Industrials"},
    {"symbol": "CAT", "name": "Caterpillar Inc.", "sector": "Industrials"},
    {"symbol": "GE", "name": "General Electric Company", "sector": "Industrials"},
    {"symbol": "MMM", "name": "3M Company", "sector": "Industrials"},
    {"symbol": "HON", "name": "Honeywell International", "sector": "Industrials"},
    {"symbol": "LMT", "name": "Lockheed Martin Corp", "sector": "Industrials"},
    {"symbol": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy"},
    {"symbol": "CVX", "name": "Chevron Corporation", "sector": "Energy"},
    {"symbol": "COP", "name": "ConocoPhillips", "sector": "Energy"},
    {"symbol": "SLB", "name": "Schlumberger NV", "sector": "Energy"},
    {"symbol": "PLTR", "name": "Palantir Technologies Inc.", "sector": "Technology"},
    {"symbol": "RKLB", "name": "Rocket Lab USA Inc.", "sector": "Industrials"},
    {"symbol": "GME", "name": "GameStop Corp.", "sector": "Consumer Cyclical"},
    {"symbol": "AMC", "name": "AMC Entertainment Holdings", "sector": "Communication Services"},
    {"symbol": "BB", "name": "BlackBerry Limited", "sector": "Technology"},
    {"symbol": "NOK", "name": "Nokia Corporation", "sector": "Technology"},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "sector": "ETF"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "sector": "ETF"},
    {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "sector": "ETF"},
    {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "sector": "ETF"},
    {"symbol": "ARKK", "name": "ARK Innovation ETF", "sector": "ETF"},
    {"symbol": "TQQQ", "name": "ProShares UltraPro QQQ", "sector": "ETF"}
]

@app.get("/")
async def root():
    return {"message": "StockScope API is running", "version": "1.0.0", "endpoints": ["/api/stocks/suggestions", "/api/stocks", "/api/stocks/analyze"]}

@app.get("/api/stocks/suggestions")
async def get_stock_suggestions(q: str = "") -> List[StockSuggestion]:
    """Get stock suggestions for autocomplete"""
    if not q:
        return STOCK_SUGGESTIONS[:10]
    
    q = q.upper()
    matches = [
        stock for stock in STOCK_SUGGESTIONS
        if q in stock["symbol"] or q in stock["name"].upper()
    ]
    
    # Sort by relevance
    exact_matches = [s for s in matches if s["symbol"] == q]
    prefix_matches = [s for s in matches if s["symbol"].startswith(q)]
    other_matches = [s for s in matches if s not in exact_matches + prefix_matches]
    
    return (exact_matches + prefix_matches + other_matches)[:10]

@app.get("/api/stocks")
async def get_available_stocks():
    """Get list of analyzed stocks"""
    try:
        tickers = get_available_tickers()
        return {"stocks": tickers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{symbol}")
async def get_stock_analysis(symbol: str) -> AnalysisResult:
    """Get analysis for a specific stock"""
    try:
        df = load_dataframes(symbol.upper())
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Calculate metrics
        total_posts = len(df)
        avg_sentiment = df['compound'].mean() if not df['compound'].isna().all() else 0
        
        # Source breakdown
        sources = {}
        if 'source' in df.columns:
            source_counts = df['source'].value_counts()
            sources = source_counts.to_dict()
        
        return AnalysisResult(
            ticker=symbol.upper(),
            total_posts=total_posts,
            avg_sentiment=float(avg_sentiment),
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stocks/analyze")
async def analyze_stock(request: StockRequest, background_tasks: BackgroundTasks):
    """Start analysis for a new stock"""
    try:
        symbol = request.symbol.upper()
        
        # Add to background tasks to avoid blocking
        background_tasks.add_task(run_analysis_background, symbol, request.sources)
        
        return {
            "message": f"Analysis started for {symbol}",
            "symbol": symbol,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{symbol}/investment-advice")
async def get_investment_advice(symbol: str):
    """Get AI investment advice for a stock"""
    try:
        df = load_dataframes(symbol.upper())
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Use your existing InvestmentAdvisor
        advisor = InvestmentAdvisor(symbol.upper())
        recommendation = advisor.generate_recommendation()
        
        return recommendation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_analysis_background(symbol: str, sources: List[str]):
    """Run analysis in background"""
    try:
        if "reddit" in sources or "sec" in sources:
            run_full_pipeline(symbol)
        
        if "news" in sources:
            fetch_news_sentiment(symbol)
            
        print(f"✅ Analysis completed for {symbol}")
        
    except Exception as e:
        print(f"❌ Analysis failed for {symbol}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)