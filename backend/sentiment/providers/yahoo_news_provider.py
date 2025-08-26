"""Yahoo Finance news sentiment provider."""

import os
import logging
from typing import List
from datetime import datetime
from backend.sentiment.providers import SentimentProvider, RawSentimentItem, SentimentResult, SentimentSource

LOG = logging.getLogger("sentiment.yahoo")


class YahooNewsProvider:
    """Yahoo Finance news provider - scaffold for future implementation."""
    
    def is_available(self) -> bool:
        """Yahoo Finance news is available through yfinance library."""
        return True
    
    def fetch(self, ticker: str, window: str) -> List[RawSentimentItem]:
        """
        TODO: Implement Yahoo Finance news fetching.
        
        Plan:
        1. Use yfinance Ticker(symbol).news property
        2. Filter by time window
        3. Extract headline and summary
        4. Return RawSentimentItem objects
        """
        LOG.info("TODO: Implement Yahoo Finance news fetching for %s (window: %s)", ticker, window)
        return []
    
    def score(self, items: List[RawSentimentItem]) -> SentimentResult:
        """
        TODO: Implement sentiment scoring for news items.
        
        Plan:
        1. Use VADER or FinBERT for headline sentiment
        2. Weight by publication credibility
        3. Aggregate to final sentiment score
        """
        LOG.info("TODO: Implement Yahoo Finance news sentiment scoring")
        return SentimentResult(
            ticker="",
            source=SentimentSource.YAHOO_NEWS,
            window="24h",
            sentiment_score=0.0,
            confidence=0.0,
            total_items=0,
            positive_count=0,
            neutral_count=0,
            negative_count=0,
            timestamp=datetime.utcnow()
        )