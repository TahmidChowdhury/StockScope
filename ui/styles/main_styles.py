import streamlit as st

def apply_main_styles():
    """Apply main CSS styles to the application"""
    
    # Add viewport meta tag for better mobile experience
    st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="StockScope">
    """, unsafe_allow_html=True)

    # Apply comprehensive CSS styling
    st.markdown("""
    <style>
        /* Mobile-First Responsive Design */
        @media (max-width: 768px) {
            .main-header {
                padding: 0.5rem 0;
                margin: -1rem -1rem 1rem -1rem;
            }
            
            .main-header h1 {
                font-size: 1.8rem !important;
            }
            
            .main-header p {
                font-size: 0.9rem !important;
            }
            
            /* Make cards stack vertically on mobile */
            .investment-card-buy, .investment-card-hold, .investment-card-sell {
                margin: 1rem 0;
                padding: 1rem;
            }
            
            .card-title {
                font-size: 1.4rem !important;
            }
            
            .card-action {
                font-size: 1.5rem !important;
            }
            
            /* Responsive metrics */
            .metric-card {
                padding: 0.8rem;
                margin: 0.3rem 0;
            }
            
            /* Mobile-friendly buttons */
            .stButton > button {
                width: 100%;
                padding: 0.7rem 1rem;
                font-size: 1rem;
                margin: 0.2rem 0;
            }
            
            /* Compact sidebar on mobile */
            .css-1d391kg {
                padding: 0.5rem;
            }
            
            /* Better form spacing */
            .stForm {
                padding: 1rem;
                border-radius: 8px;
                background: rgba(0,0,0,0.02);
            }
            
            /* Responsive tabs */
            .stTabs [data-baseweb="tab"] {
                padding: 0.5rem 0.8rem;
                font-size: 0.9rem;
            }
            
            /* Mobile-friendly visualizations */
            .plotly-chart {
                width: 100% !important;
                height: 300px !important;
            }
            
            /* Compact expanders */
            .streamlit-expanderHeader {
                font-size: 0.9rem;
            }
            
            /* Better spacing */
            .block-container {
                padding: 1rem;
            }
        }
        
        /* Tablet optimizations */
        @media (min-width: 769px) and (max-width: 1024px) {
            .main-header h1 {
                font-size: 2.2rem;
            }
            
            .investment-card-buy, .investment-card-hold, .investment-card-sell {
                padding: 1.2rem;
            }
            
            .card-title {
                font-size: 1.6rem;
            }
            
            .card-action {
                font-size: 1.8rem;
            }
        }
        
        /* Main header styling */
        .main-header {
            text-align: center;
            padding: 1rem 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: -1rem -1rem 2rem -1rem;
            border-radius: 0 0 15px 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        /* Progressive Web App feel */
        .main-header h1 {
            font-size: 2.5rem;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .main-header p {
            font-size: 1.1rem;
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }
        
        /* Enhanced Quick Actions - Mobile First */
        .quick-actions {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
            border: 1px solid rgba(102, 126, 234, 0.2);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
        }
        
        .quick-actions h3 {
            text-align: center;
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.4rem;
        }
        
        /* Investment recommendation cards - improved styling */
        .investment-card-buy {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border: 2px solid #28a745;
            color: #155724;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 0.5rem 0;
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.15);
            transition: transform 0.2s ease;
        }
        
        .investment-card-buy:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.25);
        }
        
        .investment-card-hold {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
            border: 2px solid #ffc107;
            color: #856404;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 0.5rem 0;
            box-shadow: 0 4px 12px rgba(255, 193, 7, 0.15);
            transition: transform 0.2s ease;
        }
        
        .investment-card-hold:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 193, 7, 0.25);
        }
        
        .investment-card-sell {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border: 2px solid #dc3545;
            color: #721c24;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 0.5rem 0;
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.15);
            transition: transform 0.2s ease;
        }
        
        .investment-card-sell:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220, 53, 69, 0.25);
        }
        
        /* Card titles and text styling */
        .card-title {
            font-size: 1.8rem;
            font-weight: bold;
            margin: 0 0 0.5rem 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        
        .card-action {
            font-size: 2rem;
            font-weight: bold;
            margin: 0.5rem 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .card-text {
            font-size: 1rem;
            line-height: 1.4;
            margin: 0.3rem 0;
            font-weight: 500;
        }
        
        .card-text strong {
            font-weight: 700;
        }
        
        /* Metric cards styling */
        .metric-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            margin: 0.5rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        /* Alert styling */
        .stAlert {
            border-radius: 12px;
            border: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        /* Sentiment styling with better contrast */
        .sentiment-positive { 
            color: #198754; 
            font-weight: bold; 
            background: rgba(25, 135, 84, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
        }
        .sentiment-negative { 
            color: #dc3545; 
            font-weight: bold;
            background: rgba(220, 53, 69, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
        }
        .sentiment-neutral { 
            color: #fd7e14; 
            font-weight: bold;
            background: rgba(253, 126, 20, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
        }
        
        /* Button styling improvements */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
            border: none;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* Dark mode compatibility */
        @media (prefers-color-scheme: dark) {
            .metric-card {
                background: linear-gradient(135deg, #2d3436 0%, #363a3d 100%);
                color: #ffffff;
                border-left-color: #74b9ff;
            }
            
            .investment-card-buy {
                background: linear-gradient(135deg, #1e3a1e 0%, #2d5a2d 100%);
                border-color: #40c057;
                color: #c3f7c3;
            }
            
            .investment-card-hold {
                background: linear-gradient(135deg, #3d3419 0%, #5c4e1a 100%);
                border-color: #fab005;
                color: #fff3cd;
            }
            
            .investment-card-sell {
                background: linear-gradient(135deg, #3d1a1a 0%, #5c2d2d 100%);
                border-color: #f03e3e;
                color: #ffc9c9;
            }
            
            .quick-actions {
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                border-color: rgba(102, 126, 234, 0.3);
            }
        }
    </style>
    """, unsafe_allow_html=True)