"""Load the repository's curated US-stock list, not current S&P 500 membership."""

import json
import os
from typing import List

CURATED_UNIVERSE_NAME = "Curated US-stock list (membership date unknown)"

def load_sp500_universe() -> List[str]:
    """Legacy function name retained for callers; this is a curated subset."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sp500_path = os.path.join(current_dir, "sp500.json")
        
        with open(sp500_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return list(dict.fromkeys(str(ticker).upper().replace('.', '-') for ticker in data))
        elif isinstance(data, dict) and 'tickers' in data:
            return list(dict.fromkeys(str(ticker).upper().replace('.', '-') for ticker in data['tickers']))
        elif isinstance(data, dict) and 'symbols' in data:
            return list(dict.fromkeys(str(ticker).upper().replace('.', '-') for ticker in data['symbols']))
        else:
            raise ValueError("Curated stock universe has an unsupported format")
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError("Curated stock universe is unavailable") from e
