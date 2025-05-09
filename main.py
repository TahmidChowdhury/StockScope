#main.py
import sys
from scraping.reddit_scraper import fetch_reddit_posts
from sentiment.analyzer import analyze_sentiment
from visualizations.plot_sentiment import plot_sentiment_distribution
from datetime import datetime
import json
import os

import pprint

if len(sys.argv) < 2:
    print("❌ Please provide a stock ticker symbol.")
    print("Usage: python main.py AAPL")
    sys.exit(1)

ticker = sys.argv[1].upper()

def classify_sentiment(compound):
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    else:
        return "neutral"

if __name__ == "__main__":
    posts = fetch_reddit_posts(ticker, limit=10)
    enriched_posts = []

    for post in posts:
        sentiment = analyze_sentiment(post["title"])
        label = classify_sentiment(sentiment["compound"])

        post["sentiment"] = sentiment
        post["sentiment"]["label"] = label
        enriched_posts.append(post)

    pprint.pprint(enriched_posts)
    # Save the enriched posts to a JSON file
    output_path = os.path.join("data", "AAPL_reddit_sentiment.json")

    with open(output_path, "w") as f:
        json.dump(enriched_posts, f, indent=2)

    print(f"\n✅ Saved {len(enriched_posts)} posts to {output_path}")
    # Plot the sentiment distribution
    plot_sentiment_distribution(output_path)

    