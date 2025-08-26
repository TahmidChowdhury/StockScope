"""Fundamentals data service for fetching and computing financial metrics."""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from backend.models.fundamentals import FundamentalsTTM, FundamentalsSeries

logger = logging.getLogger(__name__)

# Global service instance
_fundamentals_service = None

def get_service() -> 'FundamentalsService':
    """Get or create the global fundamentals service instance"""
    global _fundamentals_service
    if _fundamentals_service is None:
        _fundamentals_service = FundamentalsService()
    return _fundamentals_service

def compute_ttm_metrics(ticker: str) -> FundamentalsTTM:
    """Compute TTM metrics for a ticker - wrapper for router compatibility"""
    service = get_service()
    data = service.get_fundamentals_data(ticker)
    ttm_data = data['ttm']
    
    # Add debt_to_cash calculation if missing
    debt_to_cash = None
    if (ttm_data.get('total_debt') is not None and 
        ttm_data.get('cash_and_equivalents') is not None and 
        ttm_data['cash_and_equivalents'] != 0):
        debt_to_cash = ttm_data['total_debt'] / ttm_data['cash_and_equivalents']
    
    return FundamentalsTTM(
        ticker=ticker,
        revenue_ttm=ttm_data.get('revenue_ttm'),
        operating_income_ttm=ttm_data.get('operating_income_ttm'),
        operating_margin_ttm=ttm_data.get('operating_margin_ttm'),
        fcf_ttm=ttm_data.get('fcf_ttm'),
        fcf_margin_ttm=ttm_data.get('fcf_margin_ttm'),
        ebitda_ttm=ttm_data.get('ebitda_ttm'),
        revenue_growth_yoy=ttm_data.get('revenue_growth_yoy'),
        fcf_growth_yoy=ttm_data.get('fcf_growth_yoy'),
        ebitda_growth_yoy=ttm_data.get('ebitda_growth_yoy'),
        margin_growth_yoy_pp=ttm_data.get('margin_growth_yoy_pp'),
        total_debt=ttm_data.get('total_debt'),
        cash_and_equivalents=ttm_data.get('cash_and_equivalents'),
        net_debt=ttm_data.get('net_debt'),
        debt_to_cash=debt_to_cash,
        insufficient_data=ttm_data.get('insufficient_data', True)
    )

def compute_quarterly_series(ticker: str) -> FundamentalsSeries:
    """Compute quarterly series data for a ticker - wrapper for router compatibility"""
    service = get_service()
    data = service.get_fundamentals_data(ticker)
    series_data = data['series']
    
    # Convert series data to the format expected by FundamentalsSeries
    from backend.models.fundamentals import FundamentalPoint
    from datetime import datetime
    
    revenue_q = []
    operating_income_q = []
    operating_margin_q = []
    fcf_q = []
    fcf_margin_q = []
    ebitda_q = []
    
    for item in series_data:
        # Parse the period date
        try:
            if isinstance(item.get('period'), str):
                # Handle string dates like "2024-09-30"
                date_obj = datetime.strptime(item['period'][:10], '%Y-%m-%d')
            else:
                # Fallback for other formats
                date_obj = datetime.now()
        except:
            date_obj = datetime.now()
        
        revenue_q.append(FundamentalPoint(date=date_obj, value=item.get('revenue')))
        operating_income_q.append(FundamentalPoint(date=date_obj, value=item.get('operating_income')))
        operating_margin_q.append(FundamentalPoint(date=date_obj, value=item.get('operating_margin')))
        fcf_q.append(FundamentalPoint(date=date_obj, value=item.get('fcf')))
        fcf_margin_q.append(FundamentalPoint(date=date_obj, value=item.get('fcf_margin')))
        # EBITDA is not in the series data, so we'll set it to None for now
        ebitda_q.append(FundamentalPoint(date=date_obj, value=None))
    
    return FundamentalsSeries(
        revenue_q=revenue_q,
        operating_income_q=operating_income_q,
        operating_margin_q=operating_margin_q,
        fcf_q=fcf_q,
        fcf_margin_q=fcf_margin_q,
        ebitda_q=ebitda_q
    )

