# visualizations/plot_sentiment.py

import json
import os
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import streamlit as st
import io

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

def generate_wordcloud_for_streamlit(text, title="Word Cloud"):
    """
    Generate a word cloud for Streamlit display.

    Args:
        text (str): The text data to generate the word cloud from.
        title (str): Title of the word cloud plot.

    Returns:
        matplotlib figure object for Streamlit display
    """
    if not text.strip():
        return None
    
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='viridis',
        max_words=100
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title(title, fontsize=16)
    
    return fig

def generate_wordcloud(text, title="Word Cloud"):
    """
    Generate a word cloud from text data.

    Args:
        text (str): The text data to generate the word cloud from.
        title (str): Title of the word cloud plot.

    Returns:
        None
    """
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(title, fontsize=16)
    plt.show()

# Example usage
if __name__ == "__main__":
    sample_text = "Tesla stock is rising. Tesla is a great company. Stock market is volatile."
    generate_wordcloud(sample_text, title="Sample Word Cloud")
