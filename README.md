# 📊 StockScope

**StockScope** is a comprehensive multi-source stock sentiment analyzer that aggregates public sentiment from Reddit, Twitter, and financial news in real-time. Built with Python, VADER NLP, and Streamlit, this platform provides instant sentiment analysis and visualization for any stock ticker across multiple data sources.

---

## 🌟 Key Features

### 📱 **Multi-Source Data Collection**
- 🔴 **Reddit Analysis**: Scrapes r/stocks, r/wallstreetbets, and other financial subreddits
- 🐦 **Twitter Sentiment**: Real-time tweet analysis using Twitter API v2
- 📰 **Financial News**: Sentiment analysis from multiple news sources
- 🔄 **Unified Dashboard**: All sources combined in one comprehensive view

### 🧠 **Advanced Analytics**
- 💬 **VADER Sentiment Analysis**: Professional-grade NLP for accurate sentiment scoring
- 📊 **Interactive Visualizations**: Dynamic charts, trends, and distributions
- ☁️ **Word Clouds**: Visual representation of trending topics and keywords
- 🎯 **Smart Filtering**: Filter by source, sentiment, date range, and more

### ⚡ **Enhanced User Experience**
- 🚀 **One-Click Analysis**: Instant data fetching and processing
- 📈 **Real-Time Updates**: Live sentiment tracking and updates
- 💾 **Data Export**: Download results as CSV for further analysis
- 🎨 **Modern UI**: Clean, responsive design with gradient themes
- 📱 **Mobile Friendly**: Works seamlessly on all devices

### 🛡️ **Robust Infrastructure**
- ⚠️ **Rate Limit Handling**: Automatic fallback and retry mechanisms
- 🔄 **Error Recovery**: Graceful handling of API failures
- 📊 **Sample Data**: Testing mode when APIs are unavailable
- 🔒 **Secure**: Environment-based credential management

---

## 🚀 How It Works

1. **Enter Stock Ticker**: Type any stock symbol (e.g., `TSLA`, `AAPL`, `NVDA`)
2. **Fetch & Analyze**: Click to start multi-source data collection
3. **Real-Time Processing**: StockScope will simultaneously:
   - 🔴 Scrape Reddit for recent discussions
   - 🐦 Fetch Twitter sentiment from recent tweets
   - 📰 Analyze financial news articles
   - 🧠 Process sentiment using advanced NLP
   - 💾 Save structured data to JSON files
4. **Interactive Dashboard**: Explore results with:
   - 📊 Sentiment distribution charts
   - 📈 Timeline trends across all sources
   - ☁️ Word clouds of trending topics
   - 📋 Detailed data tables with filtering

---

## 🧰 Tech Stack

### **Backend**
- **Python 3.9+** - Core application logic
- **PRAW** - Reddit API integration
- **Tweepy** - Twitter API v2 client
- **VADER Sentiment** - Advanced sentiment analysis
- **Python-dotenv** - Environment variable management

### **Frontend & Visualization**
- **Streamlit** - Interactive web dashboard
- **Plotly** - Dynamic, interactive charts
- **Matplotlib** - Word cloud generation
- **Pandas** - Data manipulation and analysis

### **APIs & Data Sources**
- **Reddit API** - Real-time social sentiment
- **Twitter API v2** - Social media sentiment tracking
- **News APIs** - Financial news sentiment analysis

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/TahmidChowdhury/StockScope.git
cd StockScope
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up API Credentials

Create a `.env` file in your project root with the following credentials:

```env
# Reddit API Credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=StockScope/1.0

# Twitter API Credentials
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# News API Credentials (Optional)
NEWS_API_KEY=your_news_api_key
```

#### 🔑 **Getting API Keys:**

