# scraping/reddit_scraper.py

import os
import praw
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_reddit_client():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

def fetch_reddit_posts(ticker, limit=50, days_back=90):
    """
    Fetch recent Reddit posts about a ticker from the last X days only.
    
    Args:
        ticker (str): Stock ticker symbol
        limit (int): Maximum posts per subreddit
        days_back (int): Only get posts from last X days (default: 90 days)
    """
    reddit = get_reddit_client()
    
    # Clean up duplicate subreddits and fix issues
    subreddits = [
        # Major investment communities
        "stocks", "wallstreetbets", "investing", "SecurityAnalysis",
        
        # Growth/tech focused  
        "ValueInvesting", "GrowthInvesting", "investing_discussion",
        
        # Small caps and pennies (good for EOSE, RKLB)
        "smallcaps", "pennystocks", "RobinHoodPennyStocks",
        
        # Specific sectors (removed broken ones)
        "technology", "biotech", "energy", "spacs",
        
        # Options and active trading
        "options", "thetagang", "financialindependence",
        
        # International and emerging
        "CanadianInvestor", "UKInvesting", "EuropeFIRE", "AusFinance",
        
        # Additional major investing communities
        "StockMarket", "InvestmentClub", "portfolios", "dividends", 
        "FIRE", "Bogleheads",
        
        # Sector-specific subreddits (removed broken ones)
        "CleanEnergy", "RenewableEnergy", "solar", "ElectricVehicles", 
        "TeslaInvestorsClub", "SpaceStocks", "aerospace",
        
        # ESG and sustainability focused
        "ESGInvesting",
        
        # Meme and retail trader communities
        "Superstonk", "DDintoGME", "amcstock", "CLOV", "SPCE", "SPACs",
        
        # Cryptocurrency (for companies with crypto exposure)
        "CryptoCurrency", "BitcoinMarkets", "ethtrader",
        
        # News and discussion
        "business", "economy", "Economics", "StockMarketChat",
        
        # Specific trading strategies
        "GrowthStocks", "DividendGrowth", "REIT", "commodities",
        
        # Personal finance communities
        "PersonalFinanceCanada", "SpaceXLounge", "SpaceXMasterrace"
    ]
    results = []
    
    # Calculate cutoff date (only posts newer than this)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    cutoff_timestamp = cutoff_date.timestamp()
    
    print(f"[INFO] Fetching Reddit posts for {ticker} from last {days_back} days...")
    print(f"[INFO] Only including posts newer than: {cutoff_date.strftime('%Y-%m-%d')}")

    for sub in subreddits:
        try:
            subreddit = reddit.subreddit(sub)
            posts_found = 0
            posts_filtered = 0
            
            # Search recent posts first, then filter by date
            for submission in subreddit.search(ticker, sort='new', time_filter='month', limit=limit*2):
                # Only include posts from the last X days
                if submission.created_utc >= cutoff_timestamp:
                    created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    results.append({
                        "title": submission.title,
                        "score": submission.score,
                        "url": submission.url,
                        "created_utc": submission.created_utc,
                        "subreddit": sub,
                        "created": created,
                    })
                    posts_found += 1
                    
                    # Stop when we have enough recent posts
                    if posts_found >= limit:
                        break
                else:
                    posts_filtered += 1
            
            print(f"[DATA] r/{sub}: {posts_found} recent posts, {posts_filtered} old posts filtered out")
            
        except Exception as e:
            print(f"[WARNING] Error fetching from r/{sub}: {e}")
            continue

    print(f"[SUCCESS] Total recent posts found: {len(results)}")
    return results
