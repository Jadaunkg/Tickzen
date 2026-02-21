#!/usr/bin/env python3
"""
Supabase Data Mapper
====================

Maps pipeline-collected stock data to Supabase schema structure.
Handles transformation, validation, and batch preparation for all 12 tables.

Tables Supported:
----------------
1. stocks - Stock registry and metadata
2. daily_price_data - OHLCV historical data
3. technical_indicators - Calculated technical metrics
4. fundamental_data - Financial metrics and ratios
5. forecast_data - Price predictions and analyst targets
6. risk_data - Risk metrics and volatility
7. market_price_snapshot - Current market overview
8. dividend_data - Dividend history and info
9. ownership_data - Insider and institutional ownership
10. sentiment_data - Sentiment analysis results
11. insider_transactions - Insider trading activity
12. data_sync_log - Audit trail of data updates
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def safe_float_conversion(value, max_value=None):
    """
    Safely convert value to float, handling NaN, Infinity, and None.
    Returns None for invalid values to ensure JSON compliance.
    
    Args:
        value: Value to convert
        max_value: Optional maximum value to cap at
        
    Returns:
        Float value or None
    """
    if value is None or value == 'N/A':
        return None
    try:
        val = float(value)
        # Check for NaN or Infinity (not JSON compliant)
        if np.isnan(val) or np.isinf(val):
            return None
        # Apply max value cap if specified
        if max_value is not None and abs(val) > max_value:
            return max_value if val > 0 else -max_value
        return val
    except (ValueError, TypeError):
        return None


def sanitize_for_json(obj):
    """
    Recursively sanitize any object for JSON serialization.
    Converts inf, -inf, and NaN to None throughout nested structures.
    
    Args:
        obj: Any Python object (dict, list, number, etc.)
        
    Returns:
        Sanitized object safe for JSON serialization
    """
    if obj is None:
        return None
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (int, str, bool)):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    else:
        # For other types, try to convert to string
        return str(obj)


class DataMapper:
    """Maps pipeline data to Supabase schema format"""
    
    def __init__(self):
        self.sync_stats = {
            'records_inserted': 0,
            'records_updated': 0,
            'records_failed': 0
        }
    
    def map_stock_metadata(self, ticker: str, info: Dict, processed_data: pd.DataFrame) -> Dict:
        """
        Map stock metadata to stocks table
        
        Args:
            ticker: Stock symbol
            info: yfinance info dict
            processed_data: Historical price data
            
        Returns:
            Dict ready for stocks table insertion
        """
        try:
            # Extract data coverage dates
            data_start = processed_data['Date'].min() if not processed_data.empty else None
            data_end = processed_data['Date'].max() if not processed_data.empty else None
            
            if isinstance(data_start, pd.Timestamp):
                data_start = data_start.date()
            if isinstance(data_end, pd.Timestamp):
                data_end = data_end.date()
            
            stock_record = {
                'symbol': ticker,
                'ticker': ticker,
                'company_name': info.get('longName') or info.get('shortName') or ticker,
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'exchange': info.get('exchange'),
                'website_url': info.get('website'),
                'employee_count': info.get('fullTimeEmployees'),
                'headquarters': self._extract_headquarters(info),
                'ceo_name': self._extract_ceo_name(info),
                'founded_year': self._extract_founded_year(info),
                'business_summary': (info.get('longBusinessSummary') or '')[:500] if info.get('longBusinessSummary') else None,
                'long_business_summary': info.get('longBusinessSummary'),
                
                # Database management
                'updated_at': datetime.now().isoformat(),
                'last_sync_date': datetime.now().isoformat(),
                'last_sync_status': 'success',
                'data_quality_score': 1.0,  # Will be calculated based on completeness
                
                # Data coverage
                'data_start_date': data_start.isoformat() if data_start else None,
                'data_end_date': data_end.isoformat() if data_end else None,
                'total_records': len(processed_data),
                
                # Tracking
                'is_active': True,
                'sync_enabled': True
            }
            
            return stock_record
            
        except Exception as e:
            logger.error(f"Error mapping stock metadata for {ticker}: {e}")
            raise
    
    def _extract_headquarters(self, info: Dict) -> str:
        """Extract headquarters from city, state, country fields"""
        city = info.get('city') or ''
        state = info.get('state') or ''
        country = info.get('country') or ''
        parts = [p for p in [city, state, country] if p]
        return ', '.join(parts) if parts else None
    
    def _extract_ceo_name(self, info: Dict) -> str:
        """Extract CEO name from companyOfficers list"""
        officers = info.get('companyOfficers')
        if officers and isinstance(officers, list):
            for officer in officers:
                title = (officer.get('title') or '').lower()
                if 'ceo' in title or 'chief executive' in title:
                    return officer.get('name')
        return None
    
    def _extract_founded_year(self, info: Dict) -> int:
        """Extract founded year from longBusinessSummary using regex"""
        import re
        summary = info.get('longBusinessSummary') or ''
        # Common patterns: "founded in 1976", "was founded in 1976", "incorporated in 2003"
        patterns = [
            r'founded (?:in )?(\d{4})',
            r'incorporated (?:in )?(\d{4})',
            r'established (?:in )?(\d{4})'
        ]
        for pattern in patterns:
            match = re.search(pattern, summary, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                # Sanity check: year should be between 1800 and current year
                if 1800 <= year <= 2030:
                    return year
        return None
    
    def map_daily_prices(self, stock_id: int, processed_data: pd.DataFrame) -> List[Dict]:
        """
        Map historical price data to daily_price_data table
        
        Args:
            stock_id: Stock ID from stocks table
            processed_data: DataFrame with OHLCV data
            
        Returns:
            List of dicts ready for daily_price_data table
        """
        try:
            records = []
            
            for idx, row in processed_data.iterrows():
                # Convert date to string format
                date_val = row['Date']
                if isinstance(date_val, pd.Timestamp):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)
                
                # Calculate daily return if we have previous close
                daily_return = None
                price_change = None
                
                # Find the previous row's index in the DataFrame
                if len(records) > 0:  # If we have a previous record
                    prev_close = records[-1].get('close_price')  # Get from last processed record
                    curr_close = row.get('Close')
                    if pd.notna(prev_close) and pd.notna(curr_close) and prev_close > 0:
                        daily_return = ((curr_close - prev_close) / prev_close) * 100
                        price_change = curr_close - prev_close
                
                record = {
                    'stock_id': stock_id,
                    'date': date_str,
                    'open_price': float(row['Open']) if pd.notna(row.get('Open')) else None,
                    'high_price': float(row['High']) if pd.notna(row.get('High')) else None,
                    'low_price': float(row['Low']) if pd.notna(row.get('Low')) else None,
                    'close_price': float(row['Close']) if pd.notna(row.get('Close')) else None,
                    'adjusted_close': float(row.get('Adj Close', row['Close'])) if pd.notna(row.get('Adj Close', row.get('Close'))) else None,
                    'volume': int(row['Volume']) if pd.notna(row.get('Volume')) else None,
                    'daily_return_pct': float(daily_return) if daily_return is not None else None,
                    'price_change': float(price_change) if price_change is not None else None,
                }
                
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error mapping daily prices: {e}")
            raise
    
    def map_technical_indicators(self, stock_id: int, processed_data: pd.DataFrame) -> List[Dict]:
        """
        Map technical indicators to technical_indicators table
        
        Args:
            stock_id: Stock ID from stocks table
            processed_data: DataFrame with technical indicators
            
        Returns:
            List of dicts ready for technical_indicators table
        """
        try:
            records = []
            
            for _, row in processed_data.iterrows():
                # Convert date
                date_val = row['Date']
                if isinstance(date_val, pd.Timestamp):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)
                
                record = {
                    'stock_id': stock_id,
                    'date': date_str,
                    
                    # Trend Indicators (SMAs)
                    'sma_7': float(row.get('MA_7')) if pd.notna(row.get('MA_7')) else None,
                    'sma_20': float(row.get('MA_20')) if pd.notna(row.get('MA_20')) else None,
                    'sma_50': float(row.get('MA_50')) if pd.notna(row.get('MA_50')) else None,
                    'sma_100': float(row.get('MA_100')) if pd.notna(row.get('MA_100')) else None,
                    'sma_200': float(row.get('MA_200')) if pd.notna(row.get('MA_200')) else None,
                    'ema_12': float(row.get('EMA_12')) if pd.notna(row.get('EMA_12')) else None,
                    'ema_26': float(row.get('EMA_26')) if pd.notna(row.get('EMA_26')) else None,
                    
                    # Momentum
                    'rsi_14': float(row.get('RSI')) if pd.notna(row.get('RSI')) else None,
                    'macd_line': float(row.get('MACD')) if pd.notna(row.get('MACD')) else None,
                    'macd_signal': float(row.get('MACD_Signal')) if pd.notna(row.get('MACD_Signal')) else None,
                    'macd_histogram': float(row.get('MACD_Histogram')) if pd.notna(row.get('MACD_Histogram')) else None,
                    'stochastic_osc': float(row.get('Stochastic_K')) if pd.notna(row.get('Stochastic_K')) else None,
                    
                    # Volatility (Bollinger Bands + ATR)
                    'bb_upper': float(row.get('BB_Upper')) if pd.notna(row.get('BB_Upper')) else None,
                    'bb_middle': float(row.get('BB_Middle')) if pd.notna(row.get('BB_Middle')) else None,
                    'bb_lower': float(row.get('BB_Lower')) if pd.notna(row.get('BB_Lower')) else None,
                    'atr_14': float(row.get('ATR')) if pd.notna(row.get('ATR')) else None,
                    'volatility_7d': float(row.get('Volatility_7')) if pd.notna(row.get('Volatility_7')) else None,
                    'volatility_30d_annual': float(row.get('Volatility_30d')) if pd.notna(row.get('Volatility_30d')) else None,
                    
                    # Volume
                    'volume_sma_20': int(row.get('Volume_SMA_20')) if pd.notna(row.get('Volume_SMA_20')) else None,
                    'obv': float(row.get('OBV')) if pd.notna(row.get('OBV')) else None,
                    'green_days_count': int(row.get('Green_Days_Count')) if pd.notna(row.get('Green_Days_Count')) else None,
                    
                    # Support & Resistance
                    'support_30d': float(row.get('Support_30D')) if pd.notna(row.get('Support_30D')) else None,
                    'resistance_30d': float(row.get('Resistance_30D')) if pd.notna(row.get('Resistance_30D')) else None,
                    
                    # ADX
                    'adx': float(row.get('ADX')) if pd.notna(row.get('ADX')) else None,
                }
                
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error mapping technical indicators: {e}")
            raise
    
    def map_forecast_data(self, stock_id: int, forecast_df: pd.DataFrame, info: Dict) -> List[Dict]:
        """
        Map forecast data to forecast_data table
        
        Args:
            stock_id: Stock ID from stocks table
            forecast_df: Prophet forecast DataFrame (aggregated format with Period, Low, Average, High)
            info: yfinance info dict (not used - analyst data moved to separate table)
            
        Returns:
            List of dicts ready for forecast_data table (12 monthly records)
        """
        try:
            records = []
            
            if forecast_df is None or forecast_df.empty:
                return records
            
            # The forecast_df from pipeline has columns: Period, Low, Average, High
            # Create one record per month (skip first row if it's current month, take next 12)
            forecast_date = datetime.now().strftime('%Y-%m-%d')
            
            # Take up to 12 months of forecast (excluding current month which is row 0)
            forecast_months = forecast_df.iloc[1:13] if len(forecast_df) > 1 else forecast_df
            
            for idx, row in forecast_months.iterrows():
                # Calculate forecast period in days from now
                try:
                    period_date = pd.to_datetime(row['Period'], format='%Y-%m')
                    days_ahead = (period_date - pd.Timestamp(datetime.now())).days
                except:
                    days_ahead = (idx + 1) * 30  # Approximate
                
                record = {
                    'stock_id': stock_id,
                    'forecast_date': forecast_date,  # When forecast was generated
                    'forecast_period': max(30, days_ahead),  # Days ahead
                    
                    # Prophet Forecast Prices for this month (varies by month).
                    # forecast_price_1y stores the Prophet upper-band (High) for the
                    # nearest monthly period — it is NOT a discrete 1-year price target.
                    # The query layer exposes this as forecast_price_high.
                    'forecast_price_1y': float(row['High']) if pd.notna(row['High']) else None,
                    'forecast_avg_price': float(row['Average']) if pd.notna(row['Average']) else None,
                    'forecast_range_width': float(row['High'] - row['Low']) if pd.notna(row['High']) and pd.notna(row['Low']) else None,
                }
                
                records.append(record)
            
            logger.info(f"Created {len(records)} monthly forecast records")
            return records
            
        except Exception as e:
            logger.error(f"Error mapping forecast data: {e}")
            logger.exception("Full traceback:")
            raise
    
    def map_analyst_data(self, stock_id: int, info: Dict) -> Dict:
        """
        Map analyst information to analyst_data table
        
        Args:
            stock_id: Stock ID from stocks table
            info: yfinance info dict with analyst targets
            
        Returns:
            Dict ready for analyst_data table (one record per stock)
        """
        try:
            # Get analyst target prices
            target_price_mean = float(info.get('targetMeanPrice')) if info.get('targetMeanPrice') else None
            target_price_median = float(info.get('targetMedianPrice')) if info.get('targetMedianPrice') else None
            target_price_high = float(info.get('targetHighPrice')) if info.get('targetHighPrice') else None
            target_price_low = float(info.get('targetLowPrice')) if info.get('targetLowPrice') else None
            analyst_rating = info.get('recommendationKey')
            analyst_count = int(info.get('numberOfAnalystOpinions')) if info.get('numberOfAnalystOpinions') else None
            
            # Get earnings date (convert to US Eastern Time for correct date)
            next_earnings_date = None
            if 'earningsTimestamp' in info and info['earningsTimestamp']:
                try:
                    from datetime import datetime as dt
                    import pytz
                    # Convert timestamp to US Eastern Time
                    utc_time = dt.utcfromtimestamp(info['earningsTimestamp']).replace(tzinfo=pytz.UTC)
                    eastern = pytz.timezone('US/Eastern')
                    eastern_time = utc_time.astimezone(eastern)
                    next_earnings_date = eastern_time.strftime('%Y-%m-%d')
                except:
                    # Fallback to simple conversion if pytz not available
                    try:
                        from datetime import datetime as dt
                        next_earnings_date = dt.fromtimestamp(info['earningsTimestamp']).strftime('%Y-%m-%d')
                    except:
                        pass
            
            record = {
                'stock_id': stock_id,
                'target_price_mean': target_price_mean,
                'target_price_median': target_price_median,
                'target_price_high': target_price_high,
                'target_price_low': target_price_low,
                'analyst_rating': analyst_rating,
                'analyst_count': analyst_count,
                'next_earnings_date': next_earnings_date,
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping analyst data: {e}")
            raise
    
    def map_fundamental_data(self, stock_id: int, info: Dict, balance_sheet: pd.DataFrame = None, financials: pd.DataFrame = None) -> Dict:
        """
        Map fundamental metrics to fundamental_data table
        
        Args:
            stock_id: Stock ID from stocks table
            info: yfinance info dict
            balance_sheet: Balance sheet DataFrame from yfinance
            financials: Income statement DataFrame from yfinance
            
        Returns:
            Dict ready for fundamental_data table
        """
        try:
            # Calculate additional metrics
            # Price to Free Cash Flow
            market_cap = safe_float_conversion(info.get('marketCap'))
            free_cash_flow = safe_float_conversion(info.get('freeCashflow'))
            price_to_fcf = safe_float_conversion(market_cap / free_cash_flow) if market_cap and free_cash_flow and free_cash_flow > 0 else None
            
            record = {
                'stock_id': stock_id,
                'period_date': datetime.now().strftime('%Y-%m-%d'),
                'period_type': 'TTM',  # Trailing Twelve Months
                
                # Valuation
                'pe_ratio': safe_float_conversion(info.get('trailingPE')),
                'pe_forward': safe_float_conversion(info.get('forwardPE')),
                'price_to_sales': safe_float_conversion(info.get('priceToSalesTrailing12Months')),
                'price_to_book': safe_float_conversion(info.get('priceToBook')),
                'price_to_fcf': price_to_fcf,
                'ev_to_revenue': safe_float_conversion(info.get('enterpriseToRevenue')),
                'ev_to_ebitda': safe_float_conversion(info.get('enterpriseToEbitda')),
                
                # Profitability
                'net_margin': safe_float_conversion(info.get('profitMargins')),
                'operating_margin': safe_float_conversion(info.get('operatingMargins')),
                'gross_margin': safe_float_conversion(info.get('grossMargins')),
                'ebitda_margin': safe_float_conversion(info.get('ebitdaMargins')),
                'roe': safe_float_conversion(info.get('returnOnEquity')),
                'roa': safe_float_conversion(info.get('returnOnAssets')),
                
                # Financial Health
                'debt_to_equity': safe_float_conversion(info.get('debtToEquity')),
                'total_cash': safe_float_conversion(info.get('totalCash')),
                'total_debt': safe_float_conversion(info.get('totalDebt')),
                'free_cash_flow': safe_float_conversion(info.get('freeCashflow')),
                'operating_cash_flow': safe_float_conversion(info.get('operatingCashflow')),
                'current_ratio': safe_float_conversion(info.get('currentRatio')),
                'quick_ratio': safe_float_conversion(info.get('quickRatio')),
                
                # Growth
                'revenue_ttm': safe_float_conversion(info.get('totalRevenue')),
                'revenue_growth_yoy': safe_float_conversion(info.get('revenueGrowth')),
                'net_income_ttm': safe_float_conversion(info.get('netIncomeToCommon')),
                'earnings_growth_yoy': safe_float_conversion(info.get('earningsGrowth')),
                'ebitda_ttm': safe_float_conversion(info.get('ebitda')),
                'gross_profit_ttm': safe_float_conversion(info.get('grossProfits')),
            }
            
            # Calculate efficiency metrics from financial statements
            self._add_efficiency_metrics(record, info, balance_sheet, financials)
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping fundamental data: {e}")
            raise
    
    def map_quarterly_fundamental_data(self, stock_id: int, quarterly_data_result: Dict) -> List[Dict]:
        """
        Map quarterly fundamental metrics to fundamental_data table
        
        Args:
            stock_id: Stock ID from stocks table
            quarterly_data_result: Result from extract_quarterly_earnings_data
            
        Returns:
            List of dicts ready for fundamental_data table
        """
        try:
            records = []
            
            # extract_quarterly_earnings_data returns: 
            # {'quarterly_data': { 'Q1': {...}, 'Q2': ...}, 'growth_metrics': ..., 'ticker': ...}
            
            if not quarterly_data_result or 'quarterly_data' not in quarterly_data_result:
                return []
                
            quarterly_data = quarterly_data_result['quarterly_data']
            
            for q_key, data in quarterly_data.items():
                if not data or 'date' not in data:
                    continue
                
                # Check if we have valid raw values to store
                # We need at least Revenue or Net Income to make a meaningful record
                if 'Total Revenue_raw' not in data and 'Net Income_raw' not in data:
                    continue
                    
                # Parse date - data['date'] is like "2025-Q3" or "2025-06-30"
                # For the database period_date, we prefer the actual end date
                period_date = data.get('quarter_end')
                
                # If quarter_end is a Timestamp, format it
                if hasattr(period_date, 'strftime'):
                    period_date_str = period_date.strftime('%Y-%m-%d')
                else:
                    # Fallback to current date or try to parse 'date' field if it looks like a date
                    # But 'date' field from extract_quarterly... might be "2025-Q3" which isn't a valid date column value
                    # If we don't have a specific date, we skip to avoid database errors
                    continue

                record = {
                    'stock_id': stock_id,
                    'period_date': period_date_str,
                    'period_type': 'Q',
                    
                    # Direct Financials (using _raw values from analysis script)
                    'revenue_ttm': safe_float_conversion(data.get('Total Revenue_raw')),
                    'net_income_ttm': safe_float_conversion(data.get('Net Income_raw')), # reusing column for quarterly net income
                    'gross_profit_ttm': safe_float_conversion(data.get('Gross Profit_raw')), # reusing column
                    'operating_income': safe_float_conversion(data.get('Operating Income_raw')),
                     # Note: EPS is ratio, no need for _raw usually, but let's check analysis script
                    'eps_diluted': safe_float_conversion(data.get('Diluted EPS_raw')) if data.get('Diluted EPS_raw') else (safe_float_conversion(data.get('Diluted EPS')) if data.get('Diluted EPS') and isinstance(data.get('Diluted EPS'), (int, float)) else None),
                    'eps_basic': safe_float_conversion(data.get('Basic EPS_raw')) if data.get('Basic EPS_raw') else (safe_float_conversion(data.get('Basic EPS')) if data.get('Basic EPS') and isinstance(data.get('Basic EPS'), (int, float)) else None),
                    
                    # Calculated Margins
                    'gross_margin': safe_float_conversion(data.get('Gross Margin_raw')),
                }
                
                # Calculate Net Margin if possible
                if record['net_income_ttm'] is not None and record['revenue_ttm'] is not None and record['revenue_ttm'] != 0:
                    record['net_margin'] = safe_float_conversion(record['net_income_ttm'] / record['revenue_ttm'])
                    
                # Calculate Operating Margin if possible
                if record.get('operating_income') is not None and record['revenue_ttm'] is not None and record['revenue_ttm'] != 0:
                    record['operating_margin'] = safe_float_conversion(record['operating_income'] / record['revenue_ttm'])
                
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error mapping quarterly fundamental data: {e}")
            raise
    
    def map_peer_comparison_data(self, stock_id: int, peer_data: Dict, target_ticker: str) -> List[Dict]:
        """
        Map peer comparison data to peer_comparison_data table
        
        Args:
            stock_id: Stock ID from stocks table
            peer_data: Dict from get_peer_comparison_data {ticker: {metrics}}
            target_ticker: The primary stock ticker
            
        Returns:
            List of dicts ready for peer_comparison_data table
        """
        try:
            records = []
            
            if not peer_data:
                return []
            
            for ticker, metrics in peer_data.items():
                if not metrics:
                    continue
                
                # Parse 52-week range
                week_52_high = None
                week_52_low = None
                week_52_range = metrics.get('52-Week Range', '')
                if week_52_range and week_52_range != 'N/A' and ' - ' in str(week_52_range):
                    try:
                        low_str, high_str = str(week_52_range).split(' - ')
                        week_52_low = float(low_str.strip())
                        week_52_high = float(high_str.strip())
                    except:
                        pass
                
                # Helper to convert metric values (handles NaN and Infinity)
                def to_float(value):
                    if isinstance(value, str) and 'ETF' in value:
                        return None
                    return safe_float_conversion(value)
                
                record = {
                    'stock_id': stock_id,
                    'peer_ticker': ticker.upper(),
                    'is_target': ticker.upper() == target_ticker.upper(),
                    'market_cap': to_float(metrics.get('Market Cap')),
                    'pe_ratio': to_float(metrics.get('P/E Ratio')),
                    'revenue_growth': to_float(metrics.get('Revenue Growth')),
                    'net_margin': to_float(metrics.get('Net Margin')),
                    'eps': to_float(metrics.get('EPS')),
                    'roe': to_float(metrics.get('ROE')),
                    'debt_to_equity': to_float(metrics.get('Debt-to-Equity')),
                    'dividend_yield': to_float(metrics.get('Dividend Yield')),
                    'week_52_high': week_52_high,
                    'week_52_low': week_52_low,
                }
                
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error mapping peer comparison data: {e}")
            raise
    
    def _add_efficiency_metrics(self, record: Dict, info: Dict, balance_sheet: pd.DataFrame, financials: pd.DataFrame):
        """
        Calculate and add efficiency metrics to fundamental record
        """
        try:
            # Get PEG Ratio (trailingPegRatio is what yfinance actually provides)
            record['peg_ratio'] = safe_float_conversion(info.get('trailingPegRatio'))
            
            # Calculate ROIC from balance sheet (yfinance doesn't provide it in info)
            roic = None
            net_income = safe_float_conversion(info.get('netIncomeToCommon'))
            if balance_sheet is not None and not balance_sheet.empty and net_income:
                try:
                    recent_period = balance_sheet.columns[0]
                    if 'Invested Capital' in balance_sheet.index:
                        invested_capital = safe_float_conversion(balance_sheet.loc['Invested Capital', recent_period])
                        if invested_capital and invested_capital != 0:
                            roic = safe_float_conversion(net_income / invested_capital)
                except Exception as e:
                    logger.debug(f"Error calculating ROIC: {e}")
            
            record['roic'] = roic
            
            # Get basic data for calculations
            total_revenue = safe_float_conversion(info.get('totalRevenue'))
            
            # Extract data from balance sheet
            total_assets = None
            inventory = None
            receivables = None
            accounts_payable = None
            working_capital = None
            
            if balance_sheet is not None and not balance_sheet.empty:
                try:
                    recent_period = balance_sheet.columns[0]
                    
                    if 'Total Assets' in balance_sheet.index:
                        total_assets = safe_float_conversion(balance_sheet.loc['Total Assets', recent_period])
                    
                    if 'Inventory' in balance_sheet.index:
                        inventory = safe_float_conversion(balance_sheet.loc['Inventory', recent_period])
                    
                    if 'Accounts Receivable' in balance_sheet.index:
                        receivables = safe_float_conversion(balance_sheet.loc['Accounts Receivable', recent_period])
                    elif 'Receivables' in balance_sheet.index:
                        receivables = safe_float_conversion(balance_sheet.loc['Receivables', recent_period])
                    
                    if 'Accounts Payable' in balance_sheet.index:
                        accounts_payable = safe_float_conversion(balance_sheet.loc['Accounts Payable', recent_period])
                    elif 'Payables' in balance_sheet.index:
                        accounts_payable = safe_float_conversion(balance_sheet.loc['Payables', recent_period])
                    
                    if 'Working Capital' in balance_sheet.index:
                        working_capital = safe_float_conversion(balance_sheet.loc['Working Capital', recent_period])
                except Exception as e:
                    logger.debug(f"Error extracting balance sheet data: {e}")
            
            # Extract cost of revenue from income statement
            cost_of_revenue = None
            if financials is not None and not financials.empty:
                try:
                    recent_period = financials.columns[0]
                    if 'Cost Of Revenue' in financials.index:
                        cost_of_revenue = safe_float_conversion(financials.loc['Cost Of Revenue', recent_period])
                except Exception as e:
                    logger.debug(f"Error extracting income statement data: {e}")
            
            # Calculate Asset Turnover = Revenue / Total Assets
            if total_revenue and total_assets and total_assets != 0:
                record['asset_turnover'] = safe_float_conversion(total_revenue / total_assets)
            else:
                record['asset_turnover'] = None
            
            # Calculate Inventory Turnover = COGS / Inventory
            if cost_of_revenue and inventory and inventory != 0:
                record['inventory_turnover'] = safe_float_conversion(cost_of_revenue / inventory)
            else:
                record['inventory_turnover'] = None
            
            # Calculate Receivables Turnover = Revenue / Receivables
            if total_revenue and receivables and receivables != 0:
                record['receivables_turnover'] = safe_float_conversion(total_revenue / receivables)
            else:
                record['receivables_turnover'] = None
            
            # Calculate Working Capital Turnover = Revenue / Working Capital
            if total_revenue and working_capital and working_capital != 0:
                record['working_capital_turnover'] = safe_float_conversion(total_revenue / working_capital)
            else:
                record['working_capital_turnover'] = None
            
            # Calculate Days Sales Outstanding (DSO) = 365 / Receivables Turnover
            if record.get('receivables_turnover'):
                record['dso'] = safe_float_conversion(365 / record['receivables_turnover'])
            else:
                record['dso'] = None
            
            # Calculate Days Inventory Outstanding (DIO) = 365 / Inventory Turnover
            if record.get('inventory_turnover'):
                record['dio'] = safe_float_conversion(365 / record['inventory_turnover'])
            else:
                record['dio'] = None
            
            # Calculate Days Payables Outstanding (DPO) = 365 / (COGS / Accounts Payable)
            # DPO = (Accounts Payable / COGS) * 365
            dpo = None
            if cost_of_revenue and accounts_payable and cost_of_revenue != 0:
                dpo = safe_float_conversion((accounts_payable / cost_of_revenue) * 365)
            
            # Calculate Cash Conversion Cycle (CCC) = DSO + DIO - DPO
            # This measures how long it takes to convert cash investments in inventory back to cash
            if record.get('dio') and record.get('dso'):
                if dpo is not None:
                    # Complete CCC formula with DPO
                    record['ccc'] = safe_float_conversion(record['dio'] + record['dso'] - dpo)
                else:
                    # Partial CCC without DPO (still useful but incomplete)
                    record['ccc'] = float(record['dio'] + record['dso'])
            else:
                record['ccc'] = None
                
        except Exception as e:
            logger.warning(f"Error calculating efficiency metrics: {e}")
            # Ensure all fields have None if calculation fails
            for field in ['peg_ratio', 'roic', 'asset_turnover', 'inventory_turnover', 
                         'receivables_turnover', 'working_capital_turnover', 'dso', 'dio', 'ccc']:
                if field not in record:
                    record[field] = None
    
    def map_risk_data(self, stock_id: int, processed_data: pd.DataFrame, info: Dict, 
                     risk_profile: Dict = None, market_data: pd.DataFrame = None, 
                     ticker: str = None) -> Dict:
        """
        Map risk metrics to risk_data table WITH METADATA (v2 Enhanced)
        
        Now includes all 64 metadata fields for complete transparency
        
        Args:
            stock_id: Stock ID from stocks table
            processed_data: DataFrame with returns data
            info: yfinance info dict
            risk_profile: Optional comprehensive risk profile from RiskAnalyzer
            market_data: Optional market benchmark data (S&P 500)
            ticker: Stock ticker symbol (for liquidity/Altman calculations)
            
        Returns:
            Dict ready for risk_data table (with all metadata)
        """
        try:
            from analysis_scripts.risk_analysis import RiskAnalyzer
            
            ra = RiskAnalyzer()
            
            # Use NEW enhanced method that returns metrics + metadata
            full_profile = ra.comprehensive_risk_profile_with_metadata(
                price_data=processed_data['Close'],
                market_data=market_data['Close'] if market_data is not None else None,
                ticker=ticker
            )
            
            metrics = full_profile.get('metrics', {})
            metadata = full_profile.get('metadata', {})
            
            # Build complete record with all fields
            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                
                # === BASE METRICS ===
                'var_95': safe_float_conversion(metrics.get('var_5')),
                'var_99': safe_float_conversion(metrics.get('var_1')),
                'cvar_95': safe_float_conversion(metrics.get('cvar_5')),
                'cvar_99': safe_float_conversion(metrics.get('cvar_1')),
                'sharpe_ratio': safe_float_conversion(metrics.get('sharpe_ratio')),
                'sortino_ratio': safe_float_conversion(metrics.get('sortino_ratio')),
                'calmar_ratio': None,  # TODO: implement
                'max_drawdown': safe_float_conversion(metrics.get('max_drawdown')),
                'beta': safe_float_conversion(metrics.get('beta')) if 'beta' in metrics else safe_float_conversion(info.get('beta')),
                'market_correlation': safe_float_conversion(metrics.get('correlation_market')),
                'volatility_30d_annual': safe_float_conversion(metrics.get('volatility_30d_annualized')),
                'volatility_historical_annual': safe_float_conversion(metrics.get('volatility_annualized')),
                'skewness': safe_float_conversion(metrics.get('skewness')),
                'kurtosis': safe_float_conversion(metrics.get('kurtosis')),
                
                # === ALL 64 METADATA FIELDS ===
                # VaR metadata
                'var_95_data_period_days': metadata.get('var_95_data_period_days'),
                'var_95_sample_size': metadata.get('var_95_sample_size'),
                'var_95_calculation_method': metadata.get('var_95_calculation_method'),
                'var_95_confidence_level': metadata.get('var_95_confidence_level'),
                'var_95_return_frequency': metadata.get('var_95_return_frequency'),
                'var_99_data_period_days': metadata.get('var_99_data_period_days'),
                'var_99_sample_size': metadata.get('var_99_sample_size'),
                'var_99_calculation_method': metadata.get('var_99_calculation_method'),
                'var_99_confidence_level': metadata.get('var_99_confidence_level'),
                'var_99_return_frequency': metadata.get('var_99_return_frequency'),
                
                # CVaR metadata
                'cvar_95_data_period_days': metadata.get('cvar_95_data_period_days'),
                'cvar_95_tail_size': metadata.get('cvar_95_tail_size'),
                'cvar_95_calculation_method': metadata.get('cvar_95_calculation_method'),
                'cvar_95_confidence_level': metadata.get('cvar_95_confidence_level'),
                'cvar_99_data_period_days': metadata.get('cvar_99_data_period_days'),
                'cvar_99_tail_size': metadata.get('cvar_99_tail_size'),
                'cvar_99_calculation_method': metadata.get('cvar_99_calculation_method'),
                'cvar_99_confidence_level': metadata.get('cvar_99_confidence_level'),
                
                # Volatility metadata
                'volatility_30d_sample_days': metadata.get('volatility_30d_sample_days'),
                'volatility_30d_calculation_method': metadata.get('volatility_30d_calculation_method'),
                'volatility_30d_annualization_factor': metadata.get('volatility_30d_annualization_factor'),
                'volatility_30d_return_frequency': metadata.get('volatility_30d_return_frequency'),
                'volatility_30d_model_type': metadata.get('volatility_30d_model_type'),
                'volatility_30d_fallback_logic': metadata.get('volatility_30d_fallback_logic'),
                'volatility_historical_sample_days': metadata.get('volatility_historical_sample_days'),
                'volatility_historical_calculation_method': metadata.get('volatility_historical_calculation_method'),
                'volatility_historical_annualization_factor': metadata.get('volatility_historical_annualization_factor'),
                'volatility_historical_return_frequency': metadata.get('volatility_historical_return_frequency'),
                'volatility_historical_model_type': metadata.get('volatility_historical_model_type'),
                'volatility_trading_days_annual': metadata.get('volatility_trading_days_annual'),
                
                # Liquidity metadata
                'liquidity_calculation_method': metadata.get('liquidity_calculation_method'),
                'liquidity_data_period_days': metadata.get('liquidity_data_period_days'),
                'liquidity_actual_sample_days': metadata.get('liquidity_actual_sample_days'),
                'liquidity_volume_weight': metadata.get('liquidity_volume_weight'),
                'liquidity_volume_benchmark': metadata.get('liquidity_volume_benchmark'),
                'liquidity_mcap_weight': metadata.get('liquidity_mcap_weight'),
                'liquidity_mcap_benchmark': metadata.get('liquidity_mcap_benchmark'),
                'liquidity_stability_weight': metadata.get('liquidity_stability_weight'),
                'liquidity_stability_metric': metadata.get('liquidity_stability_metric'),
                'liquidity_data_freshness': metadata.get('liquidity_data_freshness'),
                'liquidity_minimum_required_days': metadata.get('liquidity_minimum_required_days'),
                'liquidity_sufficient_data': metadata.get('liquidity_sufficient_data'),
                
                # Altman metadata
                'altman_calculation_method': metadata.get('altman_calculation_method'),
                'altman_financial_period': metadata.get('altman_financial_period'),
                'altman_financial_period_end_date': metadata.get('altman_financial_period_end_date'),
                'altman_financial_data_source': metadata.get('altman_financial_data_source'),
                'altman_data_age_days': metadata.get('altman_data_age_days'),
                'altman_filing_type': metadata.get('altman_filing_type'),
                'altman_required_fields_count': metadata.get('altman_required_fields_count'),
                'altman_available_fields_count': metadata.get('altman_available_fields_count'),
                'altman_data_completeness_percent': metadata.get('altman_data_completeness_percent'),
                'altman_minimum_completeness_percent': metadata.get('altman_minimum_completeness_percent'),
                'altman_retained_earnings_imputed': metadata.get('altman_retained_earnings_imputed'),
                'altman_imputation_method': metadata.get('altman_imputation_method'),
                'altman_next_update_expected': metadata.get('altman_next_update_expected'),
                'altman_coefficient_a': metadata.get('altman_coefficient_a'),
                'altman_coefficient_b': metadata.get('altman_coefficient_b'),
                'altman_coefficient_c': metadata.get('altman_coefficient_c'),
                'altman_coefficient_d': metadata.get('altman_coefficient_d'),
                'altman_coefficient_e': metadata.get('altman_coefficient_e'),
                
                # Sharpe/Sortino metadata
                'sharpe_ratio_calculation_method': metadata.get('sharpe_ratio_calculation_method'),
                'sharpe_ratio_data_period_days': metadata.get('sharpe_ratio_data_period_days'),
                'sharpe_ratio_risk_free_rate_used': metadata.get('sharpe_ratio_risk_free_rate_used'),
                'sharpe_ratio_risk_free_rate_source': metadata.get('sharpe_ratio_risk_free_rate_source'),
                'sharpe_ratio_annualization_factor': metadata.get('sharpe_ratio_annualization_factor'),
                'sharpe_ratio_daily_rf_rate': metadata.get('sharpe_ratio_daily_rf_rate'),
                'sortino_ratio_calculation_method': metadata.get('sortino_ratio_calculation_method'),
                'sortino_ratio_data_period_days': metadata.get('sortino_ratio_data_period_days'),
                'sortino_ratio_annualization_factor': metadata.get('sortino_ratio_annualization_factor'),
                'sortino_ratio_downside_focus': metadata.get('sortino_ratio_downside_focus'),
                
                # Other metrics metadata
                'max_drawdown_calculation_method': metadata.get('max_drawdown_calculation_method'),
                'max_drawdown_data_period_days': metadata.get('max_drawdown_data_period_days'),
                'max_drawdown_definition': metadata.get('max_drawdown_definition'),
                'beta_calculation_method': metadata.get('beta_calculation_method'),
                'beta_data_period_days': metadata.get('beta_data_period_days'),
                'beta_market_benchmark': metadata.get('beta_market_benchmark'),
                'beta_return_frequency': metadata.get('beta_return_frequency'),
                'correlation_calculation_method': metadata.get('correlation_calculation_method'),
                'correlation_data_period_days': metadata.get('correlation_data_period_days'),
                'correlation_market_benchmark': metadata.get('correlation_market_benchmark'),
                'skewness_calculation_method': metadata.get('skewness_calculation_method'),
                'skewness_data_period_days': metadata.get('skewness_data_period_days'),
                'skewness_interpretation': metadata.get('skewness_interpretation'),
                'kurtosis_calculation_method': metadata.get('kurtosis_calculation_method'),
                'kurtosis_data_period_days': metadata.get('kurtosis_data_period_days'),
                
                # Confidence scores
                'var_estimation_confidence': metadata.get('var_estimation_confidence'),
                'volatility_estimation_confidence': metadata.get('volatility_estimation_confidence'),
                'liquidity_estimation_confidence': metadata.get('liquidity_estimation_confidence'),
                'altman_estimation_confidence': metadata.get('altman_estimation_confidence'),
                'sharpe_estimation_confidence': metadata.get('sharpe_estimation_confidence'),
                'overall_profile_confidence': metadata.get('overall_profile_confidence'),
                'has_data_gaps': metadata.get('has_data_gaps'),
                'missing_price_data': metadata.get('missing_price_data'),
                'missing_financial_data': metadata.get('missing_financial_data'),
                'insufficient_liquidity_data': metadata.get('insufficient_liquidity_data'),
                'data_quality_score': metadata.get('data_quality_score'),
                
                # Tracking
                'metadata_calculation_timestamp': metadata.get('metadata_calculation_timestamp'),
                'metadata_version': metadata.get('metadata_version'),
                'risk_profile_calculation_method': metadata.get('risk_profile_calculation_method'),
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping risk data: {e}")
            raise
    
    def map_market_snapshot(self, stock_id: int, current_price: Dict, info: Dict, 
                           processed_data: pd.DataFrame) -> Dict:
        """
        Map market snapshot to market_price_snapshot table
        
        Args:
            stock_id: Stock ID from stocks table
            current_price: Current price info from fetch_real_time_data
            info: yfinance info dict
            processed_data: Historical data for performance calculations
            
        Returns:
            Dict ready for market_price_snapshot table
        """
        def cap_percentage(value, max_val=9999.99):
            """Cap percentage values to avoid database overflow (NUMERIC(8,4) max is 9999.9999)"""
            if value is None:
                return None
            if abs(value) > max_val:
                return max_val if value > 0 else -max_val
            return value
        
        try:
            # Get the most recent close price (today's close or real-time price)
            current_close = None
            previous_close = None
            
            if not processed_data.empty and 'Close' in processed_data.columns:
                closes = processed_data['Close'].dropna()
                if len(closes) > 0:
                    current_close = float(closes.iloc[-1])  # Today's close
                if len(closes) > 1:
                    previous_close = float(closes.iloc[-2])  # Previous day's close for % calculation

            # Prefer real-time price when available; fallback to current close
            real_price = None
            if current_price and current_price.get('current_price') is not None:
                try:
                    real_price = float(current_price.get('current_price'))
                except (ValueError, TypeError):
                    real_price = None

            # Final published price (real-time if available, else today's close)
            published_price = real_price if real_price is not None else (current_close if current_close is not None else 0.0)

            # Compute price change relative to PREVIOUS day's close (not comparing to itself!)
            # Percentage change formula: (current - previous) / previous * 100
            if previous_close is not None and published_price is not None:
                price_change_val = published_price - previous_close
                # Use previous_close (previous day's price) as denominator for correct percentage
                change_pct_val = (price_change_val / previous_close * 100) if previous_close > 0 else None
            else:
                # Fall back to values from current_price dict if present
                price_change_val = current_price.get('change') if current_price else None
                change_pct_val = current_price.get('change_percent') if current_price else None

            # Use published_price for performance calculations (gives up-to-date snapshot)
            if not processed_data.empty and 'Close' in processed_data.columns:
                closes = processed_data['Close'].dropna()

                # 15-day change
                if len(closes) >= 15:
                    price_15d_ago = float(closes.iloc[-15])
                    change_15d_pct = ((published_price - price_15d_ago) / price_15d_ago * 100) if price_15d_ago > 0 else None
                else:
                    change_15d_pct = None

                # 52-week change
                if len(closes) >= 252:
                    price_52w_ago = float(closes.iloc[-252])
                    change_52w_pct = ((published_price - price_52w_ago) / price_52w_ago * 100) if price_52w_ago > 0 else None
                else:
                    change_52w_pct = None

                # 1-year performance
                if len(closes) >= 252:
                    price_1y_ago = float(closes.iloc[-252])
                    performance_1y_pct = ((published_price - price_1y_ago) / price_1y_ago * 100) if price_1y_ago > 0 else None
                else:
                    performance_1y_pct = None

                # Overall change (from start to now)
                first_price = float(closes.iloc[0])
                overall_pct_change = ((published_price - first_price) / first_price * 100) if first_price > 0 else None
            else:
                change_15d_pct = change_52w_pct = performance_1y_pct = overall_pct_change = None

            # Get macro indicators from processed_data
            interest_rate = None
            sp500_price = None
            if not processed_data.empty:
                latest_row = processed_data.iloc[-1]
                if 'Interest_Rate' in processed_data.columns:
                    interest_rate = float(latest_row['Interest_Rate']) if pd.notna(latest_row['Interest_Rate']) else None
                if 'SP500' in processed_data.columns:
                    sp500_price = float(latest_row['SP500']) if pd.notna(latest_row['SP500']) else None

            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),

                # Current Price & Changes (published_price is real-time when available)
                'current_price': float(published_price),
                'price_change': float(price_change_val) if price_change_val is not None else None,
                'change_pct': cap_percentage(change_pct_val),

                # Performance metrics (capped to avoid overflow)
                'change_15d_pct': cap_percentage(change_15d_pct),
                'change_52w_pct': cap_percentage(change_52w_pct),
                'performance_1y_pct': cap_percentage(performance_1y_pct),
                'overall_pct_change': cap_percentage(overall_pct_change),

                # 52 Week Range
                'high_52w': float(info.get('fiftyTwoWeekHigh')) if info.get('fiftyTwoWeekHigh') else None,
                'low_52w': float(info.get('fiftyTwoWeekLow')) if info.get('fiftyTwoWeekLow') else None,

                # Market Size
                'market_cap': float(info.get('marketCap')) if info.get('marketCap') else None,
                'enterprise_value': float(info.get('enterpriseValue')) if info.get('enterpriseValue') else None,
                'shares_outstanding': float(info.get('sharesOutstanding')) if info.get('sharesOutstanding') else None,
                # Fix float_shares validation - float MUST be <= outstanding
                'float_shares': (
                    float(info.get('floatShares')) if info.get('floatShares') and info.get('sharesOutstanding') and 
                    float(info.get('floatShares')) <= float(info.get('sharesOutstanding')) 
                    else (float(info.get('sharesOutstanding')) * 0.98 if info.get('sharesOutstanding') else None)
                ) if info.get('floatShares') else None,

                # Macro Context
                'interest_rate': interest_rate,
                'sp500_index': sp500_price,
            }

            return record

        except Exception as e:
            logger.error(f"Error mapping market snapshot: {e}")
            raise
    
    def _format_dividend_yield(self, raw_yield):
        """
        Format dividend yield data with proper validation and correction.
        
        Args:
            raw_yield: Raw yield value from yfinance (may be decimal or percentage)
            
        Returns:
            Properly formatted yield as decimal (0.0259 for 2.59%)
        """
        if raw_yield is None or raw_yield == 0:
            return None
            
        # Convert to float and handle edge cases
        try:
            yield_value = float(raw_yield)
        except (ValueError, TypeError):
            return None
            
        # Validation: yields should be reasonable (0-50%)
        # If raw value is > 1, it might already be a percentage
        if yield_value > 1:
            # Assume it's already a percentage, convert to decimal
            corrected_yield = yield_value / 100
        else:
            # Assume it's already a decimal
            corrected_yield = yield_value
            
        # Final validation: yields above 50% are suspicious
        if corrected_yield > 0.50:  # More than 50%
            # Log warning and return None for manual review
            logger.warning(f"Suspicious dividend yield detected: {raw_yield} -> {corrected_yield*100:.2f}%")
            return None
            
        # Ensure we return a properly formatted decimal
        return corrected_yield if corrected_yield >= 0 else None
    
    def _format_transaction_price(self, raw_price):
        """
        Format insider transaction price with proper scaling detection and correction.
        
        Handles yfinance data where prices may come in incorrectly scaled (e.g., 36,007,160 
        instead of 36.01). Uses an intelligent threshold to detect and correct the scaling.
        
        Args:
            raw_price: Raw price value from yfinance
            
        Returns:
            Properly formatted price as decimal (36.01)
        """
        if raw_price is None or raw_price == 0:
            return None
            
        try:
            price_value = float(raw_price)
        except (ValueError, TypeError):
            return None
        
        # Validation: prices should be reasonable (typically $0.01 to $50,000)
        # Stocks rarely trade above $50,000 per share
        # If price > 50,000, it's likely scaled incorrectly (off by 1M factor)
        if price_value > 50000:
            # Scale down by dividing by 1,000,000
            # This converts micro-units or other scaling back to normal dollars
            corrected_price = price_value / 1000000
            logger.info(f"Transaction price scaled down: {price_value} -> {corrected_price:.2f}")
            return corrected_price
        elif price_value < 0.01:
            # Prices below $0.01 are suspicious (penny stocks are typically at least $0.01)
            logger.warning(f"Suspicious transaction price detected: {price_value}")
            return None
        
        return price_value
        
    def map_dividend_data(self, stock_id: int, info: Dict) -> Dict:
        """
        Map dividend info to dividend_data table
        
        Args:
            stock_id: Stock ID from stocks table
            info: yfinance info dict
            
        Returns:
            Dict ready for dividend_data table
        """
        try:
            # Helper function to convert timestamp to date string
            def convert_timestamp_to_date(timestamp):
                if timestamp is None:
                    return None
                try:
                    # If it's already a date string, return it
                    if isinstance(timestamp, str):
                        return timestamp
                    # If it's a timestamp (int), convert it
                    if isinstance(timestamp, (int, float)):
                        from datetime import datetime as dt
                        return dt.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    # If it's a datetime object, convert it
                    if hasattr(timestamp, 'strftime'):
                        return timestamp.strftime('%Y-%m-%d')
                    return None
                except:
                    return None
            
            # Helper function to parse split factor
            def parse_split_factor(split_factor):
                if split_factor is None:
                    return None
                try:
                    # If it's already a number, return it
                    if isinstance(split_factor, (int, float)):
                        return float(split_factor)
                    # If it's a string like "4:1", parse it
                    if isinstance(split_factor, str) and ':' in split_factor:
                        parts = split_factor.split(':')
                        if len(parts) == 2:
                            return float(parts[0]) / float(parts[1])
                    return None
                except:
                    return None
            
            record = {
                'stock_id': stock_id,
                
                # Dividend Info
                'dividend_rate': float(info.get('dividendRate')) if info.get('dividendRate') else None,
                'dividend_yield_pct': self._format_dividend_yield(info.get('dividendYield')),
                'payout_ratio': float(info.get('payoutRatio')) if info.get('payoutRatio') else None,
                'avg_dividend_yield_5y': self._format_dividend_yield(info.get('fiveYearAvgDividendYield')),
                'dividend_forward_rate': float(info.get('dividendRate')) if info.get('dividendRate') else None,
                'dividend_forward_yield': self._format_dividend_yield(info.get('dividendYield')),
                'dividend_trailing_rate': float(info.get('trailingAnnualDividendRate')) if info.get('trailingAnnualDividendRate') else None,
                'dividend_trailing_yield': self._format_dividend_yield(info.get('trailingAnnualDividendYield')),
                
                # Dates - convert timestamps to date strings
                'ex_dividend_date': convert_timestamp_to_date(info.get('exDividendDate')),
                'payment_date': convert_timestamp_to_date(info.get('dividendDate')),
                'last_split_date': convert_timestamp_to_date(info.get('lastSplitDate')),
                'last_split_factor': parse_split_factor(info.get('lastSplitFactor')),
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping dividend data: {e}")
            raise
    
    def map_ownership_data(self, stock_id: int, info: Dict) -> Dict:
        """
        Map ownership info to ownership_data table
        
        Args:
            stock_id: Stock ID from stocks table
            info: yfinance info dict
            
        Returns:
            Dict ready for ownership_data table
        """
        try:
            record = {
                'stock_id': stock_id,
                'report_date': datetime.now().strftime('%Y-%m-%d'),
                
                # Ownership percentages
                'insider_ownership_pct': float(info.get('heldPercentInsiders', 0) * 100) if info.get('heldPercentInsiders') else None,
                'institutional_ownership_pct': float(info.get('heldPercentInstitutions', 0) * 100) if info.get('heldPercentInstitutions') else None,
                
                # Short Selling
                'shares_short': float(info.get('sharesShort')) if info.get('sharesShort') else None,
                'short_ratio_days': float(info.get('shortRatio')) if info.get('shortRatio') else None,
                'short_pct_float': float(info.get('shortPercentOfFloat', 0) * 100) if info.get('shortPercentOfFloat') else None,
                'shares_short_prev': float(info.get('sharesShortPriorMonth')) if info.get('sharesShortPriorMonth') else None,
                
                # Dilution
                'shares_outstanding_diluted': float(info.get('sharesOutstanding')) if info.get('sharesOutstanding') else None,
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping ownership data: {e}")
            raise
    
    def map_sentiment_data(self, stock_id: int, news: List[Dict], info: Dict) -> Dict:
        """
        Map sentiment analysis to sentiment_data table
        
        Args:
            stock_id: Stock ID from stocks table
            news: News articles list
            info: yfinance info dict
            
        Returns:
            Dict ready for sentiment_data table
        """
        try:
            # Simple sentiment scoring based on analyst recommendations
            recommendation_key = info.get('recommendationKey', 'hold')
            
            sentiment_map = {
                'strong_buy': 0.8,
                'buy': 0.5,
                'hold': 0.0,
                'sell': -0.5,
                'strong_sell': -0.8
            }
            
            sentiment_score = sentiment_map.get(recommendation_key.lower().replace(' ', '_'), 0.0)
            
            # Determine label
            if sentiment_score > 0.3:
                sentiment_label = 'Bullish'
            elif sentiment_score < -0.3:
                sentiment_label = 'Bearish'
            else:
                sentiment_label = 'Neutral'
            
            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                
                # Overall Sentiment
                'sentiment_score': float(sentiment_score),
                'sentiment_label': sentiment_label,
                'sentiment_confidence': 0.7,  # Default confidence
                
                # Component Sentiments
                'analyst_sentiment': float(sentiment_score),
                
                # Note: news_sentiment, article_count, sentiment_trend columns
                # are not included as news sentiment analysis is not implemented
                # These columns should be removed from the database schema
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping sentiment data: {e}")
            raise
    
    def map_insider_transactions(self, stock_id: int, insider_df: pd.DataFrame) -> List[Dict]:
        """
        Map insider transactions to insider_transactions table
        
        Args:
            stock_id: Stock ID from stocks table
            insider_df: Insider transactions DataFrame from yfinance
            
        Returns:
            List of dicts ready for insider_transactions table
        """
        try:
            if insider_df is None or insider_df.empty:
                logger.warning("No insider transactions data available")
                return []
            
            records = []
            
            def safe_float(value, max_value=None):
                """Convert to float, handling NaN and Infinity"""
                try:
                    if pd.isna(value) or value is None:
                        return None
                    val = float(value)
                    # Check for infinity or NaN
                    if np.isinf(val) or np.isnan(val):
                        return None
                    # Apply max value cap if specified
                    if max_value is not None and abs(val) > max_value:
                        return max_value if val > 0 else -max_value
                    return val
                except (ValueError, TypeError):
                    return None
            
            for idx, row in insider_df.iterrows():
                # Handle different possible column names from yfinance
                transaction_date = None
                if 'Start Date' in row:
                    transaction_date = pd.to_datetime(row['Start Date']).strftime('%Y-%m-%d')
                elif 'Date' in row:
                    transaction_date = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
                elif isinstance(idx, (pd.Timestamp, datetime, date)):
                    transaction_date = pd.to_datetime(idx).strftime('%Y-%m-%d')
                
                if not transaction_date:
                    continue
                
                # Get shares with safe conversion (cap large values)
                shares = safe_float(row.get('Shares', row.get('#Shares')), max_value=999999999999999.0)
                
                # Get price and apply formatting to correct yfinance scaling issues
                raw_price = row.get('Value', row.get('Price'))
                price = self._format_transaction_price(raw_price)
                
                record = {
                    'stock_id': stock_id,
                    
                    # Insider Info
                    'insider_name': str(row.get('Insider', row.get('Name', 'Unknown'))),
                    'relation_to_company': str(row.get('Position', row.get('Relationship', 'Unknown'))),
                    
                    # Transaction Details
                    'transaction_date': transaction_date,
                    'shares_change': shares,
                    'transaction_price': price,
                }
                
                # Calculate estimated value if we have shares and price
                # Cap at 10^15 to avoid database numeric overflow (field is NUMERIC(18,2), max ~10^16)
                if shares is not None and price is not None and shares != 0:
                    estimated = abs(shares) * price
                    # Use safe_float with max value of 999999999999999 (10^15 - 1)
                    estimated_safe = safe_float(estimated, max_value=999999999999999.0)
                    if estimated_safe is not None:
                        record['estimated_value'] = estimated_safe
                
                records.append(record)
            
            logger.info(f"Mapped {len(records)} insider transactions")
            return records
            
        except Exception as e:
            logger.error(f"Error mapping insider transactions: {e}")
            logger.exception("Full traceback:")
            return []
    
    def create_sync_log(self, stock_id: int, sync_type: str, sync_status: str, 
                       error_message: str = None, sync_duration: int = 0) -> Dict:
        """
        Create sync log entry for data_sync_log table
        
        Args:
            stock_id: Stock ID from stocks table
            sync_type: Type of sync (daily, weekly, full_history)
            sync_status: Status (success, partial, failed)
            error_message: Error message if failed
            sync_duration: Duration in seconds
            
        Returns:
            Dict ready for data_sync_log table
        """
        try:
            record = {
                'stock_id': stock_id,
                'sync_type': sync_type,
                'sync_date': datetime.now().isoformat(),
                
                # Sync Statistics
                'records_inserted': self.sync_stats['records_inserted'],
                'records_updated': self.sync_stats['records_updated'],
                'records_failed': self.sync_stats['records_failed'],
                
                # Status and Errors
                'sync_status': sync_status,
                'error_message': error_message,
                
                # Duration
                'sync_duration_seconds': sync_duration,
                'data_quality_score': 1.0 if sync_status == 'success' else 0.5,
                
                # Metadata
                'source_api': 'yfinance',
                'api_version': '0.2.x',
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error creating sync log: {e}")
            raise
    
    def reset_sync_stats(self):
        """Reset sync statistics"""
        self.sync_stats = {
            'records_inserted': 0,
            'records_updated': 0,
            'records_failed': 0
        }
    
    # ========================================================================
    # ADVANCED RISK METRICS MAPPING
    # ========================================================================
    
    def map_liquidity_risk_data(self, stock_id: int, risk_profile: Dict) -> Optional[Dict]:
        """
        Map liquidity risk metrics to liquidity_risk_data table
        
        Args:
            stock_id: Stock ID from stocks table
            risk_profile: Comprehensive risk profile from RiskAnalyzer
            
        Returns:
            Dict ready for liquidity_risk_data table or None if data unavailable
        """
        try:
            # Check if liquidity data exists in risk profile
            if not risk_profile or 'liquidity_score' not in risk_profile:
                return None
            
            liquidity_score = risk_profile.get('liquidity_score')
            if liquidity_score is None:
                return None
            
            # Extract liquidity components
            components = risk_profile.get('liquidity_components', {})
            
            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                
                # Core Metrics
                'liquidity_score': safe_float_conversion(liquidity_score, max_value=100),
                'risk_level': risk_profile.get('liquidity_risk_level', 'Unknown'),
                
                # Component Analysis
                # Note: RiskAnalyzer returns mcap_component, volume_component, stability_component
                # bid_ask_spread removed (requires Level 2 market data we don't have)
                'trading_volume_consistency': safe_float_conversion(components.get('volume_component')),
                'market_depth_score': safe_float_conversion(components.get('mcap_component')),
                'components': sanitize_for_json(components) if components else None,
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping liquidity risk data: {e}")
            return None
    
    def map_altman_zscore_data(self, stock_id: int, risk_profile: Dict) -> Optional[Dict]:
        """
        Map Altman Z-Score metrics to altman_zscore_data table
        
        Args:
            stock_id: Stock ID from stocks table
            risk_profile: Comprehensive risk profile from RiskAnalyzer
            
        Returns:
            Dict ready for altman_zscore_data table or None if data unavailable
        """
        try:
            # Check if Altman Z-Score data exists in risk profile
            if not risk_profile or 'altman_z_score' not in risk_profile:
                return None
            
            z_score = risk_profile.get('altman_z_score')
            if z_score is None:
                return None
            
            # Extract Altman Z-Score components
            components = risk_profile.get('altman_components', {})
            
            # Calculate bankruptcy risk percentage from risk zone
            risk_zone = risk_profile.get('altman_risk_zone', 'Unknown')
            bankruptcy_risk_map = {
                'Safe': 10.0,      # < 10% bankruptcy risk
                'Caution': 50.0,   # ~50% bankruptcy risk
                'Distress': 90.0,  # > 90% bankruptcy risk
                'Unknown': None
            }
            bankruptcy_risk = bankruptcy_risk_map.get(risk_zone)
            
            # Override with actual value if provided
            if 'altman_bankruptcy_risk' in risk_profile:
                bankruptcy_risk_str = risk_profile.get('altman_bankruptcy_risk')
                if bankruptcy_risk_str and bankruptcy_risk_str != 'Unknown':
                    # Extract percentage if it's a string like "15%"
                    if isinstance(bankruptcy_risk_str, str) and '%' in bankruptcy_risk_str:
                        bankruptcy_risk = float(bankruptcy_risk_str.replace('%', ''))
                    elif isinstance(bankruptcy_risk_str, (int, float)):
                        bankruptcy_risk = float(bankruptcy_risk_str)
            
            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                
                # Core Z-Score
                'z_score': safe_float_conversion(z_score),
                'risk_zone': risk_zone,
                'bankruptcy_risk': safe_float_conversion(bankruptcy_risk, max_value=100),
                'data_quality': risk_profile.get('altman_data_quality', 'Unknown'),
                
                # Component Ratios
                'working_capital_ratio': safe_float_conversion(components.get('working_capital_ratio')),
                'retained_earnings_ratio': safe_float_conversion(components.get('retained_earnings_ratio')),
                'ebit_ratio': safe_float_conversion(components.get('ebit_ratio')),
                # RiskAnalyzer returns 'market_to_liability' (component D in Altman formula)
                'market_value_ratio': safe_float_conversion(components.get('market_to_liability')),
                'sales_ratio': safe_float_conversion(components.get('sales_ratio')),
                'components': sanitize_for_json(components) if components else None,
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping Altman Z-Score data: {e}")
            return None
    
    def map_regime_risk_data(self, stock_id: int, risk_profile: Dict) -> Optional[Dict]:
        """
        Map regime risk metrics to regime_risk_data table
        
        Args:
            stock_id: Stock ID from stocks table
            risk_profile: Comprehensive risk profile from RiskAnalyzer
            
        Returns:
            Dict ready for regime_risk_data table or None if data unavailable
        """
        try:
            # Check if regime risk data exists in risk profile
            if not risk_profile or 'regime_risk' not in risk_profile:
                return None
            
            regime_data = risk_profile.get('regime_risk')
            if not regime_data or not isinstance(regime_data, dict):
                return None
            
            # Determine current regime based on profile and defensive score
            profile = regime_data.get('profile', 'Unknown')
            defensive_score = regime_data.get('defensive_score', 50.0)
            
            # Map profile to regime classification
            # Profile is Defensive/Balanced/Aggressive, not Bull/Bear
            # Use defensive_score to estimate current market regime
            if defensive_score and defensive_score > 60:
                current_regime = 'Defensive'  # Stock behavior suggests cautious market
            elif defensive_score and defensive_score < 40:
                current_regime = 'Aggressive'  # Stock behavior suggests bullish market
            else:
                current_regime = profile  # Use profile as regime
            
            # Calculate confidence based on data availability
            dist = regime_data.get('regime_distribution', {})
            total_days = sum([dist.get('bull_days', 0), dist.get('bear_days', 0), dist.get('volatile_days', 0)])
            regime_confidence = min(100.0, (total_days / 250.0) * 100.0) if total_days > 0 else 50.0
            
            # Extract regime-specific metrics from RiskAnalyzer output
            bull_volatility = regime_data.get('bull_market_volatility')
            bear_volatility = regime_data.get('bear_market_volatility')
            volatile_volatility = regime_data.get('volatile_market_volatility')
            
            bull_sharpe = regime_data.get('bull_market_sharpe')
            bear_sharpe = regime_data.get('bear_market_sharpe')
            
            volatility_ratio = regime_data.get('volatility_ratio')
            
            # Map to database schema
            # Note: beta/correlation columns removed from schema (not calculated by RiskAnalyzer)
            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                
                # Current Regime
                'current_regime': current_regime,
                'regime_confidence': safe_float_conversion(regime_confidence, max_value=100),
                
                # Bull Market Behavior
                'bull_volatility': safe_float_conversion(bull_volatility),
                
                # Bear Market Behavior
                'bear_downside_capture': safe_float_conversion(1.0 / volatility_ratio if volatility_ratio and volatility_ratio != 0 else None),
                
                # Correction/Volatile Behavior
                'correction_volatility': safe_float_conversion(volatile_volatility),
                
                # Full Analysis (JSONB)
                'regime_analysis': sanitize_for_json(regime_data),
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Error mapping regime risk data: {e}")
            return None

    def map_stock_news_data(self, stock_id: int, news: List[Dict], ticker: str = None) -> List[Dict]:
        """
        Map stock-specific news articles to stock_news_data table
        
        Args:
            stock_id: Stock ID from stocks table
            news: List of news articles (from yfinance or Finnhub)
            ticker: Stock ticker symbol (for context)
            
        Returns:
            List of Dicts ready for stock_news_data table insertion
            Returns 15-20 most recent articles with proper formatting
        """
        try:
            news_records = []
            
            # Log input details at INFO level so we can diagnose issues
            logger.info(f"  📰 Mapping news for stock_id={stock_id}: type={type(news).__name__}, size={len(news) if hasattr(news, '__len__') else 'N/A'}")
            
            if not news:
                logger.info(f"  📰 No news data (empty/None) for stock_id {stock_id}")
                return news_records
            
            # Handle different input structures
            news_input_type = type(news).__name__
            if isinstance(news, dict):
                logger.info(f"  📰 News is a dict, extracting list...")
                # If it's a dict, try to extract the list
                if 'result' in news:
                    news = news['result'] if isinstance(news['result'], list) else []
                    logger.info(f"  📰 Extracted 'result' key: {len(news)} articles")
                else:
                    # Convert dict values to list if needed
                    news = list(news.values()) if news else []
                    logger.info(f"  📰 Converted dict values to list: {len(news)} articles")
                    
            if not isinstance(news, list):
                logger.warning(f"  📰 News data is not a list or dict for stock_id {stock_id}, got {type(news).__name__} (original type was {news_input_type})")
                return news_records
            
            # Process news articles (limit to 20 most recent)
            logger.info(f"  📰 Processing up to 20 articles out of {len(news)} available")
            max_articles = min(20, len(news))
            skipped_count = 0
            
            for i, article in enumerate(news[:max_articles]):
                if not isinstance(article, dict):
                    logger.info(f"  📰 Article {i}: Skipped - not a dict (type={type(article).__name__})")
                    skipped_count += 1
                    continue
                
                try:
                    # Handle different news source formats (yfinance, Finnhub, etc.)
                    article_keys = list(article.keys())
                    
                    # Extract title (try multiple fields)
                    title = article.get('title') or article.get('headline') or None
                    
                    # Handle yfinance nested 'content' structure (modern format)
                    if not title and 'content' in article:
                        content = article.get('content')
                        if isinstance(content, dict):
                            # Extract title from nested content dict (yfinance new structure)
                            title = content.get('title') or content.get('headline') or None
                        elif isinstance(content, str) and len(content) > 0:
                            # Old format: content is text string
                            title = content[:100].split('\n')[0]  # First line or first 100 chars
                            if len(title) < 10:  # Ensure minimum length
                                title = content[:100].replace('\n', ' ')[:100].strip()
                    
                    if not title:
                        logger.info(f"  📰 Article {i}: Skipped - missing title. Keys: {article_keys[:5]}")
                        skipped_count += 1
                        continue
                    
                    # Get nested content object if it exists (yfinance new structure)
                    content_obj = article.get('content') if isinstance(article.get('content'), dict) else {}
                    
                    # Extract URL from article or nested content
                    url = (article.get('url') or 
                           article.get('link') or 
                           article.get('canonicalUrl') or
                           content_obj.get('canonicalUrl') or
                           content_obj.get('clickThroughUrl') or
                           content_obj.get('url') or
                           '')
                    
                    # Extract publisher/source from article or nested content
                    publisher = article.get('publisher') or article.get('source') or 'Unknown'
                    
                    # Handle nested provider object (yfinance new structure)
                    if isinstance(publisher, dict):
                        publisher = publisher.get('displayName', 'Unknown')
                    elif not publisher or publisher == 'Unknown':
                        # Try to get from nested content provider
                        provider = content_obj.get('provider')
                        if isinstance(provider, dict):
                            publisher = provider.get('displayName', 'Unknown')
                    
                    # Extract published timestamp from article or nested content
                    published_ts = (article.get('datetime') or 
                                   article.get('pubDate') or 
                                   article.get('providerPublishTime') or
                                   content_obj.get('pubDate') or
                                   content_obj.get('publishTime'))
                    published_date = None
                    
                    if published_ts:
                        try:
                            # Handle Unix timestamp format (Finnhub)
                            if isinstance(published_ts, (int, float)) and published_ts > 1000000000:
                                from datetime import datetime as dt
                                published_date = dt.fromtimestamp(published_ts).isoformat()
                            # Handle ISO string format (yfinance)
                            elif isinstance(published_ts, str):
                                published_date = published_ts
                            # Handle datetime object
                            elif hasattr(published_ts, 'isoformat'):
                                published_date = published_ts.isoformat()
                        except (ValueError, OverflowError):
                            published_date = None
                    
                    # Extract summary (optional) from article or nested content
                    summary = article.get('summary') or content_obj.get('summary') or None
                    
                    # Extract category if available from article or nested content
                    category = article.get('category') or content_obj.get('category') or None
                    
                    # Determine source API
                    source_api = 'yfinance'
                    if 'datetime' in article:  # Finnhub uses 'datetime'
                        source_api = 'finnhub'
                    
                    # Create record for database
                    record = {
                        'stock_id': stock_id,
                        'title': title,
                        'summary': summary,
                        'url': url,
                        'publisher': publisher,
                        'published_date': published_date,
                        'sentiment_score': None,  # Can be populated by sentiment analysis later
                        'sentiment_label': None,
                        'relevance_score': 1.0,  # Default to high relevance for stock-specific news
                        'category': category,
                        'source_api': source_api,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    news_records.append(record)
                    logger.info(f"  ✓ Article {i}: Successfully mapped '{title[:50]}...'")
                    
                except Exception as e:
                    logger.warning(f"  ⚠️  Article {i}: Error processing: {e}")
                    skipped_count += 1
                    continue
            
            logger.info(f"  📰 Mapped {len(news_records)} news articles (processed {max_articles}, skipped {skipped_count}) for stock_id {stock_id}")
            return news_records
            
        except Exception as e:
            logger.error(f"  ❌ Error mapping stock news data for stock_id {stock_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
