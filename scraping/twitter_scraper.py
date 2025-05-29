import tweepy
import pandas as pd
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sentiment.analyzer import analyze_sentiment
except ImportError:
    # Fallback if running standalone
    def analyze_sentiment(text):
        # Simple fallback sentiment analysis
        positive_words = ['good', 'great', 'buy', 'bull', 'up', 'rise', 'profit', 'gain', 'bullish', 'moon', 'rocket']
        negative_words = ['bad', 'sell', 'bear', 'down', 'fall', 'loss', 'crash', 'drop', 'bearish', 'dump', 'tank']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        compound = (pos_count - neg_count) / max(1, total_words) * 10  # Scale it
        compound = max(-1, min(1, compound))  # Clamp between -1 and 1
        
        return {
            'compound': compound,
            'pos': pos_count / max(1, total_words),
            'neu': max(0, 1 - (pos_count + neg_count) / max(1, total_words)),
            'neg': neg_count / max(1, total_words)
        }

def get_twitter_client():
    """Initialize and return Twitter API client"""
    try:
        # Get credentials from environment variables
        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        if not bearer_token:
            raise ValueError("Twitter Bearer Token not found in environment variables")
        
        # Create client with Bearer Token and wait_on_rate_limit=False for better control
        client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=False)
        return client
        
    except Exception as e:
        print(f"Error initializing Twitter client: {e}")
        return None

def check_rate_limits(client):
    """Check current rate limit status"""
    try:
        # This is a simple way to check if we can make requests
        response = client.get_me()
        return True
    except tweepy.TooManyRequests:
        return False
    except Exception as e:
        print(f"Error checking rate limits: {e}")
        return False

def fetch_twitter_sentiment(ticker, max_tweets=20, skip_rate_limit_wait=False):
    """
    Fetch tweets about a stock ticker and analyze sentiment using Twitter API v2.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        max_tweets (int): Maximum number of tweets to fetch (reduced default for rate limits)
        skip_rate_limit_wait (bool): If True, skip waiting for rate limits and return None
    
    Returns:
        str: Path to the saved JSON file with sentiment data
    """
    client = get_twitter_client()
    if not client:
        print("❌ Failed to initialize Twitter client")
        return None
    
    # Check if we're already rate limited
    if not check_rate_limits(client) and skip_rate_limit_wait:
        print("⚠️ Rate limited. Skipping Twitter data collection.")
        return None
    
    # Create search query for the ticker (no $ symbol for basic API)
    query = f"({ticker} stock OR {ticker} shares OR \"{ticker}\" trading) -is:retweet lang:en"
    
    tweets = []
    try:
        print(f"🔍 Searching for tweets about {ticker}...")
        
        # Reduce max_results to stay within rate limits
        max_results = min(max_tweets, 30)  # Lower limit for free tier
        
        # Fetch tweets using Twitter API v2
        response = client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['created_at', 'author_id', 'public_metrics', 'text'],
            expansions=['author_id'],
            user_fields=['username']
        )
        
        if not response.data:
            print(f"⚠️ No tweets found for {ticker}")
            # Create empty file to avoid errors in Streamlit
            os.makedirs("data", exist_ok=True)
            output_path = os.path.join("data", f"{ticker}_twitter_sentiment.json")
            with open(output_path, "w") as f:
                json.dump([], f)
            return output_path
        
        # Get user data for usernames
        users = {user.id: user.username for user in response.includes.get('users', [])} if response.includes else {}
        
        print(f"📊 Processing {len(response.data)} tweets...")
        
        for tweet in response.data:
            # Analyze sentiment
            sentiment = analyze_sentiment(tweet.text)
            
            # Classify sentiment
            def classify_sentiment(compound):
                if compound >= 0.05:
                    return "positive"
                elif compound <= -0.05:
                    return "negative"
                else:
                    return "neutral"
            
            # Get public metrics safely
            metrics = tweet.public_metrics or {}
            
            tweets.append({
                'id': tweet.id,
                'date': tweet.created_at.isoformat() if tweet.created_at else datetime.now().isoformat(),
                'content': tweet.text,
                'username': users.get(tweet.author_id, 'unknown'),
                'like_count': metrics.get('like_count', 0),
                'retweet_count': metrics.get('retweet_count', 0),
                'reply_count': metrics.get('reply_count', 0),
                'quote_count': metrics.get('quote_count', 0),
                'url': f"https://twitter.com/i/status/{tweet.id}",
                'sentiment': sentiment,
                'sentiment_label': classify_sentiment(sentiment['compound'])
            })
            
    except tweepy.TooManyRequests:
        print(f"⚠️ Rate limit reached for Twitter API.")
        if skip_rate_limit_wait:
            print("Skipping Twitter data collection due to rate limits.")
            return None
        else:
            print("Consider waiting 15 minutes before trying again.")
            return None
    except tweepy.Unauthorized:
        print("❌ Twitter API authentication failed. Check your credentials.")
        return None
    except Exception as e:
        print(f"❌ Error fetching tweets for {ticker}: {e}")
        return None
    
    # Save to JSON file (even if empty)
    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"{ticker}_twitter_sentiment.json")
    
    with open(output_path, "w") as f:
        json.dump(tweets, f, indent=2, default=str)
    
    if tweets:
        print(f"✅ Saved {len(tweets)} tweets for {ticker} to {output_path}")
    else:
        print(f"⚠️ No tweets collected for {ticker}, saved empty file")
    
    return output_path

