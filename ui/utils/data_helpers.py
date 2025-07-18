import streamlit as st
import json
import os
import glob
import pandas as pd
from datetime import datetime

@st.cache_data(ttl=60)
def load_json(path):
    """Load JSON data from file with caching"""
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def get_available_tickers():
    """Get available tickers without caching to ensure fresh data"""
    reddit_files = glob.glob("data/*_reddit_sentiment.json")
    news_files = glob.glob("data/*_news_sentiment.json")
    twitter_files = glob.glob("data/*_twitter_sentiment.json")
    sec_files = glob.glob("data/*_sec_sentiment.json")
    tickers = set()

    for path in reddit_files + news_files + twitter_files + sec_files:
        try:
            with open(path, "r") as f:
                data = json.load(f)
                if data:
                    ticker = os.path.basename(path).split("_")[0]
                    tickers.add(ticker)
        except json.JSONDecodeError:
            continue

    return sorted(tickers)

def load_dataframes(ticker):
    """Load and combine all data sources for a ticker"""
    reddit_data = load_json(f"data/{ticker}_reddit_sentiment.json")
    news_data = load_json(f"data/{ticker}_news_sentiment.json")
    sec_data = load_json(f"data/{ticker}_sec_sentiment.json")

    # Reddit DataFrame
    reddit_df = pd.DataFrame([{
        "title": p.get("title"),
        "score": p.get("score", 0),
        "subreddit": p.get("subreddit", ""),
        "sentiment": p.get("sentiment", {}).get("label", ""),
        "compound": p.get("sentiment", {}).get("compound", 0),
        "created_dt": pd.to_datetime(p.get("created"), errors="coerce"),
        "source": "Reddit"
    } for p in reddit_data]) if reddit_data else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

    # News DataFrame
    news_df = pd.DataFrame([{
        "title": n.get("title"),
        "score": None,
        "subreddit": None,
        "sentiment": n.get("sentiment", {}).get("label", ""),
        "compound": n.get("sentiment", {}).get("compound", 0),
        "created_dt": pd.to_datetime(n.get("publishedAt"), utc=True, errors="coerce").tz_convert(None) if n.get("publishedAt") else pd.NaT,
        "source": "News"
    } for n in news_data]) if news_data else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

    # SEC DataFrame
    sec_df = pd.DataFrame([{
        "title": f"{s.get('form_type')}: {s.get('description', 'SEC Filing')}",
        "score": None,
        "subreddit": f"Form {s.get('form_type', 'Unknown')}",
        "sentiment": s.get("sentiment", {}).get("label", ""),
        "compound": s.get("sentiment", {}).get("compound", 0),
        "created_dt": pd.to_datetime(s.get("filing_date"), errors="coerce"),
        "source": "SEC"
    } for s in sec_data]) if sec_data else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

    # Normalize and concatenate
    reddit_df["created_dt"] = pd.to_datetime(reddit_df["created_dt"], errors="coerce")
    news_df["created_dt"] = pd.to_datetime(news_df["created_dt"], errors="coerce")
    sec_df["created_dt"] = pd.to_datetime(sec_df["created_dt"], errors="coerce")
    
    # Combine all dataframes, handling empty ones properly
    dfs_to_combine = []
    if not reddit_df.empty:
        dfs_to_combine.append(reddit_df)
    if not news_df.empty:
        dfs_to_combine.append(news_df)
    if not sec_df.empty:
        dfs_to_combine.append(sec_df)
    
    if dfs_to_combine:
        combined_df = pd.concat(dfs_to_combine, ignore_index=True)
    else:
        combined_df = pd.DataFrame()  # Return empty DataFrame if no data
    
    combined_df["source"] = combined_df["source"].apply(lambda x: "SEC" if x == "SEC" else x.capitalize() if pd.notna(x) else x)
    combined_df["created_dt"] = pd.to_datetime(combined_df["created_dt"], errors="coerce")

    return combined_df if not combined_df.empty else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

def get_metric_description(metric):
    """Get description for investment metrics"""
    descriptions = {
        'sentiment_score': 'Overall sentiment from social media (-1 to +1)',
        'sentiment_trend': 'Direction of sentiment change over time',
        'volume_trend': 'Trend in discussion volume',
        'price_momentum': 'Price movement relative to average',
        'volatility': 'Price volatility (higher = more risky)',
        'rsi': 'Relative Strength Index (70+ overbought, 30- oversold)',
        'macd_signal': 'MACD signal strength (positive = bullish)'
    }
    return descriptions.get(metric, 'Investment analysis metric')

def filter_dataframe(df, selected_sources, compound_range, date_range=None):
    """Apply filters to dataframe"""
    if df.empty:
        return df
    
    # Apply filters
    df_filtered = df[df["created_dt"].notna()].copy()
    df_filtered["date"] = df_filtered["created_dt"].dt.date
    df_filtered["source"] = df_filtered["source"].fillna("Unknown").str.strip().str.capitalize()
    df_filtered["compound"] = df_filtered["compound"].fillna(0)

    # Apply user filters with case-insensitive matching
    selected_sources_upper = [s.upper() for s in selected_sources]
    df_filtered = df_filtered[
        (df_filtered["source"].str.upper().isin(selected_sources_upper)) &
        (df_filtered["compound"] >= compound_range[0]) &
        (df_filtered["compound"] <= compound_range[1])
    ]
    
    # Apply date filter if available
    if date_range and len(date_range) == 2:
        df_filtered = df_filtered[
            (df_filtered["date"] >= date_range[0]) &
            (df_filtered["date"] <= date_range[1])
        ]
    
    return df_filtered