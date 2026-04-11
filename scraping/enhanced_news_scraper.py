import os
import requests
import json
import feedparser
from gnews import GNews
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
import time

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
analyzer = SentimentIntensityAnalyzer()

# RSS feeds that reliably include stock/market news with real article URLs
RSS_FEEDS = {
    "MarketWatch":  "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "CNBC":         "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "Seeking Alpha": None,  # built per-ticker: https://seekingalpha.com/api/sa/combined/{ticker}.xml
    "Benzinga":     "https://www.benzinga.com/feed",
}

class EnhancedNewsScraper:
    """Enhanced news scraper with multiple sources including Yahoo Finance and web scraping."""
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def classify_sentiment(self, compound):
        """Classify sentiment based on compound score."""
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        else:
            return "neutral"
    
    def fetch_yahoo_finance_news(self, ticker: str) -> List[Dict]:
        """Fetch news from Yahoo Finance using yfinance."""
        try:
            print(f"🔍 Fetching Yahoo Finance news for {ticker}...")
            stock = yf.Ticker(ticker)
            
            # Get news data - handle potential errors
            try:
                news_data = stock.news
            except Exception as e:
                print(f"  ⚠️ Error accessing Yahoo news data: {e}")
                news_data = []
            
            if not news_data:
                print(f"  ⚠️ No Yahoo Finance news found for {ticker}")
                return []
            
            articles = []
            for article in news_data[:10]:  # Limit to 10 articles
                try:
                    # Handle both old and new yfinance data structures
                    if 'content' in article:
                        # New structure with nested content
                        content = article['content']
                        title = content.get('title', '')
                        summary = content.get('summary', '')
                        link = content.get('canonicalUrl', {}).get('url', '') or content.get('clickThroughUrl', {}).get('url', '')
                        
                        # Parse pubDate
                        pub_date = content.get('pubDate', '')
                        if pub_date:
                            try:
                                # Parse ISO format like '2025-10-07T12:51:54Z'
                                if pub_date.endswith('Z'):
                                    pub_date = pub_date[:-1]  # Remove 'Z'
                                published_at = datetime.fromisoformat(pub_date).isoformat()
                            except:
                                published_at = datetime.now().isoformat()
                        else:
                            published_at = datetime.now().isoformat()
                    else:
                        # Old structure (direct fields)
                        title = article.get('title', '')
                        summary = article.get('summary', '')
                        link = article.get('link', '')
                        provider_publish_time = article.get('providerPublishTime')
                        
                        if provider_publish_time:
                            published_at = datetime.fromtimestamp(provider_publish_time).isoformat()
                        else:
                            published_at = datetime.now().isoformat()
                    
                    if not title:
                        continue
                    
                    # Calculate sentiment from title and summary
                    content_text = f"{title}. {summary}".strip()
                    sentiment_scores = self.analyzer.polarity_scores(content_text)
                    
                    articles.append({
                        'source': 'Yahoo Finance',
                        'title': title,
                        'description': summary,
                        'url': link,
                        'publishedAt': published_at,
                        'sentiment': {
                            'compound': sentiment_scores['compound'],
                            'label': self.classify_sentiment(sentiment_scores['compound'])
                        }
                    })
                except Exception as e:
                    print(f"  ⚠️ Error processing Yahoo article: {e}")
                    continue
            
            print(f"  ✅ Found {len(articles)} Yahoo Finance articles")
            return articles
            
        except Exception as e:
            print(f"  ❌ Error fetching Yahoo Finance news: {e}")
            return []
    
    def fetch_newsapi_articles(self, ticker: str, company_name: str = "") -> List[Dict]:
        """Fetch articles from NewsAPI with improved filtering."""
        if not NEWS_API_KEY:
            print("  ⚠️ No NewsAPI key found, skipping NewsAPI")
            return []
        
        try:
            print(f"🔍 Fetching NewsAPI articles for {ticker}...")
            
            # Create a more comprehensive search query
            queries = [
                f'"{ticker}"',
                f'"{company_name}"' if company_name else '',
                f'{ticker} stock',
                f'{company_name} earnings' if company_name else '',
            ]
            
            # Remove empty queries
            queries = [q for q in queries if q.strip()]
            
            all_articles = []
            
            for query in queries[:2]:  # Limit to 2 queries to avoid rate limits
                params = {
                    "q": query,
                    "language": "en",
                    "pageSize": 20,
                    "sortBy": "publishedAt",
                    "apiKey": NEWS_API_KEY,
                    "domains": "reuters.com,bloomberg.com,marketwatch.com,yahoo.com,cnbc.com,fool.com,seekingalpha.com,investorplace.com,benzinga.com"
                }
                
                response = requests.get("https://newsapi.org/v2/everything", params=params)
                if response.status_code == 200:
                    articles = response.json().get("articles", [])
                    
                    for article in articles:
                        if self.is_relevant_article(article, ticker, company_name):
                            content = f"{article['title']}. {article.get('description', '')}"
                            sentiment = self.analyzer.polarity_scores(content)
                            
                            all_articles.append({
                                'title': article['title'],
                                'description': article.get('description', ''),
                                'publishedAt': article['publishedAt'],
                                'url': article['url'],
                                'source': article['source']['name'],
                                'sentiment': {
                                    **sentiment,
                                    'label': self.classify_sentiment(sentiment['compound'])
                                }
                            })
                
                time.sleep(0.1)  # Rate limiting
            
            # Remove duplicates based on title
            seen_titles = set()
            unique_articles = []
            for article in all_articles:
                if article['title'] not in seen_titles:
                    seen_titles.add(article['title'])
                    unique_articles.append(article)
            
            print(f"  ✅ Found {len(unique_articles)} NewsAPI articles")
            return unique_articles
            
        except Exception as e:
            print(f"  ❌ Error fetching NewsAPI articles: {e}")
            return []
    
    def fetch_gnews(self, ticker: str, company_name: str = "") -> List[Dict]:
        """Fetch articles from Google News RSS via gnews — always returns real URLs."""
        try:
            print(f"🔍 Fetching Google News for {ticker}...")
            gn = GNews(language='en', country='US', period='7d', max_results=10)

            query = f"{ticker} stock" if not company_name else f"{company_name} {ticker}"
            results = gn.get_news(query)

            articles = []
            for item in results:
                try:
                    title = item.get('title', '')
                    url = item.get('url', '')
                    description = item.get('description', '')
                    publisher = item.get('publisher', {})
                    source_name = publisher.get('title', 'Google News') if isinstance(publisher, dict) else str(publisher)
                    pub_date = item.get('published date', '')

                    if not title or not url:
                        continue

                    # Parse date
                    try:
                        published_at = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z').isoformat()
                    except Exception:
                        published_at = datetime.now().isoformat()

                    content = f"{title}. {description}".strip()
                    sentiment_scores = self.analyzer.polarity_scores(content)

                    articles.append({
                        'source': source_name,
                        'title': title,
                        'description': description,
                        'url': url,
                        'publishedAt': published_at,
                        'sentiment': {
                            'compound': sentiment_scores['compound'],
                            'label': self.classify_sentiment(sentiment_scores['compound'])
                        }
                    })
                except Exception:
                    continue

            print(f"  ✅ Found {len(articles)} Google News articles")
            return articles

        except Exception as e:
            print(f"  ❌ Error fetching Google News: {e}")
            return []

    def fetch_rss_feeds(self, ticker: str, company_name: str = "") -> List[Dict]:
        """Fetch and filter articles from RSS feeds, keeping only those mentioning the ticker."""
        articles = []
        ticker_upper = ticker.upper()
        company_lower = company_name.lower() if company_name else ""

        feed_urls = {
            "Seeking Alpha": f"https://seekingalpha.com/api/sa/combined/{ticker_upper}.xml",
            "MarketWatch": "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
            "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
            "CNBC": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
            "Benzinga": "https://www.benzinga.com/feed",
        }

        for source_name, feed_url in feed_urls.items():
            try:
                print(f"🔍 Fetching {source_name} RSS for {ticker}...")
                feed = feedparser.parse(feed_url)
                count = 0

                for entry in feed.entries[:30]:  # scan up to 30 entries per feed
                    try:
                        title = entry.get('title', '')
                        url = entry.get('link', '')
                        summary = entry.get('summary', '') or entry.get('description', '')
                        # Strip HTML tags from summary
                        if summary:
                            summary = BeautifulSoup(summary, 'html.parser').get_text(separator=' ', strip=True)

                        if not title or not url:
                            continue

                        # For global feeds, filter to ticker/company mentions only
                        if source_name != "Seeking Alpha":
                            combined = f"{title} {summary}".lower()
                            if ticker_upper.lower() not in combined and (not company_lower or company_lower not in combined):
                                continue

                        # Parse date
                        published_at = datetime.now().isoformat()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            try:
                                published_at = datetime(*entry.published_parsed[:6]).isoformat()
                            except Exception:
                                pass

                        content = f"{title}. {summary}".strip()
                        sentiment_scores = self.analyzer.polarity_scores(content)

                        articles.append({
                            'source': source_name,
                            'title': title,
                            'description': summary[:300] if summary else '',
                            'url': url,
                            'publishedAt': published_at,
                            'sentiment': {
                                'compound': sentiment_scores['compound'],
                                'label': self.classify_sentiment(sentiment_scores['compound'])
                            }
                        })
                        count += 1
                        if count >= 5:  # max 5 per feed
                            break

                    except Exception:
                        continue

                print(f"  ✅ Found {count} {source_name} articles")

            except Exception as e:
                print(f"  ❌ Error fetching {source_name} RSS: {e}")
                continue

        return articles

    def fetch_finviz_news(self, ticker: str) -> List[Dict]:
        """Fetch stock-specific news from Finviz."""
        try:
            print(f"🔍 Fetching Finviz news for {ticker}...")
            from finvizfinance.quote import finvizfinance

            stock = finvizfinance(ticker)
            news_df = stock.ticker_news()

            if news_df is None or news_df.empty:
                print(f"  ⚠️ No Finviz news found for {ticker}")
                return []

            articles = []
            for _, row in news_df.head(10).iterrows():
                try:
                    title = str(row.get('Title', '') or row.get('title', ''))
                    url = str(row.get('Link', '') or row.get('link', '') or row.get('URL', '') or row.get('url', ''))
                    date_val = row.get('Date', '') or row.get('date', '')

                    if not title or not url or url == 'nan':
                        continue

                    # Parse date
                    published_at = datetime.now().isoformat()
                    if date_val:
                        try:
                            published_at = datetime.strptime(str(date_val), '%b-%d-%y %I:%M%p').isoformat()
                        except Exception:
                            try:
                                published_at = str(date_val)
                            except Exception:
                                pass

                    sentiment_scores = self.analyzer.polarity_scores(title)

                    articles.append({
                        'source': 'Finviz',
                        'title': title,
                        'description': '',
                        'url': url,
                        'publishedAt': published_at,
                        'sentiment': {
                            'compound': sentiment_scores['compound'],
                            'label': self.classify_sentiment(sentiment_scores['compound'])
                        }
                    })
                except Exception:
                    continue

            print(f"  ✅ Found {len(articles)} Finviz articles")
            return articles

        except Exception as e:
            print(f"  ❌ Error fetching Finviz news: {e}")
            return []

    def fetch_stocktwits(self, ticker: str) -> List[Dict]:
        """Fetch messages from Stocktwits using their public JSON API."""
        try:
            print(f"🔍 Fetching Stocktwits messages for {ticker}...")
            
            # Use the public Stocktwits API endpoint
            url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            messages = data.get('messages', [])
            
            if not messages:
                print(f"  ⚠️ No Stocktwits messages found for {ticker}")
                return []
            
            articles = []
            for message in messages[:10]:  # Limit to 10 messages as requested
                try:
                    body = message.get('body', '')
                    created_at = message.get('created_at', '')
                    message_id = message.get('id')
                    user_data = message.get('user', {}) or {}
                    username = user_data.get('username')
                    
                    # Skip if no body content
                    if not body or len(body.strip()) < 10:
                        continue
                    
                    # Parse created_at timestamp
                    published_at = datetime.now().isoformat()  # Fallback
                    if created_at:
                        try:
                            # Stocktwits usually returns ISO format timestamps
                            # Example: "2025-10-08T14:24:00Z"
                            if created_at.endswith('Z'):
                                created_at = created_at[:-1]  # Remove 'Z'
                            published_at = datetime.fromisoformat(created_at).isoformat()
                        except:
                            published_at = datetime.now().isoformat()
                    
                    # Prefer the canonical Stocktwits message permalink.
                    source_url = None
                    if message_id and username:
                        source_url = f"https://stocktwits.com/{username}/message/{message_id}"

                    # Fall back to the API-provided source URL only if it isn't
                    # the generic site root or mobile landing page.
                    source_data = message.get('source', {})
                    if not source_url and isinstance(source_data, dict):
                        candidate_url = source_data.get('url')
                        if candidate_url and candidate_url.rstrip('/').lower() not in {
                            'https://stocktwits.com',
                            'http://stocktwits.com',
                            'https://www.stocktwits.com',
                            'http://www.stocktwits.com',
                            'https://stocktwits.com/mobile',
                            'http://stocktwits.com/mobile',
                            'https://www.stocktwits.com/mobile',
                            'http://www.stocktwits.com/mobile',
                        }:
                            source_url = candidate_url
                    
                    # Calculate sentiment from message body
                    sentiment_scores = self.analyzer.polarity_scores(body)
                    
                    # Use body as both title and description for Stocktwits messages
                    title = body[:100] + "..." if len(body) > 100 else body
                    
                    articles.append({
                        'source': 'Stocktwits',
                        'title': title,
                        'description': body,
                        'url': source_url,
                        'message_id': message_id,
                        'username': username,
                        'publishedAt': published_at,
                        'sentiment': {
                            'compound': sentiment_scores['compound'],
                            'label': self.classify_sentiment(sentiment_scores['compound'])
                        }
                    })
                    
                except Exception as e:
                    print(f"  ⚠️ Error processing Stocktwits message: {e}")
                    continue
            
            print(f"  ✅ Found {len(articles)} Stocktwits messages")
            return articles
            
        except Exception as e:
            print(f"  ❌ Error fetching Stocktwits messages: {e}")
            return []
    
    def is_relevant_article(self, article: Dict, ticker: str, company_name: str) -> bool:
        """Check if an article is relevant to the stock."""
        title = article.get('title', '') or ''
        description = article.get('description', '') or ''
        content = f"{title.lower()} {description.lower()}"
        
        ticker_lower = ticker.lower()
        company_lower = company_name.lower() if company_name else ""
        
        # Must contain ticker or company name
        has_ticker = ticker_lower in content
        has_company = company_lower and company_lower in content
        
        if not (has_ticker or has_company):
            return False
        
        # Filter out irrelevant content
        irrelevant_terms = [
            'software library', 'github', 'programming', 'code repository',
            'domain name', 'website hosting', 'app store review'
        ]
        
        for term in irrelevant_terms:
            if term in content:
                return False
        
        return True
    
    def fetch_comprehensive_news(self, ticker: str, limit: int = 50) -> str:
        """Fetch news from all sources and combine them."""
        
        print(f"📰 Fetching comprehensive news for {ticker}...")
        
        all_articles = []
        
        # Fetch from Yahoo Finance
        yahoo_articles = self.fetch_yahoo_finance_news(ticker)
        all_articles.extend(yahoo_articles)

        # Fetch from Google News via gnews
        gnews_articles = self.fetch_gnews(ticker)
        all_articles.extend(gnews_articles)

        # Fetch from RSS feeds (Seeking Alpha, MarketWatch, Reuters, CNBC, Benzinga)
        rss_articles = self.fetch_rss_feeds(ticker)
        all_articles.extend(rss_articles)

        # Fetch from Finviz
        finviz_articles = self.fetch_finviz_news(ticker)
        all_articles.extend(finviz_articles)

        # Fetch from Stocktwits
        stocktwits_articles = self.fetch_stocktwits(ticker)
        all_articles.extend(stocktwits_articles)
        
        # Deduplicate by lowercase title
        seen_titles = set()
        unique_articles = []
        
        for article in all_articles:
            title_key = article['title'].lower().strip()
            if title_key not in seen_titles and len(title_key) > 5:  # Minimum title length
                seen_titles.add(title_key)
                unique_articles.append(article)
        
        # Sort by published date (most recent first)
        unique_articles.sort(key=lambda x: x['publishedAt'], reverse=True)
        
        # Limit results
        final_articles = unique_articles[:limit]
        
        # Save to file
        os.makedirs("data", exist_ok=True)
        output_path = os.path.join("data", f"{ticker}_comprehensive_news.json")
        
        with open(output_path, "w") as f:
            json.dump(final_articles, f, indent=2)
        
        print(f"✅ Saved {len(final_articles)} comprehensive news articles to {output_path}")
        print(f"   📊 Sources breakdown:")
        
        source_counts = {}
        for article in final_articles:
            source = article['source']
            source_counts[source] = source_counts.get(source, 0) + 1
        
        for source, count in source_counts.items():
            print(f"      {source}: {count} articles")
        
        return output_path

def fetch_enhanced_news_sentiment(ticker: str, limit: int = 30) -> str:
    """Enhanced news fetching function to replace the original."""
    scraper = EnhancedNewsScraper()
    return scraper.fetch_comprehensive_news(ticker, limit)

if __name__ == "__main__":
    # Test with a few tickers
    test_tickers = ["AAPL", "TSLA", "MSFT"]
    
    for ticker in test_tickers:
        print(f"\n{'='*50}")
        print(f"Testing enhanced news scraping for {ticker}")
        print('='*50)
        
        result_path = fetch_enhanced_news_sentiment(ticker, 40)
        print(f"Results saved to: {result_path}")
        
        # Brief pause between requests
        time.sleep(2)
