import streamlit as st
from ui.utils.data_helpers import load_dataframes
from ui.utils.session_state import get_processed_cache
from main import run_pipeline
from scraping.news_scraper import fetch_news_sentiment

def render_fetch_data_tab():
    """Render the fetch data tab content"""
    st.subheader("📥 Fetch New Stock Data")
    
    processed_cache = get_processed_cache()
    
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
                _process_data_fetch(input_ticker, processed_cache)
            else:
                st.info(f"📊 {input_ticker} data already exists. Use force refresh to update.")
                df = load_dataframes(input_ticker)

def _process_data_fetch(input_ticker, processed_cache):
    """Process data fetching for a ticker"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔍 Fetching Reddit data...")
        progress_bar.progress(20)
        run_pipeline(input_ticker)
        
        status_text.text("📰 Fetching news data...")
        progress_bar.progress(40)
        fetch_news_sentiment(input_ticker)
        
        # Twitter data - COMMENTED OUT until paid API access
        status_text.text("🐦 Twitter API disabled...")
        progress_bar.progress(60)
        st.warning("⚠️ Twitter API disabled - upgrade to paid access to enable Twitter sentiment analysis")
        
        status_text.text("🏛️ Fetching SEC filings...")
        progress_bar.progress(80)
        try:
            from scraping.sec_scraper import fetch_sec_sentiment
            sec_path = fetch_sec_sentiment(input_ticker)
            if sec_path:
                status_text.text("✅ SEC data collected!")
            else:
                status_text.text("⚠️ No SEC data available for this ticker")
        except Exception as e:
            st.warning(f"SEC API issue: {str(e)}. Continuing without SEC data.")
        
        status_text.text("✅ Analysis complete!")
        progress_bar.progress(100)
        processed_cache.add(input_ticker)
        
        st.success(f"✅ Successfully analyzed {input_ticker}!")
        st.balloons()
        
        # Load the newly fetched data
        df = load_dataframes(input_ticker)
        
        # Auto-navigate to dashboard
        st.session_state.auto_select_ticker = input_ticker
        st.info("📊 **Data fetched!** Go to the Dashboard tab to view your analysis.")
        
    except Exception as e:
        st.error(f"❌ Error fetching data: {str(e)}")
    finally:
        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()