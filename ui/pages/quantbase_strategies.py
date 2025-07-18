import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.quantitative_strategies import QuantitativeStrategies
from ui.utils.data_helpers import load_sentiment_data


def render_quantbase_strategies():
    """Render the QuantBase-inspired strategies page."""
    st.title("🎯 QuantBase-Inspired Strategies")
    st.markdown("### Professional-grade quantitative strategies based on real fund performance")
    
    # Initialize strategies
    quant_strategies = QuantitativeStrategies()
    
    # Load sentiment data
    sentiment_data = load_sentiment_data()
    available_tickers = list(sentiment_data.keys())
    
    # Create strategies
    strategies = quant_strategies.create_quantbase_inspired_strategies(
        available_tickers, sentiment_data
    )
    
    # Main navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Strategy Overview", 
        "🔍 Performance Analysis", 
        "⚡ Live Signals",
        "🎯 Portfolio Optimizer"
    ])
    
    with tab1:
        render_strategy_overview(strategies)
    
    with tab2:
        render_performance_analysis(strategies, quant_strategies)
    
    with tab3:
        render_live_signals(strategies, available_tickers)
    
    with tab4:
        render_portfolio_optimizer(strategies, quant_strategies)


def render_strategy_overview(strategies):
    """Render strategy overview with performance cards."""
    st.subheader("🏆 Top Performing Strategies")
    
    # Performance metrics cards
    cols = st.columns(3)
    
    # Sort strategies by expected return
    sorted_strategies = sorted(
        strategies.items(), 
        key=lambda x: x[1].get('expected_annual_return', 0), 
        reverse=True
    )
    
    for i, (strategy_name, strategy) in enumerate(sorted_strategies[:3]):
        with cols[i]:
            performance = strategy.get('benchmark_performance', 0)
            annual_return = strategy.get('expected_annual_return', 0)
            risk_score = strategy.get('risk_score', 3)
            
            st.metric(
                label=strategy['name'],
                value=f"{annual_return:.1%}",
                delta=f"Risk: {risk_score:.1f}/5"
            )
            
            # Performance indicator
            if performance > 0.3:
                st.success(f"🚀 Exceptional: {performance:.1%} inception return")
            elif performance > 0.15:
                st.info(f"📈 Strong: {performance:.1%} inception return")
            else:
                st.warning(f"⚠️ Moderate: {performance:.1%} inception return")
    
    st.markdown("---")
    
    # Detailed strategy cards
    st.subheader("📋 Strategy Details")
    
    for strategy_name, strategy in strategies.items():
        with st.expander(f"{strategy['name']} - {strategy.get('expected_annual_return', 0):.1%} Expected Return"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Description:** {strategy['description']}")
                st.write(f"**Methodology:** {strategy.get('methodology', 'N/A')}")
                st.write(f"**Rebalance:** {strategy.get('rebalance_frequency', 'Monthly')}")
                
                # Strategy-specific details
                if strategy_name == 'social_flagship':
                    render_social_flagship_details(strategy)
                elif strategy_name == 'political_tracker':
                    render_political_tracker_details(strategy)
                elif strategy_name == 'lobbying_growth':
                    render_lobbying_growth_details(strategy)
                elif strategy_name == 'crisis_flagship':
                    render_crisis_flagship_details(strategy)
                elif strategy_name == 'quant_momentum':
                    render_momentum_details(strategy)
                elif strategy_name == 'alternative_data':
                    render_alternative_data_details(strategy)
            
            with col2:
                # Performance metrics
                st.metric("Expected Return", f"{strategy.get('expected_annual_return', 0):.1%}")
                st.metric("Volatility", f"{strategy.get('volatility', 0):.1%}")
                st.metric("Sharpe Ratio", f"{strategy.get('sharpe_ratio', 0):.2f}")
                st.metric("Risk Score", f"{strategy.get('risk_score', 3):.1f}/5")


def render_social_flagship_details(strategy):
    """Render social flagship strategy details."""
    st.write("**🎯 Current Top Positions:**")
    
    positions = strategy.get('positions', {})
    if positions:
        for ticker, position in list(positions.items())[:5]:
            st.write(f"• {ticker}: {position['weight']:.1%} - {position['signal_strength']}")
    
    st.write("**📊 Sentiment Methodology:**")
    st.write("- Multi-platform sentiment aggregation")
    st.write("- Momentum-weighted scoring")
    st.write("- Equal-weight top 10 positions")


def render_political_tracker_details(strategy):
    """Render political tracker strategy details."""
    st.write("**🏛️ Recent Political Trades:**")
    
    trades = strategy.get('recent_political_trades', [])
    for trade in trades[:3]:
        performance = trade.get('performance_since', 0)
        color = "🟢" if performance > 0 else "🔴"
        st.write(f"{color} {trade['politician']}: {trade['transaction']} {trade['ticker']} ({performance:.1%})")
    
    st.write("**📈 Strategy Focus:**")
    st.write("- Congressional disclosure tracking")
    st.write("- Lobbying expenditure correlation")
    st.write("- Government contract analysis")


def render_lobbying_growth_details(strategy):
    """Render lobbying growth strategy details."""
    st.write("**💼 Top Lobbying Growth Companies:**")
    
    companies = strategy.get('top_lobbying_companies', [])
    for company in companies[:3]:
        st.write(f"• {company['ticker']}: {company['lobbying_growth']:.1%} growth")
    
    st.write("**🎯 Selection Criteria:**")
    st.write("- 15%+ quarterly lobbying spend growth")
    st.write("- Government contract correlation")
    st.write("- Regulatory environment analysis")


def render_crisis_flagship_details(strategy):
    """Render crisis flagship strategy details."""
    st.write("**⚠️ Current Market Allocation:**")
    
    allocation = strategy.get('current_allocation', {})
    for asset, weight in allocation.items():
        st.write(f"• {asset}: {weight:.1%}")
    
    st.write("**📊 Crisis Indicators:**")
    indicators = strategy.get('crisis_indicators', {})
    st.write(f"• VIX Level: {indicators.get('vix_level', 'N/A')}")
    st.write(f"• Overall Risk: {indicators.get('overall_risk_level', 'N/A')}")


def render_momentum_details(strategy):
    """Render momentum strategy details."""
    st.write("**⚡ Current Signals:**")
    
    signals = strategy.get('current_signals', {})
    strong_signals = {k: v for k, v in signals.items() if v.get('signal') in ['Strong Buy', 'Buy']}
    
    for ticker, signal in list(strong_signals.items())[:3]:
        st.write(f"• {ticker}: {signal['signal']} (Score: {signal.get('momentum_score', 0):.3f})")
    
    st.write("**🎯 Technical Methodology:**")
    st.write("- Moving average crossovers")
    st.write("- RSI momentum confirmation")
    st.write("- ETF sector rotation")


def render_alternative_data_details(strategy):
    """Render alternative data strategy details."""
    st.write("**🔬 Innovation Leaders:**")
    
    patent_scores = strategy.get('patent_scores', {})
    top_innovators = sorted(patent_scores.items(), key=lambda x: x[1].get('innovation_score', 0), reverse=True)[:3]
    
    for ticker, data in top_innovators:
        st.write(f"• {ticker}: {data.get('innovation_score', 0):.2f} innovation score")
    
    st.write("**📊 Data Sources:**")
    st.write("- Patent application tracking")
    st.write("- Earnings call sentiment")
    st.write("- Supply chain resilience")


def render_performance_analysis(strategies, quant_strategies):
    """Render performance analysis charts."""
    st.subheader("📈 Performance Comparison")
    
    # Get performance comparison
    comparison = quant_strategies.get_strategy_performance_comparison(strategies)
    
    # Create performance chart
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Expected Returns', 'Risk-Adjusted Returns', 'Sharpe Ratios', 'Volatility'),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    strategy_names = list(strategies.keys())
    
    # Expected returns
    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=[comparison['strategy_returns'][s] for s in strategy_names],
            name='Expected Returns',
            marker_color='lightblue'
        ),
        row=1, col=1
    )
    
    # Risk-adjusted returns
    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=[comparison['risk_adjusted_returns'][s] for s in strategy_names],
            name='Risk-Adjusted Returns',
            marker_color='lightgreen'
        ),
        row=1, col=2
    )
    
    # Sharpe ratios
    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=[comparison['sharpe_ratios'][s] for s in strategy_names],
            name='Sharpe Ratios',
            marker_color='lightyellow'
        ),
        row=2, col=1
    )
    
    # Volatility
    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=[comparison['volatilities'][s] for s in strategy_names],
            name='Volatility',
            marker_color='lightcoral'
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=600,
        title_text="Strategy Performance Metrics",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Performance table
    st.subheader("📊 Detailed Performance Table")
    
    perf_df = pd.DataFrame({
        'Strategy': [strategies[s]['name'] for s in strategy_names],
        'Expected Return': [f"{comparison['strategy_returns'][s]:.1%}" for s in strategy_names],
        'Volatility': [f"{comparison['volatilities'][s]:.1%}" for s in strategy_names],
        'Sharpe Ratio': [f"{comparison['sharpe_ratios'][s]:.2f}" for s in strategy_names],
        'Risk Score': [f"{strategies[s].get('risk_score', 3):.1f}/5" for s in strategy_names],
        'Benchmark Performance': [f"{strategies[s].get('benchmark_performance', 0):.1%}" for s in strategy_names]
    })
    
    st.dataframe(perf_df, use_container_width=True)


