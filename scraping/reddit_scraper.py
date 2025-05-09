# scraping/reddit_scraper.py

import os
import praw
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_reddit_client():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

def fetch_reddit_posts(ticker, limit=50):
    reddit = get_reddit_client()
    subreddits = ["stocks", "wallstreetbets"]
    results = []

    for sub in subreddits:
        subreddit = reddit.subreddit(sub)
        for submission in subreddit.search(ticker, limit=limit):
               created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
               results.append({
                "title": submission.title,
                "score": submission.score,
                "url": submission.url,
                "created_utc": submission.created_utc,
                "subreddit": sub,
                "created": created,
            })

    return results
