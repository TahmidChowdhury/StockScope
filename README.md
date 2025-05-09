
# 📊 StockScope

**StockScope** is an interactive stock sentiment analyzer that fetches Reddit discussions in real time and runs natural language processing to detect market sentiment. Built with Python, VADER NLP, and Streamlit, this app helps you visualize public sentiment around any stock ticker — instantly.

---

## 🧠 Key Features

- 🔎 Pulls live Reddit posts from r/stocks and r/wallstreetbets
- 💬 Performs sentiment analysis using VADER
- 📊 Displays interactive sentiment charts (pie + timeline)
- 🧵 Dynamic ticker input — type in any stock symbol (e.g., TSLA, AAPL)
- ⚡ One-click scraping + analysis via Streamlit UI
- 🧩 Modular backend (can expand to news, Twitter, etc.)

---

## 🚀 How It Works

1. Type a stock ticker (e.g., `TSLA`) in the input box
2. Click **"Fetch + Analyze"**
3. StockScope will:
   - Scrape Reddit for recent posts
   - Analyze each post’s sentiment
   - Save data to JSON
   - Render interactive charts and post breakdowns

---

## 🧰 Tech Stack

- **Python 3.9+**
- **Streamlit** for frontend dashboard
- **PRAW** for Reddit API access
- **VADER Sentiment** for NLP
- **Plotly** for interactive visualizations
- (Optional: JSON, SQLite, or MongoDB for data storage)

---

## 🛠️ Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/TahmidChowdhury/StockScope.git
cd StockScope
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

You may also need to install:

```bash
pip install streamlit plotly praw vaderSentiment python-dotenv
```

### 3. Set Up Reddit API Keys

Create a `.env` file in your project root:

```
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=StockScopeSentiment/0.1
```

---

## 🖥️ Run the App

```bash
streamlit run streamlit_app.py
```

Then go to `http://localhost:8501` in your browser.

---

## 🧪 Example Screenshots

*Coming soon...*

---

## 🛣️ Roadmap

- [ ] Add news sentiment scraping
- [ ] Combine Reddit + news views
- [ ] Support Twitter/X and forums
- [ ] Add price overlays
- [ ] Deploy on Streamlit Cloud
- [ ] Save data to database (SQLite or MongoDB)
- [ ] User login + watchlist

---

## 📄 License

MIT License

---

## 👨‍💻 Author

**[Tahmid Chowdhury](https://github.com/TahmidChowdhury)**  
[Portfolio](https://tahmidchowdhury.github.io/)  
Built with 🧠, 📊, and ☕️
