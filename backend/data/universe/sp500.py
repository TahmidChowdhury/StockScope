"""S&P 500 universe data loader."""

import json
import os
from typing import List

def load_sp500_universe() -> List[str]:
    """Load S&P 500 tickers from JSON file."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sp500_path = os.path.join(current_dir, "sp500.json")
        
        with open(sp500_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'tickers' in data:
            return data['tickers']
        elif isinstance(data, dict) and 'symbols' in data:
            return data['symbols']
        else:
            # Fallback: extract values if it's a dict
            return list(data.values()) if isinstance(data, dict) else []
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load S&P 500 universe: {e}")
        # Fallback to a small set of common tickers
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK.B",
            "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "ADBE",
            "NFLX", "INTC", "CRM", "VZ", "T", "PFE", "WMT", "BAC", "KO", "NKE"
        ]