**Reddit API:**
1. Go to [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Create a new application (script type)
3. Copy your client ID and secret

**Twitter API:**
1. Apply at [developer.twitter.com](https://developer.twitter.com)
2. Create a new project/app
3. Generate your Bearer Token and API keys

**News API (Optional):**
1. Sign up at [newsapi.org](https://newsapi.org)
2. Get your free API key

---

## 🖥️ Running the Application

### Start the Streamlit Dashboard

```bash
streamlit run streamlit_app.py
```

Then open your browser and navigate to `http://localhost:8501`

### Command Line Testing

Test individual components:

```bash
# Test Reddit scraper
python scraping/reddit_scraper.py

# Test Twitter scraper
python scraping/twitter_scraper.py

# Test News scraper
python scraping/news_scraper.py

# Run full pipeline
python main.py
```

---

## 📊 Dashboard Features

### **Main Dashboard**
- 📈 **Real-time metrics**: Total posts, source breakdown, average sentiment
- 🥧 **Sentiment distribution**: Visual pie chart of positive/negative/neutral sentiment
- 📊 **Trend analysis**: Timeline showing sentiment changes over time
- ☁️ **Word clouds**: Most discussed topics and keywords

### **Advanced Filtering**
- 📅 **Date Range**: Filter data by specific time periods
- 📊 **Source Selection**: Include/exclude Reddit, Twitter, or News
- 🎯 **Sentiment Filtering**: Focus on positive, negative, or neutral content
- 🔍 **Interactive Search**: Real-time data exploration

### **Data Management**
- 💾 **Export Options**: Download analysis results as CSV
- 🔄 **Refresh Controls**: Update data with force refresh options
- 🗂️ **Data Persistence**: Automatic saving of analysis results
- 📋 **Detailed Views**: Expandable data tables with full content

---

## 🧪 Example Analysis

Here's what you get when analyzing a stock like `TSLA`:

**Sample Output:**
- **Reddit Posts**: 45 discussions from multiple subreddits
- **Twitter Mentions**: 30 recent tweets with engagement metrics
- **News Articles**: 12 financial news pieces
- **Overall Sentiment**: 65% Positive, 25% Neutral, 10% Negative
- **Trending Topics**: "earnings", "innovation", "market volatility"

---

## 🔧 Advanced Configuration

### Rate Limiting & Error Handling
- **Automatic Retry**: Built-in retry logic for API failures
- **Fallback Data**: Sample data generation when APIs are unavailable
- **Rate Limit Management**: Intelligent handling of API quotas

### Customization Options
- **Sentiment Thresholds**: Adjust positive/negative boundaries
- **Data Sources**: Enable/disable specific platforms
- **Sample Size**: Configure number of posts to analyze
- **Time Windows**: Set analysis periods

---

## 🛣️ Roadmap & Future Features

### **Short Term**
- [ ] Additional news sources integration
- [ ] Enhanced sentiment model (BERT/RoBERTa)
- [ ] Real-time price correlation analysis
- [ ] Email/SMS sentiment alerts

### **Medium Term**
- [ ] Machine learning trend prediction
- [ ] Portfolio sentiment tracking
- [ ] Historical sentiment analysis
- [ ] API endpoint for external integration

### **Long Term**
- [ ] Multi-language sentiment analysis
- [ ] Cryptocurrency sentiment tracking
- [ ] Cloud deployment (AWS/GCP)
- [ ] Mobile application
- [ ] User authentication and portfolios

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black src/
isort src/
```

---

## 📈 Performance & Limitations

### **Current Capabilities**
- **Reddit**: ~50-100 posts per ticker
- **Twitter**: ~20-50 tweets per request (rate limited)
- **News**: ~10-20 articles per ticker
- **Processing Speed**: ~30-60 seconds for full analysis

### **Known Limitations**
- Twitter API free tier has strict rate limits (15 requests/15 minutes)
- Reddit API requires authentication
- Some news sources may require premium access
- Real-time data depends on API availability

---

## 🐛 Troubleshooting

### Common Issues

**"Rate limit exceeded"**
- Wait 15 minutes for Twitter API reset
- Use sample data mode for testing

**"Authentication failed"**
- Check your `.env` file credentials
- Ensure API keys are valid and active

**"No data found"**
- Try different stock tickers
- Check if APIs are accessible
- Use force refresh option

**Installation Issues**
```bash
# Update pip
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# Clear cache if needed
pip cache purge
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **VADER Sentiment Analysis** - For robust sentiment analysis
- **Streamlit Team** - For the amazing web framework
- **Reddit API** - For access to social sentiment data
- **Twitter API** - For real-time social media insights

---

## 👨‍💻 Author

**[Tahmid Chowdhury](https://github.com/TahmidChowdhury)**  
🌐 Portfolio: [https://tahmidchowdhury.github.io/](https://tahmidchowdhury.github.io/)  
💼 LinkedIn: [Your LinkedIn Profile]

---

<div align="center">
  <p><strong>Built with 📊 Data, and ☕️ Coffee</strong></p>
  <p><em>⭐ Star this repository if you found it useful!</em></p>
</div>
