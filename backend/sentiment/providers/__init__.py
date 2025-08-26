"""Base interfaces and models for sentiment providers."""

from __future__ import annotations
from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class SentimentSource(str, Enum):
    """Available sentiment data sources."""
    REDDIT = "reddit"
    YAHOO_NEWS = "yfnews"
    STOCKTWITS = "stocktwits"
    SEC_EDGAR = "edgar"
    FINBERT = "finbert"


class RawSentimentItem(BaseModel):
    """Raw sentiment data item before processing."""
    id: str
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    source: SentimentSource
    timestamp: datetime
    author: Optional[str] = None
    score: Optional[float] = None  # Platform-specific score (upvotes, likes, etc.)
    metadata: Dict[str, Any] = {}


class SentimentResult(BaseModel):
    """Processed sentiment analysis result."""
    ticker: str
    source: SentimentSource
    window: str  # e.g., "24h", "7d", "30d"
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    total_items: int
    positive_count: int
    neutral_count: int
    negative_count: int
    timestamp: datetime
    raw_items: List[RawSentimentItem] = []


class SentimentProvider(Protocol):
    """Protocol for sentiment data providers."""
    
    def fetch(self, ticker: str, window: str) -> List[RawSentimentItem]:
        """Fetch raw sentiment items for a ticker within a time window."""
        ...
    
    def score(self, items: List[RawSentimentItem]) -> SentimentResult:
        """Process raw items and return sentiment analysis."""
        ...
    
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        ...