# visualizations/plot_sentiment.py

import json
import os
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import seaborn as sns

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

def create_sentiment_heatmap(df):
    """
    Create a sentiment intensity heatmap by source and time.
    """
    if df.empty:
        return None
    
    # Create hourly bins
    df['hour'] = pd.to_datetime(df['created_dt']).dt.hour
    df['day'] = pd.to_datetime(df['created_dt']).dt.day_name()
    
    # Create pivot table for heatmap
    heatmap_data = df.pivot_table(
        values='compound', 
        index='source', 
        columns='hour', 
        aggfunc='mean'
    ).fillna(0)
    
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Source", color="Avg Sentiment"),
        title="📅 Sentiment Intensity Heatmap by Source & Time",
        color_continuous_scale='RdYlGn',
        aspect="auto"
    )
    
    fig.update_layout(
        xaxis_title="Hour of Day (24h)",
        yaxis_title="Data Source",
        height=400
    )
    
    return fig

def create_engagement_vs_sentiment_scatter(df):
    """
    Create a scatter plot showing relationship between engagement and sentiment.
    """
    if df.empty or 'score' not in df.columns:
        return None
    
    # Filter out None values and ensure numeric
    df_clean = df.dropna(subset=['score', 'compound'])
    df_clean = df_clean[df_clean['score'] != '']
    df_clean['score'] = pd.to_numeric(df_clean['score'], errors='coerce')
    df_clean = df_clean.dropna(subset=['score'])
    
    if df_clean.empty:
        return None
    
    # Create color mapping for sentiment
    df_clean['sentiment_color'] = df_clean['sentiment'].map({
        'positive': '#28a745',
        'neutral': '#ffc107', 
        'negative': '#dc3545'
    })
    
    fig = px.scatter(
        df_clean,
        x='compound',
        y='score',
        color='source',
        size='score',
        hover_data=['title'],
        title="🎯 Engagement vs Sentiment Analysis",
        labels={
            'compound': 'Sentiment Score (-1 to +1)',
            'score': 'Engagement Score (Upvotes/Likes)'
        }
    )
    
    fig.update_layout(
        xaxis_title="Sentiment Score",
        yaxis_title="Engagement (Upvotes/Likes)",
        height=500
    )
    
    return fig

