import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from analysis.quantitative_strategies import QuantitativeStrategies
from ui.utils.data_helpers import get_available_tickers, load_dataframes
from ui.styles.main_styles import apply_main_styles

def create_quantitative_strategies_page():
    """
    Display the quantitative strategies page with QuantBase-inspired interface.
    """
    apply_main_styles()
    
    # Page header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 StockScope Quantitative Strategies</h1>
        <p>Professional-grade quantitative investment strategies powered by sentiment analysis and alternative data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize quantitative strategies
    quant_strategies = QuantitativeStrategies()
    
    # Get available tickers and load sentiment data
    available_tickers = get_available_tickers()
    sentiment_data = {}
    
    # Load sentiment data for available tickers
    for ticker in available_tickers:
        try:
            df = load_dataframes(ticker)
            if not df.empty:
                # Calculate recent sentiment for the ticker
                recent_sentiment = df['compound'].tail(30).tolist()  # Last 30 data points
                sentiment_data[ticker] = {
                    'recent_sentiment': recent_sentiment,
                    'current_sentiment': df['compound'].mean() if not df.empty else 0,
                    'trend': df['compound'].tail(10).mean() - df['compound'].head(10).mean() if len(df) >= 20 else 0
                }
        except Exception as e:
            st.error(f"Error loading data for {ticker}: {str(e)}")
    
    # Sidebar for strategy selection
    with st.sidebar:
        st.markdown("### 📊 Strategy Selection")
        
        strategy_type = st.selectbox(
            "Choose Strategy Type:",
            [
                "Sentiment Momentum",
                "Crisis Detection", 
                "Insider Tracking",
                "Multi-Factor Alpha",
                "Sector Rotation",
                "All Strategies"
            ]
        )
        
        st.markdown("### 🎯 Strategy Parameters")
        
        # Risk tolerance
        risk_tolerance = st.slider(
            "Risk Tolerance (1-5):",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = Conservative, 5 = Aggressive"
        )
        
        # Rebalancing frequency
        rebalance_freq = st.selectbox(
            "Rebalancing Frequency:",
            ["Daily", "Weekly", "Monthly", "Quarterly"],
            index=1
        )
        
        # Available tickers
        selected_tickers = st.multiselect(
            "Select Tickers:",
            available_tickers,
            default=available_tickers[:10] if available_tickers else []
        )
    
    # Main content area
    if strategy_type == "All Strategies":
        show_all_strategies_overview(quant_strategies, sentiment_data, selected_tickers)
    else:
        show_individual_strategy(quant_strategies, sentiment_data, strategy_type, selected_tickers, risk_tolerance, rebalance_freq)

def show_all_strategies_overview(quant_strategies, sentiment_data, selected_tickers):
    """Show overview of all strategies."""
    
    st.markdown("### 🎯 Strategy Performance Dashboard")
    
    # Create strategy cards
    strategies_config = [
        {
            "name": "Sentiment Momentum",
            "description": "Momentum strategy based on social sentiment trends",
            "risk_score": 3.2,
            "expected_return": 0.15,
            "icon": "📈"
        },
        {
            "name": "Crisis Detection",
            "description": "Defensive strategy that detects market crises",
            "risk_score": 2.1,
            "expected_return": 0.08,
            "icon": "🛡️"
        },
        {
            "name": "Insider Tracking",
            "description": "Follows insider trading patterns",
            "risk_score": 2.8,
            "expected_return": 0.12,
            "icon": "🔍"
        },
        {
            "name": "Multi-Factor Alpha",
            "description": "Combines multiple factors for alpha generation",
            "risk_score": 3.5,
            "expected_return": 0.18,
            "icon": "⚡"
        },
        {
            "name": "Sector Rotation",
            "description": "Rotates between sectors based on momentum",
            "risk_score": 2.9,
            "expected_return": 0.14,
            "icon": "🔄"
        }
    ]
    
    # Display strategy cards in grid
    cols = st.columns(3)
    
    for i, strategy in enumerate(strategies_config):
        with cols[i % 3]:
            create_strategy_card(strategy)
    
    # Performance comparison chart
    st.markdown("### 📊 Strategy Performance Comparison")
    
    # Create mock performance data for visualization
    performance_data = create_mock_performance_data(strategies_config)
    
    # Performance chart
    fig = create_performance_comparison_chart(performance_data)
    st.plotly_chart(fig, use_container_width=True)
    
    # Risk-Return scatter plot
    st.markdown("### 🎯 Risk-Return Profile")
    
    risk_return_fig = create_risk_return_scatter(strategies_config)
    st.plotly_chart(risk_return_fig, use_container_width=True)
    
    # Strategy correlation matrix
    st.markdown("### 🔗 Strategy Correlation Matrix")
    
    correlation_fig = create_strategy_correlation_matrix(strategies_config)
    st.plotly_chart(correlation_fig, use_container_width=True)

