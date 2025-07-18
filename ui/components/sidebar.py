import streamlit as st
from ui.utils.data_helpers import get_available_tickers

def render_sidebar():
    """Render the sidebar with controls and data status"""
    with st.sidebar:
        st.header("🎛️ StockScope Control Panel")
        
        # === DATA STATUS ===
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
        
        # === FILTERS (only show when data exists) ===
        if tickers:
            st.subheader("🔧 Filter Data")
            
            # Simple source filter
            selected_sources = st.multiselect(
                "Data Sources:",
                options=["Reddit", "News", "SEC"],
                default=["Reddit", "News", "SEC"],
                help="Choose which sources to include in analysis"
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
            
            # Store filters in session state
            st.session_state.filter_sources = selected_sources
            st.session_state.filter_compound_range = compound_range
            
            st.markdown("---")
        
        # === HELP ===
        with st.expander("❓ How to Use StockScope"):
            st.markdown("""
            **🎯 Getting Started:**
            1. Use **"Quick Actions"** below for instant analysis
            2. Or go to **"Fetch Data"** tab to analyze any stock
            3. View results in **"Dashboard"** tab
            4. Get investment advice in **"Investment Advice"** tab
            
            **📊 Understanding Sentiment:**
            - 🟢 **Positive**: Good news/optimistic posts
            - 🟡 **Neutral**: Factual/mixed sentiment  
            - 🔴 **Negative**: Bad news/pessimistic posts
            """)
    
    return tickers