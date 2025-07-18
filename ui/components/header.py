import streamlit as st

def render_header():
    """Render the main header of the application"""
    st.markdown('''
    <div class="main-header">
        <h1>📊 StockScope</h1>
        <p>Multi-Source Sentiment Analysis Dashboard</p>
    </div>
    ''', unsafe_allow_html=True)