"""Yahoo Finance news sentiment provider."""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import SentimentData, SentimentSource

LOG = logging.getLogger(__name__)

class YahooNewsProvider:
    """Yahoo Finance news provider."""
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
    
    def fetch_news(self, ticker: str, window: str = "1mo") -> List[dict]:
        """
        Fetch Yahoo Finance news for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            window: Time window (not directly used by Yahoo Finance)
        
        Returns:
            List of news articles with sentiment data
        """
        try:
            LOG.info("Fetching Yahoo Finance news for %s", ticker)
            
            # Get ticker object
            stock = yf.Ticker(ticker)
            
            # Get news data
            news_data = stock.news
            
            if not news_data:
                LOG.warning("No Yahoo Finance news found for %s", ticker)
                return []
            
            articles = []
            for article in news_data:
                try:
                    # Extract article data
                    title = article.get('title', '')
                    summary = article.get('summary', '')
                    
                    # Skip if no meaningful content
                    if not title and not summary:
                        continue
                    
                    # Combine title and summary for sentiment analysis
                    content = f"{title}. {summary}".strip()
                    
                    # Get sentiment
                    sentiment_scores = self.analyzer.polarity_scores(content)
                    
                    # Classify sentiment
                    compound = sentiment_scores['compound']
                    if compound >= 0.05:
                        sentiment_label = "positive"
                    elif compound <= -0.05:
                        sentiment_label = "negative"
                    else:
                        sentiment_label = "neutral"
                    
                    # Convert timestamp
                    published_at = article.get('providerPublishTime')
                    if published_at:
                        published_at = datetime.fromtimestamp(published_at).isoformat()
                    else:
                        published_at = datetime.now().isoformat()
                    
                    article_data = {
                        'title': title,
                        'description': summary,
                        'publishedAt': published_at,
                        'url': article.get('link', ''),
                        'source': article.get('publisher', 'Yahoo Finance'),
                        'sentiment': {
                            'compound': compound,
                            'pos': sentiment_scores['pos'],
                            'neu': sentiment_scores['neu'],
                            'neg': sentiment_scores['neg'],
                            'label': sentiment_label
                        }
                    }
                    
                    articles.append(article_data)
                    
                except Exception as e:
                    LOG.warning("Error processing Yahoo news article for %s: %s", ticker, e)
                    continue
            
            LOG.info("Successfully fetched %d Yahoo Finance news articles for %s", len(articles), ticker)
            return articles
            
        except Exception as e:
            LOG.error("Error fetching Yahoo Finance news for %s: %s", ticker, e)
            return []

    def score_sentiment(self, posts: List[dict]) -> List[SentimentData]:
        """
        Score sentiment for news items (already done in fetch_news).
        """
        LOG.info("Yahoo Finance news sentiment already scored during fetch")
        return [
            SentimentData(
                text=post.get('title', ''),
                score=post.get('sentiment', {}).get('compound', 0.0),
                timestamp=datetime.fromisoformat(post.get('publishedAt', datetime.now().isoformat()).replace('Z', '+00:00')),
                source=SentimentSource.YAHOO_NEWS,
                metadata=post
            )
            for post in posts
        ]