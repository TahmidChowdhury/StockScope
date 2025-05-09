import streamlit as st
from main import run_pipeline
import json
import os
import glob
from datetime import datetime
from collections import Counter
import plotly.express as px
import pandas as pd

# --- Streamlit Setup ---
st.set_page_config(page_title="StockScope", layout="centered")
st.title("📊 StockScope - Reddit Sentiment Tracker")

# --- Get Available Tickers ---
def get_available_tickers():
    files = glob.glob("data/*_reddit_sentiment.json")
    return sorted([os.path.basename(f).split("_")[0] for f in files])

tickers = get_available_tickers()

# --- UI ---
col1, col2 = st.columns([3, 1])
with col1:
    custom_ticker = st.text_input("Enter a stock ticker (or choose below):", value="AAPL").upper()
with col2:
    selected_ticker = st.selectbox("Or pick one:", tickers, index=0)

ticker = custom_ticker if custom_ticker else selected_ticker

# --- Load Data (with caching) ---
@st.cache_data
def load_data(ticker):
    filepath = f"data/{ticker}_reddit_sentiment.json"
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)

# --- Only Load on Button Click ---
# if st.button("Analyze"):
#     data = load_data(ticker) 
if st.button("Fetch + Analyze"):
    with st.spinner("Fetching Reddit posts and analyzing sentiment..."):
        output_path = run_pipeline(ticker)  # Run scraper + sentiment
        data = load_data(ticker)  # Then load what was saved

    if not data:
        st.error(f"No data found for ticker '{ticker}'.")
    else:
        st.success(f"Data fetched and analyzed for {ticker}!")
    if not data:
        st.error(f"No data found for ticker '{ticker}'. Try scraping it first.")
    else:
        # Format into DataFrame
        rows = []
        for post in data:
            rows.append({
                "title": post["title"],
                "score": post["score"],
                "subreddit": post["subreddit"],
                "sentiment": post["sentiment"]["label"],
                "compound": post["sentiment"]["compound"],
                "created": post["created"]
            })

        df = pd.DataFrame(rows)
        df["created_dt"] = pd.to_datetime(df["created"])
        df["date"] = df["created_dt"].dt.date

        # --- Show Date Range ---
        st.markdown(f"**Showing {len(df)} posts from** {df['created_dt'].min().strftime('%b %d, %Y')} **to** {df['created_dt'].max().strftime('%b %d, %Y')}")

        # --- Sentiment Pie Chart ---
        sentiment_counts = df["sentiment"].value_counts().reset_index()
        sentiment_counts.columns = ["sentiment", "count"]
        fig_pie = px.pie(sentiment_counts, names="sentiment", values="count",
                         title="Sentiment Distribution",
                         color_discrete_sequence=px.colors.qualitative.Set1)
        st.plotly_chart(fig_pie, use_container_width=True)

        # --- Time Series Bar Chart ---
        daily_sentiment = df.groupby(["date", "sentiment"]).size().reset_index(name="count")
        fig_bar = px.bar(daily_sentiment, x="date", y="count", color="sentiment",
                         title="Daily Post Sentiment", barmode="group")
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- Sample Posts ---
        st.subheader("📝 Sample Reddit Posts")
        st.dataframe(df[["created", "subreddit", "title", "sentiment", "compound", "score"]])
