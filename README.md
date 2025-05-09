# 📊 StockScope

**StockScope** is a Python-based sentiment analysis tool that gives you a deeper look into what the internet is saying about your favorite stocks. By combining real-time financial news and Reddit discussions, it surfaces public sentiment and trends that could influence the market.

---

## 🔍 Features

- 🔎 Pulls posts from Reddit (r/stocks, r/wallstreetbets) and financial news headlines  
- 💬 Performs sentiment analysis using VADER NLP  
- 📈 Visualizes sentiment trends over time  
- 🧩 Modular design for easy expansion (e.g., Twitter, stock price overlays, dashboards)

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/StockScope.git
cd StockScope
```
### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Run the Application
```bash
python main.py
```
🧱 Project Structure
```bash
StockScope/
├── data/                  # Raw/cached data
├── sentiment/             # Sentiment analysis logic
│   └── analyzer.py
├── scraping/              # Web scraping and API logic
│   ├── reddit_scraper.py
│   └── news_scraper.py
├── visualizations/        # Graph generation
│   └── plot_sentiment.py
├── main.py                # Entry point
├── requirements.txt       # Dependencies
└── README.md              # This file
```
📦 Dependencies

    vaderSentiment

    requests

    beautifulsoup4

    praw

    matplotlib

🛣️ Future Plans

    Correlate sentiment with stock price movement

    Integrate Twitter/X scraping or APIs

    Streamlit or Flask dashboard interface

    User-configurable sentiment alerts

📄 License

MIT License
👨‍💻 Author

[Tahmid Chowdhury](https://github.com/tahmidchowdhury)

[Portfolio Website](https://tahmidchowdhury.github.io/)

Built with 🧠, 📊, and a little caffeine.
