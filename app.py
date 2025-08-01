# Enhanced native Streamlit approach with better theming
import streamlit as st

# Page configuration with dark theme - MUST BE FIRST
st.set_page_config(
    page_title="StockScope Pro", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"  # Changed to expanded for better access to controls
)

from streamlit.components.v1 import html
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time
import threading
import json
import os

# Import utilities and main pipeline
from ui.utils.data_helpers import get_available_tickers, load_dataframes
from ui.utils.session_state import initialize_session_state
from main import run_full_pipeline
from scraping.news_scraper import fetch_news_sentiment

# Import page modules with correct function names
from ui.pages.dashboard import render_dashboard_tab
from ui.pages.quantitative_strategies import create_quantitative_strategies_page
from ui.pages.investment_advice import render_investment_advice_tab
from ui.pages.about import render_about_tab

# Initialize session state
initialize_session_state()

# Initialize additional session state for live data
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = False
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 60  # minutes
if 'is_fetching' not in st.session_state:
    st.session_state.is_fetching = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"

def apply_dark_theme():
    """Apply dark theme styling"""
    st.markdown("""
    <style>
    /* Force dark theme */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Dark theme for containers */
    .stContainer {
        background-color: #0E1117;
    }
    
    /* Enhanced sidebar styling */
    .css-1d391kg {
        background-color: #262730;
        border-right: 1px solid #4A4A4A;
    }
    
    /* Card styling for dark theme with better spacing */
    .pro-card {
        background-color: #262730;
        border: 1px solid #4A4A4A;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        overflow: hidden;
        word-wrap: break-word;
    }
    
    /* Metrics styling with responsive layout */
    .metric-card {
        background-color: #262730;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #4A4A4A;
        min-height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    /* Stock grid improvements for better spacing */
    .stock-grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 1.5rem;
        padding: 1rem 0;
    }
    
    .stock-card {
        background-color: #262730;
        border: 1px solid #4A4A4A;
        border-radius: 12px;
        padding: 1.5rem;
        min-height: 400px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        overflow: hidden;
    }
    
    /* Prevent text overflow in cards */
    .stock-card h3, .stock-card h4 {
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
        margin-bottom: 0.5rem;
    }
    
    /* Responsive metrics grid */
    .metrics-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    /* Better button spacing and sizing */
    .button-row {
        display: flex;
        gap: 0.5rem;
        margin-top: auto;
        padding-top: 1rem;
    }
    
    .button-row .stButton {
        flex: 1;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #667eea;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        width: 100%;
        min-height: 40px;
        font-size: 0.9rem;
    }
    
    .stButton > button:hover {
        background-color: #5a67d8;
        transform: translateY(-1px);
    }
    
    /* Success button styling */
    .stButton > button[kind="primary"] {
        background-color: #28a745;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #218838;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background-color: #262730;
        color: #FAFAFA;
        border: 1px solid #4A4A4A;
        border-radius: 8px;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #262730;
        border: 1px solid #4A4A4A;
        border-radius: 8px;
    }
    
    /* Success/Error/Warning styling for dark theme */
    .stAlert {
        background-color: #262730;
        border: 1px solid #4A4A4A;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    /* Text color */
    .stMarkdown {
        color: #FAFAFA;
    }
    
    /* Divider styling */
    .stDivider {
        border-color: #4A4A4A;
        margin: 1rem 0;
    }
    
    /* Plotly chart background */
    .plotly-chart {
        background-color: #262730;
    }
    
    /* Spinner styling */
    .stSpinner {
        color: #667eea;
    }
    
    /* Progress bar styling */
    .stProgress > div > div {
        background-color: #667eea;
    }
    
    /* Header metrics responsive layout */
    .header-metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    /* Tabs styling improvements */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        background-color: #262730;
        border-radius: 8px;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .stock-grid-container {
            grid-template-columns: 1fr;
            gap: 1rem;
        }
        
        .metrics-row {
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.5rem;
        }
        
        .header-metrics {
            grid-template-columns: 1fr;
            gap: 0.5rem;
        }
        
        .button-row {
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .stButton > button {
            font-size: 0.8rem;
            padding: 0.5rem;
        }
    }
    
    /* Chart container improvements */
    .chart-container {
        background-color: #262730;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        overflow: hidden;
    }
    
    /* Prevent overflow in recommendation panels */
    .recommendation-panel {
        max-width: 100%;
        overflow-x: auto;
    }
    
    /* Improved spacing for analysis panels */
    .analysis-panel {
        background-color: #262730;
        border: 1px solid #4A4A4A;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

def fetch_stock_data(ticker, show_progress=True):
    """Fetch data for a single stock with progress indication"""
    if show_progress:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text(f"🔄 Fetching data for {ticker}...")
        progress_bar.progress(10)
    
    try:
        # Run the full pipeline
        if show_progress:
            status_text.text(f"🔄 Scraping Reddit data for {ticker}...")
            progress_bar.progress(30)
        
        results = run_full_pipeline(ticker, reddit_limit=50, sec_limit=20)
        
        if show_progress:
            status_text.text(f"🔄 Fetching news data for {ticker}...")
            progress_bar.progress(60)
        
        # Fetch news data
        try:
            news_path = fetch_news_sentiment(ticker)
            results['news'] = news_path
        except Exception as e:
            st.warning(f"News scraping failed for {ticker}: {e}")
            results['news'] = None
        
        if show_progress:
            status_text.text(f"✅ Data fetched successfully for {ticker}")
            progress_bar.progress(100)
            time.sleep(1)  # Show completion briefly
            progress_bar.empty()
            status_text.empty()
        
        return results
    
    except Exception as e:
        if show_progress:
            status_text.text(f"❌ Error fetching data for {ticker}: {e}")
            progress_bar.empty()
        raise e

def refresh_all_data():
    """Refresh data for all existing stocks"""
    tickers = get_available_tickers()
    
    if not tickers:
        st.warning("No stocks to refresh")
        return
    
    st.info(f"🔄 Refreshing data for {len(tickers)} stocks...")
    
    # Create a progress bar for overall progress
    overall_progress = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        try:
            st.write(f"Refreshing {ticker}...")
            fetch_stock_data(ticker, show_progress=False)
            overall_progress.progress((i + 1) / len(tickers))
        except Exception as e:
            st.error(f"Failed to refresh {ticker}: {e}")
    
    overall_progress.empty()
    st.success("✅ All stocks refreshed successfully!")
    st.session_state.last_refresh = datetime.now()

def should_auto_refresh():
    """Check if auto refresh should trigger"""
    if not st.session_state.auto_refresh_enabled:
        return False
    
    time_since_refresh = datetime.now() - st.session_state.last_refresh
    return time_since_refresh.total_seconds() >= (st.session_state.refresh_interval * 60)

def create_data_management_sidebar():
    """Create enhanced sidebar with data management controls"""
    with st.sidebar:
        st.header("🎛️ StockScope Controls")
        
        # Live data status
        st.subheader("📡 Live Data Status")
        
        # Last refresh time
        time_since_refresh = datetime.now() - st.session_state.last_refresh
        minutes_ago = int(time_since_refresh.total_seconds() / 60)
        st.write(f"Last refresh: {minutes_ago} minutes ago")
        
        # Auto refresh toggle
        st.session_state.auto_refresh_enabled = st.checkbox(
            "🔄 Auto-refresh enabled",
            value=st.session_state.auto_refresh_enabled,
            help="Automatically refresh data at set intervals"
        )
        
        if st.session_state.auto_refresh_enabled:
            st.session_state.refresh_interval = st.slider(
                "Refresh interval (minutes)",
                min_value=15,
                max_value=240,
                value=st.session_state.refresh_interval,
                step=15,
                help="How often to refresh data automatically"
            )
            
            # Show next refresh time
            next_refresh = st.session_state.last_refresh + timedelta(minutes=st.session_state.refresh_interval)
            st.write(f"Next refresh: {next_refresh.strftime('%H:%M')}")
        
        # Manual refresh button
        if st.button("🔄 Refresh All Data", use_container_width=True):
            with st.spinner("Refreshing all stock data..."):
                refresh_all_data()
            st.rerun()
        
        st.divider()
        
        # Add new stock section
        st.subheader("➕ Add New Stock")
        
        with st.form("add_stock_form"):
            new_ticker = st.text_input(
                "Stock Symbol",
                placeholder="e.g., AAPL, GOOGL, TSLA",
                help="Enter a stock ticker symbol"
            ).upper().strip()
            
            # Data source selection
            st.write("**Data Sources:**")
            fetch_reddit = st.checkbox("Reddit discussions", value=True)
            fetch_news = st.checkbox("News articles", value=True)
            fetch_sec = st.checkbox("SEC filings", value=True)
            
            # Fetch limits
            with st.expander("🔧 Advanced Options"):
                reddit_limit = st.slider("Reddit posts limit", 10, 100, 50)
                sec_limit = st.slider("SEC filings limit", 5, 50, 20)
            
            submit_button = st.form_submit_button(
                "🚀 Add Stock",
                use_container_width=True
            )
            
            if submit_button and new_ticker:
                if new_ticker in get_available_tickers():
                    st.warning(f"{new_ticker} already exists. Use refresh to update data.")
                else:
                    try:
                        st.session_state.is_fetching = True
                        with st.spinner(f"Fetching data for {new_ticker}..."):
                            results = fetch_stock_data(new_ticker)
                        
                        st.success(f"✅ Successfully added {new_ticker}!")
                        st.session_state.is_fetching = False
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Failed to add {new_ticker}: {e}")
                        st.session_state.is_fetching = False
        
        st.divider()
        
        # Existing stock management
        st.subheader("📊 Manage Stocks")
        
        tickers = get_available_tickers()
        if tickers:
            # Stock selector for individual refresh
            selected_ticker = st.selectbox(
                "Select stock to refresh",
                [""] + tickers,
                help="Choose a stock to refresh individually"
            )
            
            if selected_ticker:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"🔄 Refresh {selected_ticker}", use_container_width=True):
                        try:
                            with st.spinner(f"Refreshing {selected_ticker}..."):
                                fetch_stock_data(selected_ticker)
                            st.success(f"✅ {selected_ticker} refreshed!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to refresh {selected_ticker}: {e}")
                
                with col2:
                    if st.button(f"🗑️ Remove", use_container_width=True):
                        # Remove stock data files
                        files_to_remove = [
                            f"data/{selected_ticker}_reddit_sentiment.json",
                            f"data/{selected_ticker}_news_sentiment.json",
                            f"data/{selected_ticker}_sec_sentiment.json",
                            f"data/{selected_ticker}_twitter_sentiment.json"
                        ]
                        
                        removed_count = 0
                        for file_path in files_to_remove:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                removed_count += 1
                        
                        if removed_count > 0:
                            st.success(f"✅ Removed {selected_ticker} ({removed_count} files)")
                            st.rerun()
                        else:
                            st.warning(f"No files found for {selected_ticker}")
                
                # Show individual stock stats
                df = load_dataframes(selected_ticker)
                if not df.empty:
                    st.write("**Quick Stats:**")
                    st.metric("Total Posts", len(df))
                    st.metric("Avg Sentiment", f"{df['compound'].mean():.3f}")
                    st.metric("Latest Post", df['created_dt'].max().strftime('%Y-%m-%d') if not df['created_dt'].isna().all() else "N/A")
            
            # Bulk operations
            st.subheader("🔧 Bulk Operations")
            
            if st.button("🔄 Refresh All Stocks", use_container_width=True):
                with st.spinner("Refreshing all stocks..."):
                    refresh_all_data()
                st.rerun()
            
            if st.button("🗑️ Clear All Data", use_container_width=True):
                # Confirmation
                st.error("⚠️ This will remove all stock data!")
                if st.button("⚠️ Confirm Clear All", use_container_width=True):
                    data_files = [f for f in os.listdir("data") if f.endswith("_sentiment.json")]
                    for file in data_files:
                        os.remove(os.path.join("data", file))
                    st.success("✅ All data cleared!")
                    st.rerun()
        else:
            st.info("No stocks available. Add a stock to get started!")

def create_navigation():
    """Create navigation sidebar"""
    with st.sidebar:
        st.header("🧭 Navigation")
        
        # Page selection
        pages = {
            "📊 Dashboard": "Dashboard",
            "🎯 Investment Advice": "Investment Advice",
            "📈 Quantitative Strategies": "Quantitative Strategies",
            "ℹ️ About": "About"
        }
        
        selected_page = st.selectbox(
            "Select Page",
            list(pages.keys()),
            index=list(pages.values()).index(st.session_state.current_page)
        )
        
        # Update current page
        if pages[selected_page] != st.session_state.current_page:
            st.session_state.current_page = pages[selected_page]
            st.rerun()
        
        st.divider()
        
        # Only show data management controls on Dashboard and Investment Advice pages
        if st.session_state.current_page in ["Dashboard", "Investment Advice"]:
            create_data_management_sidebar()

def create_modern_header():
    """Create modern header using native Streamlit components"""
    # Professional header with metrics
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("📊 StockScope Pro")
        st.markdown("**Professional Stock Sentiment Analysis**")
    
    with col2:
        tickers = get_available_tickers()
        st.metric("Analyzed Stocks", len(tickers))
    
    with col3:
        # Market sentiment overview
        if tickers:
            total_sentiment = 0
            total_posts = 0
            for ticker in tickers:
                df = load_dataframes(ticker)
                if not df.empty:
                    total_sentiment += df['compound'].mean()
                    total_posts += len(df)
            
            avg_market_sentiment = total_sentiment / len(tickers) if tickers else 0
            st.metric("Market Sentiment", f"{avg_market_sentiment:.3f}")
        else:
            st.metric("Market Sentiment", "N/A")

def create_advice_panel(ticker):
    """Create detailed advice panel for a specific stock"""
    st.subheader(f"🎯 Investment Advice for {ticker}")
    
    df = load_dataframes(ticker)
    
    if df.empty:
        st.error(f"No data available for {ticker}")
        return
    
    # Calculate detailed metrics
    avg_sentiment = df['compound'].mean()
    total_posts = len(df)
    reddit_posts = len(df[df['source'] == 'Reddit'])
    news_posts = len(df[df['source'] == 'News'])
    sec_posts = len(df[df['source'] == 'SEC'])
    
    # Recent sentiment trend (last 7 days)
    recent_df = df[df['created_dt'] > (datetime.now() - pd.Timedelta(days=7))]
    recent_sentiment = recent_df['compound'].mean() if not recent_df.empty else avg_sentiment
    
    # Sentiment distribution
    positive_posts = len(df[df['compound'] > 0.1])
    negative_posts = len(df[df['compound'] < -0.1])
    neutral_posts = total_posts - positive_posts - negative_posts
    
    # Generate recommendation
    recommendation = generate_investment_recommendation(
        avg_sentiment, total_posts, recent_sentiment, 
        positive_posts, negative_posts, neutral_posts
    )
    
    # Display recommendation card
    rec_color = "success" if recommendation['action'] == 'BUY' else "error" if recommendation['action'] == 'SELL' else "warning"
    
    if recommendation['action'] == 'BUY':
        st.success(f"🟢 **{recommendation['action']}** - {recommendation['reasoning']}")
    elif recommendation['action'] == 'SELL':
        st.error(f"🔴 **{recommendation['action']}** - {recommendation['reasoning']}")
    else:
        st.warning(f"🟡 **{recommendation['action']}** - {recommendation['reasoning']}")
    
    # Detailed metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Confidence", f"{recommendation['confidence']:.0f}%")
    
    with col2:
        st.metric("Risk Level", recommendation['risk_level'])
    
    with col3:
        st.metric("Time Horizon", recommendation['time_horizon'])
    
    with col4:
        st.metric("Position Size", recommendation['position_size'])
    
    # Sentiment breakdown
    st.subheader("📊 Sentiment Analysis")
    
    sentiment_col1, sentiment_col2 = st.columns(2)
    
    with sentiment_col1:
        # Sentiment distribution pie chart
        sentiment_data = pd.DataFrame({
            'Sentiment': ['Positive', 'Negative', 'Neutral'],
            'Count': [positive_posts, negative_posts, neutral_posts]
        })
        
        fig_pie = px.pie(sentiment_data, values='Count', names='Sentiment',
                        title=f"{ticker} Sentiment Distribution",
                        color_discrete_map={'Positive': '#28a745', 'Negative': '#dc3545', 'Neutral': '#ffc107'})
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with sentiment_col2:
        # Source breakdown
        source_data = pd.DataFrame({
            'Source': ['Reddit', 'News', 'SEC'],
            'Count': [reddit_posts, news_posts, sec_posts]
        })
        
        fig_bar = px.bar(source_data, x='Source', y='Count',
                        title=f"{ticker} Data Sources",
                        color='Source',
                        color_discrete_map={'Reddit': '#FF4500', 'News': '#1E90FF', 'SEC': '#32CD32'})
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Key factors
    st.subheader("🔑 Key Factors")
    
    factors = recommendation['factors']
    for factor in factors:
        st.write(f"• {factor}")
    
    # Risk assessment
    st.subheader("⚠️ Risk Assessment")
    
    risk_factors = recommendation['risks']
    for risk in risk_factors:
        st.write(f"• {risk}")

def generate_investment_recommendation(avg_sentiment, total_posts, recent_sentiment, 
                                     positive_posts, negative_posts, neutral_posts):
    """Generate detailed investment recommendation"""
    
    # Calculate confidence based on data quality
    data_quality = min(total_posts / 50, 1.0)  # More data = higher confidence
    sentiment_strength = abs(avg_sentiment)
    recent_trend = recent_sentiment - avg_sentiment
    
    base_confidence = (data_quality * 0.4 + sentiment_strength * 0.6) * 100
    
    # Determine action
    if avg_sentiment > 0.2 and total_posts > 20:
        action = "BUY"
        confidence = min(base_confidence + 10, 95)
        risk_level = "MEDIUM" if avg_sentiment > 0.3 else "LOW"
    elif avg_sentiment < -0.2 and total_posts > 20:
        action = "SELL"
        confidence = min(base_confidence + 10, 95)
        risk_level = "HIGH"
    else:
        action = "HOLD"
        confidence = max(base_confidence - 10, 40)
        risk_level = "MEDIUM"
    
    # Generate reasoning
    if action == "BUY":
        reasoning = f"Strong positive sentiment ({avg_sentiment:.3f}) with {positive_posts} positive discussions"
    elif action == "SELL":
        reasoning = f"Negative sentiment ({avg_sentiment:.3f}) with {negative_posts} negative discussions"
    else:
        reasoning = f"Mixed sentiment ({avg_sentiment:.3f}) suggests waiting for clearer signals"
    
    # Additional factors
    factors = [
        f"Average sentiment: {avg_sentiment:.3f}",
        f"Total discussions: {total_posts}",
        f"Positive sentiment: {positive_posts} posts ({positive_posts/total_posts*100:.1f}%)",
        f"Negative sentiment: {negative_posts} posts ({negative_posts/total_posts*100:.1f}%)",
        f"Recent trend: {'Improving' if recent_trend > 0.05 else 'Declining' if recent_trend < -0.05 else 'Stable'}"
    ]
    
    # Risk factors
    risks = []
    if total_posts < 10:
        risks.append("Limited data available - recommendations may be less reliable")
    if abs(avg_sentiment) < 0.1:
        risks.append("Neutral sentiment - market direction unclear")
    if negative_posts > positive_posts:
        risks.append("More negative than positive discussions")
    if not risks:
        risks.append("Standard market risks apply")
    
    return {
        'action': action,
        'confidence': confidence,
        'risk_level': risk_level,
        'reasoning': reasoning,
        'time_horizon': "Short-term" if abs(avg_sentiment) > 0.3 else "Medium-term",
        'position_size': "Small" if risk_level == "HIGH" else "Medium" if risk_level == "MEDIUM" else "Large",
        'factors': factors,
        'risks': risks
    }

def create_stock_grid():
    """Create modern stock grid using native components"""
    tickers = get_available_tickers()
    
    if not tickers:
        # Empty state
        st.info("🚀 **Get Started**: Use the sidebar to analyze your first stock!")
        return
    
    # Create responsive grid
    st.subheader("📈 Stock Portfolio")
    
    # Use tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Performance", "🎯 Recommendations"])
    
    with tab1:
        # Grid layout
        cols_per_row = 3
        for i in range(0, len(tickers), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, ticker in enumerate(tickers[i:i+cols_per_row]):
                with cols[j]:
                    create_pro_stock_card(ticker)
    
    with tab2:
        # Performance dashboard
        create_performance_dashboard(tickers)
    
    with tab3:
        # Recommendations
        create_recommendations_panel(tickers)

def create_pro_stock_card(ticker):
    """Create professional stock card using native components"""
    df = load_dataframes(ticker)
    
    if df.empty:
        st.warning(f"No data for {ticker}")
        return
    
    # Calculate metrics
    avg_sentiment = df['compound'].mean()
    total_posts = len(df)
    reddit_posts = len(df[df['source'] == 'Reddit'])
    news_posts = len(df[df['source'] == 'News'])
    
    # Card container
    with st.container():
        # Header
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(ticker)
        
        with col2:
            # Sentiment indicator
            if avg_sentiment > 0.1:
                st.success("🟢 Bullish")
            elif avg_sentiment < -0.1:
                st.error("🔴 Bearish")
            else:
                st.warning("🟡 Neutral")
        
        # Metrics
        metric_cols = st.columns(2)
        with metric_cols[0]:
            st.metric("Sentiment", f"{avg_sentiment:.3f}")
        with metric_cols[1]:
            st.metric("Posts", f"{total_posts:,}")
        
        # Mini chart
        if not df.empty:
            # Create sentiment timeline
            df_chart = df.copy()
            df_chart['date'] = pd.to_datetime(df_chart['created_dt']).dt.date
            daily_sentiment = df_chart.groupby('date')['compound'].mean().reset_index()
            
            if len(daily_sentiment) > 1:
                fig = px.line(daily_sentiment, x='date', y='compound', 
                             title=f"{ticker} Sentiment Trend")
                fig.update_layout(
                    height=200, 
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Action buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button(f"📊 Analyze", key=f"analyze_{ticker}", use_container_width=True):
                st.session_state.selected_ticker = ticker
                st.session_state.show_analysis = True
                st.session_state.show_advice = False  # Close advice if open
        
        with col_btn2:
            if st.button(f"🎯 Advice", key=f"advice_{ticker}", use_container_width=True):
                st.session_state.advice_ticker = ticker
                st.session_state.show_advice = True
                st.session_state.show_analysis = False  # Close analysis if open
        
        st.divider()

def create_performance_dashboard(tickers):
    """Create performance dashboard with charts"""
    if not tickers:
        st.info("No data available for performance analysis")
        return
    
    # Multi-stock comparison
    st.subheader("📊 Multi-Stock Comparison")
    
    # Prepare data for comparison
    comparison_data = []
    for ticker in tickers:
        df = load_dataframes(ticker)
        if not df.empty:
            comparison_data.append({
                'Ticker': ticker,
                'Avg Sentiment': df['compound'].mean(),
                'Total Posts': len(df),
                'Reddit Posts': len(df[df['source'] == 'Reddit']),
                'News Posts': len(df[df['source'] == 'News']),
                'Latest Activity': df['created_dt'].max() if not df['created_dt'].isna().all() else None
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Sentiment comparison
            fig1 = px.bar(comparison_df, x='Ticker', y='Avg Sentiment',
                         title="Average Sentiment by Stock",
                         color='Avg Sentiment',
                         color_continuous_scale='RdYlGn')
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Activity comparison
            fig2 = px.scatter(comparison_df, x='Total Posts', y='Avg Sentiment',
                            size='Reddit Posts', hover_name='Ticker',
                            title="Sentiment vs Activity",
                            color='Avg Sentiment',
                            color_continuous_scale='RdYlGn')
            st.plotly_chart(fig2, use_container_width=True)
        
        # Data table
        st.subheader("📋 Detailed Comparison")
        st.dataframe(comparison_df, use_container_width=True)

def create_recommendations_panel(tickers):
    """Create AI recommendations panel"""
    st.subheader("🎯 AI Investment Recommendations")
    
    if not tickers:
        st.info("No stocks analyzed yet")
        return
    
    # Simple recommendation logic
    recommendations = []
    for ticker in tickers:
        df = load_dataframes(ticker)
        if not df.empty:
            avg_sentiment = df['compound'].mean()
            total_posts = len(df)
            
            # Simple scoring
            if avg_sentiment > 0.2 and total_posts > 10:
                action = "BUY"
                color = "🟢"
            elif avg_sentiment < -0.2:
                action = "SELL"
                color = "🔴"
            else:
                action = "HOLD"
                color = "🟡"
            
            recommendations.append({
                'Stock': ticker,
                'Action': action,
                'Sentiment': avg_sentiment,
                'Confidence': min(abs(avg_sentiment) * 100, 95),
                'Color': color
            })
    
    if recommendations:
        # Sort by confidence
        recommendations.sort(key=lambda x: x['Confidence'], reverse=True)
        
        # Display recommendations
        for rec in recommendations:
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            
            with col1:
                st.subheader(f"{rec['Color']} {rec['Stock']}")
            
            with col2:
                st.metric("Action", rec['Action'])
            
            with col3:
                st.metric("Confidence", f"{rec['Confidence']:.0f}%")
            
            with col4:
                if rec['Action'] == 'BUY':
                    st.success(f"Strong buy signal with {rec['Confidence']:.0f}% confidence")
                elif rec['Action'] == 'SELL':
                    st.error(f"Sell signal with {rec['Confidence']:.0f}% confidence")
                else:
                    st.warning(f"Hold position with {rec['Confidence']:.0f}% confidence")

def create_analysis_sidebar():
    """Create analysis sidebar"""
    with st.sidebar:
        st.header("🎛️ Analysis Controls")
        
        # Stock selector
        tickers = get_available_tickers()
        if tickers:
            selected_ticker = st.selectbox("Select Stock", [""] + tickers)
            
            if selected_ticker:
                st.subheader(f"📊 {selected_ticker} Analysis")
                
                df = load_dataframes(selected_ticker)
                if not df.empty:
                    # Quick stats
                    st.metric("Total Posts", len(df))
                    st.metric("Avg Sentiment", f"{df['compound'].mean():.3f}")
                    
                    # Filters
                    st.subheader("🔧 Filters")
                    
                    sources = st.multiselect(
                        "Data Sources",
                        ["Reddit", "News", "SEC"],
                        default=["Reddit", "News", "SEC"]
                    )
                    
                    sentiment_range = st.slider(
                        "Sentiment Range",
                        -1.0, 1.0, (-1.0, 1.0)
                    )
                    
                    # Export button
                    if st.button("💾 Export Data"):
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "Download CSV",
                            csv,
                            f"{selected_ticker}_analysis.csv",
                            "text/csv"
                        )
        else:
            st.info("No stocks analyzed yet")

def main():
    """Main application"""
    # Apply dark theme
    apply_dark_theme()
    
    # Create navigation
    create_navigation()
    
    # Route to appropriate page
    if st.session_state.current_page == "Dashboard":
        # Check for auto-refresh
        if should_auto_refresh():
            st.info("🔄 Auto-refresh triggered - updating data...")
            with st.spinner("Refreshing all stock data..."):
                refresh_all_data()
            st.rerun()
        
        # Create layout
        create_modern_header()
        
        # Add refresh status in header
        if st.session_state.auto_refresh_enabled:
            time_until_refresh = st.session_state.refresh_interval - (datetime.now() - st.session_state.last_refresh).total_seconds() / 60
            if time_until_refresh > 0:
                st.info(f"🔄 Auto-refresh enabled - next refresh in {time_until_refresh:.0f} minutes")
            else:
                st.info("🔄 Auto-refresh ready - refreshing on next interaction")
        
        st.markdown("---")
        
        # Main content
        create_stock_grid()
        
        # Handle analysis panels
        if st.session_state.get('show_analysis') and st.session_state.get('selected_ticker'):
            ticker = st.session_state.selected_ticker
            
            with st.expander(f"📊 {ticker} Detailed Analysis", expanded=True):
                df = load_dataframes(ticker)
                
                if not df.empty:
                    # Detailed analysis
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Sentiment Timeline")
                        # Create timeline chart
                        df_timeline = df.copy()
                        df_timeline['date'] = pd.to_datetime(df_timeline['created_dt']).dt.date
                        daily_sentiment = df_timeline.groupby('date')['compound'].agg(['mean', 'count']).reset_index()
                        
                        fig = px.line(daily_sentiment, x='date', y='mean', 
                                     title=f"{ticker} Daily Sentiment Trend")
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font_color='white'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Source Breakdown")
                        # Source distribution
                        source_counts = df['source'].value_counts()
                        fig2 = px.pie(values=source_counts.values, names=source_counts.index,
                                     title="Data Sources Distribution")
                        fig2.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font_color='white'
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                
                if st.button("❌ Close Analysis"):
                    st.session_state.show_analysis = False
                    st.rerun()
        
        # Handle advice panels
        if st.session_state.get('show_advice') and st.session_state.get('advice_ticker'):
            ticker = st.session_state.advice_ticker
            
            with st.expander(f"🎯 {ticker} Investment Advice", expanded=True):
                create_advice_panel(ticker)
                
                if st.button("❌ Close Advice"):
                    st.session_state.show_advice = False
                    st.rerun()
    
    elif st.session_state.current_page == "Investment Advice":
        tickers = get_available_tickers()
        render_investment_advice_tab(tickers)
    
    elif st.session_state.current_page == "Quantitative Strategies":
        create_quantitative_strategies_page()
    
    elif st.session_state.current_page == "About":
        render_about_tab()

if __name__ == "__main__":
    main()