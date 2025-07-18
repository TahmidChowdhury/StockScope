# StockScope Pro - Live Stock Sentiment Analysis Platform

**StockScope Pro** is a comprehensive real-time stock sentiment analysis platform that combines social media sentiment, financial news analysis, and SEC filings to provide AI-powered investment recommendations. Built with Python and featuring a modern dark-themed Streamlit dashboard with live data capabilities.

---

## SECURITY & DISCLAIMER

### Security Notice
- **API Key Protection**: Never commit API keys to version control. Use .env files (included in .gitignore)
- **Environment Variables**: Copy .env.example to .env and add your actual API keys
- **Private Repository**: Keep your repository private if it contains sensitive configuration
- **Sample Data**: Application works with sample data if no API keys are provided

### Important Disclaimers
- **Educational Purpose**: This tool is for educational and research purposes only
- **Not Financial Advice**: Do not use as sole basis for investment decisions
- **Market Risk**: All investments carry risk of loss
- **Data Accuracy**: Verify all data independently before making investment decisions
- **Professional Consultation**: Consult with qualified financial professionals for investment advice

---

## Key Features

### Live Data Management
- **Auto-refresh**: Automatically updates data every 15-240 minutes
- **Manual refresh**: Update individual stocks or entire portfolio on demand
- **Add new stocks**: Dynamically expand your portfolio with any ticker
- **Real-time progress**: Live status updates during data collection
- **Individual management**: Refresh, analyze, or remove specific stocks

### AI Investment Advisor
- **Smart Recommendations**: Get BUY/SELL/HOLD signals with confidence scores
- **Risk Assessment**: Automatic risk level analysis (LOW/MEDIUM/HIGH)
- **Detailed Analysis**: Comprehensive breakdown of key factors and risks
- **Interactive Charts**: Sentiment distribution and source breakdown visualizations
- **Position Sizing**: Suggested investment amounts based on risk levels

### Multi-Source Sentiment Intelligence
- **Reddit Analysis**: Scrapes r/stocks, r/wallstreetbets, r/investing, and r/SecurityAnalysis
- **Financial News**: Professional news source sentiment analysis via NewsAPI
- **SEC Filings**: Official regulatory document analysis
- **VADER NLP**: Advanced sentiment scoring and classification

### Professional Dashboard
- **Dark Theme**: Modern, professional interface optimized for extended use
- **Responsive Grid**: Clean card-based layout for multiple stocks
- **Performance Analytics**: Multi-stock comparison and trend analysis
- **Export Capabilities**: Download analysis data as CSV
- **Mobile Friendly**: Responsive design for all devices

### Enhanced Visualizations
- **Sentiment Timeline**: Track sentiment trends over time
- **Source Distribution**: Compare Reddit vs News vs SEC data
- **Performance Dashboard**: Multi-stock comparison charts
- **Interactive Cards**: Expandable analysis and advice panels

---

## What Makes StockScope Pro Special?

Think of StockScope Pro as your **personal investment research assistant** that:

1. **Listens** to what people are saying about stocks on social media and news
2. **Analyzes** official SEC filings and regulatory documents
3. **Processes** thousands of data points using AI sentiment analysis
4. **Recommends** exactly what to buy, sell, or hold with detailed reasoning
5. **Updates** automatically to keep your analysis current

### Live Data Features

**Before**: Static analysis of old data  
**After**: "Auto-refresh enabled - TSLA updated 5 minutes ago with 50 new posts"

- **Real-time Updates**: Never miss important market sentiment shifts
- **Expandable Portfolio**: Add any stock ticker instantly
- **Smart Notifications**: Know when your data is refreshed
- **Bulk Operations**: Manage your entire portfolio efficiently

---

## Tech Stack

### Core Platform
- **Streamlit** - Modern web application framework
- **Plotly** - Interactive financial charts and visualizations
- **Pandas** - Advanced data manipulation and analysis
- **NumPy** - Numerical computing for financial calculations

