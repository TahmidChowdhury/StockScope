
import streamlit as st
import json
import os
import glob
from datetime import datetime
import plotly.express as px
import pandas as pd
from main import run_pipeline
from scraping.news_scraper import fetch_news_sentiment

# --- Streamlit Setup ---
st.set_page_config(page_title="StockScope", layout="centered")
st.title("📊 StockScope - Multi-Source Sentiment Tracker")

# --- Get Available Tickers ---
def get_available_tickers():
    files = glob.glob("data/*_reddit_sentiment.json")
    return sorted([os.path.basename(f).split("_")[0] for f in files])

tickers = get_available_tickers()

# --- Ticker Input + Select ---
col1, col2 = st.columns([3, 1])
with col1:
    custom_ticker = st.text_input("Enter a stock ticker (or choose below):", value="AAPL").upper()
with col2:
    selected_ticker = st.selectbox("Or pick one:", tickers, index=0)

ticker = custom_ticker if custom_ticker else selected_ticker

# --- Load Helpers ---
@st.cache_data(ttl=60)
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

# --- Analyze Button ---
if st.button("Fetch + Analyze"):
    with st.spinner("Scraping Reddit and news, analyzing sentiment..."):
        run_pipeline(ticker)
        fetch_news_sentiment(ticker)

# --- Load Reddit Data ---
reddit_data = load_json(f"data/{ticker}_reddit_sentiment.json")
if reddit_data:
    reddit_df = pd.DataFrame([{
        "title": p["title"],
        "score": p["score"],
        "subreddit": p["subreddit"],
        "sentiment": p["sentiment"]["label"],
        "compound": p["sentiment"]["compound"],
        "created_dt": pd.to_datetime(p.get("created"), errors="coerce"),
    } for p in reddit_data])
else:
    reddit_df = pd.DataFrame(columns=["created_dt"])

# --- Load News Data ---
news_data = load_json(f"data/{ticker}_news_sentiment.json")
if news_data:
    news_df = pd.DataFrame([{
        "title": n["title"],
        "source": n["source"],
        "sentiment": n["sentiment"]["label"],
        "compound": n["sentiment"]["compound"],
        "created_dt": pd.to_datetime(n.get("publishedAt"), errors="coerce"),
    } for n in news_data])
else:
    news_df = pd.DataFrame(columns=["created_dt"])

# --- Combine Both ---
reddit_df["source"] = "Reddit"
news_df["source"] = "News"
merged_df = pd.concat([reddit_df, news_df], ignore_index=True)

# --- Source Filter ---
st.subheader("📂 Source Filter")
selected_sources = st.multiselect(
    "Select sources to include:",
    options=["Reddit", "News"],
    default=["Reddit", "News"]
)

# --- Filter and Clean Data ---
merged_df["created_dt"] = pd.to_datetime(merged_df["created_dt"], errors="coerce")
valid_dates = merged_df["created_dt"].notna()
filtered_df = merged_df[merged_df["source"].isin(selected_sources) & valid_dates]

# --- Sentiment Pie Chart ---
if not filtered_df.empty:
    filtered_df["date"] = filtered_df["created_dt"].dt.date

    sentiment_counts = filtered_df["sentiment"].value_counts().reset_index()
    sentiment_counts.columns = ["sentiment", "count"]
    fig_pie = px.pie(
        sentiment_counts,
        names="sentiment",
        values="count",
        title="Sentiment Distribution",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- Sentiment Over Time Chart ---
    grouped = filtered_df.groupby(["date", "sentiment"]).size().reset_index(name="count")
    fig_bar = px.bar(
        grouped,
        x="date",
        y="count",
        color="sentiment",
        barmode="group",
        title="Sentiment Over Time",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Data Table ---
    st.subheader("📝 Posts and Articles")
    st.dataframe(filtered_df[["date", "source", "title", "sentiment", "compound"]])
else:
    st.warning("No sentiment data available. Please try fetching again.")
