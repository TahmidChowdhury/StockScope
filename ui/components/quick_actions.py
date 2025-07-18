import streamlit as st
from ui.utils.session_state import get_processed_cache
from main import run_pipeline
from scraping.news_scraper import fetch_news_sentiment

def render_quick_actions(available_tickers):
    """Render quick actions section for instant stock analysis"""
    processed_cache = get_processed_cache()
    
    # Enhanced mobile navigation hints
    if st.session_state.get('mobile_view', False):
        st.info("💡 **Mobile Tip**: Swipe through tabs above for different features!")
    
    st.markdown("---")
    
    # Define popular stocks for quick actions
    popular_stocks = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX"]
    
    # Smart logic: show stocks that aren't analyzed yet, or provide different actions
    unanalyzed_stocks = [stock for stock in popular_stocks if stock not in available_tickers]
    
    if len(available_tickers) == 0:
        # No data yet - show quick start options
        st.markdown("""
        <div class="quick-actions">
            <h3>🚀 Quick Start</h3>
            <p>Get started with instant analysis of popular stocks</p>
        </div>
        """, unsafe_allow_html=True)
        
        quick_actions_to_show = popular_stocks[:4]  # Show first 4 popular stocks
        action_type = "analyze"
        
    elif len(unanalyzed_stocks) >= 2:
        # Some data exists, show unanalyzed popular stocks
        st.markdown("""
        <div class="quick-actions">
            <h3>⚡ Analyze More Stocks</h3>
            <p>Quick analysis for popular stocks not yet in your portfolio</p>
        </div>
        """, unsafe_allow_html=True)
        
        quick_actions_to_show = unanalyzed_stocks[:4]  # Show up to 4 unanalyzed stocks
        action_type = "analyze"
        
    else:
        # Most popular stocks are analyzed, show quick navigation instead
        st.markdown("""
        <div class="quick-actions">
            <h3>🎯 Quick Navigation</h3>
            <p>Jump to analysis of your available stocks</p>
        </div>
        """, unsafe_allow_html=True)
        
        quick_actions_to_show = available_tickers[:4]  # Show first 4 available stocks
        action_type = "navigate"
    
    # Create responsive grid for quick actions
    quick_actions_container = st.container()
    with quick_actions_container:
        # Get stock icons
        stock_icons = {
            "AAPL": "🍎", "TSLA": "🚗", "NVDA": "🔥", "MSFT": "💻", 
            "GOOGL": "🔍", "AMZN": "📦", "META": "👥", "NFLX": "🎬",
            "BTC": "₿", "ETH": "⟠", "DOGE": "🐕", "PLTR": "🛡️", "RKLB": "🚀"
        }
        
        # Mobile responsive layout
        if st.session_state.get('mobile_view', False):
            # Mobile: 2x2 grid
            if len(quick_actions_to_show) >= 2:
                quick_row1_col1, quick_row1_col2 = st.columns(2)
                if len(quick_actions_to_show) >= 4:
                    quick_row2_col1, quick_row2_col2 = st.columns(2)
                
                for i, stock in enumerate(quick_actions_to_show[:4]):
                    icon = stock_icons.get(stock, "📊")
                    
                    if i == 0:
                        col = quick_row1_col1
                    elif i == 1:
                        col = quick_row1_col2
                    elif i == 2:
                        col = quick_row2_col1 if len(quick_actions_to_show) >= 4 else quick_row1_col1
                    else:
                        col = quick_row2_col2
                    
                    with col:
                        button_text = f"{icon} {stock}"
                        button_key = f"mobile_{action_type}_{stock}"
                        
                        if action_type == "analyze":
                            if st.button(button_text, use_container_width=True, type="primary", key=button_key):
                                st.session_state.selected_quick_action = stock
                        else:  # navigate
                            if st.button(button_text, use_container_width=True, type="secondary", key=button_key):
                                st.session_state.auto_select_ticker = stock
                                st.rerun()
        else:
            # Desktop: horizontal layout
            cols = st.columns(len(quick_actions_to_show))
            
            for i, stock in enumerate(quick_actions_to_show):
                icon = stock_icons.get(stock, "📊")
                
                with cols[i]:
                    if action_type == "analyze":
                        button_text = f"{icon} Analyze {stock}"
                        if st.button(button_text, use_container_width=True, type="primary", key=f"desktop_{stock}"):
                            st.session_state.selected_quick_action = stock
                    else:  # navigate
                        button_text = f"{icon} View {stock}"
                        if st.button(button_text, use_container_width=True, type="secondary", key=f"desktop_nav_{stock}"):
                            st.session_state.auto_select_ticker = stock
                            st.rerun()
    
    # Show additional context based on action type
    if action_type == "navigate":
        st.info("💡 **Tip**: These buttons will take you directly to the analysis for stocks you've already processed. Use the 'Fetch Data' tab to analyze new stocks.")
    elif len(available_tickers) > 0:
        st.info(f"💡 **Note**: You have {len(available_tickers)} stocks analyzed. Quick actions show popular stocks not yet analyzed.")
    
    # Process quick action selection (for analyze actions)
    if 'selected_quick_action' in st.session_state:
        _process_quick_action(st.session_state.selected_quick_action)

def _process_quick_action(ticker):
    """Process a quick action for stock analysis"""
    with st.spinner(f"Fetching complete {ticker} analysis..."):
        try:
            # Status updates for better UX
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            # Reddit data
            status_placeholder.info(f"🔍 Analyzing Reddit discussions for {ticker}...")
            progress_bar.progress(25)
            run_pipeline(ticker)
            
            # News data
            status_placeholder.info(f"📰 Gathering news sentiment for {ticker}...")
            progress_bar.progress(50)
            fetch_news_sentiment(ticker)
            
            # Twitter data - COMMENTED OUT until paid API access
            status_placeholder.info(f"🐦 Twitter API disabled...")
            progress_bar.progress(60)
            st.warning("⚠️ Twitter API disabled - upgrade to paid access to enable Twitter sentiment analysis")
            
            # SEC data
            status_placeholder.info(f"🏛️ Fetching SEC filings for {ticker}...")
            progress_bar.progress(80)
            try:
                from scraping.sec_scraper import fetch_sec_sentiment
                sec_path = fetch_sec_sentiment(ticker)
                if sec_path:
                    status_placeholder.success(f"✅ SEC data collected for {ticker}!")
                else:
                    status_placeholder.warning(f"⚠️ No SEC data available for {ticker}")
            except Exception as e:
                st.warning(f"SEC API issue: {str(e)}. Continuing without SEC data.")
            
            # Complete
            status_placeholder.success(f"✅ {ticker} analysis complete!")
            progress_bar.progress(100)
            
            # Clean up progress indicators
            import time
            time.sleep(1)
            status_placeholder.empty()
            progress_bar.empty()
            
            st.success(f"✅ {ticker} analysis complete!")
            st.balloons()
            
            # Auto-navigate to results
            st.session_state.auto_select_ticker = ticker
            
            # Clear the action to prevent re-running
            del st.session_state.selected_quick_action
            
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error analyzing {ticker}: {e}")
            if 'selected_quick_action' in st.session_state:
                del st.session_state.selected_quick_action