### Data Collection
- **PRAW** - Reddit API integration for social sentiment
- **NewsAPI** - Professional news source integration
- **SEC API** - Official regulatory document access
- **Requests** - HTTP client for web scraping

### Analysis Engine
- **VADER Sentiment** - Advanced NLP sentiment analysis
- **Python-dotenv** - Environment variable management
- **JSON** - Data storage and processing
- **DateTime** - Time-based analysis and filtering

---

## Quick Start Guide

### 1. Installation

```bash
git clone https://github.com/TahmidChowdhury/StockScope.git
cd StockScope
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. API Setup (Optional - works with sample data)

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` file with your API keys:
```env
# Reddit API (optional)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=StockScope/2.0

# News API (optional)
NEWS_API_KEY=your_news_key

# Twitter API (optional)
TWITTER_BEARER_TOKEN=your_bearer_token
```

### 3. Launch StockScope Pro

```bash
streamlit run app.py
```

Open `http://localhost:8501` and start analyzing!

---

## Dashboard Walkthrough

### Main Dashboard
- **Stock Portfolio Grid**: Visual cards showing all analyzed stocks
- **Performance Tab**: Multi-stock comparison and trend analysis
- **Recommendations Tab**: AI-generated investment suggestions
- **Live Status**: Real-time data refresh information

### Investment Advice
1. **Click "Get Advice"** on any stock card
2. **View Recommendation**: BUY/HOLD/SELL with confidence score
3. **Analyze Risk Factors**: Detailed breakdown of investment considerations
4. **Review Charts**: Sentiment distribution and source analysis

### Analysis Features
- **Sentiment Timeline**: Track how sentiment changes over time
- **Source Breakdown**: See data from Reddit, News, and SEC
- **Recent Activity**: Latest posts and discussions
- **Export Data**: Download analysis as CSV

### Live Data Management
- **Auto-refresh Toggle**: Set automatic updates (15-240 minutes)
- **Add New Stocks**: Instantly expand your portfolio
- **Individual Refresh**: Update specific stocks on demand
- **Bulk Operations**: Manage entire portfolio efficiently

---

## How the AI Analysis Works

### Step 1: Multi-Source Data Collection
- **Reddit**: Scrapes financial subreddits for community sentiment
- **News**: Analyzes professional financial news articles
- **SEC**: Processes official regulatory filings
- **Real-time**: Continuously updates with fresh data

### Step 2: Advanced Sentiment Analysis
- **VADER NLP**: Analyzes text sentiment with high accuracy
- **Confidence Scoring**: Measures reliability of sentiment signals
- **Trend Analysis**: Identifies improving/declining sentiment patterns
- **Source Weighting**: Balances different data sources appropriately

### Step 3: AI Recommendation Engine
- **Multi-factor Analysis**: Combines sentiment, volume, and recency
- **Risk Assessment**: Evaluates investment risk levels
- **Confidence Metrics**: Transparent scoring system
- **Detailed Reasoning**: Explains every recommendation

### Step 4: Interactive Visualization
- **Real-time Charts**: Live updating visualizations
- **Comparative Analysis**: Multi-stock performance comparison
- **Export Capabilities**: Download data for further analysis
- **Mobile Responsive**: Works on all devices

---

## Sample Investment Analysis

**Example: Analyzing NVDA with live data**

```
[STRONG BUY] - NVIDIA (NVDA)
Score: 92/100 | Confidence: 87%
Risk Level: MEDIUM | Time Horizon: Short-term

Key Factors:
• Average sentiment: 0.342 (strongly positive)
• Total discussions: 83 posts
• Positive sentiment: 64 posts (77.1%)
• Recent trend: Improving
• Data quality: High (multiple sources)

Data Sources:
• Reddit: 83 posts from financial subreddits
• News: 20 recent articles
• SEC: 6 regulatory filings

Risk Assessment:
• Standard market risks apply
• Medium volatility expected
• Strong community support
```

---

## Advanced Features

### Live Data Management
- **Auto-refresh Scheduling**: Set custom refresh intervals
- **Progress Tracking**: Real-time status of data collection
- **Error Handling**: Graceful handling of API failures
- **Data Persistence**: Automatic saving of all analysis