def render_live_signals(strategies, available_tickers):
    """Render live trading signals."""
    st.subheader("⚡ Live Trading Signals")
    
    # Signal strength filter
    signal_filter = st.selectbox(
        "Filter by Signal Strength:",
        ["All Signals", "Strong Buy", "Buy", "Hold", "Sell"]
    )
    
    # Collect all signals
    all_signals = []
    
    for strategy_name, strategy in strategies.items():
        if 'signals' in strategy:
            for ticker, signal_data in strategy['signals'].items():
                if signal_filter == "All Signals" or signal_data.get('signal') == signal_filter:
                    all_signals.append({
                        'Strategy': strategy['name'],
                        'Ticker': ticker,
                        'Signal': signal_data.get('signal', 'N/A'),
                        'Confidence': signal_data.get('confidence', 0),
                        'Score': signal_data.get('sentiment_score', signal_data.get('momentum_score', 0))
                    })
    
    if all_signals:
        # Convert to DataFrame
        signals_df = pd.DataFrame(all_signals)
        
        # Sort by confidence
        signals_df = signals_df.sort_values('Confidence', ascending=False)
        
        # Color code signals
        def highlight_signals(row):
            if row['Signal'] == 'Strong Buy':
                return ['background-color: lightgreen'] * len(row)
            elif row['Signal'] == 'Buy':
                return ['background-color: lightblue'] * len(row)
            elif row['Signal'] == 'Sell':
                return ['background-color: lightcoral'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            signals_df.style.apply(highlight_signals, axis=1),
            use_container_width=True
        )
        
        # Signal distribution chart
        st.subheader("📊 Signal Distribution")
        
        signal_counts = signals_df['Signal'].value_counts()
        fig = px.pie(
            values=signal_counts.values,
            names=signal_counts.index,
            title="Current Signal Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("No signals match the selected filter.")


def render_portfolio_optimizer(strategies, quant_strategies):
    """Render portfolio optimizer."""
    st.subheader("🎯 Portfolio Optimizer")
    
    # Risk tolerance slider
    risk_tolerance = st.slider(
        "Risk Tolerance (Target Volatility):",
        min_value=0.1,
        max_value=0.3,
        value=0.15,
        step=0.01,
        format="%.1%"
    )
    
    # Get optimization results
    optimizer_results = quant_strategies.create_quantbase_portfolio_optimizer(
        strategies, risk_tolerance
    )
    
    # Display optimal allocation
    st.subheader("📊 Recommended Portfolio Allocation")
    
    allocation = optimizer_results['recommended_allocation']
    
    # Pie chart
    fig = px.pie(
        values=list(allocation.values()),
        names=[strategies[s]['name'] for s in allocation.keys()],
        title="Optimal Strategy Allocation"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Portfolio metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Expected Portfolio Return",
            f"{optimizer_results['expected_portfolio_return']:.1%}"
        )
    
    with col2:
        st.metric(
            "Expected Portfolio Volatility",
            f"{optimizer_results['expected_portfolio_volatility']:.1%}"
        )
    
    with col3:
        st.metric(
            "Portfolio Sharpe Ratio",
            f"{optimizer_results['portfolio_sharpe_ratio']:.2f}"
        )
    
    # Allocation table
    st.subheader("📋 Detailed Allocation")
    
    allocation_df = pd.DataFrame({
        'Strategy': [strategies[s]['name'] for s in allocation.keys()],
        'Allocation': [f"{w:.1%}" for w in allocation.values()],
        'Expected Return': [f"{strategies[s].get('expected_annual_return', 0):.1%}" for s in allocation.keys()],
        'Risk Score': [f"{strategies[s].get('risk_score', 3):.1f}/5" for s in allocation.keys()],
        'Contribution to Return': [f"{w * strategies[s].get('expected_annual_return', 0):.1%}" for s, w in allocation.items()]
    })
    
    st.dataframe(allocation_df, use_container_width=True)
    
    # Implementation notes
    st.info("""
    **Implementation Notes:**
    - Allocation uses equal-risk-contribution methodology
    - Rebalancing recommended monthly
    - Monitor strategy performance quarterly
    - Adjust allocation based on market conditions
    """)


if __name__ == "__main__":
    render_quantbase_strategies()