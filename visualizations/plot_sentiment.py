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
import yfinance as yf
from scipy import stats
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

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

def create_investment_dashboard(df, ticker, advisor_result):
    """
    Create a comprehensive investment dashboard.
    """
    if df.empty or 'recommendation' not in advisor_result:
        return None
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '📊 Investment Score Breakdown',
            '🎯 Recommendation Summary', 
            '📈 Sentiment vs Price Correlation',
            '⚡ Key Metrics'
        ),
        specs=[[{"type": "bar"}, {"type": "indicator"}],
               [{"type": "scatter"}, {"type": "table"}]]
    )
    
    # 1. Score breakdown
    if 'metrics' in advisor_result:
        metrics = advisor_result['metrics']
        metric_names = []
        metric_values = []
        
        for k, v in metrics.items():
            if isinstance(v, (int, float)) and k != 'support_resistance':
                metric_names.append(k.replace('_', ' ').title())
                metric_values.append(v)
        
        if metric_names:
            fig.add_trace(
                go.Bar(
                    x=metric_names,
                    y=metric_values,
                    name="Metrics",
                    marker_color=['#28a745' if v > 0 else '#dc3545' for v in metric_values],
                    text=[f"{v:.3f}" for v in metric_values],
                    textposition="outside"
                ),
                row=1, col=1
            )
    
    # 2. Recommendation gauge
    rec = advisor_result['recommendation']
    gauge_value = rec['score'] * 100
    
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=gauge_value,
            title={'text': f"{rec['color']} {rec['action']}"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#28a745" if gauge_value > 50 else "#dc3545"},
                'steps': [
                    {'range': [0, 30], 'color': "#ffebee"},
                    {'range': [30, 70], 'color': "#fff3e0"},
                    {'range': [70, 100], 'color': "#e8f5e8"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ),
        row=1, col=2
    )
    
    # 3. Sentiment vs Price correlation
    try:
        stock = yf.Ticker(ticker)
        hist = stock.get_history(period="30d")
        
        if not hist.empty and len(df) > 0:
            # Align dates
            df['date'] = pd.to_datetime(df['created_dt']).dt.date
            daily_sentiment = df.groupby('date')['compound'].mean().reset_index()
            
            # Merge with price data
            hist_reset = hist.reset_index()
            hist_reset['date'] = hist_reset['Date'].dt.date
            
            merged = pd.merge(daily_sentiment, hist_reset, on='date', how='inner')
            
            if not merged.empty:
                fig.add_trace(
                    go.Scatter(
                        x=merged['compound'],
                        y=merged['Close'],
                        mode='markers',
                        name='Price vs Sentiment',
                        marker=dict(
                            size=10,
                            color=merged['compound'],
                            colorscale='RdYlGn',
                            showscale=True,
                            colorbar=dict(title="Sentiment")
                        ),
                        text=[f"Date: {d}<br>Sentiment: {s:.3f}<br>Price: ${p:.2f}" 
                              for d, s, p in zip(merged['date'], merged['compound'], merged['Close'])],
                        hovertemplate='%{text}<extra></extra>'
                    ),
                    row=2, col=1
                )
    except Exception as e:
        pass
    
    # 4. Key metrics table
    table_data = []
    if 'metrics' in advisor_result:
        for key, value in advisor_result['metrics'].items():
            if key == 'support_resistance' and isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, (int, float)):
                        table_data.append([f"Price {k.title()}", f"${v:.2f}"])
            elif isinstance(value, (int, float)):
                table_data.append([key.replace('_', ' ').title(), f"{value:.3f}"])
    
    if table_data:
        headers, values = zip(*table_data)
        fig.add_trace(
            go.Table(
                header=dict(values=['Metric', 'Value'], 
                           fill_color='lightgray',
                           align='left'),
                cells=dict(values=[list(headers), list(values)],
                          fill_color='white',
                          align='left')
            ),
            row=2, col=2
        )
    
    fig.update_layout(
        height=800,
        title=f"📊 Investment Analysis Dashboard - {ticker}",
        showlegend=False
    )
    
    return fig