def create_sample_twitter_data(ticker, num_tweets=10):
    """
    Create sample Twitter data for testing when API is rate limited.
    """
    print(f"🧪 Creating sample Twitter data for {ticker}...")
    
    sample_tweets = []
    sample_contents = [
        f"{ticker} stock is looking bullish today! 🚀",
        f"Just bought more {ticker} shares, great long-term investment",
        f"{ticker} earnings report disappointed investors",
        f"Thinking about selling my {ticker} position",
        f"{ticker} breaking through resistance levels!",
        f"Market volatility affecting {ticker} price",
        f"{ticker} fundamentals look strong despite market conditions",
        f"Technical analysis suggests {ticker} might see correction",
        f"{ticker} innovation continues to drive growth",
        f"Analyst upgraded {ticker} price target"
    ]
    
    for i in range(min(num_tweets, len(sample_contents))):
        content = sample_contents[i]
        sentiment = analyze_sentiment(content)
        
        def classify_sentiment(compound):
            if compound >= 0.05:
                return "positive"
            elif compound <= -0.05:
                return "negative"
            else:
                return "neutral"
        
        sample_tweets.append({
            'id': f"sample_{i+1}",
            'date': datetime.now().isoformat(),
            'content': content,
            'username': f"sample_user_{i+1}",
            'like_count': (i + 1) * 5,
            'retweet_count': (i + 1) * 2,
            'reply_count': i + 1,
            'quote_count': i,
            'url': f"https://twitter.com/sample/status/sample_{i+1}",
            'sentiment': sentiment,
            'sentiment_label': classify_sentiment(sentiment['compound'])
        })
    
    # Save sample data
    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", f"{ticker}_twitter_sentiment.json")
    
    with open(output_path, "w") as f:
        json.dump(sample_tweets, f, indent=2, default=str)
    
    print(f"✅ Created {len(sample_tweets)} sample tweets for {ticker}")
    return output_path

def fetch_twitter_data(query, max_tweets=100):
    """
    Legacy function - kept for backward compatibility.
    Fetch tweets based on a query using Twitter API v2.

    Args:
        query (str): The search query for tweets.
        max_tweets (int): Maximum number of tweets to fetch.

    Returns:
        pd.DataFrame: A DataFrame containing tweet data (content, date, username).
    """
    client = get_twitter_client()
    if not client:
        return pd.DataFrame()
    
    try:
        response = client.search_recent_tweets(
            query=query,
            max_results=min(max_tweets, 100),
            tweet_fields=['created_at', 'author_id'],
            expansions=['author_id'],
            user_fields=['username']
        )
        
        if not response.data:
            return pd.DataFrame()
        
        users = {user.id: user.username for user in response.includes.get('users', [])} if response.includes else {}
        
        tweets = []
        for tweet in response.data:
            tweets.append({
                'date': tweet.created_at,
                'content': tweet.text,
                'username': users.get(tweet.author_id, 'unknown')
            })
        
        return pd.DataFrame(tweets)
        
    except Exception as e:
        print(f"Error in legacy Twitter function: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Example usage
    ticker = "TSLA"
    print(f"🐦 Testing Twitter API for {ticker}...")
    result_path = fetch_twitter_sentiment(ticker, max_tweets=20)
    if result_path:
        print(f"✅ Successfully analyzed Twitter sentiment for {ticker}")
        
        # Show a sample of the data
        with open(result_path, 'r') as f:
            data = json.load(f)
            print(f"\n📊 Sample of {len(data)} tweets:")
            for i, tweet in enumerate(data[:3]):
                print(f"{i+1}. @{tweet['username']}: {tweet['content'][:100]}...")
                print(f"   Sentiment: {tweet['sentiment_label']} ({tweet['sentiment']['compound']:.3f})")
    else:
        print(f"❌ Failed to fetch Twitter data for {ticker}")