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

def is_relevant_article(title, description, ticker, company_name):
    """
    Check if an article is relevant to the stock ticker.
    Filter out unrelated content like software libraries, domains, etc.
    """
    content = f"{title} {description}".lower()
    ticker_lower = ticker.lower()
    company_lower = company_name.lower() if company_name else ""
    
    # Exclude articles about software/tech libraries
    tech_exclusions = [
        "pypi", "python", "django", "library", "package", "npm", 
        "github", "repository", "api", "framework", "software development",
        "programming", "code", "developer", "application", "app store"
    ]
    
    # Exclude domain/website related content
    domain_exclusions = [
        "domain", "website", "web hosting", "server", "hosting"
    ]
    
    # Check for tech exclusions
    for exclusion in tech_exclusions + domain_exclusions:
        if exclusion in content and ticker_lower in content:
            # Additional check: if company name is also present, it might be legitimate
            if company_lower and company_lower in content:
                continue
            return False
    
    # Must contain either the ticker in financial context or company name
    financial_indicators = [
        "stock", "share", "nasdaq", "nyse", "trading", "market", "analyst",
        "earnings", "revenue", "profit", "financial", "investor", "portfolio",
        "price target", "rating", "upgrade", "downgrade", "enterprise",
        "corporation", "inc.", "ltd.", "company"
    ]
    
    has_financial_context = any(indicator in content for indicator in financial_indicators)
    has_ticker = ticker_lower in content
    has_company = company_lower and company_lower in content
    
    return (has_ticker or has_company) and has_financial_context

def is_trusted_source(source_name):
    """
    Check if the news source is a trusted financial publication.
    """
    trusted_sources = {
        # Tier 1 - Premium financial sources
        "Bloomberg", "Reuters", "Wall Street Journal", "Financial Times", 
        "MarketWatch", "Yahoo Finance", "CNBC", "Forbes",
        
        # Tier 2 - Reliable business sources  
        "Business Insider", "The Motley Fool", "Seeking Alpha", "Barron's",
        "Investor's Business Daily", "TheStreet", "Benzinga",
        
        # Tier 3 - General but reliable
        "ETF Daily News", "PR Newswire", "Business Wire", "Globe Newswire"
    }
    
    # Partial matches for sources with varying formats
    for trusted in trusted_sources:
        if trusted.lower() in source_name.lower():
            return True
    return False

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
        "EOSE": "Eos Energy Enterprises",
        "PLTR": "Palantir",
        "VG": "Virgin Galactic",
        "VWAGY": "Volkswagen",
        "NEXT": "NextDecade",
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
    filtered_count = 0
    flagged_for_review = []
    
    for article in articles:
        title = article["title"]
        description = article.get("description") or ""
        source_name = article["source"]["name"]
        
        # Filter for trusted sources first
        if not is_trusted_source(source_name):
            filtered_count += 1
            continue
        
        # Filter for relevance
        if not is_relevant_article(title, description, ticker, company_name):
            filtered_count += 1
            continue
        
        # Flag potentially questionable articles for manual review
        content = f"{title} {description}".lower()
        questionable_indicators = [
            "added to", "version", "release", "update", "library", 
            "package", "framework", "tool", "software"
        ]
        
        is_questionable = any(indicator in content for indicator in questionable_indicators)
        
        content = f"{title}. {description}"
        sentiment = analyzer.polarity_scores(content)

        article_data = {
            "title": title,
            "description": description,
            "publishedAt": article["publishedAt"],
            "url": article["url"],
            "source": article["source"]["name"],
            "flagged_for_review": is_questionable,  # Add flag for manual review
            "sentiment": {
                **sentiment,
                "label": classify_sentiment(sentiment["compound"])
            }
        }
        
        if is_questionable:
            flagged_for_review.append(article_data)
        
        results.append(article_data)

    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"{ticker}_news_sentiment.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    if flagged_for_review:
        print(f"⚠️  {len(flagged_for_review)} articles flagged for manual review")
        for article in flagged_for_review:
            print(f"   - {article['title'][:60]}...")
    
    print(f"✅ Filtered out {filtered_count} irrelevant articles")
    print(f"✅ Saved {len(results)} relevant news articles to {output_path}")
    return output_path

# Run this script standalone with a test ticker
if __name__ == "__main__":
    fetch_news_sentiment("AAPL")