### Portfolio Management
- **Dynamic Addition**: Add any stock ticker instantly
- **Individual Control**: Refresh or remove specific stocks
- **Bulk Operations**: Manage entire portfolio efficiently
- **Export Capabilities**: Download analysis as CSV

### Analysis Tools
- **Multi-timeframe Analysis**: Compare different time periods
- **Source Filtering**: Focus on specific data sources
- **Sentiment Thresholds**: Filter by sentiment strength
- **Performance Comparison**: Multi-stock analysis

---

## Current Portfolio

The platform currently tracks **12 stocks** with live data:

### Tech Giants
- **AAPL** (Apple) - Consumer electronics leader
- **GOOGL** (Google) - Search and cloud computing
- **MSFT** (Microsoft) - Software and cloud services
- **META** (Meta) - Social media and metaverse
- **NVDA** (NVIDIA) - AI and graphics processing
- **TSLA** (Tesla) - Electric vehicles and energy

### Growth Stocks
- **AMZN** (Amazon) - E-commerce and cloud services
- **PLTR** (Palantir) - Data analytics and AI
- **RKLB** (Rocket Lab) - Space technology

### Cryptocurrencies
- **BTC** (Bitcoin) - Digital currency
- **ETH** (Ethereum) - Blockchain platform
- **DOGE** (Dogecoin) - Meme cryptocurrency

*Add any stock instantly using the sidebar!*

---

## Requirements

Our streamlined requirements.txt includes **essential packages**:

### Core Platform
```
streamlit==1.45.0        # Web application framework
plotly==6.0.1            # Interactive visualizations
pandas==2.2.3            # Data manipulation
numpy==2.0.2             # Numerical computing
```

### Data Collection
```
praw==7.8.1              # Reddit API client
requests==2.32.3         # HTTP client
beautifulsoup4==4.13.4   # Web scraping
python-dotenv==1.0.1     # Environment variables
```

### Analysis Engine
```
vaderSentiment==3.3.2    # Sentiment analysis
lxml==5.3.0              # XML/HTML parsing
```

---

## Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**App not loading:**
```bash
streamlit run app.py --server.port 8501
```

**Data not updating:**
- Check internet connection
- Verify API keys in .env file
- Use manual refresh button

**Charts not displaying:**
```bash
pip install plotly --upgrade
streamlit cache clear
```

---

## Roadmap

### Phase 1: Enhanced Analytics
- [ ] Technical indicators integration
- [ ] Price data correlation
- [ ] Volatility analysis
- [ ] Risk-adjusted returns

### Phase 2: Advanced Features
- [ ] Real-time alerts and notifications
- [ ] Custom watchlists
- [ ] Performance tracking
- [ ] Backtesting capabilities

### Phase 3: Professional Tools
- [ ] Portfolio optimization
- [ ] API endpoints
- [ ] Multi-user support
- [ ] Advanced reporting

---

## Contributing

We welcome contributions to make StockScope Pro even better!

```bash
# Development setup
git clone https://github.com/TahmidChowdhury/StockScope.git
cd StockScope
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
streamlit run app.py

# Submit changes
git checkout -b feature/amazing-feature
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

---

## License

MIT License - Use this code to build amazing investment tools!

---

## Acknowledgments

- **Streamlit** - Making beautiful web apps simple
- **Plotly** - Interactive visualization library
- **PRAW** - Reddit API integration
- **NewsAPI** - Professional news data
- **VADER** - Robust sentiment analysis

---

## Created By

**Tahmid Chowdhury**  
Portfolio: https://tahmidchowdhury.github.io/ | GitHub: https://github.com/TahmidChowdhury

---

<div align="center">
  <h3>From Social Sentiment to Smart Investment Decisions</h3>
  <p><strong>Star this repo if StockScope Pro helped your investment research!</strong></p>
  <p><em>Built with Live Data, AI Analysis, and Coffee</em></p>
</div>
