# visualizations/plot_sentiment.py

import json
import os
from collections import Counter
import matplotlib.pyplot as plt

def plot_sentiment_distribution(filepath):
    # Load the JSON data
    with open(filepath, "r") as f:
        data = json.load(f)

    # Count sentiment labels
    sentiment_labels = [post["sentiment"]["label"] for post in data]
    counts = Counter(sentiment_labels)

    # Prepare pie chart
    labels = counts.keys()
    sizes = counts.values()
    colors = ["green", "gold", "red"]  # positive, neutral, negative

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=140)
    plt.title("Sentiment Distribution")
    plt.axis("equal")  # Equal aspect ratio makes it a circle.
    plt.show()
