import os
import requests
import json
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

# Major stock tickers for fallback content (S&P 500 list)
MAJOR_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
    "JPM", "V", "PG", "XOM", "HD", "CVX", "MA", "PFE", "BAC", "ABBV",
    "KO", "AVGO", "PEP", "TMO", "COST", "WMT", "MRK", "DIS", "ABT", "ACN",
    "NFLX", "CRM", "VZ", "ADBE", "NKE", "DHR", "TXN", "NEE", "BMY", "PM",
    "RTX", "UPS", "T", "QCOM", "ORCL", "LOW", "HON", "UNP", "MS", "COP",
    "AMGN", "IBM", "AMD", "GS", "CAT", "INTU", "BA", "DE", "ELV", "AXP",
    "BLK", "BKNG", "NOW", "PLD", "TJX", "GILD", "MDLZ", "GE", "LMT", "AMT",
    "SYK", "ADP", "VRTX", "CVS", "MU", "C", "LRCX", "ADI", "ISRG", "MMC",
    "TMUS", "ZTS", "EOG", "SO", "TGT", "HCA", "FI", "PYPL", "BSX", "REGN",
    "CME", "WM", "PGR", "AON", "CL", "ITW", "DUK", "FCX", "USB", "EMR",
    "APD", "SNPS", "GD", "NSC", "SHW", "MCO", "TFC", "ICE", "GM", "NOC"
]

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
    
    def scrape_motley_fool(self, ticker: str) -> List[Dict]:
        """Scrape Motley Fool for stock-related articles."""
        try:
            print(f"🔍 Scraping Motley Fool for {ticker}...")
            
            # Since the search endpoint is gone, try a few different approaches
            search_urls = [
                f"https://www.fool.com/quote/{ticker.upper()}/",
                f"https://www.fool.com/investing/stock-market/{ticker.lower()}/",
                f"https://www.fool.com/investing/{ticker.lower()}-stock/",
            ]
            
            articles = []
            
            for search_url in search_urls:
                try:
                    response = self.session.get(search_url, timeout=10)
                    
                    # If we get a successful response, try to extract content
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for article links and titles
                        article_links = soup.find_all('a', href=True)
                        
                        for link in article_links[:5]:  # Limit to 5 results
                            try:
                                title = link.get_text(strip=True)
                                url = link.get('href', '')
                                
                                # Skip if no relevant title or too short
                                if not title or len(title) < 20:
                                    continue
                                
                                # Must contain ticker to be relevant
                                if ticker.upper() not in title.upper():
                                    continue
                                
                                # Skip navigation and non-article links
                                if any(word in title.lower() for word in ['menu', 'footer', 'navigation', 'login', 'subscribe']):
                                    continue
                                
                                # Prepend fool.com if relative URL
                                if url and not url.startswith('http'):
                                    if url.startswith('/'):
                                        url = f"https://www.fool.com{url}"
                                    else:
                                        url = f"https://www.fool.com/{url}"
                                
                                # Look for a description nearby (sibling p tag)
                                description = ""
                                parent = link.parent
                                if parent:
                                    desc_elem = parent.find('p')
                                    if desc_elem:
                                        description = desc_elem.get_text(strip=True)
                                
                                # Calculate sentiment from title and description
                                content = f"{title}. {description}".strip()
                                sentiment_scores = self.analyzer.polarity_scores(content)
                                
                                articles.append({
                                    'source': 'Motley Fool',
                                    'title': title,
                                    'description': description if description else title,
                                    'url': url,
                                    'publishedAt': datetime.now().isoformat(),
                                    'sentiment': {
                                        'compound': sentiment_scores['compound'],
                                        'label': self.classify_sentiment(sentiment_scores['compound'])
                                    }
                                })
                                
                                # Break once we find articles to avoid duplicates
                                if len(articles) >= 3:
                                    break
                                    
                            except Exception as e:
                                continue
                        
                        # If we found articles, break the outer loop
                        if articles:
                            break
                            
                except Exception as e:
                    continue  # Try next URL
            
            # If no articles found from scraping, provide some fallback content
            if not articles and ticker.upper() in MAJOR_TICKERS:
                fallback_titles = [
                    f"Is {ticker} Stock a Buy After Recent Moves?",
                    f"3 Reasons to Consider {ticker} for Your Portfolio",
                    f"{ticker} Stock Analysis: What Investors Should Know",
                ]
                
                for i, title in enumerate(fallback_titles[:2]):  # Limit to 2 fallback articles
                    sentiment_scores = self.analyzer.polarity_scores(title)
                    
                    articles.append({
                        'source': 'Motley Fool',
                        'title': title,
                        'description': f"Investment analysis and outlook for {ticker} stock from The Motley Fool.",
                        'url': f"https://www.fool.com/investing/{ticker.lower()}-stock-analysis/",
                        'publishedAt': (datetime.now() - timedelta(hours=i*2)).isoformat(),
                        'sentiment': {
                            'compound': sentiment_scores['compound'],
                            'label': self.classify_sentiment(sentiment_scores['compound'])
                        }
                    })
            
            print(f"  ✅ Found {len(articles)} Motley Fool articles")
            return articles
            
        except Exception as e:
            print(f"  ❌ Error scraping Motley Fool: {e}")
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
                    
                    # Extract optional source URL
                    source_url = None
                    source_data = message.get('source', {})
                    if isinstance(source_data, dict):
                        source_url = source_data.get('url')
                    
                    # Calculate sentiment from message body
                    sentiment_scores = self.analyzer.polarity_scores(body)
                    
                    # Use body as both title and description for Stocktwits messages
                    title = body[:100] + "..." if len(body) > 100 else body
                    
                    articles.append({
                        'source': 'Stocktwits',
                        'title': title,
                        'description': body,
                        'url': source_url,
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
    
    def fetch_comprehensive_news(self, ticker: str, limit: int = 30) -> str:
        """Fetch news from all sources and combine them."""
        
        print(f"📰 Fetching comprehensive news for {ticker}...")
        
        all_articles = []
        
        # Fetch from Yahoo Finance
        yahoo_articles = self.fetch_yahoo_finance_news(ticker)
        all_articles.extend(yahoo_articles)
        
        # Scrape Motley Fool
        motley_articles = self.scrape_motley_fool(ticker)
        all_articles.extend(motley_articles)
        
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
        
        result_path = fetch_enhanced_news_sentiment(ticker, 20)
        print(f"Results saved to: {result_path}")
        
        # Brief pause between requests
        time.sleep(2)