def create_sentiment_gauge(df):
    """
    Create a gauge chart showing overall sentiment health.
    """
    if df.empty:
        return None
    
    avg_sentiment = df['compound'].mean()
    
    # Convert to 0-100 scale for gauge
    gauge_value = (avg_sentiment + 1) * 50
    
    # Determine color based on sentiment
    if avg_sentiment > 0.1:
        color = "green"
        status = "Bullish 🐂"
    elif avg_sentiment < -0.1:
        color = "red"
        status = "Bearish 🐻"
    else:
        color = "yellow"
        status = "Neutral ⚖️"
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = gauge_value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"Market Sentiment: {status}"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 25], 'color': "lightgray"},
                {'range': [25, 75], 'color': "gray"},
                {'range': [75, 100], 'color': "lightgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=400)
    return fig

def create_trending_topics_bar(df, top_n=10):
    """
    Create a bar chart of trending keywords/topics.
    """
    if df.empty:
        return None
    
    # Combine all text content
    all_text = ' '.join(df['title'].fillna('').astype(str))
    
    # Simple keyword extraction (you could use more sophisticated NLP here)
    import re
    
    # Common stock-related keywords
    stock_keywords = [
        'buy', 'sell', 'hold', 'earnings', 'profit', 'loss', 'revenue',
        'growth', 'market', 'price', 'stock', 'shares', 'investment',
        'bullish', 'bearish', 'rally', 'crash', 'volatile', 'analysis'
    ]
    
    # Count keyword occurrences
    keyword_counts = {}
    text_lower = all_text.lower()
    
    for keyword in stock_keywords:
        count = len(re.findall(r'\b' + keyword + r'\b', text_lower))
        if count > 0:
            keyword_counts[keyword] = count
    
    if not keyword_counts:
        return None
    
    # Sort and take top N
    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    keywords, counts = zip(*top_keywords)
    
    fig = px.bar(
        x=list(counts),
        y=list(keywords),
        orientation='h',
        title=f"🔥 Top {top_n} Trending Topics",
        labels={'x': 'Mentions', 'y': 'Keywords'},
        color=list(counts),
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=400,
        showlegend=False
    )
    
    return fig

def create_sentiment_timeline_advanced(df):
    """
    Create an advanced timeline with sentiment bands and volume.
    """
    if df.empty:
        return None
    
    # Prepare data
    df['date'] = pd.to_datetime(df['created_dt']).dt.date
    daily_sentiment = df.groupby(['date', 'source']).agg({
        'compound': 'mean',
        'title': 'count'
    }).reset_index()
    daily_sentiment.rename(columns={'title': 'volume'}, inplace=True)
    
    # Create subplot
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=('📈 Sentiment Over Time', '📊 Post Volume'),
        row_heights=[0.7, 0.3]
    )
    
    # Add sentiment lines for each source
    colors = {'Reddit': '#ff4500', 'Twitter': '#1da1f2', 'News': '#00d4aa'}
    
    for source in daily_sentiment['source'].unique():
        source_data = daily_sentiment[daily_sentiment['source'] == source]
        
        # Sentiment line
        fig.add_trace(
            go.Scatter(
                x=source_data['date'],
                y=source_data['compound'],
                mode='lines+markers',
                name=f'{source} Sentiment',
                line=dict(color=colors.get(source, '#333333'), width=3),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        # Volume bars
        fig.add_trace(
            go.Bar(
                x=source_data['date'],
                y=source_data['volume'],
                name=f'{source} Volume',
                marker_color=colors.get(source, '#333333'),
                opacity=0.6
            ),
            row=2, col=1
        )
    
    # Add sentiment zones
    fig.add_hline(y=0.1, line_dash="dash", line_color="green", 
                  annotation_text="Bullish Zone", row=1, col=1)
    fig.add_hline(y=-0.1, line_dash="dash", line_color="red", 
                  annotation_text="Bearish Zone", row=1, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=1, col=1)
    
    fig.update_layout(
        height=600,
        title="📊 Advanced Sentiment & Volume Analysis",
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text="Sentiment Score", row=1, col=1)
    fig.update_yaxes(title_text="Post Count", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    
    return fig

def create_source_comparison_radar(df):
    """
    Create a radar chart comparing sentiment across sources.
    """
    if df.empty:
        return None
    
    # Calculate metrics by source
    source_metrics = df.groupby('source').agg({
        'compound': ['mean', 'std', 'count'],
        'score': 'mean'
    }).round(3)
    
    source_metrics.columns = ['avg_sentiment', 'sentiment_volatility', 'post_count', 'avg_engagement']
    source_metrics = source_metrics.reset_index()
    
    if len(source_metrics) < 2:
        return None
    
    # Normalize metrics to 0-1 scale for radar chart
    metrics_to_plot = ['avg_sentiment', 'sentiment_volatility', 'post_count', 'avg_engagement']
    
    fig = go.Figure()
    
    colors = ['#ff4500', '#1da1f2', '#00d4aa']
    
    for i, source in enumerate(source_metrics['source']):
        source_data = source_metrics[source_metrics['source'] == source]
        
        values = []
        for metric in metrics_to_plot:
            val = source_data[metric].iloc[0]
            if pd.notna(val):
                # Normalize to 0-1 (simple min-max scaling)
                if metric == 'avg_sentiment':
                    normalized = (val + 1) / 2  # -1 to 1 -> 0 to 1
                else:
                    max_val = source_metrics[metric].max()
                    min_val = source_metrics[metric].min()
                    if max_val != min_val:
                        normalized = (val - min_val) / (max_val - min_val)
                    else:
                        normalized = 0.5
            else:
                normalized = 0
            values.append(normalized)
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=['Avg Sentiment', 'Volatility', 'Volume', 'Engagement'],
            fill='toself',
            name=source,
            line_color=colors[i % len(colors)]
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="🎯 Source Performance Comparison",
        height=500
    )
    
    return fig

# Example usage
if __name__ == "__main__":
    sample_text = "Tesla stock is rising. Tesla is a great company. Stock market is volatile."
    generate_wordcloud(sample_text, title="Sample Word Cloud")
