import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from ui.utils.data_helpers import get_available_tickers, load_dataframes
import json
import os

def render_articles_tab():
    """Render the articles tab content with filtering and link access"""
    st.subheader("📰 Articles & Sentiment Data")
    
    # Get available tickers
    tickers = get_available_tickers()
    
    if not tickers:
        st.warning("⚠️ No articles found. Please fetch some data first using the 'Fetch Data' tab.")
        return
    
    # Filtering controls
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        selected_tickers = st.multiselect(
            "📈 Filter by Stocks:",
            options=tickers,
            default=tickers,
            help="Select which stocks to show articles for"
        )
    
    with col2:
        source_filter = st.multiselect(
            "📊 Filter by Source:",
            options=["Reddit", "News", "SEC"],
            default=["Reddit", "News", "SEC"],
            help="Select which data sources to include"
        )
    
    with col3:
        days_filter = st.selectbox(
            "📅 Time Period:",
            options=[7, 14, 30, 60, 90, 180, 365, "All"],
            index=4,  # Default to 90 days
            help="Show articles from the last X days"
        )
    
    # Date filtering logic
    if days_filter != "All":
        cutoff_date = datetime.now() - timedelta(days=days_filter)
    else:
        cutoff_date = None
    
    # Collect and display articles
    all_articles = []
    
    for ticker in selected_tickers:
        df = load_dataframes(ticker)
        
        if not df.empty:
            # Filter by source
            if source_filter:
                df = df[df['source'].isin(source_filter)]
            
            # Filter by date
            if cutoff_date:
                df = df[pd.to_datetime(df['created_dt']) >= cutoff_date]
            
            # Add ticker column for reference
            df['ticker'] = ticker
            all_articles.append(df)
    
    if not all_articles:
        st.info("No articles match your current filters.")
        return
    
    # Combine all articles
    combined_df = pd.concat(all_articles, ignore_index=True)
    
    # Sort by date (newest first)
    combined_df = combined_df.sort_values('created_dt', ascending=False)
    
    # Display summary metrics
    st.markdown("---")
    _render_articles_summary(combined_df, selected_tickers)
    
    # Display articles
    st.markdown("---")
    _render_articles_list(combined_df)

