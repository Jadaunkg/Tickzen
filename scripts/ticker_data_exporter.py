#!/usr/bin/env python3
"""
Ticker Data Exporter - Complete Variable Collection Pipeline
=============================================================

This script collects all variables used in TickZen2 reports and exports them
to a CSV file for use in external applications and ticker-specific pages.

Features:
- Collects 220+ variables across all analysis categories
- Integrates with existing TickZen2 analysis modules
- Exports data in CSV format for easy consumption
- Handles missing data gracefully
- Supports batch processing of multiple tickers

Usage:
    python ticker_data_exporter.py AAPL
    python ticker_data_exporter.py AAPL MSFT GOOGL --output custom_output.csv
    
Author: TickZen Development Team
Version: 1.0
Last Updated: January 2026
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import logging
import argparse
import yfinance as yf

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import TickZen2 analysis modules
from analysis_scripts.technical_analysis import calculate_detailed_ta
from analysis_scripts.fundamental_analysis import (
    extract_company_profile,
    extract_valuation_metrics,
    extract_financial_health,
    extract_profitability,
    extract_quarterly_earnings_data
)
from analysis_scripts.risk_analysis import RiskAnalyzer
from analysis_scripts.peer_comparison import (
    get_insider_transactions_data
)

# Import Prophet forecasting
try:
    from Models.prophet_model import train_prophet_model
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet model not available - forecasts will not be generated")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TickerDataExporter:
    """Main class for collecting and exporting ticker data."""
    
    def __init__(self, ticker):
        """Initialize exporter for a specific ticker."""
        self.ticker = ticker.upper()
        self.data = {}
        self.risk_analyzer = RiskAnalyzer()
        self.error_log = []
        self.insider_transactions = []  # Store detailed transaction data
        self.quarterly_details = []  # Store quarterly data per quarter
        self.peer_data = []  # Store peer comparison data
        self.historical_data = None  # Store complete historical time-series data
        self.forecast_data = None  # Store Prophet forecast data
        
    def collect_all_data(self):
        """Collect all data from various analysis modules."""
        logging.info(f"Starting data collection for {self.ticker}...")
        
        try:
            # Fetch fundamental data
            logging.info("Fetching fundamental data...")
            stock = yf.Ticker(self.ticker)
            fundamentals = {
                'info': stock.info,
                'financials': stock.financials,
                'quarterly_financials': stock.quarterly_financials,
                'balance_sheet': stock.balance_sheet,
                'cashflow': stock.cashflow
            }
            
            # Fetch historical price data
            logging.info("Fetching historical price data...")
            hist_data = stock.history(period="max")  # Get maximum available history (typically 10+ years)
            
            if hist_data.empty:
                raise ValueError(f"No historical data available for {self.ticker}")
            
            # Store historical data before reset
            self.historical_data = hist_data.copy()
            
            # Reset index to make Date a column
            hist_data.reset_index(inplace=True)
            
            # Generate Prophet forecasts
            logging.info("Generating Prophet forecasts...")
            self._generate_forecasts(hist_data)
            
            # 1. OVERVIEW TAB DATA
            logging.info("Collecting Overview data...")
            self._collect_overview_data(fundamentals, hist_data)
            
            # 2. FORECAST TAB DATA
            logging.info("Collecting Forecast data...")
            self._collect_forecast_data(fundamentals)
            
            # 3. TECHNICALS TAB DATA
            logging.info("Collecting Technical Analysis data...")
            self._collect_technical_data(hist_data)
            
            # 4. FUNDAMENTALS TAB DATA
            logging.info("Collecting Fundamental data...")
            self._collect_fundamental_data(fundamentals)
            
            # 5. RISK & SENTIMENT TAB DATA
            logging.info("Collecting Risk & Sentiment data...")
            self._collect_risk_sentiment_data(fundamentals, hist_data)
            
            # 6. COMPANY TAB DATA
            logging.info("Collecting Company & Insider data...")
            self._collect_company_data(fundamentals)
            
            # 7. QUARTERLY EARNINGS DATA
            logging.info("Collecting Quarterly Earnings data...")
            self._collect_quarterly_data(fundamentals)
            
            # 8. PEER COMPARISON DATA
            logging.info("Collecting Peer Comparison data...")
            self._collect_peer_data(fundamentals, hist_data)
            
            logging.info(f"Data collection complete. Collected {len(self.data)} variables.")
            logging.info(f"Collected {len(self.insider_transactions)} insider transactions.")
            logging.info(f"Collected {len(self.quarterly_details)} quarterly records.")
            logging.info(f"Collected {len(self.peer_data)} peer comparison records.")
            
        except Exception as e:
            logging.error(f"Error collecting data for {self.ticker}: {e}")
            self.error_log.append(str(e))
            raise
    
    def _collect_overview_data(self, fundamentals, hist_data):
        """Collect Overview tab variables."""
        info = fundamentals.get('info', {})
        
        # Latest price data
        latest = hist_data.iloc[-1] if not hist_data.empty else {}
        
        # Market Price
        self.data['ticker'] = self.ticker
        self.data['current_price'] = info.get('currentPrice', latest.get('Close', np.nan))
        self.data['regularMarketPrice'] = info.get('regularMarketPrice', np.nan)
        self.data['open_price'] = latest.get('Open', np.nan)
        self.data['high_price'] = latest.get('High', np.nan)
        self.data['low_price'] = latest.get('Low', np.nan)
        self.data['close_price'] = latest.get('Close', np.nan)
        self.data['volume'] = latest.get('Volume', np.nan)
        
        # Market Size
        self.data['market_cap'] = info.get('marketCap', np.nan)
        self.data['enterprise_value'] = info.get('enterpriseValue', np.nan)
        self.data['shares_outstanding'] = info.get('sharesOutstanding', np.nan)
        
        # Fix float_shares validation - float MUST be <= outstanding
        raw_float = info.get('floatShares', np.nan)
        shares_out = self.data['shares_outstanding']
        
        if pd.notna(raw_float) and pd.notna(shares_out):
            if raw_float > shares_out:
                # Float can't be higher than outstanding - use 95% of outstanding as estimate
                # (Apple typically has ~98-99% float due to minimal insider holdings)
                self.data['float_shares'] = shares_out * 0.98
                print(f"⚠️  WARNING: floatShares ({raw_float:,.0f}) > sharesOutstanding ({shares_out:,.0f})")
                print(f"   Corrected to {self.data['float_shares']:,.0f} (98% of outstanding)")
            else:
                self.data['float_shares'] = raw_float
        else:
            self.data['float_shares'] = raw_float
        
        # Performance
        if len(hist_data) >= 2:
            self.data['daily_return_pct'] = ((hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[-2]) / hist_data['Close'].iloc[-2] * 100)
        else:
            self.data['daily_return_pct'] = np.nan
            
        if len(hist_data) >= 16:
            self.data['change_15d_pct'] = ((hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[-16]) / hist_data['Close'].iloc[-16] * 100)
        else:
            self.data['change_15d_pct'] = np.nan
        
        self.data['change_52w_pct'] = info.get('52WeekChange', np.nan)
        
        if len(hist_data) >= 252:
            self.data['performance_1y_pct'] = ((hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[-252]) / hist_data['Close'].iloc[-252] * 100)
        else:
            self.data['performance_1y_pct'] = np.nan
        
        self.data['high_52w'] = info.get('fiftyTwoWeekHigh', np.nan)
        self.data['low_52w'] = info.get('fiftyTwoWeekLow', np.nan)
        
        # Market Context
        self.data['exchange'] = info.get('exchange', '')
        self.data['country'] = info.get('country', '')
        self.data['sp500_index'] = np.nan  # Would need separate data source
        self.data['interest_rate'] = np.nan  # Would need separate data source
        
        # Historical/Lifecycle Data
        try:
            # Calculate CAGR (Compound Annual Growth Rate)
            if len(hist_data) >= 252:  # At least 1 year of data
                start_price = hist_data['Close'].iloc[0]
                end_price = hist_data['Close'].iloc[-1]
                days = len(hist_data)
                years = days / 252
                if start_price > 0 and years > 0:
                    cagr = (pow(end_price / start_price, 1 / years) - 1) * 100
                    self.data['cagr_all_time'] = cagr
                else:
                    self.data['cagr_all_time'] = np.nan
            else:
                self.data['cagr_all_time'] = np.nan
            
            # IPO info and returns
            ipo_date = info.get('ipoExpectedDate') or info.get('ipoDate', '')
            self.data['ipo_date'] = ipo_date
            
            if ipo_date and len(hist_data) > 0:
                self.data['ipo_adjusted_return_pct'] = ((hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[0]) / hist_data['Close'].iloc[0] * 100)
            else:
                self.data['ipo_adjusted_return_pct'] = np.nan
                
            # First trade price (from earliest available data)
            if len(hist_data) > 0:
                self.data['first_trade_price'] = hist_data['Close'].iloc[0]
            else:
                self.data['first_trade_price'] = np.nan
                
        except Exception as e:
            logging.warning(f"Error calculating historical metrics: {e}")
            self.data['cagr_all_time'] = np.nan
            self.data['ipo_adjusted_return_pct'] = np.nan
            self.data['first_trade_price'] = np.nan
        
        # Backend Control Fields
        self.data['success'] = True
        self.data['error'] = ''
        self.data['period_months'] = 12
        self.data['max_days_search'] = 1825  # ~5 years
        
    def _collect_forecast_data(self, fundamentals):
        """Collect Forecast tab variables."""
        info = fundamentals.get('info', {})
        
        # Analyst Targets
        self.data['target_price_mean'] = info.get('targetMeanPrice', np.nan)
        self.data['target_price_median'] = info.get('targetMedianPrice', np.nan)
        self.data['target_price_high'] = info.get('targetHighPrice', np.nan)
        self.data['target_price_low'] = info.get('targetLowPrice', np.nan)
        self.data['analyst_rating'] = info.get('recommendationKey', '')
        self.data['analyst_count'] = info.get('numberOfAnalystOpinions', np.nan)
        
        # Earnings Timing
        earnings_ts = info.get('earningsTimestamp')
        if earnings_ts:
            earnings_date = datetime.fromtimestamp(earnings_ts)
            self.data['next_earnings_date'] = earnings_date.strftime('%Y-%m-%d')
            self.data['earningsTimestamp'] = earnings_ts
        else:
            self.data['next_earnings_date'] = ''
            self.data['earningsTimestamp'] = np.nan
        
        earnings_call_ts = info.get('earningsCallTimestampStart')
        if earnings_call_ts:
            call_time = datetime.fromtimestamp(earnings_call_ts)
            self.data['earnings_call_time'] = call_time.strftime('%Y-%m-%d %H:%M')
            self.data['earningsCallTimestampStart'] = earnings_call_ts
        else:
            self.data['earnings_call_time'] = ''
            self.data['earningsCallTimestampStart'] = np.nan
        
        # Prophet Forecast Prices - populated if forecast generation succeeded
        if self.forecast_data is not None and not self.forecast_data.empty:
            # Get 1-year forecast (approximately 252 trading days ahead)
            forecast_1y_idx = min(251, len(self.forecast_data) - 1)
            if forecast_1y_idx > 0:
                self.data['forecast_price_1y'] = self.forecast_data.iloc[forecast_1y_idx]['yhat']
                self.data['forecast_avg_price'] = self.forecast_data['yhat'].mean()
                self.data['forecast_range_width'] = (self.forecast_data['yhat_upper'].max() - 
                                                     self.forecast_data['yhat_lower'].min())
                self.data['forecast_period'] = '1 year'
            else:
                self.data['forecast_price_1y'] = np.nan
                self.data['forecast_avg_price'] = np.nan
                self.data['forecast_range_width'] = np.nan
                self.data['forecast_period'] = ''
        else:
            self.data['forecast_price_1y'] = np.nan
            self.data['forecast_avg_price'] = np.nan
            self.data['forecast_range_width'] = np.nan
            self.data['forecast_period'] = ''
        
    def _collect_technical_data(self, hist_data):
        """Collect Technical Analysis tab variables."""
        try:
            # Calculate technical indicators
            ta_data = calculate_detailed_ta(hist_data)
            
            # Trend indicators
            self.data['sma_7'] = ta_data.get('SMA_7', np.nan)
            self.data['sma_20'] = ta_data.get('SMA_20', np.nan)
            self.data['sma_50'] = ta_data.get('SMA_50', np.nan)
            self.data['sma_100'] = ta_data.get('SMA_100', np.nan)
            self.data['sma_200'] = ta_data.get('SMA_200', np.nan)
            
            # Momentum indicators
            self.data['rsi_14'] = ta_data.get('RSI_14', np.nan)
            self.data['macd_line'] = ta_data.get('MACD_Line', np.nan)
            self.data['macd_signal'] = ta_data.get('MACD_Signal', np.nan)
            self.data['macd_hist'] = ta_data.get('MACD_Hist', np.nan)
            
            # Volatility indicators
            self.data['bb_upper'] = ta_data.get('BB_Upper', np.nan)
            self.data['bb_middle'] = ta_data.get('BB_Middle', np.nan)
            self.data['bb_lower'] = ta_data.get('BB_Lower', np.nan)
            
            # Volume indicators
            self.data['volume_sma_20'] = ta_data.get('Volume_SMA20', np.nan)
            self.data['volume_sma_ratio'] = ta_data.get('Volume_vs_SMA20_Ratio', np.nan)
            self.data['volume_trend_5d'] = ta_data.get('Volume_Trend_5D', '')
            
            # Support & Resistance
            self.data['support_30d'] = ta_data.get('Support_30D', np.nan)
            self.data['resistance_30d'] = ta_data.get('Resistance_30D', np.nan)
            
            # Current price
            self.data['current_price_ta'] = ta_data.get('Current_Price', np.nan)
            
            # Additional indicators (set to NaN - would need additional calculation)
            self.data['ema_12'] = np.nan
            self.data['ema_26'] = np.nan
            self.data['adx'] = np.nan
            self.data['parabolic_sar'] = np.nan
            self.data['stochastic_osc'] = np.nan
            self.data['williams_r'] = np.nan
            self.data['atr_14'] = np.nan
            self.data['volatility_7d'] = np.nan
            self.data['keltner_upper'] = np.nan
            self.data['keltner_lower'] = np.nan
            self.data['obv'] = np.nan
            self.data['vpt'] = np.nan
            self.data['chaikin_money_flow'] = np.nan
            self.data['green_days_count'] = np.nan
            
        except Exception as e:
            logging.warning(f"Error in technical analysis: {e}")
            self.error_log.append(f"Technical analysis error: {e}")
    
    def _collect_fundamental_data(self, fundamentals):
        """Collect Fundamentals tab variables."""
        info = fundamentals.get('info', {})
        
        # Valuation
        self.data['pe_trailing'] = info.get('trailingPE', np.nan)
        self.data['pe_forward'] = info.get('forwardPE', np.nan)
        self.data['price_to_sales'] = info.get('priceToSalesTrailing12Months', np.nan)
        self.data['price_to_book'] = info.get('priceToBook', np.nan)
        self.data['peg_ratio'] = info.get('pegRatio', np.nan)
        self.data['ev_to_revenue'] = info.get('enterpriseToRevenue', np.nan)
        self.data['ev_to_ebitda'] = info.get('enterpriseToEbitda', np.nan)
        
        # Calculate Price to FCF if possible
        fcf = info.get('freeCashflow', np.nan)
        market_cap = info.get('marketCap', np.nan)
        if fcf and market_cap and fcf > 0:
            self.data['price_to_fcf'] = market_cap / fcf
        else:
            self.data['price_to_fcf'] = np.nan
        
        # Profitability
        self.data['net_margin'] = info.get('profitMargins', np.nan)
        self.data['operating_margin'] = info.get('operatingMargins', np.nan)
        self.data['gross_margin'] = info.get('grossMargins', np.nan)
        self.data['ebitda_margin'] = info.get('ebitdaMargins', np.nan)
        self.data['roe'] = info.get('returnOnEquity', np.nan)
        self.data['roa'] = info.get('returnOnAssets', np.nan)
        
        # Calculate ROIC if possible
        ebit = info.get('ebit', np.nan)
        total_capital = info.get('totalDebt', 0) + info.get('totalStockholderEquity', 0)
        if ebit and total_capital and total_capital > 0:
            self.data['roic'] = ebit / total_capital
        else:
            self.data['roic'] = np.nan
        
        # Financial Health
        self.data['debt_to_equity'] = info.get('debtToEquity', np.nan)
        self.data['total_cash'] = info.get('totalCash', np.nan)
        self.data['totalCash'] = info.get('totalCash', np.nan)
        self.data['total_debt'] = info.get('totalDebt', np.nan)
        self.data['free_cash_flow'] = info.get('freeCashflow', np.nan)
        self.data['freeCashflow'] = info.get('freeCashflow', np.nan)
        self.data['operating_cash_flow'] = info.get('operatingCashflow', np.nan)
        self.data['current_ratio'] = info.get('currentRatio', np.nan)
        self.data['quick_ratio'] = info.get('quickRatio', np.nan)
        
        # Growth
        self.data['revenue_ttm'] = info.get('totalRevenue', np.nan)
        self.data['revenue_growth_yoy'] = info.get('revenueGrowth', np.nan)
        self.data['net_income_ttm'] = info.get('netIncomeToCommon', np.nan)
        self.data['netIncomeToCommon'] = info.get('netIncomeToCommon', np.nan)
        self.data['earnings_growth_yoy'] = info.get('earningsGrowth', np.nan)
        self.data['ebitda_ttm'] = info.get('ebitda', np.nan)
        self.data['gross_profit_ttm'] = info.get('grossProfits', np.nan)
        
        # Efficiency
        # Calculate efficiency ratios
        total_revenue = info.get('totalRevenue', np.nan)
        total_assets = info.get('totalAssets', np.nan)
        
        if total_revenue and total_assets and total_assets > 0:
            self.data['asset_turnover'] = total_revenue / total_assets
        else:
            self.data['asset_turnover'] = np.nan
        
        self.data['inventory_turnover'] = info.get('inventoryTurnover', np.nan)
        self.data['receivables_turnover'] = np.nan  # Not directly available
        self.data['working_capital_turnover'] = np.nan  # Not directly available
        self.data['dso'] = np.nan  # Days Sales Outstanding
        self.data['dio'] = np.nan  # Days Inventory Outstanding
        self.data['ccc'] = np.nan  # Cash Conversion Cycle
        
        # Dividends
        self.data['dividend_rate'] = info.get('dividendRate', np.nan)
        self.data['dividend_yield_pct'] = info.get('dividendYield', np.nan)
        self.data['payout_ratio'] = info.get('payoutRatio', np.nan)
        self.data['avg_dividend_yield_5y'] = info.get('fiveYearAvgDividendYield', np.nan)
        self.data['dividend_forward_rate'] = info.get('forwardDividendRate', np.nan)
        self.data['dividend_forward_yield'] = info.get('forwardDividendYield', np.nan)
        self.data['dividend_trailing_rate'] = info.get('trailingAnnualDividendRate', np.nan)
        self.data['dividend_trailing_yield'] = info.get('trailingAnnualDividendYield', np.nan)
        
        ex_div_date = info.get('exDividendDate')
        if ex_div_date:
            self.data['ex_dividend_date'] = datetime.fromtimestamp(ex_div_date).strftime('%Y-%m-%d')
        else:
            self.data['ex_dividend_date'] = ''
        
        split_date = info.get('lastSplitDate')
        if split_date:
            self.data['last_split_date'] = datetime.fromtimestamp(split_date).strftime('%Y-%m-%d')
        else:
            self.data['last_split_date'] = ''
        
        self.data['last_split_factor'] = info.get('lastSplitFactor', '')
    
    def _collect_risk_sentiment_data(self, fundamentals, hist_data):
        """Collect Risk & Sentiment tab variables."""
        info = fundamentals.get('info', {})
        
        try:
            # Calculate risk metrics
            if len(hist_data) > 30:
                close_prices = hist_data['Close']
                returns = close_prices.pct_change().dropna()
                
                risk_profile = self.risk_analyzer.comprehensive_risk_profile(close_prices)
                
                self.data['volatility_30d_annual'] = risk_profile.get('volatility_30d_annualized', np.nan)
                self.data['var_95'] = risk_profile.get('var_5', np.nan)
                self.data['var_99'] = risk_profile.get('var_1', np.nan)
                self.data['sharpe_ratio'] = risk_profile.get('sharpe_ratio', np.nan)
                self.data['sortino_ratio'] = risk_profile.get('sortino_ratio', np.nan)
                self.data['max_drawdown'] = risk_profile.get('max_drawdown', np.nan)
                self.data['skewness'] = risk_profile.get('skewness', np.nan)
                self.data['kurtosis'] = risk_profile.get('kurtosis', np.nan)
                self.data['beta'] = risk_profile.get('beta', info.get('beta', np.nan))
                self.data['market_correlation'] = risk_profile.get('correlation_market', np.nan)
            else:
                self.data['volatility_30d_annual'] = np.nan
                self.data['var_95'] = np.nan
                self.data['var_99'] = np.nan
                self.data['sharpe_ratio'] = np.nan
                self.data['sortino_ratio'] = np.nan
                self.data['max_drawdown'] = np.nan
                self.data['skewness'] = np.nan
                self.data['kurtosis'] = np.nan
                self.data['beta'] = info.get('beta', np.nan)
                self.data['market_correlation'] = np.nan
            
            self.data['calmar_ratio'] = np.nan  # Would need additional calculation
            
        except Exception as e:
            logging.warning(f"Error calculating risk metrics: {e}")
            self.error_log.append(f"Risk calculation error: {e}")
        
        # Sentiment (placeholder - would need sentiment analysis module)
        self.data['sentiment_score'] = np.nan
        self.data['sentiment_label'] = ''
        self.data['sentiment_confidence'] = np.nan
        self.data['news_sentiment'] = np.nan
        self.data['analyst_sentiment'] = np.nan
        self.data['options_sentiment'] = np.nan
        self.data['put_call_ratio'] = np.nan
    
    def _collect_company_data(self, fundamentals):
        """Collect Company tab variables."""
        info = fundamentals.get('info', {})
        
        # Profile
        self.data['company_name'] = info.get('longName', info.get('shortName', ''))
        self.data['shortName'] = info.get('shortName', '')
        self.data['longName'] = info.get('longName', '')
        self.data['symbol'] = self.ticker
        self.data['sector'] = info.get('sector', '')
        self.data['industry'] = info.get('industry', '')
        self.data['website_url'] = info.get('website', '')
        self.data['employee_count'] = info.get('fullTimeEmployees', np.nan)
        self.data['business_summary'] = info.get('longBusinessSummary', '')
        self.data['longBusinessSummary'] = info.get('longBusinessSummary', '')
        
        first_trade_date = info.get('firstTradeDateEpochUtc')
        if first_trade_date:
            self.data['firstTradeDateEpochUtc'] = first_trade_date
            self.data['first_trade_date'] = datetime.fromtimestamp(first_trade_date).strftime('%Y-%m-%d')
        else:
            self.data['firstTradeDateEpochUtc'] = np.nan
            self.data['first_trade_date'] = ''
        
        # Ownership
        self.data['sharesOutstanding'] = info.get('sharesOutstanding', np.nan)
        self.data['shares_outstanding_diluted'] = info.get('impliedSharesOutstanding', np.nan)
        self.data['insider_ownership_pct'] = info.get('heldPercentInsiders', np.nan)
        self.data['institutional_ownership_pct'] = info.get('heldPercentInstitutions', np.nan)
        self.data['shares_short'] = info.get('sharesShort', np.nan)
        self.data['short_ratio_days'] = info.get('shortRatio', np.nan)
        self.data['short_pct_float'] = info.get('shortPercentOfFloat', np.nan)
        self.data['shares_short_prev'] = info.get('sharesShortPriorMonth', np.nan)
        self.data['shares_change_yoy'] = np.nan  # Not directly available
        
        # Insider Transactions Summary
        try:
            insider_data = get_insider_transactions_data(self.ticker, months_back=3)
            if insider_data.get('success'):
                summary = insider_data.get('summary', {})
                self.data['total_transactions'] = summary.get('total_transactions', 0)
                self.data['buy_count'] = summary.get('buy_count', 0)
                self.data['sell_count'] = summary.get('sell_count', 0)
                self.data['net_shares'] = summary.get('net_shares', 0)
                self.data['net_sentiment'] = summary.get('net_sentiment', '')
                
                # Count transaction types
                transactions = insider_data.get('formatted_transactions', [])
                self.data['market_transactions'] = len([t for t in transactions if t.get('code') in ['P', 'S']])
                self.data['option_exercises'] = len([t for t in transactions if t.get('code') == 'M'])
                self.data['awards'] = len([t for t in transactions if t.get('code') == 'A'])
                
                # Store detailed transaction records
                for trans in transactions:
                    trans_record = {
                        'ticker': self.ticker,
                        'name': trans.get('name', ''),
                        'transaction_date': trans.get('transaction_date', ''),
                        'filing_date': trans.get('filing_date', ''),
                        'transaction_code': trans.get('code', ''),
                        'code_description': trans.get('code_description', ''),
                        'type': trans.get('type', ''),
                        'type_detailed': trans.get('type_detailed', ''),
                        'change': trans.get('change', ''),
                        'change_display': trans.get('change_display', ''),
                        'price': trans.get('price', np.nan),
                        'price_display': trans.get('price_display', ''),
                        'estimated_value': trans.get('estimated_value', np.nan),
                        'shares_after': trans.get('shares_after', np.nan)
                    }
                    self.insider_transactions.append(trans_record)
            else:
                self.data['total_transactions'] = 0
                self.data['buy_count'] = 0
                self.data['sell_count'] = 0
                self.data['net_shares'] = 0
                self.data['net_sentiment'] = ''
                self.data['market_transactions'] = 0
                self.data['option_exercises'] = 0
                self.data['awards'] = 0
        except Exception as e:
            logging.warning(f"Error collecting insider transaction data: {e}")
            self.data['total_transactions'] = 0
            self.data['buy_count'] = 0
            self.data['sell_count'] = 0
            self.data['net_shares'] = 0
            self.data['net_sentiment'] = ''
            self.data['market_transactions'] = 0
            self.data['option_exercises'] = 0
            self.data['awards'] = 0
    
    def _collect_quarterly_data(self, fundamentals):
        """Collect Quarterly Earnings variables for all quarters (Q1-Q4)."""
        try:
            quarterly_data = extract_quarterly_earnings_data(fundamentals, self.ticker)
            stock = yf.Ticker(self.ticker)
            
            # Get quarterly financials from yfinance
            q_financials = stock.quarterly_financials if hasattr(stock, 'quarterly_financials') else None
            
            if quarterly_data:
                q_data = quarterly_data.get('quarterly_data', {})
                growth = quarterly_data.get('growth_metrics', {})
                
                # Quarters: Most recent to oldest
                quarters = ['Q1', 'Q2', 'Q3', 'Q4']
                
                for q in quarters:
                    q_info = q_data.get(q, {})
                    q_lower = q.lower()
                    
                    self.data[f'{q_lower}_date'] = q_info.get('date', '')
                    self.data[f'{q_lower}_total_revenue'] = q_info.get('Total Revenue', '')
                    self.data[f'{q_lower}_net_income'] = q_info.get('Net Income', '')
                    self.data[f'{q_lower}_gross_profit'] = q_info.get('Gross Profit', '')
                    self.data[f'{q_lower}_operating_income'] = q_info.get('Operating Income', '')
                    self.data[f'{q_lower}_eps_basic'] = q_info.get('Basic EPS', '')
                    self.data[f'{q_lower}_eps_diluted'] = q_info.get('Diluted EPS', '')
                    self.data[f'{q_lower}_gross_margin'] = q_info.get('Gross Margin', '')
                    
                    # Store detailed quarterly record
                    q_record = {
                        'ticker': self.ticker,
                        'quarter': q,
                        'date': q_info.get('date', ''),
                        'total_revenue': q_info.get('Total Revenue', ''),
                        'net_income': q_info.get('Net Income', ''),
                        'gross_profit': q_info.get('Gross Profit', ''),
                        'operating_income': q_info.get('Operating Income', ''),
                        'eps_basic': q_info.get('Basic EPS', ''),
                        'eps_diluted': q_info.get('Diluted EPS', ''),
                        'gross_margin': q_info.get('Gross Margin', '')
                    }
                    self.quarterly_details.append(q_record)
                
                # Growth metrics (same for all quarters)
                self.data['qoq_revenue_growth'] = growth.get('QoQ Revenue Growth', '')
                self.data['qoq_net_income_growth'] = growth.get('QoQ Net Income Growth', '')
                self.data['yoy_revenue_growth'] = growth.get('YoY Revenue Growth', '')
            else:
                # Set defaults for all quarters
                for field in ['q1_date', 'q1_total_revenue', 'q1_net_income', 'q1_gross_profit',
                             'q1_operating_income', 'q1_eps_basic', 'q1_eps_diluted', 'q1_gross_margin',
                             'q2_date', 'q2_total_revenue', 'q2_net_income', 'q2_gross_profit',
                             'q2_operating_income', 'q2_eps_basic', 'q2_eps_diluted', 'q2_gross_margin',
                             'q3_date', 'q3_total_revenue', 'q3_net_income', 'q3_gross_profit',
                             'q3_operating_income', 'q3_eps_basic', 'q3_eps_diluted', 'q3_gross_margin',
                             'q4_date', 'q4_total_revenue', 'q4_net_income', 'q4_gross_profit',
                             'q4_operating_income', 'q4_eps_basic', 'q4_eps_diluted', 'q4_gross_margin',
                             'qoq_revenue_growth', 'qoq_net_income_growth', 'yoy_revenue_growth']:
                    self.data[field] = ''
                    
        except Exception as e:
            logging.warning(f"Error collecting quarterly data: {e}")
            self.error_log.append(f"Quarterly data error: {e}")
    
    def _collect_peer_data(self, fundamentals, hist_data):
        """Collect peer comparison data including rankings and averages."""
        try:
            stock = yf.Ticker(self.ticker)
            info = fundamentals.get('info', {})
            
            # Get industry/sector for finding peers
            industry = info.get('industry', '')
            sector = info.get('sector', '')
            
            # Get recommended symbols (similar companies) from yfinance
            recommendations = stock.recommendations
            peers_list = []
            
            # Try to get peer tickers from info
            if hasattr(stock, 'info') and 'companyOfficers' in stock.info:
                # yfinance doesn't directly provide peers, so we'll use a simplified approach
                # In production, you'd use a proper peer discovery API
                pass
            
            # For now, store basic peer comparison metrics
            current_market_cap = info.get('marketCap', 0)
            current_pe = info.get('trailingPE', np.nan)
            
            # Calculate performance
            if len(hist_data) >= 252:
                performance_1y = ((hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[-252]) / hist_data['Close'].iloc[-252] * 100)
            else:
                performance_1y = np.nan
            
            # Store summary peer metrics in main data
            self.data['peer_list'] = ''  # Would need external API for real peer list
            self.data['market_cap_rank'] = np.nan  # Requires peer data
            self.data['pe_rank'] = np.nan  # Requires peer data
            self.data['performance_rank_1y'] = np.nan  # Requires peer data
            self.data['peer_avg_valuation'] = np.nan  # Requires peer data
            self.data['peer_avg_performance'] = np.nan  # Requires peer data
            
            # Create a peer record for this ticker (for comparison)
            peer_record = {
                'ticker': self.ticker,
                'company_name': info.get('longName', ''),
                'sector': sector,
                'industry': industry,
                'market_cap': current_market_cap,
                'pe_ratio': current_pe,
                'performance_1y_pct': performance_1y,
                'current_price': info.get('currentPrice', np.nan),
                'market_cap_rank': np.nan,  # Would be calculated with real peer data
                'pe_rank': np.nan,
                'performance_rank': np.nan
            }
            
            self.peer_data.append(peer_record)
            
            logging.info(f"Peer data collection: Industry={industry}, Sector={sector}")
            
        except Exception as e:
            logging.warning(f"Error collecting peer data: {e}")
            self.error_log.append(f"Peer data error: {e}")
            # Set default values
            self.data['peer_list'] = ''
            self.data['market_cap_rank'] = np.nan
            self.data['pe_rank'] = np.nan
            self.data['performance_rank_1y'] = np.nan
            self.data['peer_avg_valuation'] = np.nan
            self.data['peer_avg_performance'] = np.nan
    
    def _generate_forecasts(self, hist_data):
        """Generate Prophet forecasts for the ticker."""
        if not PROPHET_AVAILABLE:
            logging.warning("Prophet not available - skipping forecast generation")
            return
        
        try:
            # Prepare data for Prophet (needs Date and Close columns)
            forecast_input = hist_data[['Date', 'Close']].copy()
            
            # Train Prophet model and get forecasts
            logging.info(f"Training Prophet model for {self.ticker}...")
            model, forecast, agg_actual, agg_forecast = train_prophet_model(
                data=forecast_input,
                ticker=self.ticker,
                forecast_horizon='1y',  # 1-year forecast
                timestamp=None
            )
            
            # Store forecast data
            self.forecast_data = forecast
            
            logging.info(f"Prophet forecast generated: {len(forecast)} data points")
            
        except Exception as e:
            logging.warning(f"Error generating Prophet forecast: {e}")
            self.forecast_data = None
            self.error_log.append(f"Forecast generation error: {e}")
    
    def export_to_csv(self, output_path=None):
        """Export collected data to CSV file."""
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_complete_data_{timestamp}.csv"
        
        try:
            # Convert data to DataFrame
            df = pd.DataFrame([self.data])
            
            # Add metadata
            df['data_collection_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            df['data_source'] = 'TickZen2 Pipeline'
            df['errors'] = '; '.join(self.error_log) if self.error_log else ''
            
            # Save to CSV
            df.to_csv(output_path, index=False)
            logging.info(f"Data exported successfully to CSV: {output_path}")
            
            return output_path
            
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            raise
    
    def export_to_json(self, output_path=None):
        """Export collected data to JSON file."""
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_complete_data_{timestamp}.json"
        
        try:
            # Prepare data for JSON serialization
            json_data = self.data.copy()
            
            # Add metadata
            json_data['data_collection_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            json_data['data_source'] = 'TickZen2 Pipeline'
            json_data['errors'] = self.error_log if self.error_log else []
            
            # Convert numpy types to native Python types for JSON serialization
            def convert_types(obj):
                """Convert numpy/pandas types to native Python types."""
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    # Round to 4 decimal places for readability
                    val = float(obj)
                    return round(val, 4) if val != 0 else val
                elif isinstance(obj, (np.ndarray, pd.Series)):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {k: convert_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_types(item) for item in obj]
                elif pd.isna(obj):
                    return None
                return obj
            
            json_data = convert_types(json_data)
            
            # Write to JSON file with pretty formatting
            with open(output_path, 'w') as f:
                json.dump(json_data, f, indent=2, default=str)
            
            logging.info(f"Data exported successfully to JSON: {output_path}")
            
            return output_path
            
        except Exception as e:
            logging.error(f"Error exporting to JSON: {e}")
            raise
    
    def export_all(self, csv_path=None, json_path=None):
        """Export data to both CSV and JSON formats, plus supplementary CSV files."""
        # Generate timestamp for consistent file naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export main data files
        csv_file = self.export_to_csv(csv_path)
        json_file = self.export_to_json(json_path)
        
        # Export supplementary CSV files
        insider_file = self.export_insider_transactions(f"{self.ticker}_insider_transactions_{timestamp}.csv")
        quarterly_file = self.export_quarterly_details(f"{self.ticker}_quarterly_earnings_{timestamp}.csv")
        peer_file = self.export_peer_data(f"{self.ticker}_peer_comparison_{timestamp}.csv")
        
        # Export historical time-series data
        historical_file = self.export_historical_data(f"{self.ticker}_historical_timeseries_{timestamp}.csv")
        
        # Export forecast data
        forecast_file = self.export_forecast_data(f"{self.ticker}_forecast_monthly_{timestamp}.csv")
        
        return {
            'main_csv': csv_file,
            'main_json': json_file,
            'insider_csv': insider_file,
            'quarterly_csv': quarterly_file,
            'peer_csv': peer_file,
            'historical_csv': historical_file,
            'forecast_csv': forecast_file
        }
    
    def export_insider_transactions(self, output_path=None):
        """Export detailed insider transaction records to CSV."""
        if not self.insider_transactions:
            logging.warning(f"No insider transactions to export for {self.ticker}")
            return None
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_insider_transactions_{timestamp}.csv"
        
        try:
            df = pd.DataFrame(self.insider_transactions)
            df.to_csv(output_path, index=False)
            logging.info(f"Insider transactions exported to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting insider transactions: {e}")
            return None
    
    def export_quarterly_details(self, output_path=None):
        """Export quarterly earnings data (one row per quarter) to CSV."""
        if not self.quarterly_details:
            logging.warning(f"No quarterly data to export for {self.ticker}")
            return None
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_quarterly_earnings_{timestamp}.csv"
        
        try:
            df = pd.DataFrame(self.quarterly_details)
            df.to_csv(output_path, index=False)
            logging.info(f"Quarterly data exported to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting quarterly data: {e}")
            return None
    
    def export_peer_data(self, output_path=None):
        """Export peer comparison data to CSV."""
        if not self.peer_data:
            logging.warning(f"No peer data to export for {self.ticker}")
            return None
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_peer_comparison_{timestamp}.csv"
        
        try:
            df = pd.DataFrame(self.peer_data)
            df.to_csv(output_path, index=False)
            logging.info(f"Peer data exported to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting peer data: {e}")
            return None
    
    def export_historical_data(self, output_path=None):
        """Export complete historical time-series data to CSV (10+ years of daily data)."""
        if self.historical_data is None or self.historical_data.empty:
            logging.warning(f"No historical data to export for {self.ticker}")
            return None
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_historical_timeseries_{timestamp}.csv"
        
        try:
            # Create comprehensive historical data export
            hist_df = self.historical_data.copy()
            hist_df.reset_index(inplace=True)
            
            # Add ticker column
            hist_df.insert(0, 'ticker', self.ticker)
            
            # Rename columns for clarity
            column_mapping = {
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividends',
                'Stock Splits': 'stock_splits'
            }
            hist_df.rename(columns=column_mapping, inplace=True)
            
            # Calculate basic technical indicators for historical data
            hist_df['sma_20'] = hist_df['close'].rolling(window=20).mean()
            hist_df['sma_50'] = hist_df['close'].rolling(window=50).mean()
            hist_df['sma_200'] = hist_df['close'].rolling(window=200).mean()
            
            # Calculate daily returns
            hist_df['daily_return_pct'] = hist_df['close'].pct_change() * 100
            
            # Calculate cumulative returns
            hist_df['cumulative_return_pct'] = ((hist_df['close'] / hist_df['close'].iloc[0]) - 1) * 100
            
            # Save to CSV
            hist_df.to_csv(output_path, index=False)
            logging.info(f"Historical data exported to: {output_path} ({len(hist_df)} rows)")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting historical data: {e}")
            return None
    
    def export_forecast_data(self, output_path=None):
        """Export Prophet forecast data to CSV (monthly forecasts for 1 year)."""
        if self.forecast_data is None or self.forecast_data.empty:
            logging.warning(f"No forecast data to export for {self.ticker}")
            return None
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.ticker}_forecast_monthly_{timestamp}.csv"
        
        try:
            # Create forecast export
            forecast_df = self.forecast_data.copy()
            
            # Add ticker column
            forecast_df.insert(0, 'ticker', self.ticker)
            
            # Rename columns for clarity
            column_mapping = {
                'ds': 'date',
                'yhat': 'forecast_price',
                'yhat_lower': 'forecast_lower_bound',
                'yhat_upper': 'forecast_upper_bound',
                'trend': 'trend_component',
                'seasonal': 'seasonal_component',
                'yearly': 'yearly_seasonality',
                'weekly': 'weekly_seasonality'
            }
            
            # Rename only columns that exist
            rename_dict = {k: v for k, v in column_mapping.items() if k in forecast_df.columns}
            forecast_df.rename(columns=rename_dict, inplace=True)
            
            # Calculate confidence interval width
            if 'forecast_lower_bound' in forecast_df.columns and 'forecast_upper_bound' in forecast_df.columns:
                forecast_df['confidence_interval_width'] = (
                    forecast_df['forecast_upper_bound'] - forecast_df['forecast_lower_bound']
                )
            
            # Save to CSV
            forecast_df.to_csv(output_path, index=False)
            logging.info(f"Forecast data exported to: {output_path} ({len(forecast_df)} rows)")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting forecast data: {e}")
            return None
        try:
            df = pd.DataFrame(self.peer_data)
            df.to_csv(output_path, index=False)
            logging.info(f"Peer data exported to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Error exporting peer data: {e}")
            return None


def process_multiple_tickers(tickers, output_path=None, format='both'):
    """Process multiple tickers and export to CSV and/or JSON.
    
    Args:
        tickers: List of ticker symbols
        output_path: Base output path (without extension)
        format: 'csv', 'json', or 'both' (default)
    
    Returns:
        Dict with all exported file paths
    """
    all_data = []
    json_array = []
    all_insider_transactions = []
    all_quarterly_details = []
    all_peer_data = []
    
    def convert_types(obj):
        """Convert numpy/pandas types to native Python types."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            val = float(obj)
            return round(val, 4) if val != 0 else val
        elif isinstance(obj, (np.ndarray, pd.Series)):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        elif pd.isna(obj):
            return None
        return obj
    
    for ticker in tickers:
        try:
            logging.info(f"\n{'='*60}")
            logging.info(f"Processing {ticker}...")
            logging.info(f"{'='*60}")
            
            exporter = TickerDataExporter(ticker)
            exporter.collect_all_data()
            all_data.append(exporter.data)
            
            # Collect insider transactions
            all_insider_transactions.extend(exporter.insider_transactions)
            
            # Collect quarterly details
            all_quarterly_details.extend(exporter.quarterly_details)
            
            # Collect peer data
            all_peer_data.extend(exporter.peer_data)
            
            # Prepare JSON data
            json_data = exporter.data.copy()
            json_data['data_collection_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            json_data['data_source'] = 'TickZen2 Pipeline'
            json_data['errors'] = exporter.error_log if exporter.error_log else []
            json_data = convert_types(json_data)
            json_array.append(json_data)
            
        except Exception as e:
            logging.error(f"Failed to process {ticker}: {e}")
            continue
    
    if not all_data:
        logging.error("No data collected for any ticker.")
        return None, None
    
    # Generate timestamp for consistency
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Generate output paths
    if not output_path:
        if len(tickers) == 1:
            base_name = f"{tickers[0]}_complete_data_{timestamp}"
        else:
            base_name = f"multi_ticker_data_{timestamp}"
    else:
        # Remove extension if provided
        base_name = output_path.replace('.csv', '').replace('.json', '')
    
    csv_path = f"{base_name}.csv"
    json_path = f"{base_name}.json"
    
    # Export to CSV if requested
    csv_file = None
    if format in ['csv', 'both']:
        try:
            # Create DataFrame
            df = pd.DataFrame(all_data)
            
            # Add metadata
            df['data_collection_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            df['data_source'] = 'TickZen2 Pipeline'
            
            # Save to CSV
            df.to_csv(csv_path, index=False)
            logging.info(f"CSV exported to: {csv_path}")
            csv_file = csv_path
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
    
    # Export supplementary CSV files
    insider_file = None
    quarterly_file = None
    peer_file = None
    
    if all_insider_transactions:
        insider_path = f"multi_ticker_insider_transactions_{timestamp}.csv" if len(tickers) > 1 else f"{tickers[0]}_insider_transactions_{timestamp}.csv"
        try:
            df_insider = pd.DataFrame(all_insider_transactions)
            df_insider.to_csv(insider_path, index=False)
            logging.info(f"Insider transactions CSV exported to: {insider_path}")
            insider_file = insider_path
        except Exception as e:
            logging.error(f"Error exporting insider transactions: {e}")
    
    if all_quarterly_details:
        quarterly_path = f"multi_ticker_quarterly_earnings_{timestamp}.csv" if len(tickers) > 1 else f"{tickers[0]}_quarterly_earnings_{timestamp}.csv"
        try:
            df_quarterly = pd.DataFrame(all_quarterly_details)
            df_quarterly.to_csv(quarterly_path, index=False)
            logging.info(f"Quarterly earnings CSV exported to: {quarterly_path}")
            quarterly_file = quarterly_path
        except Exception as e:
            logging.error(f"Error exporting quarterly data: {e}")
    
    if all_peer_data:
        peer_path = f"multi_ticker_peer_comparison_{timestamp}.csv" if len(tickers) > 1 else f"{tickers[0]}_peer_comparison_{timestamp}.csv"
        try:
            df_peer = pd.DataFrame(all_peer_data)
            df_peer.to_csv(peer_path, index=False)
            logging.info(f"Peer comparison CSV exported to: {peer_path}")
            peer_file = peer_path
        except Exception as e:
            logging.error(f"Error exporting peer data: {e}")
    
    # Export to JSON if requested
    json_file = None
    if format in ['json', 'both']:
        try:
            # Create JSON structure
            json_output = {
                'metadata': {
                    'data_collection_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'data_source': 'TickZen2 Pipeline',
                    'total_tickers': len(json_array),
                    'tickers': [t.upper() for t in tickers],
                    'total_variables': len(json_array[0]) if json_array else 0
                },
                'data': json_array
            }
            
            # Write to JSON file
            with open(json_path, 'w') as f:
                json.dump(json_output, f, indent=2, default=str)
            
            logging.info(f"JSON exported to: {json_path}")
            json_file = json_path
        except Exception as e:
            logging.error(f"Error exporting to JSON: {e}")
    
    # Print summary
    logging.info(f"\n{'='*60}")
    logging.info(f"Export Complete!")
    logging.info(f"{'='*60}")
    logging.info(f"Total tickers processed: {len(all_data)}")
    if all_data:
        logging.info(f"Total variables collected: {len(all_data[0])}")
    if csv_file:
        logging.info(f"Main CSV: {csv_file}")
    if insider_file:
        logging.info(f"Insider Transactions CSV: {insider_file} ({len(all_insider_transactions)} records)")
    if quarterly_file:
        logging.info(f"Quarterly Earnings CSV: {quarterly_file} ({len(all_quarterly_details)} records)")
    if peer_file:
        logging.info(f"Peer Comparison CSV: {peer_file} ({len(all_peer_data)} records)")
    if json_file:
        logging.info(f"Main JSON: {json_file}")
    logging.info(f"{'='*60}")
    
    return {
        'main_csv': csv_file,
        'main_json': json_file,
        'insider_csv': insider_file,
        'quarterly_csv': quarterly_file,
        'peer_csv': peer_file
    }


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Export complete ticker data from TickZen2 pipeline to CSV and/or JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ticker_data_exporter.py AAPL
  python ticker_data_exporter.py AAPL MSFT GOOGL
  python ticker_data_exporter.py AAPL --output my_data
  python ticker_data_exporter.py AAPL MSFT --output combined --format json
  python ticker_data_exporter.py AAPL --format both
        """
    )
    
    parser.add_argument('tickers', nargs='+', help='One or more ticker symbols')
    parser.add_argument('--output', '-o', help='Output file path (without extension)')
    parser.add_argument('--format', '-f', choices=['csv', 'json', 'both'], default='both',
                       help='Export format (default: both)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Process tickers
        result = process_multiple_tickers(args.tickers, args.output, args.format)
        
        if result and (result.get('main_csv') or result.get('main_json')):
            print(f"\n✅ Success! Files exported:")
            if result.get('main_csv'):
                print(f"   📊 Main CSV: {result['main_csv']}")
            if result.get('insider_csv'):
                print(f"   👤 Insider Transactions CSV: {result['insider_csv']}")
            if result.get('quarterly_csv'):
                print(f"   📅 Quarterly Earnings CSV: {result['quarterly_csv']}")
            if result.get('peer_csv'):
                print(f"   🏢 Peer Comparison CSV: {result['peer_csv']}")
            if result.get('historical_csv'):
                print(f"   📈 Historical Time-Series CSV: {result['historical_csv']}")
            if result.get('forecast_csv'):
                print(f"   🔮 Monthly Forecast CSV: {result['forecast_csv']}")
            if result.get('main_json'):
                print(f"   📄 Main JSON: {result['main_json']}")
            return 0
        else:
            print("\n❌ Failed to export data.")
            return 1
            
    except Exception as e:
        logging.error(f"Script failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