def create_risk_reward_matrix(advisor_results):
    """
    Create a risk-reward matrix for multiple stocks.
    """
    if not advisor_results:
        return None
    
    data = []
    for result in advisor_results:
        if 'recommendation' in result and 'error' not in result:
            data.append({
                'ticker': result['ticker'],
                'reward': result['recommendation']['score'],
                'risk': 1 - result['confidence'],
                'action': result['recommendation']['action'],
                'risk_level': result.get('risk_level', 'MEDIUM')
            })
    
    if not data:
        return None
    
    df_matrix = pd.DataFrame(data)
    
    # Color mapping
    color_map = {
        'STRONG BUY': '#28a745',
        'BUY': '#20c997', 
        'HOLD': '#ffc107',
        'WEAK SELL': '#fd7e14',
        'SELL': '#dc3545'
    }
    
    fig = px.scatter(
        df_matrix,
        x='risk',
        y='reward',
        color='action',
        text='ticker',
        size=[30] * len(df_matrix),
        color_discrete_map=color_map,
        title="🎯 Risk-Reward Investment Matrix",
        labels={
            'risk': 'Investment Risk →',
            'reward': 'Expected Reward →'
        }
    )
    
    # Add quadrant lines
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=0.5, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Add quadrant labels
    fig.add_annotation(x=0.25, y=0.75, text="💎 Sweet Spot<br>High Reward, Low Risk", 
                      showarrow=False, font=dict(size=12, color="green"))
    fig.add_annotation(x=0.75, y=0.75, text="⚠️ High Risk<br>High Reward", 
                      showarrow=False, font=dict(size=12, color="orange"))
    fig.add_annotation(x=0.25, y=0.25, text="😴 Safe Play<br>Low Risk, Low Reward", 
                      showarrow=False, font=dict(size=12, color="blue"))
    fig.add_annotation(x=0.75, y=0.25, text="💀 Danger Zone<br>High Risk, Low Reward", 
                      showarrow=False, font=dict(size=12, color="red"))
    
    fig.update_traces(textposition="top center", textfont_size=14)
    fig.update_layout(height=600, showlegend=True)
    
    return fig

def create_technical_analysis_chart(ticker, days=30):
    """
    Create technical analysis chart with key indicators.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.get_history(period=f"{days}d")
        
        if hist.empty:
            return None
        
        # Calculate technical indicators
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['RSI'] = calculate_rsi(hist['Close'])
        hist['MACD'], hist['MACD_signal'] = calculate_macd(hist['Close'])
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f'{ticker} Price & Moving Averages', 'RSI', 'MACD'),
            row_heights=[0.6, 0.2, 0.2]
        )
        
        # Price and Moving Averages
        fig.add_trace(
            go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name='Price'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=hist.index, y=hist['MA5'], mode='lines', name='MA5', line=dict(color='orange')),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=hist.index, y=hist['MA20'], mode='lines', name='MA20', line=dict(color='blue')),
            row=1, col=1
        )
        
        # RSI
        fig.add_trace(
            go.Scatter(x=hist.index, y=hist['RSI'], mode='lines', name='RSI', line=dict(color='purple')),
            row=2, col=1
        )
        
        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold", row=2, col=1)
        
        # MACD
        fig.add_trace(
            go.Scatter(x=hist.index, y=hist['MACD'], mode='lines', name='MACD', line=dict(color='blue')),
            row=3, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=hist.index, y=hist['MACD_signal'], mode='lines', name='Signal', line=dict(color='red')),
            row=3, col=1
        )
        
        fig.update_layout(
            title=f"📈 Technical Analysis - {ticker}",
            height=800,
            xaxis_rangeslider_visible=False
        )
        
        return fig
        
    except Exception as e:
        return None

def calculate_rsi(prices, window=14):
    """Calculate RSI indicator."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator."""
    exp1 = prices.ewm(span=fast).mean()
    exp2 = prices.ewm(span=slow).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal).mean()
    return macd, signal_line

