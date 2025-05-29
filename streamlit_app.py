import streamlit as st
import json
import os
import glob
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from main import run_pipeline, run_full_pipeline
from scraping.news_scraper import fetch_news_sentiment
from scraping.twitter_scraper import fetch_twitter_sentiment
from visualizations.plot_sentiment import generate_wordcloud_for_streamlit

# Page configuration
st.set_page_config(
    page_title="StockScope", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 10px 10px;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .stAlert {
        border-radius: 10px;
    }
    .sentiment-positive { color: #28a745; font-weight: bold; }
    .sentiment-negative { color: #dc3545; font-weight: bold; }
    .sentiment-neutral { color: #ffc107; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>📊 StockScope</h1><p>Multi-Source Sentiment Analysis Dashboard</p></div>', unsafe_allow_html=True)

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
    """Get available tickers without caching to ensure fresh data"""
    reddit_files = glob.glob("data/*_reddit_sentiment.json")
    news_files = glob.glob("data/*_news_sentiment.json")
    twitter_files = glob.glob("data/*_twitter_sentiment.json")
    tickers = set()

    for path in reddit_files + news_files + twitter_files:
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
    twitter_data = load_json(f"data/{ticker}_twitter_sentiment.json")

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

    # Twitter DataFrame
    twitter_df = pd.DataFrame([{
        "title": t.get("content"),
        "score": t.get("like_count", 0),
        "subreddit": f"@{t.get('username', 'unknown')}",
        "sentiment": t.get("sentiment_label", ""),
        "compound": t.get("sentiment", {}).get("compound", 0),
        "created_dt": pd.to_datetime(t.get("date"), errors="coerce"),
        "source": "Twitter"
    } for t in twitter_data]) if twitter_data else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

    # Normalize and concatenate
    reddit_df["created_dt"] = pd.to_datetime(reddit_df["created_dt"], errors="coerce")
    news_df["created_dt"] = pd.to_datetime(news_df["created_dt"], errors="coerce")
    twitter_df["created_dt"] = pd.to_datetime(twitter_df["created_dt"], errors="coerce")
    
    combined_df = pd.concat([reddit_df, news_df, twitter_df], ignore_index=True)
    combined_df["source"] = combined_df["source"].str.capitalize()
    combined_df["created_dt"] = pd.to_datetime(combined_df["created_dt"], errors="coerce")

    return combined_df if not combined_df.empty else pd.DataFrame(columns=["title", "score", "subreddit", "sentiment", "compound", "created_dt", "source"])

# --- Sidebar ---
# Sidebar for controls
with st.sidebar:
    st.header("🎛️ StockScope Control Panel")
    
    # === STEP 1: DATA STATUS ===
    st.subheader("📊 Current Data")
    tickers = get_available_tickers()
    
    if tickers:
        st.success(f"✅ {len(tickers)} stocks analyzed")
        st.write("**Available stocks:**")
        # Show tickers in a more compact way
        ticker_cols = st.columns(3)
        for i, ticker in enumerate(tickers):
            with ticker_cols[i % 3]:
                st.text(f"• {ticker}")
    else:
        st.warning("⚠️ No data yet")
        st.info("👆 Use 'Fetch Data' tab to get started")
    
    # Manual refresh if needed
    if st.button("🔄 Refresh List", help="Click if new data doesn't appear"):
        st.rerun()
    
    st.markdown("---")
    
    # === STEP 2: QUICK ANALYSIS ===
    st.subheader("⚡ Quick Analysis")
    st.write("**Analyze popular stocks instantly:**")
    
    # Show only available popular stocks
    popular_stocks = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN"]
    available_popular = [t for t in popular_stocks if t in tickers]
    
    if available_popular:
        # Create 2 columns for buttons
        button_cols = st.columns(2)
        for i, ticker in enumerate(available_popular):
            with button_cols[i % 2]:
                if st.button(f"📈 {ticker}", key=f"analyze_{ticker}", use_container_width=True):
                    st.session_state.quick_select = ticker
                    st.success(f"Selected {ticker}! Go to Dashboard tab.")
    else:
        st.info("Fetch some popular stocks first!")
    
    st.markdown("---")
    
    # === STEP 3: FILTERS (only show when data exists) ===
    if 'df' in locals() and not df.empty:
        st.subheader("🔧 Filter Data")
        
        # Simple source filter
        selected_sources = st.multiselect(
            "Data Sources:",
            options=["Reddit", "News", "Twitter"],
            default=["Reddit", "News", "Twitter"],
            help="Choose which sources to include"
        )
        
        # Simple sentiment filter with preset options
        sentiment_filter = st.selectbox(
            "Show Sentiment:",
            options=["All", "Positive Only", "Negative Only", "Neutral Only"],
            index=0,
            help="Filter by sentiment type"
        )
        
        # Convert to range for backward compatibility
        if sentiment_filter == "Positive Only":
            compound_range = (0.05, 1.0)
        elif sentiment_filter == "Negative Only":
            compound_range = (-1.0, -0.05)
        elif sentiment_filter == "Neutral Only":
            compound_range = (-0.05, 0.05)
        else:
            compound_range = (-1.0, 1.0)
        
        st.markdown("---")
    
    # === STEP 4: QUICK ACTIONS ===
    st.subheader("🚀 Quick Actions")
    
    # Fetch popular stocks
    st.write("**Get data for trending stocks:**")
    trending_buttons = st.columns(2)
    with trending_buttons[0]:
        if st.button("📊 Get AAPL", use_container_width=True):
            st.session_state.auto_fetch = "AAPL"
    with trending_buttons[1]:
        if st.button("📊 Get TSLA", use_container_width=True):
            st.session_state.auto_fetch = "TSLA"
    
    # Data management
    st.markdown("**🗂️ Data Management:**")
    if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
        if st.button("⚠️ Confirm Delete", key="confirm_delete"):
            try:
                for file in glob.glob("data/*.json"):
                    os.remove(file)
                st.success("✅ All data cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    st.markdown("---")
    
    # === STEP 5: HELP ===
    with st.expander("❓ How to Use StockScope"):
        st.markdown("""
        **🎯 Getting Started:**
        1. Go to **"Fetch Data"** tab
        2. Enter a stock ticker (like AAPL)
        3. Click **"Fetch & Analyze"**
        4. Go to **"Dashboard"** tab to view results
        
        **⚡ Quick Tips:**
        - Use buttons above for instant analysis
        - Filter data with the controls
        - Download results as CSV
        
        **📊 Understanding Sentiment:**
        - 🟢 **Positive**: Good news/optimistic posts
        - 🟡 **Neutral**: Factual/mixed sentiment  
        - 🔴 **Negative**: Bad news/pessimistic posts
        """)

# Initialize processed cache
processed_cache = get_processed_cache()

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    # Enhanced tabs with better styling
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📥 Fetch Data", "ℹ️ About"])
    
    with tab1:
        st.subheader("📈 Analyze Existing Data")
        
        if tickers:
            # Better ticker selection with search
            selected_ticker = st.selectbox(
                "🔍 Select a stock ticker:", 
                options=[""] + tickers,
                index=0,
                help="Choose a ticker to analyze its sentiment data"
            )
            
            if selected_ticker:
                df = load_dataframes(selected_ticker)
                
                if not df.empty:
                    # Display key metrics at the top
                    col_metrics = st.columns(4)
                    
                    total_posts = len(df)
                    reddit_posts = len(df[df['source'] == 'Reddit'])
                    news_articles = len(df[df['source'] == 'News'])
                    twitter_posts = len(df[df['source'] == 'Twitter'])
                    avg_sentiment = df['compound'].mean()
                    
                    with col_metrics[0]:
                        st.metric("Total Posts", total_posts)
                    with col_metrics[1]:
                        st.metric("Reddit Posts", reddit_posts)
                    with col_metrics[2]:
                        st.metric("News Articles", news_articles)
                    with col_metrics[3]:
                        sentiment_color = "normal"
                        if avg_sentiment > 0.1:
                            sentiment_color = "normal"
                        elif avg_sentiment < -0.1:
                            sentiment_color = "inverse"
                        st.metric("Avg Sentiment", f"{avg_sentiment:.3f}", 
                                delta=None, delta_color=sentiment_color)
        else:
            st.warning("⚠️ No data available. Please fetch some data first!")
    
    with tab2:
        st.subheader("📥 Fetch New Stock Data")
        
        # Better input form
        with st.form("fetch_form"):
            col_input1, col_input2 = st.columns([2, 1])
            
            with col_input1:
                input_ticker = st.text_input(
                    "Stock Ticker", 
                    value="AAPL",
                    placeholder="Enter ticker (e.g., TSLA, AAPL, MSFT)",
                    help="Enter a valid stock ticker symbol"
                ).upper()
            
            with col_input2:
                force_refresh = st.checkbox("🔄 Force refresh", help="Re-fetch data even if it exists")
            
            fetch_button = st.form_submit_button("🚀 Fetch & Analyze", type="primary")
            
            if fetch_button and input_ticker:
                if force_refresh or input_ticker not in processed_cache:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        status_text.text("🔍 Fetching Reddit data...")
                        progress_bar.progress(25)
                        run_pipeline(input_ticker)
                        
                        status_text.text("📰 Fetching news data...")
                        progress_bar.progress(50)
                        fetch_news_sentiment(input_ticker)
                        
                        status_text.text("🐦 Fetching Twitter data...")
                        progress_bar.progress(75)
                        try:
                            twitter_path = fetch_twitter_sentiment(input_ticker, max_tweets=20, skip_rate_limit_wait=True)
                            if not twitter_path:
                                status_text.text("⚠️ Twitter rate limited, creating sample data...")
                                from scraping.twitter_scraper import create_sample_twitter_data
                                create_sample_twitter_data(input_ticker, num_tweets=15)
                        except Exception as e:
                            st.warning(f"Twitter API issue: {str(e)}. Using sample data instead.")
                            from scraping.twitter_scraper import create_sample_twitter_data
                            create_sample_twitter_data(input_ticker, num_tweets=15)
                        
                        status_text.text("✅ Analysis complete!")
                        progress_bar.progress(100)
                        processed_cache.add(input_ticker)
                        
                        st.success(f"✅ Successfully analyzed {input_ticker}!")
                        st.balloons()
                        
                        # Load the newly fetched data
                        df = load_dataframes(input_ticker)
                    except Exception as e:
                        st.error(f"❌ Error fetching data: {str(e)}")
                else:
                    st.info(f"📊 {input_ticker} data already exists. Use force refresh to update.")
                    df = load_dataframes(input_ticker)
    
    with tab3:
        st.subheader("ℹ️ About StockScope")
        st.markdown("""
        **StockScope** is a comprehensive sentiment analysis tool that tracks public opinion about stocks across multiple platforms:
        
        **📊 Features:**
        - 🔴 **Reddit Analysis**: Scrapes relevant subreddits for stock discussions
        - 📰 **News Sentiment**: Analyzes financial news articles
        - 🐦 **Twitter Sentiment**: Gauges public sentiment from Twitter
        - 📈 **Real-time Visualization**: Interactive charts and metrics
        - ☁️ **Word Clouds**: Visual representation of trending topics
        - 🎯 **Filtering**: Customizable date and sentiment filters
        
        **🛠️ Technology Stack:**
        - Frontend: Streamlit
        - Sentiment Analysis: VADER
        - Data Sources: Reddit API, News APIs, Twitter API
        - Visualization: Plotly, Matplotlib
        """)

with col2:
    st.subheader("🎛️ Analysis Controls")
    
    # Initialize default filter values
    selected_sources = ["Reddit", "News", "Twitter"]
    compound_range = (-1.0, 1.0)
    date_range = None
    
    if 'df' in locals() and not df.empty:
        # Advanced filtering controls
        st.markdown("### 🔧 Filters")
        
        # Source selection with icons
        selected_sources = st.multiselect(
            "📊 Data Sources:",
            options=["Reddit", "News", "Twitter"],
            default=["Reddit", "News", "Twitter"],
            help="Select which data sources to include"
        )
        
        # Sentiment score filter with better labels
        compound_range = st.slider(
            "📈 Sentiment Score Range",
            min_value=-1.0,
            max_value=1.0,
            value=(-1.0, 1.0),
            step=0.05,
            help="Filter posts by sentiment score (-1: very negative, +1: very positive)"
        )
        
        # Date range filter
        if not df.empty and 'created_dt' in df.columns:
            min_date = df['created_dt'].min().date()
            max_date = df['created_dt'].max().date()
            
            date_range = st.date_input(
                "📅 Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                help="Select date range for analysis"
            )

# Enhanced visualization section
if 'df' in locals() and not df.empty:
    # Apply filters
    df_filtered = df[df["created_dt"].notna()]
    df_filtered["date"] = df_filtered["created_dt"].dt.date
    df_filtered["source"] = df_filtered["source"].fillna("Unknown").str.strip().str.capitalize()
    df_filtered["compound"] = df_filtered["compound"].fillna(0)

    # Apply user filters
    df_filtered = df_filtered[
        (df_filtered["source"].isin(selected_sources)) &
        (df_filtered["compound"] >= compound_range[0]) &
        (df_filtered["compound"] <= compound_range[1])
    ]
    
    # Apply date filter if available
    if 'date_range' in locals() and len(date_range) == 2:
        df_filtered = df_filtered[
            (df_filtered["date"] >= date_range[0]) &
            (df_filtered["date"] <= date_range[1])
        ]

    if not df_filtered.empty:
        st.markdown("---")
        st.header("📊 Sentiment Analysis Results")
        
        # Create enhanced visualizations in columns
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            # Enhanced pie chart
            sentiment_counts = df_filtered["sentiment"].value_counts().reset_index()
            sentiment_counts.columns = ["sentiment", "count"]
            
            colors = {'positive': '#28a745', 'neutral': '#ffc107', 'negative': '#dc3545'}
            fig_pie = px.pie(
                sentiment_counts,
                names="sentiment",
                values="count",
                title="🥧 Sentiment Distribution",
                color="sentiment",
                color_discrete_map=colors
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with viz_col2:
            # Enhanced sentiment over time
            grouped = df_filtered.groupby(["date", "sentiment"]).size().reset_index(name="count")
            fig_bar = px.bar(
                grouped,
                x="date",
                y="count",
                color="sentiment",
                barmode="group",
                title="📈 Sentiment Trends Over Time",
                color_discrete_map=colors
            )
            fig_bar.update_layout(xaxis_title="Date", yaxis_title="Number of Posts")
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Word cloud section
        st.subheader("☁️ Trending Topics")
        combined_text = " ".join(df_filtered["title"].dropna().tolist())
        if combined_text and len(combined_text) > 10:
            fig_wordcloud = generate_wordcloud_for_streamlit(combined_text, title="Most Discussed Topics")
            if fig_wordcloud:
                st.pyplot(fig_wordcloud)
        else:
            st.info("💡 Not enough text data for word cloud generation")
        
        # Enhanced data table
        st.subheader("📋 Detailed Data")
        
        # Add sentiment styling to dataframe
        def style_sentiment(val):
            if val == 'positive':
                return 'background-color: #d4edda; color: #155724'
            elif val == 'negative':
                return 'background-color: #f8d7da; color: #721c24'
            else:
                return 'background-color: #fff3cd; color: #856404'
        
        display_df = df_filtered[["date", "source", "title", "sentiment", "compound"]].copy()
        display_df = display_df.sort_values("date", ascending=False)
        
        st.dataframe(
            display_df.style.map(style_sentiment, subset=['sentiment']),
            use_container_width=True,
            height=400
        )
        
        # Download option
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="💾 Download Data as CSV",
            data=csv,
            file_name=f"{selected_ticker}_sentiment_data.csv",
            mime="text/csv"
        )
    else:
        st.info("🔍 No data matches your current filters. Try adjusting the criteria.")
else:
    # Welcome message for new users
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 10px; margin: 2rem 0;">
        <h2>👋 Welcome to StockScope!</h2>
        <p>Get started by fetching sentiment data for your favorite stocks.</p>
        <p>Use the <strong>"Fetch Data"</strong> tab to analyze a stock ticker.</p>
    </div>
    """, unsafe_allow_html=True)