class FundamentalsService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
    
    def get_fundamentals_data(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive fundamentals data with smart fallback logic"""
        cache_key = f"fundamentals_{ticker}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_duration:
                return cached_data
        
        try:
            stock = yf.Ticker(ticker)
            
            # Get quarterly data (primary)
            quarterly_income = stock.quarterly_financials
            quarterly_cashflow = stock.quarterly_cashflow
            quarterly_balance = stock.quarterly_balance_sheet
            
            # Get annual data (fallback)
            annual_income = stock.financials
            annual_cashflow = stock.cashflow
            annual_balance = stock.balance_sheet
            
            logger.info(f"Data availability for {ticker}:")
            logger.info(f"Quarterly income: {len(quarterly_income.columns) if not quarterly_income.empty else 0} periods")
            logger.info(f"Annual income: {len(annual_income.columns) if not annual_income.empty else 0} periods")
            
            # Smart data selection: use quarterly if sufficient, otherwise annual
            use_quarterly = (
                not quarterly_income.empty and 
                not quarterly_cashflow.empty and 
                len(quarterly_income.columns) >= 4  # At least 4 quarters
            )
            
            if use_quarterly:
                logger.info(f"Using quarterly data for {ticker}")
                income = quarterly_income
                cashflow = quarterly_cashflow
                balance = quarterly_balance
                is_quarterly = True
            else:
                logger.info(f"Falling back to annual data for {ticker}")
                income = annual_income
                cashflow = annual_cashflow 
                balance = annual_balance
                is_quarterly = False
            
            # Calculate metrics based on available data
            result = self._calculate_comprehensive_metrics(
                ticker, income, cashflow, balance, is_quarterly
            )
            
            # Cache the result
            self.cache[cache_key] = (result, datetime.now())
            return result
            
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return self._get_empty_result(ticker, str(e))
    
    def _calculate_comprehensive_metrics(
        self, ticker: str, income: pd.DataFrame, cashflow: pd.DataFrame, 
        balance: pd.DataFrame, is_quarterly: bool
    ) -> Dict[str, Any]:
        """Calculate metrics with intelligent handling of available data"""
        
        try:
            # Sort columns by date (most recent first)
            if not income.empty:
                income = income.reindex(sorted(income.columns, reverse=True), axis=1)
            if not cashflow.empty:
                cashflow = cashflow.reindex(sorted(cashflow.columns, reverse=True), axis=1)
            if not balance.empty:
                balance = balance.reindex(sorted(balance.columns, reverse=True), axis=1)
            
            num_periods = len(income.columns) if not income.empty else 0
            logger.info(f"Processing {num_periods} periods of data for {ticker}")
            
            # Calculate TTM and series data
            ttm_data = self._calculate_ttm_metrics(income, cashflow, balance, is_quarterly)
            series_data = self._calculate_series_data(income, cashflow, balance, is_quarterly)
            
            return {
                "ticker": ticker,
                "ttm": ttm_data,
                "series": series_data,
                "metadata": {
                    "data_type": "quarterly" if is_quarterly else "annual",
                    "periods_available": num_periods,
                    "last_updated": datetime.now().isoformat(),
                    "insufficient_data": num_periods < 2  # Need at least 2 periods for any calculations
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics for {ticker}: {str(e)}")
            return self._get_empty_result(ticker, str(e))
    
    def _calculate_ttm_metrics(self, income: pd.DataFrame, cashflow: pd.DataFrame, 
                              balance: pd.DataFrame, is_quarterly: bool) -> Dict[str, Any]:
        """Calculate TTM metrics with smart data handling"""
        
        if income.empty:
            return self._get_empty_ttm()
        
        num_periods = len(income.columns)
        
        # Determine if we have sufficient data based on data type
        if is_quarterly:
            # For quarterly data, we need at least 2 periods for growth calculations
            has_sufficient_data = num_periods >= 2
            # For TTM metrics, we prefer 4 quarters but can work with 1+
            can_calculate_ttm = num_periods >= 1
        else:
            # For annual data, 1 period is sufficient for TTM metrics
            has_sufficient_data = num_periods >= 1
            can_calculate_ttm = num_periods >= 1
        
        if not can_calculate_ttm:
            logger.warning(f"Insufficient data periods for TTM calculation: {num_periods}")
            return self._get_empty_ttm()
        
        try:
            if is_quarterly and num_periods >= 4:
                # Use last 4 quarters for TTM
                recent_periods = income.columns[:4]
                ttm_multiplier = 1  # Already TTM
            elif is_quarterly and num_periods >= 2:
                # Use available quarters and extrapolate
                recent_periods = income.columns[:num_periods]
                ttm_multiplier = 4 / num_periods  # Extrapolate to annual
                logger.info(f"Extrapolating from {num_periods} quarters")
            elif is_quarterly and num_periods >= 1:
                # Use single quarter and extrapolate (least preferred)
                recent_periods = income.columns[:1]
                ttm_multiplier = 4  # Extrapolate single quarter to annual
                logger.info(f"Extrapolating from 1 quarter (least reliable)")
            elif not is_quarterly and num_periods >= 1:
                # Use most recent annual data
                recent_periods = income.columns[:1]
                ttm_multiplier = 1  # Already annual
            else:
                logger.warning(f"Cannot calculate TTM with {num_periods} periods")
                return self._get_empty_ttm()
            
            # Calculate TTM values
            revenue_ttm = self._safe_sum(income, 'Total Revenue', recent_periods) * ttm_multiplier
            operating_income_ttm = self._safe_sum(income, 'Operating Income', recent_periods) * ttm_multiplier
            
            # Free Cash Flow from cashflow statement
            fcf_ttm = None
            if not cashflow.empty:
                operating_cf = self._safe_sum(cashflow, 'Operating Cash Flow', recent_periods[:min(len(recent_periods), len(cashflow.columns))])
                capex = self._safe_sum(cashflow, 'Capital Expenditures', recent_periods[:min(len(recent_periods), len(cashflow.columns))])
                if operating_cf is not None and capex is not None:
                    fcf_ttm = (operating_cf + capex) * ttm_multiplier  # CapEx is negative
            
            # EBITDA calculation
            ebitda_ttm = None
            if operating_income_ttm is not None:
                depreciation = self._safe_sum(income, 'Depreciation And Amortization', recent_periods)
                if depreciation is not None:
                    ebitda_ttm = (operating_income_ttm + abs(depreciation)) * (ttm_multiplier if is_quarterly else 1)
            
            # Calculate margins
            operating_margin_ttm = None
            fcf_margin_ttm = None
            if revenue_ttm and revenue_ttm != 0:
                if operating_income_ttm is not None:
                    operating_margin_ttm = operating_income_ttm / revenue_ttm
                if fcf_ttm is not None:
                    fcf_margin_ttm = fcf_ttm / revenue_ttm
            
            # Growth calculations with improved logic
            growth_data = self._calculate_growth_rates(income, cashflow, is_quarterly)
            
            # Debt metrics from balance sheet
            debt_metrics = self._calculate_debt_metrics(balance)
            
            return {
                "ticker": income.columns[0] if len(income.columns) > 0 else "Unknown",
                "revenue_ttm": revenue_ttm,
                "operating_income_ttm": operating_income_ttm,
                "operating_margin_ttm": operating_margin_ttm,
                "fcf_ttm": fcf_ttm,
                "fcf_margin_ttm": fcf_margin_ttm,
                "ebitda_ttm": ebitda_ttm,
                **growth_data,
                **debt_metrics,
                "insufficient_data": not has_sufficient_data  # Fixed logic
            }
            
        except Exception as e:
            logger.error(f"Error in TTM calculation: {str(e)}")
            return self._get_empty_ttm()
    
    def _calculate_growth_rates(self, income: pd.DataFrame, cashflow: pd.DataFrame, 
                               is_quarterly: bool) -> Dict[str, Optional[float]]:
        """Calculate growth rates with flexible period handling"""
        
        if income.empty or len(income.columns) < 2:
            return {
                "revenue_growth_yoy": None,
                "fcf_growth_yoy": None,
                "ebitda_growth_yoy": None,
                "margin_growth_yoy_pp": None
            }
        
        try:
            num_periods = len(income.columns)
            
            if is_quarterly:
                # For quarterly data, compare year-over-year
                if num_periods >= 5:  # Need at least 5 quarters to compare Q1 vs Q1 of previous year
                    current_q = income.columns[0]  # Most recent quarter
                    yoy_q = income.columns[4]      # Same quarter, previous year
                    periods_for_comparison = [current_q, yoy_q]
                    multiplier = 1
                elif num_periods >= 2:
                    # Fall back to sequential quarter comparison, annualized
                    current_q = income.columns[0]
                    prev_q = income.columns[1]
                    periods_for_comparison = [current_q, prev_q]
                    multiplier = 4  # Annualize quarterly growth
                else:
                    return self._get_empty_growth()
            else:
                # For annual data, compare year-over-year
                if num_periods >= 2:
                    current_year = income.columns[0]
                    prev_year = income.columns[1]
                    periods_for_comparison = [current_year, prev_year]
                    multiplier = 1
                else:
                    return self._get_empty_growth()
            
            # Calculate growth rates
            current_period, comparison_period = periods_for_comparison
            
            # Revenue growth
            current_revenue = self._safe_get(income, 'Total Revenue', current_period)
            prev_revenue = self._safe_get(income, 'Total Revenue', comparison_period)
            revenue_growth_yoy = self._calculate_growth_rate(current_revenue, prev_revenue, multiplier)
            
            # FCF growth
            fcf_growth_yoy = None
            if not cashflow.empty and len(cashflow.columns) >= len(periods_for_comparison):
                current_cf = self._safe_get(cashflow, 'Operating Cash Flow', current_period)
                current_capex = self._safe_get(cashflow, 'Capital Expenditures', current_period)
                prev_cf = self._safe_get(cashflow, 'Operating Cash Flow', comparison_period)
                prev_capex = self._safe_get(cashflow, 'Capital Expenditures', comparison_period)
                
                if all(v is not None for v in [current_cf, current_capex, prev_cf, prev_capex]):
                    current_fcf = current_cf + current_capex  # CapEx is negative
                    prev_fcf = prev_cf + prev_capex
                    fcf_growth_yoy = self._calculate_growth_rate(current_fcf, prev_fcf, multiplier)
            
            # Operating margin change (in percentage points)
            margin_growth_yoy_pp = None
            current_oi = self._safe_get(income, 'Operating Income', current_period)
            prev_oi = self._safe_get(income, 'Operating Income', comparison_period)
            
            if all(v is not None and v != 0 for v in [current_revenue, prev_revenue, current_oi, prev_oi]):
                current_margin = current_oi / current_revenue
                prev_margin = prev_oi / prev_revenue
                margin_growth_yoy_pp = (current_margin - prev_margin) * (multiplier ** 0.5)  # Moderate multiplier effect
            
            # EBITDA growth (simplified calculation)
            ebitda_growth_yoy = None
            current_ebitda = current_oi
            prev_ebitda = prev_oi
            if current_ebitda is not None and prev_ebitda is not None:
                # Add back depreciation if available
                current_depreciation = self._safe_get(income, 'Depreciation And Amortization', current_period)
                prev_depreciation = self._safe_get(income, 'Depreciation And Amortization', comparison_period)
                if current_depreciation is not None and prev_depreciation is not None:
                    current_ebitda += abs(current_depreciation)
                    prev_ebitda += abs(prev_depreciation)
                ebitda_growth_yoy = self._calculate_growth_rate(current_ebitda, prev_ebitda, multiplier)
            
            return {
                "revenue_growth_yoy": revenue_growth_yoy,
                "fcf_growth_yoy": fcf_growth_yoy,
                "ebitda_growth_yoy": ebitda_growth_yoy,
                "margin_growth_yoy_pp": margin_growth_yoy_pp
            }
            
        except Exception as e:
            logger.error(f"Error calculating growth rates: {str(e)}")
            return self._get_empty_growth()

    def _safe_get(self, df: pd.DataFrame, field: str, period) -> Optional[float]:
        """Safely get a value from DataFrame with multiple field name attempts"""
        if df.empty:
            return None
        
        # Handle period matching - yfinance uses Timestamp objects as column names
        period_key = None
        try:
            # Convert period to a comparable format first
            if hasattr(period, 'date'):
                target_date = period.date()
            else:
                try:
                    target_date = pd.Timestamp(period).date()
                except:
                    target_date = str(period)
            
            # Find matching column using safe comparison
            for col in df.columns:
                try:
                    if hasattr(col, 'date'):
                        col_date = col.date()
                        if col_date == target_date:
                            period_key = col
                            break
                    elif str(col) == str(period) or str(col)[:10] == str(target_date):
                        period_key = col
                        break
                except (TypeError, ValueError, AttributeError):
                    continue
                    
        except Exception as e:
            logger.warning(f"Period comparison error: {e}")
            
        # Fallback: use first column if no match found
        if period_key is None and len(df.columns) > 0:
            period_key = df.columns[0]
            logger.debug(f"Using first available period {period_key} instead of requested {period}")
            
        if period_key is None:
            return None
        
        # Field mappings remain the same
        field_mappings = {
            'Total Revenue': ['Total Revenue', 'Operating Revenue', 'Revenue', 'Net Sales', 'Sales'],
            'Operating Income': ['Operating Income', 'Total Operating Income As Reported', 'Operating Revenue', 'EBIT'],
            'Operating Cash Flow': ['Operating Cash Flow', 'Cash Flow From Operating Activities', 'Total Cash From Operating Activities'],
            'Capital Expenditures': ['Capital Expenditures', 'Capital Expenditure', 'Capex', 'Property Plant Equipment Investments', 'Net PPE Purchase And Sale'],
            'Depreciation And Amortization': ['Depreciation And Amortization', 'Depreciation', 'Amortization', 'Reconciled Depreciation']
        }
        
        # Build list of field variants to try
        field_variants = [field]
        if field in field_mappings:
            field_variants.extend(field_mappings[field])
        
        # Try to get the value using field variants
        for variant in field_variants:
            # First try exact match
            if variant in df.index:
                try:
                    value = df.loc[variant, period_key]
                    if pd.notna(value) and value != 0:
                        return float(value)
                except Exception as e:
                    logger.debug(f"Error accessing {variant} for period {period_key}: {e}")
                    continue
            
            # Then try case-insensitive search
            for idx in df.index:
                if str(idx).lower() == variant.lower():
                    try:
                        value = df.loc[idx, period_key]
                        if pd.notna(value) and value != 0:
                            return float(value)
                    except Exception as e:
                        logger.debug(f"Error accessing {idx} for period {period_key}: {e}")
                        continue
        
        # Log available fields for debugging
        logger.debug(f"Field '{field}' not found. Available fields: {list(df.index)[:10]}...")
        return None

    def _safe_sum(self, df: pd.DataFrame, field: str, periods: List) -> Optional[float]:
        """Safely sum values across multiple periods"""
        if df.empty or not periods:
            return None
        
        total = 0
        valid_values = 0
        
        for period in periods:
            # Safe period existence check
            try:
                period_exists = False
                # Convert period to string for comparison to avoid DatetimeIndex issues
                period_str = str(period)[:10] if hasattr(period, 'date') else str(period)
                
                for col in df.columns:
                    col_str = str(col)[:10] if hasattr(col, 'date') else str(col)
                    if period_str == col_str or col == period:
                        period_exists = True
                        break
                
                if not period_exists:
                    continue
                    
            except Exception as e:
                logger.debug(f"Error checking period existence: {e}")
                continue
                
            value = self._safe_get(df, field, period)
            if value is not None:
                total += value
                valid_values += 1
        
        return total if valid_values > 0 else None
    
    def _calculate_growth_rate(self, current: Optional[float], previous: Optional[float], 
                              multiplier: float = 1) -> Optional[float]:
        """Calculate growth rate with multiplier for annualization"""
        if current is None or previous is None or previous == 0:
            return None
        
        growth_rate = (current / previous - 1) * multiplier
        
        # Cap extreme growth rates to reasonable bounds
        if abs(growth_rate) > 10:  # 1000% growth cap
            return None
        
        return growth_rate
    
    def _calculate_debt_metrics(self, balance: pd.DataFrame) -> Dict[str, Optional[float]]:
        """Calculate debt-related metrics from balance sheet"""
        if balance.empty:
            return {
                "total_debt": None,
                "cash_and_equivalents": None,
                "net_debt": None
            }
        
        try:
            most_recent = balance.columns[0]
            
            # Total debt (sum of short-term and long-term debt)
            short_term_debt = self._safe_get(balance, 'Current Debt', most_recent) or 0
            long_term_debt = self._safe_get(balance, 'Long Term Debt', most_recent) or 0
            total_debt = short_term_debt + long_term_debt if (short_term_debt or long_term_debt) else None
            
            # Cash and cash equivalents
            cash = self._safe_get(balance, 'Cash And Cash Equivalents', most_recent)
            
            # Net debt
            net_debt = None
            if total_debt is not None and cash is not None:
                net_debt = total_debt - cash
            
            return {
                "total_debt": total_debt,
                "cash_and_equivalents": cash,
                "net_debt": net_debt
            }
            
        except Exception as e:
            logger.error(f"Error calculating debt metrics: {str(e)}")
            return {
                "total_debt": None,
                "cash_and_equivalents": None,
                "net_debt": None
            }
    
    def _calculate_series_data(self, income: pd.DataFrame, cashflow: pd.DataFrame, 
                              balance: pd.DataFrame, is_quarterly: bool) -> List[Dict[str, Any]]:
        """Calculate time series data for charts"""
        if income.empty:
            return []
        
        series = []
        num_periods = min(8, len(income.columns))  # Limit to last 8 periods for performance
        
        for i in range(num_periods):
            period = income.columns[i]
            
            # Basic metrics for this period
            revenue = self._safe_get(income, 'Total Revenue', period)
            operating_income = self._safe_get(income, 'Operating Income', period)
            
            # FCF for this period
            fcf = None
            if not cashflow.empty and period in cashflow.columns:
                operating_cf = self._safe_get(cashflow, 'Operating Cash Flow', period)
                capex = self._safe_get(cashflow, 'Capital Expenditures', period)
                if operating_cf is not None and capex is not None:
                    fcf = operating_cf + capex  # CapEx is negative
            
            # Margins
            operating_margin = None
            fcf_margin = None
            if revenue and revenue != 0:
                if operating_income is not None:
                    operating_margin = operating_income / revenue
                if fcf is not None:
                    fcf_margin = fcf / revenue
            
            series.append({
                "period": str(period)[:10] if hasattr(period, 'strftime') else str(period),
                "revenue": revenue,
                "operating_income": operating_income,
                "operating_margin": operating_margin,
                "fcf": fcf,
                "fcf_margin": fcf_margin,
                "is_quarterly": is_quarterly
            })
        
        return series
    
    def _get_empty_result(self, ticker: str, error: str = "") -> Dict[str, Any]:
        """Return empty result structure for error cases"""
        return {
            "ticker": ticker,
            "ttm": self._get_empty_ttm(),
            "series": [],
            "metadata": {
                "data_type": "unknown",
                "periods_available": 0,
                "last_updated": datetime.now().isoformat(),
                "insufficient_data": True,
                "error": error
            }
        }
    
    def _get_empty_ttm(self, insufficient_data: bool = False) -> Dict[str, Any]:
        """Get empty TTM structure with proper insufficient_data flag."""
        return {
            "revenue": None,
            "net_income": None,
            "total_debt": None,
            "cash_and_equivalents": None,
            "total_assets": None,
            "shareholders_equity": None,
            "operating_cash_flow": None,
            "free_cash_flow": None,
            "insufficient_data": insufficient_data
        }
    
    def _get_empty_growth(self) -> Dict[str, Optional[float]]:
        """Return empty growth structure"""
        return {
            "revenue_growth_yoy": None,
            "fcf_growth_yoy": None,
            "ebitda_growth_yoy": None,
            "margin_growth_yoy_pp": None
        }

    def get_trailing_periods(self, ticker: str, num_quarters: int = 4) -> List:
        """Get the last N quarters for TTM calculations"""
        try:
            stock = yf.Ticker(ticker)
            # Get quarterly financials
            quarterly_financials = stock.quarterly_financials
            
            if quarterly_financials.empty:
                logger.warning(f"No quarterly financials available for {ticker}")
                return []
            
            # Sort columns by date (most recent first) and take the required number
            periods = sorted(quarterly_financials.columns, reverse=True)[:num_quarters]
            
            logger.info(f"Found {len(periods)} periods for {ticker}: {[str(p) for p in periods]}")
            return periods
            
        except Exception as e:
            logger.error(f"Error getting trailing periods for {ticker}: {e}")
            return []

# Check if we have sufficient data for TTM calculations
        num_periods = len(valid_periods)
        if num_periods == 0:
            logger.warning(f"No valid periods found for {ticker}")
            return self._get_empty_ttm(insufficient_data=True)
        
        # For annual data, we can calculate TTM with just 1 period
        # For quarterly data, we need at least 4 quarters
        min_periods_required = 4 if period == 'quarterly' else 1
        if num_periods < min_periods_required:
            logger.warning(f"Insufficient periods for {ticker}: {num_periods} < {min_periods_required}")
            return self._get_empty_ttm(insufficient_data=True)

# Calculate TTM metrics
        num_periods = len(data)
        
        if num_periods == 0:
            return self._get_empty_ttm(insufficient_data=True)
        
        # For annual data, we can calculate TTM with just one period
        # For quarterly data, we need at least 4 quarters for proper TTM
        is_quarterly = any('Q' in item.get('period', '') for item in data)
        min_required_periods = 4 if is_quarterly else 1
        
        if num_periods < min_required_periods:
            return self._get_empty_ttm(insufficient_data=True)