def create_portfolio_optimization_chart(advisor_results, budget=10000):
    """
    Create portfolio allocation suggestion based on investment analysis.
    """
    if not advisor_results:
        return None
    
    # Filter successful analyses
    valid_results = [r for r in advisor_results if 'recommendation' in r and 'error' not in r]
    
    if not valid_results:
        return None
    
    # Calculate allocation weights based on score and inverse risk
    allocations = []
    total_score = 0
    
    for result in valid_results:
        score = result['recommendation']['score']
        confidence = result['confidence']
        risk_multiplier = 1 if result['risk_level'] == 'LOW' else 0.7 if result['risk_level'] == 'MEDIUM' else 0.4
        
        # Only include BUY recommendations
        if result['recommendation']['action'] in ['BUY', 'STRONG BUY']:
            weighted_score = score * confidence * risk_multiplier
            allocations.append({
                'ticker': result['ticker'],
                'score': weighted_score,
                'action': result['recommendation']['action'],
                'risk_level': result['risk_level']
            })
            total_score += weighted_score
    
    if not allocations or total_score == 0:
        return None
    
    # Calculate percentages and dollar amounts
    for allocation in allocations:
        allocation['percentage'] = (allocation['score'] / total_score) * 100
        allocation['amount'] = (allocation['percentage'] / 100) * budget
    
    # Create pie chart
    fig = px.pie(
        values=[a['percentage'] for a in allocations],
        names=[a['ticker'] for a in allocations],
        title=f"💰 Suggested Portfolio Allocation (${budget:,})",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>' +
                      'Allocation: %{percent}<br>' +
                      'Amount: $%{value:,.0f}<br>' +
                      '<extra></extra>'
    )
    
    return fig

def create_sentiment_donut_chart(df, title="Sentiment Distribution"):
    """
    Create a beautiful donut chart for sentiment distribution.
    """
    if df.empty:
        return None
    
    sentiment_counts = df['sentiment'].value_counts()
    
    # Beautiful color palette
    colors = {
        'positive': '#28a745',
        'negative': '#dc3545', 
        'neutral': '#ffc107'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=sentiment_counts.index,
        values=sentiment_counts.values,
        hole=0.5,
        marker_colors=[colors.get(label, '#6c757d') for label in sentiment_counts.index],
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=14),
        hovertemplate='<b>%{label}</b><br>' +
                      'Count: %{value}<br>' +
                      'Percentage: %{percent}<br>' +
                      '<extra></extra>'
    )])
    
    # Add center text
    total_posts = len(df)
    avg_sentiment = df['compound'].mean()
    
    fig.add_annotation(
        text=f"<b>{total_posts}</b><br>Total Posts<br><br><b>{avg_sentiment:.3f}</b><br>Avg Score",
        x=0.5, y=0.5,
        font_size=16,
        showarrow=False
    )
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

def create_sentiment_over_time_smooth(df):
    """
    Create a smooth sentiment timeline with confidence bands.
    """
    if df.empty:
        return None
    
    # Prepare data with proper date handling
    df['date'] = pd.to_datetime(df['created_dt']).dt.date
    daily_data = df.groupby('date').agg({
        'compound': ['mean', 'std', 'count']
    }).reset_index()
    
    daily_data.columns = ['date', 'sentiment_mean', 'sentiment_std', 'post_count']
    daily_data['sentiment_std'] = daily_data['sentiment_std'].fillna(0)
    
    # Calculate confidence bands
    daily_data['upper_bound'] = daily_data['sentiment_mean'] + daily_data['sentiment_std']
    daily_data['lower_bound'] = daily_data['sentiment_mean'] - daily_data['sentiment_std']
    
    fig = go.Figure()
    
    # Add confidence band
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['upper_bound'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['lower_bound'],
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(102, 126, 234, 0.2)',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add main sentiment line
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['sentiment_mean'],
        mode='lines+markers',
        name='Average Sentiment',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8, color='#667eea'),
        hovertemplate='<b>Date: %{x}</b><br>' +
                      'Sentiment: %{y:.3f}<br>' +
                      'Posts: %{customdata}<br>' +
                      '<extra></extra>',
        customdata=daily_data['post_count']
    ))
    
    # Add horizontal reference lines
    fig.add_hline(y=0.1, line_dash="dash", line_color="green", opacity=0.5,
                  annotation_text="Bullish Threshold", annotation_position="bottom right")
    fig.add_hline(y=-0.1, line_dash="dash", line_color="red", opacity=0.5,
                  annotation_text="Bearish Threshold", annotation_position="top right")
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title="📈 Sentiment Timeline with Confidence Bands",
        xaxis_title="Date",
        yaxis_title="Sentiment Score",
        height=500,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_source_volume_comparison(df):
    """
    Create a stacked bar chart comparing post volume by source over time.
    """
    if df.empty:
        return None
    
    df['date'] = pd.to_datetime(df['created_dt']).dt.date
    volume_data = df.groupby(['date', 'source']).size().reset_index(name='count')
    
    # Create stacked bar chart
    fig = px.bar(
        volume_data,
        x='date',
        y='count',
        color='source',
        title="📊 Post Volume by Source Over Time",
        labels={'count': 'Number of Posts', 'date': 'Date'},
        color_discrete_map={
            'Reddit': '#ff4500',
            'Twitter': '#1da1f2', 
            'News': '#00d4aa',
            'SEC': '#6f42c1'
        }
    )
    
    fig.update_layout(
        height=400,
        barmode='stack',
        hovermode='x unified'
    )
    
    return fig

