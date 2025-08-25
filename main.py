# main.py

from scraping.reddit_scraper import fetch_reddit_posts
# from scraping.twitter_scraper import fetch_twitter_sentiment  # COMMENTED OUT - Twitter API disabled until paid access
from scraping.sec_scraper import fetch_sec_sentiment
from sentiment.analyzer import analyze_sentiment
from datetime import datetime
import json
import os
import asyncio

async def run_pipeline(ticker: str, limit=20):
    """Run the complete data pipeline for Reddit data"""
    posts = await fetch_reddit_posts(ticker, limit=limit)
    enriched_posts = []

    def classify_sentiment(compound):
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        else:
            return "neutral"

    for post in posts:
        sentiment = analyze_sentiment(post["title"])
        post["sentiment"] = sentiment
        post["sentiment"]["label"] = classify_sentiment(sentiment["compound"])
        post["created"] = datetime.fromtimestamp(post["created_utc"]).strftime("%Y-%m-%d %H:%M:%S")
        enriched_posts.append(post)

    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"{ticker}_reddit_sentiment.json")

    with open(output_path, "w") as f:
        json.dump(enriched_posts, f, indent=2)

    return output_path  # return the path so Streamlit can load it

async def run_full_pipeline_async(ticker: str, reddit_limit=20, twitter_limit=50, sec_limit=10):
    """Run the complete data pipeline for all sources (async version)"""
    results = {}
    
    # Fetch Reddit data (now async)
    try:
        reddit_path = await run_pipeline(ticker, limit=reddit_limit)
        results['reddit'] = reddit_path
        print(f"[SUCCESS] Reddit data saved to {reddit_path}")
    except Exception as e:
        print(f"[ERROR] Reddit scraping failed: {e}")
        results['reddit'] = None
    
    # Twitter data - COMMENTED OUT until paid API access
    # try:
    #     twitter_path = fetch_twitter_sentiment(ticker, max_tweets=twitter_limit)
    #     results['twitter'] = twitter_path
    #     if twitter_path:
    #         print(f"[SUCCESS] Twitter data saved to {twitter_path}")
    # except Exception as e:
    #     print(f"[ERROR] Twitter scraping failed: {e}")
    #     results['twitter'] = None
    
    print("[WARNING] Twitter API disabled - upgrade to paid access to enable Twitter sentiment analysis")
    results['twitter'] = None
    
    # Fetch SEC data (keeping sync for now)
    try:
        sec_path = fetch_sec_sentiment(ticker, limit=sec_limit)
        results['sec'] = sec_path
        if sec_path:
            print(f"[SUCCESS] SEC data saved to {sec_path}")
    except Exception as e:
        print(f"[ERROR] SEC scraping failed: {e}")
        results['sec'] = None
    
    return results

def run_full_pipeline(ticker: str, reddit_limit=20, twitter_limit=50, sec_limit=10):
    """Synchronous wrapper for the async pipeline (for backward compatibility)"""
    return asyncio.run(run_full_pipeline_async(ticker, reddit_limit, twitter_limit, sec_limit))

# Add this section to start the API server when main.py is run directly
if __name__ == "__main__":
    print("🚀 Starting StockScope API server...")
    import uvicorn
    from backend.api import app
    
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get("PORT", 8000))
    
    print(f"📡 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
