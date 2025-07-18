import streamlit as st

def render_about_tab():
    """Render the about tab content"""
    st.subheader("ℹ️ About StockScope")
    st.markdown("""
    **StockScope** is a comprehensive sentiment analysis and investment advisor tool that tracks public opinion about stocks across multiple platforms:
    
    **📊 Core Features:**
    - 🔴 **Reddit Analysis**: Scrapes relevant subreddits for stock discussions
    - 📰 **News Sentiment**: Analyzes financial news articles
    - 🏛️ **SEC Filings**: Official regulatory filings and insider trading data
    - 📈 **Interactive Visualizations**: Real-time charts and analytics
    - 📊 **Sentiment Trends**: Timeline analysis and heatmaps
    - 🎯 **Advanced Filtering**: Customizable date and sentiment filters
    
    **🎯 Investment Analysis Features:**
    - 🤖 **AI-Powered Recommendations**: BUY/SELL/HOLD signals
    - 📊 **Technical Analysis**: RSI, MACD, Moving Averages
    - 🎯 **Risk Assessment**: Volatility and risk level analysis
    - 💰 **Portfolio Optimization**: Suggested allocation strategies
    - 📈 **Price Correlation**: Sentiment vs price movement analysis
    - 🔥 **Trending Topics**: Keyword frequency analysis
    - ⚡ **Engagement Analytics**: Social media interaction metrics
    
    **📊 Visualization Features:**
    - 🎯 **Sentiment Gauge**: Real-time market mood indicator
    - 📈 **Advanced Timeline**: Multi-layer sentiment and volume trends
    - 🎭 **Source Comparison**: Radar charts comparing platforms
    - 📅 **Sentiment Heatmaps**: Time-based sentiment intensity
    - ⚡ **Engagement Scatter Plots**: Correlation analysis
    
    **🛠️ Technology Stack:**
    - **Frontend**: Streamlit with custom CSS styling
    - **Sentiment Analysis**: VADER sentiment analyzer
    - **Technical Analysis**: yfinance for market data
    - **Data Sources**: Reddit API, News APIs, SEC EDGAR database
    - **Visualization**: Plotly for interactive charts
    - **Machine Learning**: Scikit-learn for optimization algorithms
    - **Data Processing**: Pandas for data manipulation
    
    **🎨 UI/UX Features:**
    - 🌙 **Dark Mode Support**: Automatic theme detection
    - 📱 **Responsive Design**: Works on all screen sizes
    - 🎨 **Professional Styling**: Modern gradient cards and animations
    - ♿ **Accessibility**: WCAG compliant color contrasts
    - 🚀 **Performance**: Optimized caching and data loading
    """)
    
    # Additional technical information
    with st.expander("🔧 Technical Architecture"):
        st.markdown("""
        **Modular Design:**
        - **UI Components**: Reusable header, sidebar, and navigation components
        - **Page Components**: Separate modules for dashboard, data fetching, and investment advice
        - **Utility Modules**: Data helpers, session state management, and styling
        - **Analysis Engine**: Investment advisor with technical analysis capabilities
        - **Visualization Layer**: Advanced plotting and chart generation
        
        **Performance Optimizations:**
        - **Caching**: Streamlit caching for data loading and processing
        - **Lazy Loading**: Components load only when needed
        - **Responsive Design**: Mobile-first approach for all screen sizes
        - **Code Splitting**: Modular architecture for better maintainability
        """)
    
    # Version and updates
    with st.expander("📋 Version Information"):
        st.markdown("""
        **Current Version**: 2.0 (Refactored Architecture)
        
        **Recent Updates:**
        - ✅ **Modular Architecture**: Complete code restructuring for maintainability
        - ✅ **Enhanced UI Components**: Reusable and responsive design elements
        - ✅ **Improved Performance**: Better caching and session state management
        - ✅ **Mobile-First Design**: Optimized for all device types
        - ✅ **Advanced Investment Analysis**: Comprehensive portfolio optimization
        - ✅ **Better Error Handling**: Robust error management and user feedback
        """)
    
    # Contact and support
    st.markdown("---")
    st.markdown("""
    **💡 Need Help?**
    
    Use the help section in the sidebar for quick guidance, or explore each tab to discover all features.
    """)