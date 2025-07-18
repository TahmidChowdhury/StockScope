import streamlit as st
from ui.utils.data_helpers import load_dataframes

def render_dashboard_tab(tickers):
    """Render the dashboard tab content"""
    st.subheader("📈 Analyze Existing Data")
    
    if tickers:
        # Better ticker selection with search
        selected_ticker = st.selectbox(
            "🔍 Select a stock ticker:", 
            options=[""] + tickers,
            index=1 if st.session_state.get('auto_select_ticker') in tickers else 0,
            help="Choose a ticker to analyze its sentiment data"
        )
        
        # Auto-select ticker if set in session state
        if st.session_state.get('auto_select_ticker') and st.session_state.auto_select_ticker in tickers:
            selected_ticker = st.session_state.auto_select_ticker
        
        if selected_ticker:
            # Update session state
            st.session_state.auto_select_ticker = selected_ticker
            
            df = load_dataframes(selected_ticker)
            
            if not df.empty:
                # Display key metrics at the top
                _render_metrics_section(df)
            else:
                st.warning("⚠️ No data found for this ticker. Try fetching data first.")
    else:
        st.warning("⚠️ No data available. Please fetch some data first!")

def _render_metrics_section(df):
    """Render the metrics section for a selected ticker"""
    total_posts = len(df)
    reddit_posts = len(df[df['source'] == 'Reddit'])
    news_articles = len(df[df['source'] == 'News'])
    sec_filings = len(df[df['source'] == 'SEC'])
    avg_sentiment = df['compound'].mean()
    
    # Create metric rows to show data sources (excluding Twitter)
    metric_row1_cols = st.columns(3)
    metric_row2_cols = st.columns(3)
    
    with metric_row1_cols[0]:
        st.metric("Total Posts", total_posts)
    with metric_row1_cols[1]:
        st.metric("Reddit Posts", reddit_posts)
    with metric_row1_cols[2]:
        st.metric("News Articles", news_articles)
    
    with metric_row2_cols[0]:
        st.metric("SEC Filings", sec_filings)
    with metric_row2_cols[1]:
        sentiment_color = "normal"
        if avg_sentiment > 0.1:
            sentiment_color = "normal"
        elif avg_sentiment < -0.1:
            sentiment_color = "inverse"
        st.metric("Avg Sentiment", f"{avg_sentiment:.3f}", 
                delta=None, delta_color=sentiment_color)
    with metric_row2_cols[2]:
        st.metric("Data Sources", "3 Active")
    
    # Additional analytics could go here
    st.markdown("---")
    st.info("💡 **Tip**: Use the Analysis Controls in the right panel to filter and explore the data in detail.")