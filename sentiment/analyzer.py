# sentiment/analyzer.py

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    """
    Returns a dictionary of sentiment scores for the given text.
    """
    return analyzer.polarity_scores(text)
