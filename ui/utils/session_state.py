import streamlit as st

@st.cache_resource
def get_processed_cache():
    """Get cache for processed tickers"""
    return set()

def initialize_session_state():
    """Initialize session state variables"""
    # Mobile viewport detection
    if 'mobile_view' not in st.session_state:
        st.session_state.mobile_view = False
    
    # Initialize other session variables
    if 'selected_ticker' not in st.session_state:
        st.session_state.selected_ticker = ""
    
    if 'filter_sources' not in st.session_state:
        st.session_state.filter_sources = ["Reddit", "News", "SEC"]
    
    if 'filter_compound_range' not in st.session_state:
        st.session_state.filter_compound_range = (-1.0, 1.0)

def update_session_state(key, value):
    """Update session state with key-value pair"""
    st.session_state[key] = value

def get_session_state(key, default=None):
    """Get session state value with default"""
    return st.session_state.get(key, default)