#!/usr/bin/env python3
"""Debug script to test actual service calls with detailed field analysis"""

import sys
import os
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
from backend.services.fundamentals import FundamentalsService

def debug_service_with_field_analysis():
    print("=== Debug Service with Field Analysis ===\n")
    
    ticker = "AAPL"
    
    # Test direct service call
    try:
        service = FundamentalsService()
        
        # Get raw yfinance data first
        print("1. Analyzing available fields in yfinance data...")
        stock = yf.Ticker(ticker)
        quarterly_income = stock.quarterly_financials
        quarterly_cashflow = stock.quarterly_cashflow
        quarterly_balance = stock.quarterly_balance_sheet
        
        print(f"   Income statement fields: {list(quarterly_income.index)}")
        print(f"   Cashflow statement fields: {list(quarterly_cashflow.index) if not quarterly_cashflow.empty else 'EMPTY'}")
        print(f"   Balance sheet fields: {list(quarterly_balance.index) if not quarterly_balance.empty else 'EMPTY'}")
        
        # Test each calculation step individually
        print("\n2. Testing individual calculation steps...")
        
        # Test column sorting
        print("   a) Testing column sorting...")
        if not quarterly_income.empty:
            sorted_income = quarterly_income.reindex(quarterly_income.columns.sort_values(ascending=False), axis=1)
            print(f"   Sorted income shape: {sorted_income.shape}")
        
        # Test TTM calculation with manual field matching
        print("   b) Testing manual TTM calculation...")
        if not quarterly_income.empty:
            recent_periods = quarterly_income.columns[:4]
            print(f"   Recent periods: {list(recent_periods)}")
            
            # Try to find revenue field manually
            revenue_fields = [field for field in quarterly_income.index if 'revenue' in field.lower()]
            print(f"   Available revenue fields: {revenue_fields}")
            
            if revenue_fields:
                revenue_field = revenue_fields[0]
                print(f"   Using revenue field: {revenue_field}")
                
                # Calculate TTM revenue manually
                ttm_revenue = 0
                valid_periods = 0
                for period in recent_periods:
                    try:
                        value = quarterly_income.loc[revenue_field, period]
                        if pd.notna(value) and value != 0:
                            ttm_revenue += float(value)
                            valid_periods += 1
                            print(f"   Period {period}: {value}")
                    except Exception as e:
                        print(f"   Error accessing {period}: {e}")
                
                print(f"   Manual TTM Revenue: {ttm_revenue} (from {valid_periods} periods)")
        
        # Test actual service call
        print("\n3. Testing actual service call...")
        try:
            result = service.get_fundamentals_data(ticker)
            print(f"   Service call successful")
            print(f"   TTM data: {result['ttm']}")
        except Exception as e:
            print(f"   Service call failed: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"Overall error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    import pandas as pd
    debug_service_with_field_analysis()