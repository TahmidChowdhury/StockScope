import os
import requests
import json
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

# Load environment variables from .env
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2/everything"

analyzer = SentimentIntensityAnalyzer()

def classify_sentiment(compound):
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    else:
        return "neutral"

def fetch_news_sentiment(ticker, limit=20):
    TICKER_MAP = {
        "AAPL": "Apple",
        "TSLA": "Tesla",
        "MSFT": "Microsoft",
        "GOOGL": "Google",
        "AMZN": "Amazon",
        "META": "Meta",
        "NFLX": "Netflix",
        "NVDA": "Nvidia",
        # Add more as needed
    }

    company_name = TICKER_MAP.get(ticker.upper(), "")
    query = f"{ticker} {company_name}".strip()

    params = {
        "q": query,
        "language": "en",
        "pageSize": limit,
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY
    }

    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"NewsAPI error: {response.status_code} - {response.text}")

    articles = response.json().get("articles", [])
    print(f"🔍 Found {len(articles)} articles for query: '{query}'")

    results = []
    for article in articles:
        title = article["title"]
        description = article.get("description") or ""
        content = f"{title}. {description}"
        sentiment = analyzer.polarity_scores(content)

        results.append({
            "title": title,
            "description": description,
            "publishedAt": article["publishedAt"],
            "url": article["url"],
            "source": article["source"]["name"],
            "sentiment": {
                **sentiment,
                "label": classify_sentiment(sentiment["compound"])
            }
        })

    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"{ticker}_news_sentiment.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Saved {len(results)} news articles to {output_path}")
    return output_path

# Run this script standalone with a test ticker
if __name__ == "__main__":
    fetch_news_sentiment("AAPL")
