#!/usr/bin/env python3
"""Simplified debug script to isolate the DatetimeIndex ambiguity error"""

import sys
import os
import traceback
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf

def test_specific_operations():
    print("=== Testing DatetimeIndex Operations ===\n")
    
    ticker = "AAPL"
    stock = yf.Ticker(ticker)
    
    try:
        # Get the data
        print("1. Fetching data...")
        quarterly_income = stock.quarterly_financials
        quarterly_cashflow = stock.quarterly_cashflow
        
        print(f"   Income columns: {list(quarterly_income.columns)}")
        print(f"   Column type: {type(quarterly_income.columns)}")
        
        # Test column sorting operations
        print("\n2. Testing column sorting operations...")
        try:
            print("   Testing pandas sort_values...")
            sorted_cols = quarterly_income.columns.sort_values(ascending=False)
            print(f"   Sorted columns: {list(sorted_cols)}")
        except Exception as e:
            print(f"   Error in sort_values: {e}")
            traceback.print_exc()
            
        # Test reindex operation
        print("\n3. Testing reindex operations...")
        try:
            print("   Testing reindex with sort_values...")
            reindexed_df = quarterly_income.reindex(quarterly_income.columns.sort_values(ascending=False), axis=1)
            print(f"   Reindex successful, shape: {reindexed_df.shape}")
        except Exception as e:
            print(f"   Error in reindex: {e}")
            traceback.print_exc()
            
        # Test column slicing operations
        print("\n4. Testing column slicing operations...")
        try:
            print("   Testing column[:4] slicing...")
            recent_periods = quarterly_income.columns[:4]
            print(f"   Recent periods: {list(recent_periods)}")
        except Exception as e:
            print(f"   Error in slicing: {e}")
            traceback.print_exc()
            
        # Test specific period matching
        print("\n5. Testing period matching...")
        try:
            print("   Testing isin() method...")
            period = quarterly_income.columns[0]
            print(f"   Testing period: {period}")
            matching_cols = quarterly_income.columns[quarterly_income.columns.isin([period])]
            print(f"   Matching columns: {list(matching_cols)}")
        except Exception as e:
            print(f"   Error in isin(): {e}")
            traceback.print_exc()
            
        # Test data access
        print("\n6. Testing data access...")
        try:
            print("   Testing _safe_get simulation...")
            period = quarterly_income.columns[0]
            field = 'Total Revenue'
            
            if field in quarterly_income.index:
                value = quarterly_income.loc[field, period]
                print(f"   Retrieved value: {value}")
        except Exception as e:
            print(f"   Error in data access: {e}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"Overall error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_specific_operations()