def show_individual_strategy(quant_strategies, sentiment_data, strategy_type, selected_tickers, risk_tolerance, rebalance_freq):
    """Show detailed view of individual strategy."""
    
    if not selected_tickers:
        st.warning("Please select at least one ticker to analyze.")
        return
    
    # Create strategy based on type
    if strategy_type == "Sentiment Momentum":
        strategy = quant_strategies.create_sentiment_momentum_strategy(selected_tickers, sentiment_data)
    elif strategy_type == "Crisis Detection":
        strategy = quant_strategies.create_crisis_detection_strategy()
    elif strategy_type == "Insider Tracking":
        strategy = quant_strategies.create_insider_tracking_strategy(selected_tickers)
    elif strategy_type == "Multi-Factor Alpha":
        strategy = quant_strategies.create_multi_factor_strategy(selected_tickers, sentiment_data)
    elif strategy_type == "Sector Rotation":
        strategy = quant_strategies.create_sector_rotation_strategy(sentiment_data)
    
    # Strategy header
    st.markdown(f"""
    <div class="strategy-header">
        <h2>📊 {strategy['name']}</h2>
        <p>{strategy['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        risk_score = strategy.get('risk_score', 0.0)
        st.metric(
            "Risk Score",
            f"{risk_score:.1f}/5",
            help="1 = Conservative, 5 = Aggressive"
        )
    
    with col2:
        expected_return = strategy.get('expected_return', 0.0)
        st.metric(
            "Expected Return",
            f"{expected_return:.1%}",
            help="Annualized expected return"
        )
    
    with col3:
        if 'weights' in strategy:
            num_positions = len([w for w in strategy['weights'].values() if w > 0.01])
            st.metric("Active Positions", num_positions)
        else:
            st.metric("Active Positions", "N/A")
    
    with col4:
        st.metric("Rebalance Frequency", rebalance_freq)
    
    # Portfolio composition
    if 'weights' in strategy and strategy['weights']:
        st.markdown("### 📈 Current Portfolio Allocation")
        
        # Portfolio pie chart
        portfolio_fig = create_portfolio_pie_chart(strategy['weights'])
        st.plotly_chart(portfolio_fig, use_container_width=True)
        
        # Detailed positions table
        st.markdown("### 📋 Detailed Position Breakdown")
        
        positions_df = create_positions_dataframe(strategy['weights'])
        st.dataframe(positions_df, use_container_width=True)
    
    # Strategy-specific visualizations
    if strategy_type == "Sentiment Momentum":
        show_sentiment_momentum_analysis(strategy, sentiment_data, selected_tickers)
    elif strategy_type == "Crisis Detection":
        show_crisis_detection_analysis(strategy)
    elif strategy_type == "Multi-Factor Alpha":
        show_multi_factor_analysis(strategy, sentiment_data, selected_tickers)
    elif strategy_type == "Sector Rotation":
        show_sector_rotation_analysis(strategy, sentiment_data)
    
    # Strategy signals and recommendations
    st.markdown("### 🎯 Current Strategy Signals")
    
    signals = generate_strategy_signals(strategy, sentiment_data, selected_tickers)
    display_strategy_signals(signals)
    
    # Backtesting results
    st.markdown("### 📊 Strategy Backtesting Results")
    
    backtest_results = run_strategy_backtest(strategy, sentiment_data, selected_tickers)
    display_backtest_results(backtest_results)

def create_strategy_card(strategy):
    """Create a strategy card component."""
    st.markdown(f"""
    <div class="strategy-card">
        <div class="strategy-icon">{strategy['icon']}</div>
        <h3>{strategy['name']}</h3>
        <p>{strategy['description']}</p>
        <div class="strategy-metrics">
            <div class="metric">
                <span class="metric-label">Risk Score:</span>
                <span class="metric-value">{strategy['risk_score']:.1f}/5</span>
            </div>
            <div class="metric">
                <span class="metric-label">Expected Return:</span>
                <span class="metric-value">{strategy['expected_return']:.1%}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_mock_performance_data(strategies_config):
    """Create mock performance data for visualization."""
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    
    performance_data = {}
    for strategy in strategies_config:
        # Generate realistic performance curves
        returns = np.random.normal(
            strategy['expected_return'] / 252,  # Daily return
            strategy['risk_score'] * 0.02,     # Volatility
            len(dates)
        )
        
        # Add some momentum and mean reversion
        for i in range(1, len(returns)):
            returns[i] += 0.1 * returns[i-1] - 0.05 * returns[i-1]
        
        cumulative_returns = (1 + returns).cumprod()
        performance_data[strategy['name']] = cumulative_returns
    
    return pd.DataFrame(performance_data, index=dates)

def create_performance_comparison_chart(performance_data):
    """Create performance comparison chart."""
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, (strategy, data) in enumerate(performance_data.items()):
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data.values,
            mode='lines',
            name=strategy,
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate='%{y:.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Strategy Performance Comparison (Cumulative Returns)",
        xaxis_title="Date",
        yaxis_title="Cumulative Return",
        height=500,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig

def create_risk_return_scatter(strategies_config):
    """Create risk-return scatter plot."""
    fig = go.Figure()
    
    risk_scores = [s['risk_score'] for s in strategies_config]
    expected_returns = [s['expected_return'] for s in strategies_config]
    names = [s['name'] for s in strategies_config]
    
    fig.add_trace(go.Scatter(
        x=risk_scores,
        y=expected_returns,
        mode='markers+text',
        text=names,
        textposition='top center',
        marker=dict(
            size=15,
            color=expected_returns,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Expected Return")
        ),
        hovertemplate='<b>%{text}</b><br>Risk: %{x:.1f}<br>Return: %{y:.1%}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Risk-Return Profile of Strategies",
        xaxis_title="Risk Score (1-5)",
        yaxis_title="Expected Return",
        height=500
    )
    
    return fig

def create_strategy_correlation_matrix(strategies_config):
    """Create strategy correlation matrix."""
    # Generate mock correlation data
    n_strategies = len(strategies_config)
    correlation_matrix = np.random.rand(n_strategies, n_strategies)
    
    # Make it symmetric and add diagonal of 1s
    correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
    np.fill_diagonal(correlation_matrix, 1)
    
    # Scale correlations to realistic range
    correlation_matrix = correlation_matrix * 0.6 + 0.2
    
    strategy_names = [s['name'] for s in strategies_config]
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix,
        x=strategy_names,
        y=strategy_names,
        colorscale='RdBu',
        zmid=0,
        text=correlation_matrix.round(2),
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate='%{y} vs %{x}<br>Correlation: %{z:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Strategy Correlation Matrix",
        height=500
    )
    
    return fig

def create_portfolio_pie_chart(weights):
    """Create portfolio allocation pie chart."""
    # Filter out zero weights
    filtered_weights = {k: v for k, v in weights.items() if v > 0.01}
    
    fig = go.Figure(data=[go.Pie(
        labels=list(filtered_weights.keys()),
        values=list(filtered_weights.values()),
        hole=0.3,
        textinfo='label+percent',
        textposition='outside',
        marker=dict(
            colors=px.colors.qualitative.Set3
        )
    )])
    
    fig.update_layout(
        title="Portfolio Allocation",
        height=500,
        showlegend=True
    )
    
    return fig

def create_positions_dataframe(weights):
    """Create positions DataFrame for display."""
    positions = []
    for ticker, weight in weights.items():
        if weight > 0.001:  # Only show significant positions
            positions.append({
                'Ticker': ticker,
                'Weight': f"{weight:.2%}",
                'Weight_Numeric': weight,
                'Position_Size': 'Long' if weight > 0 else 'Short',
                'Allocation': '●' * int(weight * 20)  # Visual bar
            })
    
    df = pd.DataFrame(positions)
    if not df.empty:
        df = df.sort_values('Weight_Numeric', ascending=False)
        df = df.drop('Weight_Numeric', axis=1)
    
    return df

def show_sentiment_momentum_analysis(strategy, sentiment_data, selected_tickers):
    """Show sentiment momentum specific analysis."""
    st.markdown("### 📊 Sentiment Momentum Analysis")
    
    # Sentiment trends
    sentiment_trends = calculate_sentiment_trends(sentiment_data, selected_tickers)
    
    if sentiment_trends:
        trend_fig = create_sentiment_trend_chart(sentiment_trends)
        st.plotly_chart(trend_fig, use_container_width=True)
        
        # Sentiment momentum table
        st.markdown("#### 📈 Current Sentiment Momentum")
        momentum_df = create_sentiment_momentum_table(sentiment_trends)
        st.dataframe(momentum_df, use_container_width=True)

def show_crisis_detection_analysis(strategy):
    """Show crisis detection specific analysis."""
    st.markdown("### 🛡️ Crisis Detection Analysis")
    
    # Mock crisis indicators
    crisis_indicators = {
        'VIX Level': 18.5,
        'Market Stress': 'Low',
        'Volatility Regime': 'Normal',
        'Correlation Spike': 'No',
        'Liquidity Conditions': 'Good'
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🚨 Current Crisis Indicators")
        for indicator, value in crisis_indicators.items():
            if isinstance(value, (int, float)):
                st.metric(indicator, f"{value:.1f}")
            else:
                st.metric(indicator, value)
    
    with col2:
        # Crisis probability gauge
        crisis_prob = 0.15  # 15% probability
        gauge_fig = create_crisis_probability_gauge(crisis_prob)
        st.plotly_chart(gauge_fig, use_container_width=True)

def show_multi_factor_analysis(strategy, sentiment_data, selected_tickers):
    """Show multi-factor analysis."""
    st.markdown("### ⚡ Multi-Factor Analysis")
    
    # Factor exposures
    factors = ['Momentum', 'Sentiment', 'Quality', 'Value', 'Low Vol']
    exposures = np.random.uniform(-0.5, 0.5, len(factors))
    
    factor_fig = create_factor_exposure_chart(factors, exposures)
    st.plotly_chart(factor_fig, use_container_width=True)

def show_sector_rotation_analysis(strategy, sentiment_data):
    """Show sector rotation analysis."""
    st.markdown("### 🔄 Sector Rotation Analysis")
    
    # Sector momentum
    sectors = ['Technology', 'Healthcare', 'Financials', 'Energy', 'Consumer']
    momentum = np.random.uniform(-0.2, 0.2, len(sectors))
    
    sector_fig = create_sector_momentum_chart(sectors, momentum)
    st.plotly_chart(sector_fig, use_container_width=True)

def calculate_sentiment_trends(sentiment_data, selected_tickers):
    """Calculate sentiment trends for selected tickers."""
    trends = {}
    
    for ticker in selected_tickers:
        if ticker in sentiment_data:
            # Calculate trend from recent sentiment data
            recent_sentiment = sentiment_data[ticker].get('recent_sentiment', [])
            if len(recent_sentiment) >= 2:
                trend = recent_sentiment[-1] - recent_sentiment[-2]
                trends[ticker] = {
                    'current_sentiment': recent_sentiment[-1],
                    'trend': trend,
                    'momentum': 'Positive' if trend > 0 else 'Negative'
                }
    
    return trends

def create_sentiment_trend_chart(sentiment_trends):
    """Create sentiment trend chart."""
    fig = go.Figure()
    
    tickers = list(sentiment_trends.keys())
    current_sentiment = [sentiment_trends[t]['current_sentiment'] for t in tickers]
    trends = [sentiment_trends[t]['trend'] for t in tickers]
    
    fig.add_trace(go.Scatter(
        x=tickers,
        y=current_sentiment,
        mode='markers+text',
        text=[f"{t:.1f}" for t in trends],
        textposition='top center',
        marker=dict(
            size=15,
            color=trends,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Sentiment Trend")
        ),
        name='Current Sentiment'
    ))
    
    fig.update_layout(
        title="Sentiment Momentum by Ticker",
        xaxis_title="Ticker",
        yaxis_title="Current Sentiment",
        height=400
    )
    
    return fig

def create_sentiment_momentum_table(sentiment_trends):
    """Create sentiment momentum table."""
    data = []
    for ticker, trend_data in sentiment_trends.items():
        data.append({
            'Ticker': ticker,
            'Current Sentiment': f"{trend_data['current_sentiment']:.2f}",
            'Trend': f"{trend_data['trend']:.2f}",
            'Momentum': trend_data['momentum'],
            'Signal': '🔥' if trend_data['trend'] > 0.1 else '❄️' if trend_data['trend'] < -0.1 else '➡️'
        })
    
    return pd.DataFrame(data)

def create_crisis_probability_gauge(probability):
    """Create crisis probability gauge."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = probability * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Crisis Probability (%)"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgray"},
                {'range': [25, 50], 'color': "yellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

def create_factor_exposure_chart(factors, exposures):
    """Create factor exposure chart."""
    fig = go.Figure()
    
    colors = ['green' if e > 0 else 'red' for e in exposures]
    
    fig.add_trace(go.Bar(
        x=factors,
        y=exposures,
        marker_color=colors,
        text=[f"{e:.2f}" for e in exposures],
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Factor Exposures",
        xaxis_title="Factor",
        yaxis_title="Exposure",
        height=400
    )
    
    return fig

def create_sector_momentum_chart(sectors, momentum):
    """Create sector momentum chart."""
    fig = go.Figure()
    
    colors = ['green' if m > 0 else 'red' for m in momentum]
    
    fig.add_trace(go.Bar(
        x=sectors,
        y=momentum,
        marker_color=colors,
        text=[f"{m:.1%}" for m in momentum],
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Sector Momentum",
        xaxis_title="Sector",
        yaxis_title="Momentum",
        height=400
    )
    
    return fig

def generate_strategy_signals(strategy, sentiment_data, selected_tickers):
    """Generate current strategy signals."""
    signals = []
    
    # Mock signal generation based on strategy type
    for ticker in selected_tickers[:5]:  # Show top 5 signals
        signal_strength = np.random.uniform(0.1, 0.9)
        signal_type = 'BUY' if signal_strength > 0.6 else 'SELL' if signal_strength < 0.4 else 'HOLD'
        
        signals.append({
            'ticker': ticker,
            'signal': signal_type,
            'strength': signal_strength,
            'confidence': np.random.uniform(0.7, 0.95),
            'reason': f"Sentiment momentum {'positive' if signal_type == 'BUY' else 'negative' if signal_type == 'SELL' else 'neutral'}"
        })
    
    return signals

def display_strategy_signals(signals):
    """Display strategy signals."""
    if not signals:
        st.info("No signals generated for current selection.")
        return
    
    # Create signals DataFrame
    signals_data = []
    for signal in signals:
        signals_data.append({
            'Ticker': signal['ticker'],
            'Signal': signal['signal'],
            'Strength': f"{signal['strength']:.1%}",
            'Confidence': f"{signal['confidence']:.1%}",
            'Reason': signal['reason'],
            'Action': '🔥' if signal['signal'] == 'BUY' else '❄️' if signal['signal'] == 'SELL' else '➡️'
        })
    
    df = pd.DataFrame(signals_data)
    st.dataframe(df, use_container_width=True)

def run_strategy_backtest(strategy, sentiment_data, selected_tickers):
    """Run strategy backtest."""
    # Mock backtest results
    return {
        'total_return': 0.157,
        'annual_return': 0.142,
        'volatility': 0.185,
        'sharpe_ratio': 0.89,
        'max_drawdown': -0.078,
        'win_rate': 0.64,
        'num_trades': 156
    }

def display_backtest_results(results):
    """Display backtest results."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Return", f"{results['total_return']:.1%}")
        st.metric("Annual Return", f"{results['annual_return']:.1%}")
    
    with col2:
        st.metric("Volatility", f"{results['volatility']:.1%}")
        st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
    
    with col3:
        st.metric("Max Drawdown", f"{results['max_drawdown']:.1%}")
        st.metric("Win Rate", f"{results['win_rate']:.1%}")
    
    with col4:
        st.metric("Number of Trades", results['num_trades'])
        st.metric("Strategy Age", "2.3 years")

# Add CSS for strategy cards
st.markdown("""
<style>
.strategy-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    border: 1px solid #e0e0e0;
    transition: transform 0.2s;
}

.strategy-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.strategy-icon {
    font-size: 48px;
    text-align: center;
    margin-bottom: 15px;
}

.strategy-card h3 {
    color: #2c3e50;
    margin-bottom: 10px;
    font-size: 18px;
}

.strategy-card p {
    color: #7f8c8d;
    margin-bottom: 15px;
    font-size: 14px;
}

.strategy-metrics {
    border-top: 1px solid #ecf0f1;
    padding-top: 15px;
}

.metric {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
}

.metric-label {
    font-weight: 500;
    color: #34495e;
}

.metric-value {
    font-weight: bold;
}

.strategy-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 12px;
    margin-bottom: 30px;
    text-align: center;
}

.strategy-header h2 {
    margin: 0;
    font-size: 32px;
}

.strategy-header p {
    margin: 10px 0 0 0;
    font-size: 16px;
    opacity: 0.9;
}
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    create_quantitative_strategies_page()