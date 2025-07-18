# main.py

from scraping.reddit_scraper import fetch_reddit_posts
# from scraping.twitter_scraper import fetch_twitter_sentiment  # COMMENTED OUT - Twitter API disabled until paid access
from scraping.sec_scraper import fetch_sec_sentiment
from sentiment.analyzer import analyze_sentiment
from datetime import datetime
import json
import os

def run_pipeline(ticker: str, limit=20):
    """Run the complete data pipeline for Reddit data"""
    posts = fetch_reddit_posts(ticker, limit=limit)
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

def run_full_pipeline(ticker: str, reddit_limit=20, twitter_limit=50, sec_limit=10):
    """Run the complete data pipeline for all sources"""
    results = {}
    
    # Fetch Reddit data
    try:
        reddit_path = run_pipeline(ticker, limit=reddit_limit)
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
    
    # Fetch SEC data
    try:
        sec_path = fetch_sec_sentiment(ticker, limit=sec_limit)
        results['sec'] = sec_path
        if sec_path:
            print(f"[SUCCESS] SEC data saved to {sec_path}")
    except Exception as e:
        print(f"[ERROR] SEC scraping failed: {e}")
        results['sec'] = None
    
    return results
