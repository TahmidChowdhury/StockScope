#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from backend.services.fundamentals import compute_ttm_metrics, get_service
import yfinance as yf

def debug_ttm_calculation():
    ticker = "AAPL"
    print(f"=== Debug TTM Calculation for {ticker} ===\n")
    
    # Test basic yfinance data availability
    print("1. Testing yfinance data availability...")
    try:
        stock = yf.Ticker(ticker)
        quarterly_income = stock.quarterly_financials
        print(f"   Quarterly income statements: {len(quarterly_income.columns) if not quarterly_income.empty else 0} periods")
        
        if not quarterly_income.empty:
            print(f"   Columns (periods): {quarterly_income.columns.tolist()}")
            print(f"   Available fields: {quarterly_income.index.tolist()[:10]}...")
            
            # Check for Total Revenue specifically
            revenue_fields = [field for field in quarterly_income.index if 'revenue' in field.lower()]
            print(f"   Revenue-related fields: {revenue_fields}")
            
            if len(quarterly_income.columns) > 0:
                recent_period = quarterly_income.columns[0]
                if 'Total Revenue' in quarterly_income.index:
                    revenue_value = quarterly_income.loc['Total Revenue', recent_period]
                    print(f"   Most recent revenue ({recent_period}): {revenue_value}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2. Testing service data retrieval...")
    try:
        service = get_service()
        data = service.get_fundamentals_data(ticker)
        print(f"   Service returned data: {list(data.keys())}")
        print(f"   TTM data keys: {list(data['ttm'].keys())}")
        print(f"   TTM insufficient_data: {data['ttm'].get('insufficient_data')}")
        print(f"   TTM revenue_ttm: {data['ttm'].get('revenue_ttm')}")
        print(f"   Metadata: {data.get('metadata', {})}")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing TTM computation wrapper...")
    try:
        ttm_result = compute_ttm_metrics(ticker)
        print(f"   TTM result type: {type(ttm_result)}")
        print(f"   TTM insufficient_data: {ttm_result.insufficient_data}")
        print(f"   TTM revenue_ttm: {ttm_result.revenue_ttm}")
        print(f"   TTM operating_margin_ttm: {ttm_result.operating_margin_ttm}")
    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ttm_calculation()