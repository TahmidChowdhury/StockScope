"""
Custom Streamlit Component for Modern Stock Cards
This uses React under the hood for better UI control
"""
import streamlit as st
import streamlit.components.v1 as components
import json

# Create a custom component for stock cards
def stock_card_component(ticker, data, key=None):
    """
    Custom React component for stock cards with modern styling
    """
    component_html = f"""
    <div id="stock-card-{ticker}" style="font-family: sans-serif;">
        <div style="
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            border: 1px solid #dee2e6;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            cursor: pointer;
        " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.15)';" 
           onmouseout="this.style.transform='translateY(0px)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)';">
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; font-size: 1.5rem; color: #2c3e50;">{ticker}</h3>
                <div style="
                    background: {'#28a745' if data.get('sentiment', 0) > 0.1 else '#dc3545' if data.get('sentiment', 0) < -0.1 else '#ffc107'};
                    color: white;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-size: 0.8rem;
                    font-weight: bold;
                ">
                    {'🟢 Bullish' if data.get('sentiment', 0) > 0.1 else '🔴 Bearish' if data.get('sentiment', 0) < -0.1 else '🟡 Neutral'}
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem;">
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #495057;">{data.get('sentiment', 0):.3f}</div>
                    <div style="font-size: 0.8rem; color: #6c757d;">Sentiment</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #495057;">{data.get('posts', 0)}</div>
                    <div style="font-size: 0.8rem; color: #6c757d;">Posts</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #495057;">{data.get('sources', 0)}</div>
                    <div style="font-size: 0.8rem; color: #6c757d;">Sources</div>
                </div>
            </div>
            
            <div style="display: flex; gap: 0.5rem;">
                <button onclick="parent.postMessage({{type: 'analyze', ticker: '{ticker}'}}, '*')" style="
                    flex: 1;
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                    color: white;
                    border: none;
                    padding: 0.75rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                    transition: all 0.2s ease;
                " onmouseover="this.style.transform='scale(1.02)';" onmouseout="this.style.transform='scale(1)';">
                    📊 Analyze
                </button>
                <button onclick="parent.postMessage({{type: 'advice', ticker: '{ticker}'}}, '*')" style="
                    flex: 1;
                    background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
                    color: white;
                    border: none;
                    padding: 0.75rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                    transition: all 0.2s ease;
                " onmouseover="this.style.transform='scale(1.02)';" onmouseout="this.style.transform='scale(1)';">
                    🎯 Advice
                </button>
            </div>
        </div>
    </div>
    
    <script>
        // Listen for messages from the component
        window.addEventListener('message', function(event) {{
            if (event.data.type === 'analyze' || event.data.type === 'advice') {{
                // Send data back to Streamlit
                window.parent.postMessage({{
                    type: 'streamlit:componentValue',
                    value: event.data
                }}, '*');
            }}
        }});
    </script>
    """
    
    # Use the component
    result = components.html(component_html, height=200, key=key)
    
    # Handle the result
    if result:
        if result.get('type') == 'analyze':
            st.session_state.selected_ticker = result.get('ticker')
            st.session_state.show_analysis = True
        elif result.get('type') == 'advice':
            st.session_state.advice_ticker = result.get('ticker')
            st.session_state.show_advice = True
    
    return result