def create_sentiment_correlation_matrix(df):
    """
    Create a correlation matrix between different sentiment sources.
    """
    if df.empty:
        return None
    
    # Pivot to get sentiment by source and date
    df['date'] = pd.to_datetime(df['created_dt']).dt.date
    pivot_data = df.pivot_table(
        values='compound',
        index='date',
        columns='source',
        aggfunc='mean'
    ).fillna(0)
    
    if pivot_data.shape[1] < 2:
        return None
    
    # Calculate correlation matrix
    corr_matrix = pivot_data.corr()
    
    # Create heatmap
    fig = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        title="🔗 Sentiment Correlation Between Sources",
        color_continuous_scale='RdBu',
        color_continuous_midpoint=0
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_engagement_heatmap(df):
    """
    Create a heatmap showing engagement patterns by day and hour.
    """
    if df.empty or 'score' not in df.columns:
        return None
    
    # Prepare data
    df_clean = df.dropna(subset=['score', 'created_dt'])
    df_clean['score'] = pd.to_numeric(df_clean['score'], errors='coerce')
    df_clean = df_clean.dropna(subset=['score'])
    
    if df_clean.empty:
        return None
    
    df_clean['hour'] = pd.to_datetime(df_clean['created_dt']).dt.hour
    df_clean['day_of_week'] = pd.to_datetime(df_clean['created_dt']).dt.day_name()
    
    # Create pivot table
    engagement_matrix = df_clean.pivot_table(
        values='score',
        index='day_of_week',
        columns='hour',
        aggfunc='mean'
    ).fillna(0)
    
    # Reorder days properly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    engagement_matrix = engagement_matrix.reindex(day_order, fill_value=0)
    
    fig = px.imshow(
        engagement_matrix,
        labels=dict(x="Hour of Day", y="Day of Week", color="Avg Engagement"),
        title="🔥 Engagement Heatmap by Day & Hour",
        color_continuous_scale='Viridis',
        aspect="auto"
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_sentiment_violin_plot(df):
    """
    Create violin plots showing sentiment distribution by source.
    """
    if df.empty:
        return None
    
    fig = px.violin(
        df,
        y='compound',
        x='source',
        color='source',
        title="🎻 Sentiment Distribution by Source",
        labels={'compound': 'Sentiment Score', 'source': 'Data Source'},
        color_discrete_map={
            'Reddit': '#ff4500',
            'Twitter': '#1da1f2', 
            'News': '#00d4aa',
            'SEC': '#6f42c1'
        }
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_hline(y=0.1, line_dash="dash", line_color="green", opacity=0.5)
    fig.add_hline(y=-0.1, line_dash="dash", line_color="red", opacity=0.5)
    
    fig.update_layout(
        height=500,
        showlegend=False
    )
    
    return fig

def create_topic_sentiment_bubble(df):
    """
    Create a bubble chart showing topic sentiment and frequency.
    """
    if df.empty:
        return None
    
    # Extract keywords from titles
    all_text = ' '.join(df['title'].fillna('').astype(str))
    
    # Financial keywords
    keywords = [
        'earnings', 'revenue', 'profit', 'loss', 'growth', 'dividend',
        'buyback', 'merger', 'acquisition', 'partnership', 'launch',
        'innovation', 'expansion', 'investment', 'debt', 'cash',
        'market', 'competition', 'regulation', 'patent', 'technology'
    ]
    
    keyword_data = []
    text_lower = all_text.lower()
    
    for keyword in keywords:
        # Count occurrences
        count = text_lower.count(keyword)
        if count > 0:
            # Calculate average sentiment for posts containing this keyword
            keyword_posts = df[df['title'].str.contains(keyword, case=False, na=False)]
            if not keyword_posts.empty:
                avg_sentiment = keyword_posts['compound'].mean()
                keyword_data.append({
                    'keyword': keyword,
                    'count': count,
                    'sentiment': avg_sentiment,
                    'size': min(count * 20, 100)  # Cap bubble size
                })
    
    if not keyword_data:
        return None
    
    keyword_df = pd.DataFrame(keyword_data)
    
    fig = px.scatter(
        keyword_df,
        x='sentiment',
        y='count',
        size='size',
        color='sentiment',
        text='keyword',
        title="💭 Topic Sentiment vs Frequency",
        labels={'sentiment': 'Average Sentiment', 'count': 'Mention Count'},
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0
    )
    
    fig.update_traces(textposition="top center")
    fig.update_layout(height=500)
    
    return fig

def create_market_mood_indicator(df):
    """
    Create a comprehensive market mood indicator dashboard.
    """
    if df.empty:
        return None
    
    # Calculate key metrics
    total_posts = len(df)
    avg_sentiment = df['compound'].mean()
    sentiment_std = df['compound'].std()
    
    # Sentiment distribution
    positive_pct = (df['compound'] > 0.1).mean() * 100
    negative_pct = (df['compound'] < -0.1).mean() * 100
    neutral_pct = 100 - positive_pct - negative_pct
    
    # Recent trend (last 3 days vs previous)
    df['date'] = pd.to_datetime(df['created_dt']).dt.date
    recent_date = df['date'].max()
    cutoff_date = recent_date - timedelta(days=3)
    
    recent_sentiment = df[df['date'] > cutoff_date]['compound'].mean()
    older_sentiment = df[df['date'] <= cutoff_date]['compound'].mean()
    sentiment_trend = recent_sentiment - older_sentiment if not pd.isna(older_sentiment) else 0
    
    # Create subplot layout
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=(
            '🎯 Overall Mood', '📊 Sentiment Mix', '📈 Recent Trend',
            '🌡️ Volatility', '📱 Activity Level', '⚡ Momentum'
        ),
        specs=[[{"type": "indicator"}, {"type": "pie"}, {"type": "indicator"}],
               [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]]
    )
    
    # Overall mood gauge
    mood_value = (avg_sentiment + 1) * 50
    mood_color = "green" if avg_sentiment > 0.1 else "red" if avg_sentiment < -0.1 else "yellow"
    
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=mood_value,
            title={'text': "Market Mood"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': mood_color},
                'steps': [
                    {'range': [0, 30], 'color': "lightgray"},
                    {'range': [30, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "lightgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ),
        row=1, col=1
    )
    
    # Sentiment distribution pie
    fig.add_trace(
        go.Pie(
            labels=['Positive', 'Neutral', 'Negative'],
            values=[positive_pct, neutral_pct, negative_pct],
            hole=0.3,
            marker_colors=['#28a745', '#ffc107', '#dc3545']
        ),
        row=1, col=2
    )
    
    # Trend indicator
    trend_value = sentiment_trend * 100
    trend_color = "green" if sentiment_trend > 0 else "red" if sentiment_trend < 0 else "gray"
    
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=trend_value,
            title={'text': "3-Day Trend"},
            delta={'reference': 0, 'relative': False},
            number={'suffix': '%'}
        ),
        row=1, col=3
    )
    
    # Volatility
    volatility_value = sentiment_std * 100
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=volatility_value,
            title={'text': "Volatility"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "orange"},
                'steps': [
                    {'range': [0, 30], 'color': "lightgreen"},
                    {'range': [30, 70], 'color': "yellow"},
                    {'range': [70, 100], 'color': "lightcoral"}
                ]
            }
        ),
        row=2, col=1
    )
    
    # Activity level
    activity_score = min(total_posts / 10, 100)  # Normalize to 0-100
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=activity_score,
            title={'text': "Activity Level"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "blue"},
                'steps': [
                    {'range': [0, 25], 'color': "lightgray"},
                    {'range': [25, 50], 'color': "lightblue"},
                    {'range': [50, 75], 'color': "blue"},
                    {'range': [75, 100], 'color': "darkblue"}
                ]
            }
        ),
        row=2, col=2
    )
    
    # Momentum (combining trend and volume)
    momentum_value = (sentiment_trend + (total_posts / 100)) * 50
    momentum_value = max(0, min(100, momentum_value))  # Clamp to 0-100
    
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=momentum_value,
            title={'text': "Momentum"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "purple"},
                'steps': [
                    {'range': [0, 40], 'color': "lightgray"},
                    {'range': [40, 60], 'color': "mediumpurple"},
                    {'range': [60, 100], 'color': "darkviolet"}
                ]
            }
        ),
        row=2, col=3
    )
    
    fig.update_layout(
        title="🎯 Market Mood Dashboard",
        height=600,
        showlegend=False
    )
    
    return fig

