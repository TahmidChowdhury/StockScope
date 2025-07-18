import streamlit as st
import pandas as pd
from datetime import datetime
from analysis.investment_advisor import InvestmentAdvisor
from ui.utils.data_helpers import load_dataframes, get_metric_description
from visualizations.plot_sentiment import (
    create_risk_reward_matrix,
    create_portfolio_optimization_chart,
    create_technical_analysis_chart,
    create_investment_dashboard
)

def render_investment_advice_tab(tickers):
    """Render the investment advice tab content"""
    st.subheader("🎯 Investment Recommendations & Analysis")
    
    # Initialize advisor
    advisor = InvestmentAdvisor()
    
    # Get all analyzed tickers
    if tickers:
        st.success(f"✅ Found {len(tickers)} analyzed stocks")
        
        # Stock selection for investment analysis
        investment_col1, investment_col2 = st.columns([2, 1])
        
        with investment_col1:
            selected_stocks = st.multiselect(
                "📈 Select stocks for investment analysis:",
                options=tickers,
                default=tickers[:3] if len(tickers) >= 3 else tickers,
                help="Choose stocks to analyze for investment potential"
            )
        
        with investment_col2:
            budget = st.number_input(
                "💰 Investment Budget ($)",
                min_value=1000,
                max_value=1000000,
                value=10000,
                step=1000,
                help="Total amount you're planning to invest"
            )
        
        if selected_stocks:
            _process_investment_analysis(advisor, selected_stocks, budget)
        else:
            st.info("👆 Select stocks above to start investment analysis")
    else:
        st.warning("⚠️ No analyzed stocks found. Please analyze some stocks first using the 'Fetch Data' tab.")

def _process_investment_analysis(advisor, selected_stocks, budget):
    """Process investment analysis for selected stocks"""
    # Run investment analysis
    with st.spinner("🔍 Analyzing investment opportunities..."):
        advisor_results = []
        
        # Progress bar
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(selected_stocks):
            # Load data
            df = load_dataframes(ticker)
            
            if not df.empty:
                # Run investment analysis
                result = advisor.analyze_investment_opportunity(ticker, df)
                advisor_results.append(result)
            
            # Update progress
            progress_bar.progress((i + 1) / len(selected_stocks))
        
        progress_bar.empty()
    
    # Display results
    if advisor_results:
        # Filter successful analyses
        successful_results = [r for r in advisor_results if 'recommendation' in r and 'error' not in r]
        failed_results = [r for r in advisor_results if 'error' in r]
        
        if failed_results:
            st.warning(f"⚠️ Failed to analyze {len(failed_results)} stocks: {', '.join([r['ticker'] for r in failed_results])}")
        
        if successful_results:
            _render_investment_results(successful_results, budget)
        else:
            st.error("❌ No successful analyses completed. Please check your data.")

def _render_investment_results(successful_results, budget):
    """Render investment analysis results"""
    st.markdown("---")
    st.subheader("📊 Investment Recommendations")
    
    # Create recommendation cards
    _render_recommendation_cards(successful_results)
    
    # Risk-Reward Matrix
    st.markdown("---")
    st.subheader("🎯 Risk-Reward Analysis")
    
    risk_reward_fig = create_risk_reward_matrix(successful_results)
    if risk_reward_fig:
        st.plotly_chart(risk_reward_fig, use_container_width=True)
        
        # Interpretation guide
        with st.expander("📖 How to Read This Chart"):
            st.markdown("""
            **Quadrant Guide:**
            - **💎 Sweet Spot (Top Left)**: High reward, low risk - ideal investments
            - **⚠️ High Risk/High Reward (Top Right)**: Potential for big gains but risky
            - **😴 Safe Play (Bottom Left)**: Low risk but limited upside
            - **💀 Danger Zone (Bottom Right)**: High risk with low expected returns - avoid!
            """)
    
    # Portfolio Optimization
    st.markdown("---")
    st.subheader("💰 Suggested Portfolio Allocation")
    
    portfolio_fig = create_portfolio_optimization_chart(successful_results, budget)
    if portfolio_fig:
        st.plotly_chart(portfolio_fig, use_container_width=True)
        _render_allocation_table(successful_results, budget)
    
    # Technical Analysis Section
    _render_technical_analysis_section(successful_results)
    
    # Export recommendations
    _render_export_section(successful_results)

