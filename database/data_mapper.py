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
                    
                    # Prophet Forecast Prices for this month (varies by month)
                    'forecast_price_1y': float(row['High']) if pd.notna(row['High']) else None,  # High price
                    'forecast_avg_price': float(row['Average']) if pd.notna(row['Average']) else None,  # Average price
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
            market_cap = info.get('marketCap')
            free_cash_flow = info.get('freeCashflow')
            price_to_fcf = float(market_cap / free_cash_flow) if market_cap and free_cash_flow and free_cash_flow > 0 else None
            
            record = {
                'stock_id': stock_id,
                'period_date': datetime.now().strftime('%Y-%m-%d'),
                'period_type': 'TTM',  # Trailing Twelve Months
                
                # Valuation
                'pe_ratio': float(info.get('trailingPE')) if info.get('trailingPE') else None,
                'pe_forward': float(info.get('forwardPE')) if info.get('forwardPE') else None,
                'price_to_sales': float(info.get('priceToSalesTrailing12Months')) if info.get('priceToSalesTrailing12Months') else None,
                'price_to_book': float(info.get('priceToBook')) if info.get('priceToBook') else None,
                'price_to_fcf': price_to_fcf,
                'ev_to_revenue': float(info.get('enterpriseToRevenue')) if info.get('enterpriseToRevenue') else None,
                'ev_to_ebitda': float(info.get('enterpriseToEbitda')) if info.get('enterpriseToEbitda') else None,
                
                # Profitability
                'net_margin': float(info.get('profitMargins')) if info.get('profitMargins') else None,
                'operating_margin': float(info.get('operatingMargins')) if info.get('operatingMargins') else None,
                'gross_margin': float(info.get('grossMargins')) if info.get('grossMargins') else None,
                'ebitda_margin': float(info.get('ebitdaMargins')) if info.get('ebitdaMargins') else None,
                'roe': float(info.get('returnOnEquity')) if info.get('returnOnEquity') else None,
                'roa': float(info.get('returnOnAssets')) if info.get('returnOnAssets') else None,
                
                # Financial Health
                'debt_to_equity': float(info.get('debtToEquity')) if info.get('debtToEquity') else None,
                'total_cash': float(info.get('totalCash')) if info.get('totalCash') else None,
                'total_debt': float(info.get('totalDebt')) if info.get('totalDebt') else None,
                'free_cash_flow': float(info.get('freeCashflow')) if info.get('freeCashflow') else None,
                'operating_cash_flow': float(info.get('operatingCashflow')) if info.get('operatingCashflow') else None,
                'current_ratio': float(info.get('currentRatio')) if info.get('currentRatio') else None,
                'quick_ratio': float(info.get('quickRatio')) if info.get('quickRatio') else None,
                
                # Growth
                'revenue_ttm': float(info.get('totalRevenue')) if info.get('totalRevenue') else None,
                'revenue_growth_yoy': float(info.get('revenueGrowth')) if info.get('revenueGrowth') else None,
                'net_income_ttm': float(info.get('netIncomeToCommon')) if info.get('netIncomeToCommon') else None,
                'earnings_growth_yoy': float(info.get('earningsGrowth')) if info.get('earningsGrowth') else None,
                'ebitda_ttm': float(info.get('ebitda')) if info.get('ebitda') else None,
                'gross_profit_ttm': float(info.get('grossProfits')) if info.get('grossProfits') else None,
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
                    'revenue_ttm': float(data.get('Total Revenue_raw')) if data.get('Total Revenue_raw') else None,
                    'net_income_ttm': float(data.get('Net Income_raw')) if data.get('Net Income_raw') else None, # reusing column for quarterly net income
                    'gross_profit_ttm': float(data.get('Gross Profit_raw')) if data.get('Gross Profit_raw') else None, # reusing column
                    'operating_income': float(data.get('Operating Income_raw')) if data.get('Operating Income_raw') else None,
                     # Note: EPS is ratio, no need for _raw usually, but let's check analysis script
                    'eps_diluted': float(data.get('Diluted EPS_raw')) if data.get('Diluted EPS_raw') else (float(data.get('Diluted EPS')) if data.get('Diluted EPS') and isinstance(data.get('Diluted EPS'), (int, float)) else None),
                    'eps_basic': float(data.get('Basic EPS_raw')) if data.get('Basic EPS_raw') else (float(data.get('Basic EPS')) if data.get('Basic EPS') and isinstance(data.get('Basic EPS'), (int, float)) else None),
                    
                    # Calculated Margins
                    'gross_margin': float(data.get('Gross Margin_raw')) if data.get('Gross Margin_raw') else None,
                }
                
                # Calculate Net Margin if possible
                if record['net_income_ttm'] is not None and record['revenue_ttm'] is not None and record['revenue_ttm'] != 0:
                    record['net_margin'] = float(record['net_income_ttm'] / record['revenue_ttm'])
                    
                # Calculate Operating Margin if possible
                if record.get('operating_income') is not None and record['revenue_ttm'] is not None and record['revenue_ttm'] != 0:
                    record['operating_margin'] = float(record['operating_income'] / record['revenue_ttm'])
                
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
                
                # Helper to convert metric values
                def to_float(value):
                    if value is None or value == 'N/A' or (isinstance(value, str) and 'ETF' in value):
                        return None
                    try:
                        return float(value)
                    except:
                        return None
                
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
            record['peg_ratio'] = float(info.get('trailingPegRatio')) if info.get('trailingPegRatio') else None
            
            # Calculate ROIC from balance sheet (yfinance doesn't provide it in info)
            roic = None
            net_income = info.get('netIncomeToCommon')
            if balance_sheet is not None and not balance_sheet.empty and net_income:
                try:
                    recent_period = balance_sheet.columns[0]
                    if 'Invested Capital' in balance_sheet.index:
                        invested_capital = float(balance_sheet.loc['Invested Capital', recent_period])
                        if invested_capital != 0:
                            roic = float(net_income / invested_capital)
                except Exception as e:
                    logger.debug(f"Error calculating ROIC: {e}")
            
            record['roic'] = roic
            
            # Get basic data for calculations
            total_revenue = info.get('totalRevenue')
            
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
                        total_assets = float(balance_sheet.loc['Total Assets', recent_period])
                    
                    if 'Inventory' in balance_sheet.index:
                        inventory = float(balance_sheet.loc['Inventory', recent_period])
                    
                    if 'Accounts Receivable' in balance_sheet.index:
                        receivables = float(balance_sheet.loc['Accounts Receivable', recent_period])
                    elif 'Receivables' in balance_sheet.index:
                        receivables = float(balance_sheet.loc['Receivables', recent_period])
                    
                    if 'Accounts Payable' in balance_sheet.index:
                        accounts_payable = float(balance_sheet.loc['Accounts Payable', recent_period])
                    elif 'Payables' in balance_sheet.index:
                        accounts_payable = float(balance_sheet.loc['Payables', recent_period])
                    
                    if 'Working Capital' in balance_sheet.index:
                        working_capital = float(balance_sheet.loc['Working Capital', recent_period])
                except Exception as e:
                    logger.debug(f"Error extracting balance sheet data: {e}")
            
            # Extract cost of revenue from income statement
            cost_of_revenue = None
            if financials is not None and not financials.empty:
                try:
                    recent_period = financials.columns[0]
                    if 'Cost Of Revenue' in financials.index:
                        cost_of_revenue = float(financials.loc['Cost Of Revenue', recent_period])
                except Exception as e:
                    logger.debug(f"Error extracting income statement data: {e}")
            
            # Calculate Asset Turnover = Revenue / Total Assets
            if total_revenue and total_assets and total_assets != 0:
                record['asset_turnover'] = float(total_revenue / total_assets)
            else:
                record['asset_turnover'] = None
            
            # Calculate Inventory Turnover = COGS / Inventory
            if cost_of_revenue and inventory and inventory != 0:
                record['inventory_turnover'] = float(cost_of_revenue / inventory)
            else:
                record['inventory_turnover'] = None
            
            # Calculate Receivables Turnover = Revenue / Receivables
            if total_revenue and receivables and receivables != 0:
                record['receivables_turnover'] = float(total_revenue / receivables)
            else:
                record['receivables_turnover'] = None
            
            # Calculate Working Capital Turnover = Revenue / Working Capital
            if total_revenue and working_capital and working_capital != 0:
                record['working_capital_turnover'] = float(total_revenue / working_capital)
            else:
                record['working_capital_turnover'] = None
            
            # Calculate Days Sales Outstanding (DSO) = 365 / Receivables Turnover
            if record.get('receivables_turnover'):
                record['dso'] = float(365 / record['receivables_turnover'])
            else:
                record['dso'] = None
            
            # Calculate Days Inventory Outstanding (DIO) = 365 / Inventory Turnover
            if record.get('inventory_turnover'):
                record['dio'] = float(365 / record['inventory_turnover'])
            else:
                record['dio'] = None
            
            # Calculate Days Payables Outstanding (DPO) = 365 / (COGS / Accounts Payable)
            # DPO = (Accounts Payable / COGS) * 365
            dpo = None
            if cost_of_revenue and accounts_payable and cost_of_revenue != 0:
                dpo = float((accounts_payable / cost_of_revenue) * 365)
            
            # Calculate Cash Conversion Cycle (CCC) = DSO + DIO - DPO
            # This measures how long it takes to convert cash investments in inventory back to cash
            if record.get('dio') and record.get('dso'):
                if dpo is not None:
                    # Complete CCC formula with DPO
                    record['ccc'] = float(record['dio'] + record['dso'] - dpo)
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
    
    def map_risk_data(self, stock_id: int, processed_data: pd.DataFrame, info: Dict) -> Dict:
        """
        Map risk metrics to risk_data table
        
        Args:
            stock_id: Stock ID from stocks table
            processed_data: DataFrame with returns data
            info: yfinance info dict
            
        Returns:
            Dict ready for risk_data table
        """
        try:
            # Calculate risk metrics from returns
            returns = processed_data['Close'].pct_change().dropna()
            
            # Calculate VaR (95% and 99%)
            var_95 = float(returns.quantile(0.05)) if len(returns) > 0 else None
            var_99 = float(returns.quantile(0.01)) if len(returns) > 0 else None
            
            # Calculate max drawdown
            cum_returns = (1 + returns).cumprod()
            running_max = cum_returns.cummax()
            drawdown = (cum_returns - running_max) / running_max
            max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else None
            
            # Calculate Sharpe ratio (annualized)
            risk_free_rate = 0.02  # Assume 2% risk-free rate
            excess_returns = returns - (risk_free_rate / 252)
            sharpe_ratio = float((excess_returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() > 0 else None
            
            # Calculate Calmar Ratio (Annual Return / Max Drawdown)
            annual_return = float(returns.mean() * 252) if len(returns) > 0 else None
            calmar_ratio = float(annual_return / abs(max_drawdown)) if max_drawdown and max_drawdown != 0 and annual_return else None
            
            # Calculate Kurtosis (tail risk)
            kurtosis = float(returns.kurtosis()) if len(returns) > 3 else None
            
            # Calculate Skewness (distribution asymmetry)
            skewness = float(returns.skew()) if len(returns) > 2 else None
            
            # Calculate Sortino Ratio (downside risk-adjusted return)
            downside_returns = returns[returns < 0]
            downside_std = float(downside_returns.std()) if len(downside_returns) > 1 else None
            sortino_ratio = float((excess_returns.mean() / downside_std) * np.sqrt(252)) if downside_std and downside_std > 0 else None
            
            # Calculate Market Correlation (with S&P 500)
            market_correlation = None
            if 'SP500' in processed_data.columns and len(processed_data) > 30:
                sp500_returns = processed_data['SP500'].pct_change().dropna()
                # Align the two series
                aligned_returns = returns.align(sp500_returns, join='inner')
                if len(aligned_returns[0]) > 30:
                    market_correlation = float(aligned_returns[0].corr(aligned_returns[1]))
            
            record = {
                'stock_id': stock_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                
                # Value at Risk
                'var_95': var_95,
                'var_99': var_99,
                
                # Risk-adjusted metrics
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'max_drawdown': max_drawdown,
                
                # Distribution metrics
                'kurtosis': kurtosis,
                'skewness': skewness,
                
                # Market Risk
                'beta': float(info.get('beta')) if info.get('beta') else None,
                'market_correlation': market_correlation,
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
        try:
            # Determine last historical close (for reference and as fallback)
            historical_close = None
            if not processed_data.empty and 'Close' in processed_data.columns:
                closes = processed_data['Close'].dropna()
                if len(closes) > 0:
                    historical_close = float(closes.iloc[-1])

            # Prefer real-time price when available; fallback to historical close
            real_price = None
            if current_price and current_price.get('current_price') is not None:
                try:
                    real_price = float(current_price.get('current_price'))
                except (ValueError, TypeError):
                    real_price = None

            # Final published price (real-time if available)
            published_price = real_price if real_price is not None else (historical_close if historical_close is not None else 0.0)

            # Compute price change relative to last historical close when possible
            # Percentage change should be shown relative to the published (real-time) price
            if historical_close is not None and published_price is not None:
                price_change_val = published_price - historical_close
                # Use published price (real-time) as denominator for percentage change per product decision
                change_pct_val = (price_change_val / published_price * 100) if published_price > 0 else None
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
                'change_pct': float(change_pct_val) if change_pct_val is not None else None,

                # Performance metrics
                'change_15d_pct': float(change_15d_pct) if change_15d_pct is not None else None,
                'change_52w_pct': float(change_52w_pct) if change_52w_pct is not None else None,
                'performance_1y_pct': float(performance_1y_pct) if performance_1y_pct is not None else None,
                'overall_pct_change': float(overall_pct_change) if overall_pct_change is not None else None,

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
                'dividend_yield_pct': float(info.get('dividendYield', 0) * 100) if info.get('dividendYield') else None,
                'payout_ratio': float(info.get('payoutRatio')) if info.get('payoutRatio') else None,
                'avg_dividend_yield_5y': float(info.get('fiveYearAvgDividendYield')) if info.get('fiveYearAvgDividendYield') else None,
                'dividend_forward_rate': float(info.get('dividendRate')) if info.get('dividendRate') else None,
                'dividend_forward_yield': float(info.get('dividendYield', 0) * 100) if info.get('dividendYield') else None,
                'dividend_trailing_rate': float(info.get('trailingAnnualDividendRate')) if info.get('trailingAnnualDividendRate') else None,
                'dividend_trailing_yield': float(info.get('trailingAnnualDividendYield', 0) * 100) if info.get('trailingAnnualDividendYield') else None,
                
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
            
            def safe_float(value):
                """Convert to float, handling NaN and Infinity"""
                try:
                    if pd.isna(value) or value is None:
                        return None
                    val = float(value)
                    # Check for infinity or NaN
                    if np.isinf(val) or np.isnan(val):
                        return None
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
                
                # Get shares and price with safe conversion
                shares = safe_float(row.get('Shares', row.get('#Shares')))
                price = safe_float(row.get('Value', row.get('Price')))
                
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
                if shares is not None and price is not None and shares != 0:
                    estimated = safe_float(abs(shares) * price)
                    if estimated is not None:
                        record['estimated_value'] = estimated
                
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