def _render_articles_summary(df, selected_tickers):
    """Render summary metrics for articles"""
    st.subheader("📊 Articles Summary")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Articles", len(df))
    
    with col2:
        avg_sentiment = df['compound'].mean() if not df.empty else 0
        sentiment_delta = "📈" if avg_sentiment > 0 else "📉" if avg_sentiment < 0 else "➡️"
        st.metric("Avg Sentiment", f"{avg_sentiment:.3f}", delta=sentiment_delta)
    
    with col3:
        if not df.empty:
            most_active_source = df['source'].value_counts().index[0]
            st.metric("Most Active Source", most_active_source)
        else:
            st.metric("Most Active Source", "N/A")
    
    with col4:
        if not df.empty:
            latest_article = df['created_dt'].max()
            hours_ago = (datetime.now() - latest_article).total_seconds() / 3600
            if hours_ago < 24:
                time_str = f"{int(hours_ago)}h ago"
            else:
                time_str = f"{int(hours_ago/24)}d ago"
            st.metric("Latest Article", time_str)
        else:
            st.metric("Latest Article", "N/A")
    
    # Source distribution chart
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            source_counts = df['source'].value_counts()
            import plotly.express as px
            fig1 = px.pie(
                values=source_counts.values, 
                names=source_counts.index,
                title="Articles by Source"
            )
            fig1.update_layout(height=300)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            sentiment_by_source = df.groupby('source')['compound'].mean().reset_index()
            fig2 = px.bar(
                sentiment_by_source, 
                x='source', 
                y='compound',
                title="Average Sentiment by Source",
                color='compound',
                color_continuous_scale='RdYlGn'
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

def _render_articles_list(df):
    """Render the list of articles with links and filtering"""
    st.subheader("📋 Articles List")
    
    # Pagination
    items_per_page = 10
    total_items = len(df)
    total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1
    
    if total_pages > 1:
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col2:
            current_page = st.selectbox(
                "📄 Page",
                options=list(range(1, total_pages + 1)),
                index=0,
                format_func=lambda x: f"Page {x} of {total_pages}"
            )
    else:
        current_page = 1
    
    # Calculate slice
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_data = df.iloc[start_idx:end_idx]
    
    # Display articles as cards
    for idx, row in page_data.iterrows():
        with st.container():
            # Card header
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Source icon and ticker
                source_icons = {
                    'Reddit': '🔴',
                    'News': '📰',
                    'SEC': '🏛️'
                }
                source_icon = source_icons.get(row['source'], '📊')
                st.markdown(f"**{source_icon} {row['source']} • {row['ticker']}**")
            
            with col2:
                # Sentiment indicator
                sentiment = row['compound']
                if sentiment > 0.1:
                    sentiment_color = "🟢"
                    sentiment_text = "Positive"
                elif sentiment < -0.1:
                    sentiment_color = "🔴"
                    sentiment_text = "Negative"
                else:
                    sentiment_color = "🟡"
                    sentiment_text = "Neutral"
                
                st.markdown(f"{sentiment_color} **{sentiment_text}** ({sentiment:.3f})")
            
            with col3:
                # Time ago
                if pd.notna(row['created_dt']):
                    time_ago = datetime.now() - row['created_dt'].replace(tzinfo=None)
                    if time_ago.days > 0:
                        time_str = f"{time_ago.days}d ago"
                    elif time_ago.seconds > 3600:
                        time_str = f"{time_ago.seconds // 3600}h ago"
                    else:
                        time_str = f"{time_ago.seconds // 60}m ago"
                else:
                    time_str = "Recently"
                
                st.markdown(f"<div style='text-align: right; color: #888;'>{time_str}</div>", 
                           unsafe_allow_html=True)
            
            # Article title and link
            title = str(row['title'])
            if len(title) > 120:
                title = title[:120] + "..."
            
            # Create clickable link
            if pd.notna(row.get('url')) and row['url'] != '':
                st.markdown(f"[**{title}**]({row['url']})")
            else:
                st.markdown(f"**{title}**")
            
            # Additional info row
            info_col1, info_col2, info_col3 = st.columns([2, 1, 1])
            
            with info_col1:
                # Subreddit for Reddit posts
                if row['source'] == 'Reddit' and pd.notna(row.get('subreddit')):
                    st.markdown(f"*r/{row['subreddit']}*")
            
            with info_col2:
                # Additional source info
                if row['source'] == 'News' and pd.notna(row.get('source_name')):
                    st.markdown(f"*{row.get('source_name', '')}*")
            
            with info_col3:
                # Empty space for cleaner layout
                pass
            
            st.divider()
    
    # Page info
    if total_pages > 1:
        st.info(f"Showing {start_idx + 1}-{end_idx} of {total_items} articles")
    
    # Download option
    if not df.empty:
        # Get available columns dynamically to avoid KeyError
        available_columns = ['ticker', 'created_dt', 'source', 'title', 'sentiment', 'compound']
        if 'url' in df.columns:
            available_columns.append('url')
        if 'source_name' in df.columns:
            available_columns.append('source_name')
        
        csv_data = df[available_columns].copy()
        
        # Rename columns for export
        column_renames = {
            'created_dt': 'Date',
            'source': 'Source',
            'title': 'Title',
            'compound': 'Sentiment Score'
        }
        if 'url' in csv_data.columns:
            column_renames['url'] = 'URL'
        if 'source_name' in csv_data.columns:
            column_renames['source_name'] = 'Source Name'
            
        csv_data = csv_data.rename(columns=column_renames)
        
        csv = csv_data.to_csv(index=False)
        st.download_button(
            label="💾 Download Articles Data",
            data=csv,
            file_name=f"articles_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download filtered articles as CSV file"
        )