def create_social_media_analytics(df):
    """
    Create social media analytics dashboard.
    """
    if df.empty:
        return None
    
    # Filter for social media sources
    social_df = df[df['source'].isin(['Reddit', 'Twitter'])].copy()
    
    if social_df.empty:
        return None
    
    # Prepare data
    social_df['date'] = pd.to_datetime(social_df['created_dt']).dt.date
    social_df['hour'] = pd.to_datetime(social_df['created_dt']).dt.hour
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '📱 Daily Social Activity',
            '🕐 Activity by Hour',
            '💬 Engagement vs Sentiment',
            '🔥 Top Performing Posts'
        ),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "scatter"}, {"type": "table"}]]
    )
    
    # Daily activity
    daily_activity = social_df.groupby(['date', 'source']).size().reset_index(name='count')
    
    for source in daily_activity['source'].unique():
        source_data = daily_activity[daily_activity['source'] == source]
        fig.add_trace(
            go.Bar(
                x=source_data['date'],
                y=source_data['count'],
                name=source,
                marker_color='#ff4500' if source == 'Reddit' else '#1da1f2'
            ),
            row=1, col=1
        )
    
    # Hourly activity
    hourly_activity = social_df.groupby(['hour', 'source']).size().reset_index(name='count')
    
    for source in hourly_activity['source'].unique():
        source_data = hourly_activity[hourly_activity['source'] == source]
        fig.add_trace(
            go.Bar(
                x=source_data['hour'],
                y=source_data['count'],
                name=f'{source} (hourly)',
                marker_color='#ff4500' if source == 'Reddit' else '#1da1f2',
                opacity=0.7
            ),
            row=1, col=2
        )
    
    # Engagement vs sentiment (only for Reddit with scores)
    reddit_with_scores = social_df[
        (social_df['source'] == 'Reddit') & 
        (social_df['score'].notna()) & 
        (social_df['score'] != '')
    ].copy()
    
    if not reddit_with_scores.empty:
        reddit_with_scores['score'] = pd.to_numeric(reddit_with_scores['score'], errors='coerce')
        reddit_with_scores = reddit_with_scores.dropna(subset=['score'])
        
        fig.add_trace(
            go.Scatter(
                x=reddit_with_scores['compound'],
                y=reddit_with_scores['score'],
                mode='markers',
                name='Reddit Posts',
                marker=dict(
                    size=8,
                    color=reddit_with_scores['compound'],
                    colorscale='RdYlGn',
                    showscale=True
                ),
                text=reddit_with_scores['title'].str[:50] + '...',
                hovertemplate='<b>%{text}</b><br>' +
                              'Sentiment: %{x:.3f}<br>' +
                              'Score: %{y}<br>' +
                              '<extra></extra>'
            ),
            row=2, col=1
        )
    
    # Top performing posts table
    if not reddit_with_scores.empty:
        top_posts = reddit_with_scores.nlargest(5, 'score')[['title', 'score', 'compound']]
        
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['Title', 'Score', 'Sentiment'],
                    fill_color='lightblue',
                    align='left'
                ),
                cells=dict(
                    values=[
                        [title[:40] + '...' if len(title) > 40 else title for title in top_posts['title']],
                        top_posts['score'],
                        [f"{s:.3f}" for s in top_posts['compound']]
                    ],
                    fill_color='white',
                    align='left'
                )
            ),
            row=2, col=2
        )
    
    fig.update_layout(
        title="📱 Social Media Analytics Dashboard",
        height=700,
        showlegend=True
    )
    
    return fig

# Example usage
if __name__ == "__main__":
    sample_text = "Tesla stock is rising. Tesla is a great company. Stock market is volatile."
    generate_wordcloud(sample_text, title="Sample Word Cloud")