def _render_recommendation_cards(successful_results):
    """Render investment recommendation cards"""
    recommendation_cols = st.columns(min(len(successful_results), 3))
    
    for i, result in enumerate(successful_results):
        with recommendation_cols[i % 3]:
            rec = result['recommendation']
            
            # Determine CSS class based on recommendation
            if rec['action'] in ['BUY', 'STRONG BUY']:
                card_class = "investment-card-buy"
            elif rec['action'] == 'HOLD':
                card_class = "investment-card-hold"
            else:  # SELL
                card_class = "investment-card-sell"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div class="card-title">{rec['color']} {result['ticker']}</div>
                <div class="card-action">{rec['action']}</div>
                <div class="card-text"><strong>Score:</strong> {rec['score']:.2f}/1.0</div>
                <div class="card-text"><strong>Confidence:</strong> {result['confidence']:.0%}</div>
                <div class="card-text"><strong>Risk Level:</strong> {result['risk_level']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show reasoning
            with st.expander("🔍 Analysis Details"):
                st.markdown("**Key Factors:**")
                for reason in rec['reasoning']:
                    st.markdown(f"• {reason}")

def _render_allocation_table(successful_results, budget):
    """Render portfolio allocation table"""
    buy_recommendations = [r for r in successful_results if r['recommendation']['action'] in ['BUY', 'STRONG BUY']]
    
    if buy_recommendations:
        st.markdown("**📋 Recommended Allocations:**")
        
        allocation_data = []
        total_score = sum(r['recommendation']['score'] * r['confidence'] * 
                        (1 if r['risk_level'] == 'LOW' else 0.7 if r['risk_level'] == 'MEDIUM' else 0.4) 
                        for r in buy_recommendations)
        
        for result in buy_recommendations:
            score = result['recommendation']['score']
            confidence = result['confidence']
            risk_multiplier = 1 if result['risk_level'] == 'LOW' else 0.7 if result['risk_level'] == 'MEDIUM' else 0.4
            weighted_score = score * confidence * risk_multiplier
            
            percentage = (weighted_score / total_score) * 100 if total_score > 0 else 0
            amount = (percentage / 100) * budget
            
            allocation_data.append({
                'Stock': result['ticker'],
                'Action': result['recommendation']['action'],
                'Allocation %': f"{percentage:.1f}%",
                'Amount': f"${amount:,.0f}",
                'Risk Level': result['risk_level']
            })
        
        st.dataframe(pd.DataFrame(allocation_data), use_container_width=True, hide_index=True)

def _render_technical_analysis_section(successful_results):
    """Render technical analysis section"""
    st.markdown("---")
    st.subheader("📈 Technical Analysis")
    
    # Select stock for detailed technical analysis
    tech_analysis_ticker = st.selectbox(
        "Select stock for detailed technical analysis:",
        options=[r['ticker'] for r in successful_results],
        help="View candlestick chart with technical indicators"
    )
    
    if tech_analysis_ticker:
        tech_fig = create_technical_analysis_chart(tech_analysis_ticker)
        if tech_fig:
            st.plotly_chart(tech_fig, use_container_width=True)
        else:
            st.info("Unable to load technical analysis data for this stock.")
    
    # Detailed Investment Dashboard
    st.markdown("---")
    st.subheader("📊 Detailed Investment Dashboard")
    
    detailed_ticker = st.selectbox(
        "Select stock for detailed investment dashboard:",
        options=[r['ticker'] for r in successful_results],
        help="Comprehensive analysis dashboard for selected stock"
    )
    
    if detailed_ticker:
        # Find the result and load data
        detailed_result = next((r for r in successful_results if r['ticker'] == detailed_ticker), None)
        
        if detailed_result:
            df_detailed = load_dataframes(detailed_ticker)
            
            # Create investment dashboard
            investment_dashboard_fig = create_investment_dashboard(df_detailed, detailed_ticker, detailed_result)
            if investment_dashboard_fig:
                st.plotly_chart(investment_dashboard_fig, use_container_width=True)
            
            # Show raw metrics
            with st.expander("📊 Raw Investment Metrics"):
                if 'metrics' in detailed_result:
                    _render_raw_metrics(detailed_result['metrics'])

def _render_raw_metrics(metrics):
    """Render raw investment metrics table"""
    metrics_df_data = []
    for key, value in metrics.items():
        if key == 'support_resistance' and isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, (int, float)):
                    metrics_df_data.append({
                        'Metric': f"Price {k.title()}",
                        'Value': f"${v:.2f}" if 'price' in k.lower() else f"{v:.4f}",
                        'Description': f"Support/Resistance level"
                    })
        elif isinstance(value, (int, float)):
            metrics_df_data.append({
                'Metric': key.replace('_', ' ').title(),
                'Value': f"{value:.4f}",
                'Description': get_metric_description(key)
            })
    
    if metrics_df_data:
        st.dataframe(pd.DataFrame(metrics_df_data), use_container_width=True, hide_index=True)

def _render_export_section(successful_results):
    """Render export recommendations section"""
    st.markdown("---")
    st.subheader("📤 Export Recommendations")
    
    # Create export data
    export_data = []
    for result in successful_results:
        export_data.append({
            'Ticker': result['ticker'],
            'Recommendation': result['recommendation']['action'],
            'Score': result['recommendation']['score'],
            'Confidence': result['confidence'],
            'Risk Level': result['risk_level'],
            'Reasoning': '; '.join(result['recommendation']['reasoning'])
        })
    
    export_df = pd.DataFrame(export_data)
    csv = export_df.to_csv(index=False)
    
    st.download_button(
        label="💾 Download Investment Analysis Report",
        data=csv,
        file_name=f"investment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )