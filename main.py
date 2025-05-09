# main.py

from scraping.reddit_scraper import fetch_reddit_posts
from sentiment.analyzer import analyze_sentiment
from datetime import datetime
import json
import os

def run_pipeline(ticker: str, limit=20):
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
