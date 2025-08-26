#!/usr/bin/env python3
"""Debug script to test TTM calculation issues"""

import sys
import os
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
from backend.services.fundamentals import get_service

def debug_ttm_calculation():
    print("=== Debug TTM Calculation for AAPL ===\n")
    
    ticker = "AAPL"
    
    # 1. Test yfinance data availability
    print("1. Testing yfinance data availability...")
    try:
        stock = yf.Ticker(ticker)
        quarterly_income = stock.quarterly_financials
        quarterly_cashflow = stock.quarterly_cashflow
        
        if not quarterly_income.empty:
            print(f"   Quarterly income statements: {len(quarterly_income.columns)} periods")
            print(f"   Columns (periods): {list(quarterly_income.columns)}")
            print(f"   Available fields: {list(quarterly_income.index[:10])}...")
            
            # Check for revenue fields
            revenue_fields = [field for field in quarterly_income.index if 'revenue' in field.lower()]
            print(f"   Revenue-related fields: {revenue_fields}")
            
            if len(quarterly_income.columns) > 0:
                most_recent_period = quarterly_income.columns[0]
                if 'Total Revenue' in quarterly_income.index:
                    revenue_value = quarterly_income.loc['Total Revenue', most_recent_period]
                    print(f"   Most recent revenue ({most_recent_period}): {revenue_value}")
        else:
            print("   No quarterly income data available")
            
    except Exception as e:
        print(f"   Error: {e}")
        traceback.print_exc()
    
    print()
    
    # 2. Test service data retrieval with detailed error tracking
    print("2. Testing service data retrieval...")
    try:
        service = get_service()
        
        # Add detailed error tracking to the service call
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger()
        
        # Capture the exact error location
        try:
            data = service.get_fundamentals_data(ticker)
            print("   Service call completed successfully")
        except Exception as service_error:
            print(f"Error in service call: {service_error}")
            print("Full traceback:")
            traceback.print_exc()
            return
            
        print(f"   Service returned data: {list(data.keys())}")
        
        ttm = data['ttm']
        print(f"   TTM data keys: {list(ttm.keys())}")
        print(f"   TTM insufficient_data: {ttm.get('insufficient_data')}")
        print(f"   TTM revenue_ttm: {ttm.get('revenue_ttm')}")
        print(f"   Metadata: {data['metadata']}")
        
    except Exception as e:
        print(f"Error in TTM calculation: {e}")
        print("Full traceback:")
        traceback.print_exc()
    
    print()
    
    # 3. Test TTM computation wrapper
    print("3. Testing TTM computation wrapper...")
    try:
        from backend.services.fundamentals import compute_ttm_metrics
        ttm_result = compute_ttm_metrics(ticker)
        print(f"   TTM result type: {type(ttm_result)}")
        print(f"   TTM insufficient_data: {ttm_result.insufficient_data}")
        print(f"   TTM revenue_ttm: {ttm_result.revenue_ttm}")
        print(f"   TTM operating_margin_ttm: {ttm_result.operating_margin_ttm}")
    except Exception as e:
        print(f"   Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_ttm_calculation()