import streamlit as st
import json
import os
import glob
import pandas as pd
import plotly.express as px
from main import run_pipeline
from scraping.news_scraper import fetch_news_sentiment

st.set_page_config(page_title="StockScope", layout="centered")
st.title("📊 StockScope - Multi-Source Sentiment Tracker")

# --- Helpers ---
@st.cache_data(ttl=60)
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

@st.cache_resource
def get_processed_cache():
    return set()

def get_available_tickers():
    reddit_files = glob.glob("data/*_reddit_sentiment.json")
    news_files = glob.glob("data/*_news_sentiment.json")
    tickers = set()

    for path in reddit_files + news_files:
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
    reddit_data = load_json(f"data/{ticker}_reddit_sentiment.json")
    news_data = load_json(f"data/{ticker}_news_sentiment.json")

    reddit_df = pd.DataFrame([{
        "title": p.get("title"),
        "score": p.get("score", 0),
        "subreddit": p.get("subreddit", ""),
        "sentiment": p.get("sentiment", {}).get("label", ""),
        "compound": p.get("sentiment", {}).get("compound", 0),
        "created_dt": pd.to_datetime(p.get("created"), errors="coerce"),
        "source": "Reddit"
    } for p in reddit_data]) if reddit_data else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

    news_df = pd.DataFrame([{
        "title": n.get("title"),
        "score": None,
        "subreddit": None,
        "sentiment": n.get("sentiment", {}).get("label", ""),
        "compound": n.get("sentiment", {}).get("compound", 0),
        "created_dt": pd.to_datetime(n.get("publishedAt"), utc=True, errors="coerce").tz_convert(None) if n.get("publishedAt") else pd.NaT,        "source": "News"
    } for n in news_data]) if news_data else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

    # Normalize and concatenate
    reddit_df["created_dt"] = pd.to_datetime(reddit_df["created_dt"], errors="coerce")
    news_df["created_dt"] = pd.to_datetime(news_df["created_dt"], errors="coerce")
    combined_df = pd.concat([reddit_df, news_df], ignore_index=True)
    combined_df["source"] = combined_df["source"].str.capitalize()
    combined_df["created_dt"] = pd.to_datetime(combined_df["created_dt"], errors="coerce")

    return combined_df if not combined_df.empty else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

# --- Tabs ---
tab1, tab2 = st.tabs(["📂 Analyze Existing", "📥 Fetch New Data"])
processed_cache = get_processed_cache()
df = pd.DataFrame()

with tab1:
    tickers = get_available_tickers()
    if tickers:
        selected_ticker = st.selectbox("Select a stock ticker to analyze:", tickers)
        if selected_ticker:
            df = load_dataframes(selected_ticker)
    else:
        st.warning("No available tickers found. Please fetch new data first.")

with tab2:
    input_ticker = st.text_input("Enter a stock ticker to fetch data:", value="AAPL").upper()
    force_refresh = st.checkbox("🔄 Force refresh data")

    if st.button("Fetch + Analyze"):
        if force_refresh or input_ticker not in processed_cache:
            with st.spinner("Fetching Reddit and News..."):
                run_pipeline(input_ticker)
                fetch_news_sentiment(input_ticker)
                processed_cache.add(input_ticker)
            st.success(f"✅ Fetched and analyzed data for {input_ticker}!")
        else:
            st.info(f"{input_ticker} already processed. Showing cached results.")
        df = load_dataframes(input_ticker)

# --- Visualize ---
if not df.empty:
    df = df[df["created_dt"].notna()]
    df["date"] = df["created_dt"].dt.date
    df["source"] = df["source"].fillna("Unknown").str.strip().str.capitalize()
    df["compound"] = df["compound"].fillna(0)

    st.subheader("📊 Sentiment Distribution")
    selected_sources = st.multiselect("Include sources:", ["Reddit", "News"], default=["Reddit", "News"])
    compound_range = st.slider("📈 Filter by compound sentiment score", -1.0, 1.0, (-1.0, 1.0), 0.05)

    filtered_df = df[
        (df["source"].isin(selected_sources)) &
        (df["compound"] >= compound_range[0]) &
        (df["compound"] <= compound_range[1])
    ]

    if filtered_df.empty:
        st.info("No data available for the selected filters.")
    else:
        sentiment_counts = filtered_df["sentiment"].value_counts().reset_index()
        sentiment_counts.columns = ["sentiment", "count"]
        fig_pie = px.pie(
            sentiment_counts,
            names="sentiment",
            values="count",
            title="Sentiment Breakdown",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        grouped = filtered_df.groupby(["date", "sentiment"]).size().reset_index(name="count")
        fig_bar = px.bar(
            grouped,
            x="date",
            y="count",
            color="sentiment",
            barmode="group",
            title="Sentiment Over Time"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("📝 Posts and Articles")
        st.dataframe(filtered_df[["date", "source", "title", "sentiment", "compound"]])

        # Optional: feedback for missing sources
        if "Reddit" not in filtered_df["source"].unique():
            st.info("No Reddit data available.")
        if "News" not in filtered_df["source"].unique():
            st.info("No News data available.")
else:
    st.warning("No data loaded yet. Try fetching or selecting a ticker.")
