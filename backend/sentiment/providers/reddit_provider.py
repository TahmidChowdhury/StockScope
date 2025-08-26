"""Reddit sentiment provider using PRAW."""

import os
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from backend.sentiment.providers import SentimentProvider, RawSentimentItem, SentimentResult, SentimentSource

LOG = logging.getLogger("sentiment.reddit")


class RedditProvider:
    """Reddit sentiment provider - scaffold for future implementation."""
    
    def __init__(self):
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_SECRET") 
        self.user_agent = os.getenv("REDDIT_USER_AGENT", "StockScope/1.0")
        self._client = None
    
    def is_available(self) -> bool:
        """Check if Reddit credentials are configured."""
        return bool(self.client_id and self.client_secret)
    
    def fetch(self, ticker: str, window: str) -> List[RawSentimentItem]:
        """
        TODO: Implement Reddit data fetching.
        
        Plan:
        1. Search subreddits: r/stocks, r/investing, r/SecurityAnalysis, r/wallstreetbets
        2. Query by ticker symbol and cashtag ($AAPL)
        3. Filter by time window (24h, 7d, 30d)
        4. Respect rate limits and Reddit API TOS
        5. Return RawSentimentItem objects
        """
        if not self.is_available():
            LOG.warning("Reddit provider not configured")
            return []
            
        LOG.info("TODO: Implement Reddit fetching for %s (window: %s)", ticker, window)
        return []
    
    def score(self, items: List[RawSentimentItem]) -> SentimentResult:
        """
        TODO: Implement sentiment scoring for Reddit items.
        
        Plan:
        1. Use VADER sentiment for titles and content
        2. Weight by Reddit score (upvotes)
        3. Filter out deleted/removed posts
        4. Aggregate to final sentiment score
        """
        LOG.info("TODO: Implement Reddit sentiment scoring")
        return SentimentResult(
            ticker="",
            source=SentimentSource.REDDIT,
            window="24h",
            sentiment_score=0.0,
            confidence=0.0,
            total_items=0,
            positive_count=0,
            neutral_count=0,
            negative_count=0,
            timestamp=datetime.utcnow()
        )