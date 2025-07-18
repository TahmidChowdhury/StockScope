import streamlit as st
from ui.utils.data_helpers import load_dataframes, filter_dataframe
from datetime import datetime
import pandas as pd

def render_analysis_controls():
    """Render analysis controls in the right column"""
    st.subheader("🎛️ Analysis Controls")
    
    # Initialize default filter values
    selected_sources = st.session_state.get('filter_sources', ["Reddit", "News", "SEC"])
    compound_range = st.session_state.get('filter_compound_range', (-1.0, 1.0))
    date_range = None
    
    # Get selected ticker from session state
    selected_ticker = st.session_state.get('auto_select_ticker', '')
    
    if selected_ticker:
        df = load_dataframes(selected_ticker)
        
        if not df.empty:
            # Advanced filtering controls
            st.markdown("### 🔧 Filters")
            
            # Source selection with icons
            selected_sources = st.multiselect(
                "📊 Data Sources:",
                options=["Reddit", "News", "SEC"],
                default=selected_sources,
                help="Select which data sources to include"
            )
            
            # Sentiment score filter with better labels
            compound_range = st.slider(
                "📈 Sentiment Score Range",
                min_value=-1.0,
                max_value=1.0,
                value=compound_range,
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
            
            # Apply filters and show results
            if date_range and len(date_range) == 2:
                df_filtered = filter_dataframe(df, selected_sources, compound_range, date_range)
                
                # Enhanced data table with beautiful styling
                st.subheader("📋 Latest Discussions & Analysis")
                
                # Create beautiful data cards instead of plain table
                if not df_filtered.empty:
                    _render_data_cards(df_filtered, selected_ticker)
                else:
                    st.info("No data matches your current filters.")
    else:
        st.info("👈 Select a ticker from the Dashboard tab to see analysis controls.")

def _render_data_cards(df_filtered, selected_ticker):
    """Render data cards with pagination using Streamlit native components"""
    # Sort by date for freshest content first
    display_df = df_filtered.sort_values("created_dt", ascending=False)
    
    # Pagination for better UX
    items_per_page = 5
    total_items = len(display_df)
    total_pages = (total_items - 1) // items_per_page + 1
    
    # Page selector
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
    page_data = display_df.iloc[start_idx:end_idx]
    
    # Create cards using Streamlit containers and columns
    for idx, row in page_data.iterrows():
        # Create a container for each card
        with st.container():
            # Determine sentiment styling
            if row['sentiment'] == 'positive':
                sentiment_emoji = "🟢"
                sentiment_color = "green"
            elif row['sentiment'] == 'negative':
                sentiment_emoji = "🔴"
                sentiment_color = "red"
            else:
                sentiment_emoji = "🟡"
                sentiment_color = "orange"
            
            # Format date nicely
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
            
            # Source icon
            source_icons = {
                'Reddit': '🔴',
                'News': '📰',
                'SEC': '🏛️'
            }
            source_icon = source_icons.get(row['source'], '📊')
            
            # Create card layout with columns
            header_col1, header_col2 = st.columns([3, 1])
            
            with header_col1:
                # Fix f-string syntax error by using separate variables
                subreddit_text = f"• r/{row['subreddit']}" if row['source'] == 'Reddit' and pd.notna(row['subreddit']) else ""
                st.markdown(f"**{source_icon} {row['source']}** {subreddit_text}")
            
            with header_col2:
                st.markdown(f"<div style='text-align: right; color: #888; font-size: 0.9rem;'>{time_str}</div>", unsafe_allow_html=True)
            
            # Title and content
            title_text = str(row['title'])
            if len(title_text) > 150:
                title_text = title_text[:150] + "..."
            
            st.markdown(f"**{title_text}**")
            
            # Sentiment and score row
            sentiment_col1, sentiment_col2, sentiment_col3 = st.columns([2, 1, 1])
            
            with sentiment_col1:
                st.markdown(f"{sentiment_emoji} **{row['sentiment'].title()}** ({row['compound']:.3f})")
            
            with sentiment_col2:
                if pd.notna(row['score']) and row['score'] != 0:
                    st.markdown(f"👍 {row['score']}")
            
            with sentiment_col3:
                # Empty column for spacing
                pass
            
            # Add separator
            st.divider()
    
    # Page navigation info
    if total_pages > 1:
        st.info(f"Showing {start_idx + 1}-{end_idx} of {total_items} posts")
    
    # Download option
    csv = display_df[["created_dt", "source", "title", "sentiment", "compound"]].to_csv(index=False)
    st.download_button(
        label="💾 Download Complete Dataset",
        data=csv,
        file_name=f"{selected_ticker}_sentiment_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        help="Download all filtered data as CSV file"
    )