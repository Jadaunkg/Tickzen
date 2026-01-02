"""
Earnings Data Processor Module

Processes, normalizes, and validates earnings data collected from multiple sources.
Handles data merging, calculation of derived metrics, and data quality checks.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

try:
    from .earnings_config import EarningsConfig
except ImportError:
    from earnings_config import EarningsConfig

logger = logging.getLogger(__name__)

# Try to import Finnhub utilities
try:
    try:
        from .finnhub_financials import fetch_balance_sheet_supplement
    except ImportError:
        from finnhub_financials import fetch_balance_sheet_supplement
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False
    logger.warning("Finnhub financials module not available")

# Try to import Enhanced Data Extractor
try:
    try:
        from .enhanced_data_extractor import enhance_earnings_data_for_ticker
    except ImportError:
        from enhanced_data_extractor import enhance_earnings_data_for_ticker
    ENHANCED_EXTRACTOR_AVAILABLE = True
except ImportError:
    ENHANCED_EXTRACTOR_AVAILABLE = False
    logger.warning("Enhanced data extractor module not available")


class EarningsDataProcessor:
    """
    Processes and normalizes earnings data from multiple sources.
    
    This class takes raw data from yfinance, Alpha Vantage, and Finnhub,
    normalizes it to a standard format, fills gaps, calculates derived metrics,
    and validates data quality.
    """
    
    def __init__(self, config: Optional[EarningsConfig] = None):
        """
        Initialize the data processor.
        
        Args:
            config: Optional EarningsConfig instance
        """
        self.config = config or EarningsConfig()
    
    def process_earnings_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw earnings data into normalized format.
        
        Args:
            raw_data: Raw data from EarningsDataCollector
            
        Returns:
            Processed and normalized earnings data
        """
        ticker = raw_data.get('ticker', 'UNKNOWN')
        logger.info(f"Processing earnings data for {ticker}")
        
        processed_data = {
            'ticker': ticker,
            'processing_timestamp': datetime.now().isoformat(),
            'data_quality': {},
            'earnings_data': {}
        }
        
        # Extract and normalize data by category
        processed_data['earnings_data']['company_identification'] = self._process_company_identification(raw_data)
        processed_data['earnings_data']['earnings_timeline'] = self._process_earnings_timeline(raw_data)
        processed_data['earnings_data']['income_statement'] = self._process_income_statement(raw_data)
        processed_data['earnings_data']['balance_sheet'] = self._process_balance_sheet(raw_data)
        processed_data['earnings_data']['cash_flow'] = self._process_cash_flow(raw_data)
        processed_data['earnings_data']['analyst_estimates'] = self._process_analyst_estimates(raw_data)
        processed_data['earnings_data']['actual_vs_estimate'] = self._process_actual_vs_estimate(raw_data)
        processed_data['earnings_data']['stock_price'] = self._process_stock_price(raw_data)
        processed_data['earnings_data']['guidance'] = self._process_guidance(raw_data)
        
        # Add new comprehensive data processing
        processed_data['earnings_data']['analyst_sentiment'] = self._process_analyst_sentiment(raw_data)
        processed_data['earnings_data']['valuation_metrics'] = self._process_valuation_metrics(raw_data)
        processed_data['earnings_data']['performance_metrics'] = self._process_performance_metrics(raw_data)
        processed_data['earnings_data']['key_focus_areas'] = self._identify_key_focus_areas(raw_data)
        processed_data['earnings_data']['risk_factors'] = self._assess_risks(raw_data)
        
        # ENHANCED ANALYTICS INTEGRATION - Phase 1
        processed_data['earnings_data']['enhanced_analytics'] = self._process_enhanced_analytics(raw_data)
        processed_data['earnings_data']['risk_factors'] = self._assess_risks(raw_data)
        
        # Get yf_info for ratio calculations
        yf_info = self._safe_get(raw_data, ['data_sources', 'yfinance', 'data', 'info']) or {}
        processed_data['earnings_data']['calculated_ratios'] = self._calculate_ratios(processed_data['earnings_data'], yf_info)
        
        # Validate data quality
        processed_data['data_quality'] = self._validate_data_quality(processed_data['earnings_data'])
        
        # ENHANCED DATA EXTRACTION - Fill missing values and improve data completeness
        if ENHANCED_EXTRACTOR_AVAILABLE:
            try:
                processed_data = enhance_earnings_data_for_ticker(processed_data, raw_data)
                logger.info(f"Enhanced data extraction completed for {ticker}")
                
                # Re-validate data quality after enhancement
                processed_data['data_quality'] = self._validate_data_quality(processed_data['earnings_data'])
                
            except Exception as e:
                logger.error(f"Enhanced data extraction failed for {ticker}: {e}")
        else:
            logger.warning("Enhanced data extractor not available, skipping data enhancement")
        
        logger.info(f"Completed processing for {ticker}")
        return processed_data
    
    def _process_company_identification(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process company identification data using ONLY yfinance"""
        company_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Get yfinance data
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        
        # Ticker
        company_data['ticker'] = raw_data.get('ticker', 'N/A')
        
        # Company Name
        company_data['company_name'] = yf_info.get('longName') or yf_info.get('shortName') or 'N/A'
        
        # CIK (Central Index Key)
        cik_value = yf_info.get('cik')
        company_data['cik'] = str(cik_value) if cik_value else 'N/A'
        
        # Exchange
        company_data['exchange'] = yf_info.get('exchange') or 'N/A'
        
        # Sector
        company_data['sector'] = yf_info.get('sector') or 'N/A'
        
        # Industry
        company_data['industry'] = yf_info.get('industry') or 'N/A'
        
        # Market Cap
        company_data['market_cap'] = yf_info.get('marketCap') or 'N/A'
        
        # Description
        company_data['description'] = yf_info.get('longBusinessSummary') or 'N/A'
        
        # Website
        company_data['website'] = yf_info.get('website') or 'N/A'
        
        # Headquarters
        city = yf_info.get('city') or ''
        state = yf_info.get('state') or ''
        country = yf_info.get('country') or ''
        headquarters_parts = [p for p in [city, state, country] if p]
        company_data['headquarters'] = ', '.join(headquarters_parts) if headquarters_parts else 'N/A'
        
        # CEO Name
        officers = yf_info.get('companyOfficers')
        if officers and isinstance(officers, list):
            for officer in officers:
                title = officer.get('title', '').lower()
                if 'ceo' in title or 'chief executive' in title:
                    company_data['ceo_name'] = officer.get('name', 'N/A')
                    break
            else:
                company_data['ceo_name'] = 'N/A'
        else:
            company_data['ceo_name'] = 'N/A'
        
        return company_data
    
    def _process_earnings_timeline(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process earnings timeline data using ONLY yfinance"""
        timeline_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Get yfinance data
        yf_calendar = self._safe_get(sources, ['yfinance', 'data', 'calendar'])
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        yf_quarterly_financials = self._safe_get(sources, ['yfinance', 'data', 'quarterly_financials'])
        
        if yf_calendar and isinstance(yf_calendar, dict):
            earnings_date = yf_calendar.get('Earnings Date')
            if earnings_date:
                from datetime import datetime, timezone
                today = datetime.now(timezone.utc).date()
                
                # Handle list of dates (filter for future dates only)
                if isinstance(earnings_date, list) and len(earnings_date) > 0:
                    # Filter for future dates only
                    future_dates = []
                    for date in earnings_date:
                        try:
                            if hasattr(date, 'date'):
                                date_obj = date.date()
                            elif isinstance(date, str):
                                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                            else:
                                date_obj = date
                            
                            # Only include dates that are today or in the future
                            if date_obj >= today:
                                future_dates.append(date)
                        except Exception as e:
                            logger.warning(f"Error parsing earnings date {date}: {e}")
                            continue
                    
                    # Use the earliest future date, or first date if no future dates
                    if future_dates:
                        earnings_date = future_dates[0]
                    else:
                        # No future dates available, mark as N/A
                        earnings_date = None
                        logger.warning(f"All earnings dates are in the past for this ticker")
                
                # Convert to string format
                if earnings_date:
                    if hasattr(earnings_date, 'strftime'):
                        timeline_data['earnings_date'] = earnings_date.strftime('%Y-%m-%d')
                    else:
                        timeline_data['earnings_date'] = str(earnings_date)
                else:
                    timeline_data['earnings_date'] = 'N/A'
            else:
                timeline_data['earnings_date'] = 'N/A'
        else:
            timeline_data['earnings_date'] = 'N/A'
        
        # Earnings Time (BMO - Before Market Open, AMC - After Market Close, or specific time)
        # yfinance doesn't provide specific time, default to 'N/A'
        timeline_data['earnings_time'] = 'N/A'
        
        # Report Time (when the report is released)
        timeline_data['report_time'] = timeline_data['earnings_time']  # Usually same
        
        # Fiscal Quarter & Year - get from mostRecentQuarter or quarterly income statement
        most_recent_quarter = yf_info.get('mostRecentQuarter')
        if most_recent_quarter:
            # mostRecentQuarter is a timestamp
            from datetime import datetime
            try:
                quarter_date = datetime.fromtimestamp(most_recent_quarter)
                quarter_month = quarter_date.month
                fiscal_quarter = ((quarter_month - 1) // 3) + 1  # 1-4
                timeline_data['fiscal_quarter'] = f"Q{fiscal_quarter}"
                timeline_data['fiscal_year'] = quarter_date.year
                timeline_data['fiscal_year_end'] = quarter_date.strftime('%Y-%m-%d')
            except:
                timeline_data['fiscal_quarter'] = 'N/A'
                timeline_data['fiscal_year'] = 'N/A'
                timeline_data['fiscal_year_end'] = yf_info.get('lastFiscalYearEnd', 'N/A')
        else:
            timeline_data['fiscal_quarter'] = 'N/A'
            timeline_data['fiscal_year'] = 'N/A'
            timeline_data['fiscal_year_end'] = yf_info.get('lastFiscalYearEnd', 'N/A')
        
        # Filing information (not directly available in yfinance)
        timeline_data['filing_date'] = 'N/A'
        timeline_data['period_end_date'] = timeline_data.get('fiscal_year_end', 'N/A')
        timeline_data['filing_type'] = 'N/A'  # Would be 10-Q or 10-K
        
        # Reporting type
        timeline_data['reporting_type'] = 'N/A'  # BMO/AMC/During Hours
        
        # Earnings Call Details - typically not available in free APIs
        timeline_data['earnings_call_time'] = 'N/A'
        timeline_data['earnings_call_date'] = timeline_data['earnings_date']  # Usually same day
        timeline_data['conference_call_url'] = 'N/A'
        
        # Calculate days until earnings (if future date)
        if timeline_data['earnings_date'] != 'N/A':
            try:
                earnings_dt = pd.to_datetime(timeline_data['earnings_date'])
                today = pd.Timestamp.now()
                days_diff = (earnings_dt - today).days
                timeline_data['days_until_earnings'] = max(0, days_diff) if days_diff >= 0 else 'Past'
            except:
                timeline_data['days_until_earnings'] = 'N/A'
        else:
            timeline_data['days_until_earnings'] = 'N/A'
        
        return timeline_data
    
    def _process_income_statement(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process income statement data using ONLY yfinance"""
        income_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Get the most recent quarterly data from yfinance only
        yf_quarterly = self._safe_get(sources, ['yfinance', 'data', 'quarterly_income_stmt'])
        yf_cashflow = self._safe_get(sources, ['yfinance', 'data', 'quarterly_cashflow'])
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        
        # Total Revenue
        income_data['total_revenue'] = (
            self._get_latest_financial_value(yf_quarterly, 'Total Revenue') or
            yf_info.get('totalRevenue') or
            'N/A'
        )
        
        # Revenue Growth YoY
        revenue_growth = yf_info.get('revenueGrowth')
        if revenue_growth:
            income_data['revenue_growth_yoy'] = f"{revenue_growth * 100:.2f}%" if isinstance(revenue_growth, (int, float)) else revenue_growth
        else:
            income_data['revenue_growth_yoy'] = 'N/A'
        
        # Cost of Revenue
        income_data['cost_of_revenue'] = (
            self._get_latest_financial_value(yf_quarterly, 'Cost Of Revenue') or
            'N/A'
        )
        
        # Gross Profit
        income_data['gross_profit'] = (
            self._get_latest_financial_value(yf_quarterly, 'Gross Profit') or
            'N/A'
        )
        
        # Gross Margin - calculate if not available
        if income_data['gross_profit'] != 'N/A' and income_data['total_revenue'] != 'N/A':
            try:
                margin = (float(income_data['gross_profit']) / float(income_data['total_revenue'])) * 100
                income_data['gross_margin'] = f"{margin:.2f}%"
            except:
                income_data['gross_margin'] = yf_info.get('grossMargins', 'N/A')
        else:
            income_data['gross_margin'] = yf_info.get('grossMargins', 'N/A')
        
        # Operating Expenses
        income_data['operating_expenses'] = (
            self._get_latest_financial_value(yf_quarterly, 'Operating Expense') or
            'N/A'
        )
        
        # Research & Development
        income_data['research_and_development'] = (
            self._get_latest_financial_value(yf_quarterly, 'Research And Development') or
            'N/A'
        )
        
        # Sales and Marketing (Selling General Administrative in yfinance)
        sga = self._get_latest_financial_value(yf_quarterly, 'Selling General And Administration')
        if not sga:
            # Try alternative field name
            sga = self._get_latest_financial_value(yf_quarterly, 'Selling General And Administrative')
        income_data['sales_and_marketing'] = sga or 'N/A'
        
        # General and Administrative
        income_data['general_and_administrative'] = income_data['sales_and_marketing']  # Combined in yfinance
        
        # Operating Income
        income_data['operating_income'] = (
            self._get_latest_financial_value(yf_quarterly, 'Operating Income') or
            yf_info.get('operatingCashflow') or
            'N/A'
        )
        
        # Operating Margin
        if income_data['operating_income'] != 'N/A' and income_data['total_revenue'] != 'N/A':
            try:
                margin = (float(income_data['operating_income']) / float(income_data['total_revenue'])) * 100
                income_data['operating_margin'] = f"{margin:.2f}%"
            except:
                income_data['operating_margin'] = yf_info.get('operatingMargins', 'N/A')
        else:
            income_data['operating_margin'] = yf_info.get('operatingMargins', 'N/A')
        
        # EBITDA
        income_data['ebitda'] = (
            self._get_latest_financial_value(yf_quarterly, 'EBITDA') or
            self._get_latest_financial_value(yf_quarterly, 'Normalized EBITDA') or
            yf_info.get('ebitda') or
            'N/A'
        )
        
        # Depreciation and Amortization
        income_data['depreciation_and_amortization'] = (
            self._get_latest_financial_value(yf_quarterly, 'Reconciled Depreciation') or
            'N/A'
        )
        
        # Interest Expense
        income_data['interest_expense'] = (
            self._get_latest_financial_value(yf_quarterly, 'Interest Expense') or
            'N/A'
        )
        
        # Tax Provision
        income_data['tax_provision'] = (
            self._get_latest_financial_value(yf_quarterly, 'Tax Provision') or
            self._get_latest_financial_value(yf_quarterly, 'Tax Effect Of Unusual Items') or
            'N/A'
        )
        
        # Stock Based Compensation (from cash flow statement)
        income_data['stock_based_compensation'] = (
            self._get_latest_financial_value(yf_cashflow, 'Stock Based Compensation') or
            'N/A'
        )
        
        # Net Income
        income_data['net_income'] = (
            self._get_latest_financial_value(yf_quarterly, 'Net Income') or
            yf_info.get('netIncomeToCommon') or
            'N/A'
        )
        
        # EPS (Earnings Per Share)
        income_data['earnings_per_share_basic'] = yf_info.get('trailingEps') or 'N/A'
        income_data['earnings_per_share_diluted'] = income_data['earnings_per_share_basic']  # Same in yfinance
        
        # Weighted Average Shares
        income_data['weighted_average_shares_basic'] = yf_info.get('sharesOutstanding') or 'N/A'
        income_data['weighted_average_shares_diluted'] = yf_info.get('sharesOutstanding') or 'N/A'
        
        return income_data
    
    def _process_balance_sheet(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process balance sheet data using ONLY yfinance"""
        balance_data = {}
        sources = raw_data.get('data_sources', {})
        
        yf_balance = self._safe_get(sources, ['yfinance', 'data', 'quarterly_balance_sheet'])
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        
        # Total Assets
        balance_data['total_assets'] = (
            self._get_latest_financial_value(yf_balance, 'Total Assets') or
            'N/A'
        )
        
        # Current Assets
        balance_data['current_assets'] = (
            self._get_latest_financial_value(yf_balance, 'Current Assets') or
            'N/A'
        )
        
        # Cash and Equivalents
        balance_data['cash_and_equivalents'] = (
            self._get_latest_financial_value(yf_balance, 'Cash And Cash Equivalents') or
            yf_info.get('totalCash') or
            'N/A'
        )
        
        # Accounts Receivable
        balance_data['accounts_receivable'] = (
            self._get_latest_financial_value(yf_balance, 'Accounts Receivable') or
            'N/A'
        )
        
        # Inventory
        balance_data['inventory'] = (
            self._get_latest_financial_value(yf_balance, 'Inventory') or
            'N/A'
        )
        
        # Property, Plant & Equipment
        balance_data['property_plant_equipment'] = (
            self._get_latest_financial_value(yf_balance, 'Net PPE') or
            'N/A'
        )
        
        # Goodwill
        balance_data['goodwill'] = (
            self._get_latest_financial_value(yf_balance, 'Goodwill') or
            'N/A'
        )
        
        # Intangible Assets (Other Intangible Assets in yfinance)
        balance_data['intangible_assets'] = (
            self._get_latest_financial_value(yf_balance, 'Other Intangible Assets') or
            'N/A'
        )
        
        # Total Liabilities
        balance_data['total_liabilities'] = (
            self._get_latest_financial_value(yf_balance, 'Total Liabilities Net Minority Interest') or
            'N/A'
        )
        
        # Current Liabilities
        balance_data['current_liabilities'] = (
            self._get_latest_financial_value(yf_balance, 'Current Liabilities') or
            'N/A'
        )
        
        # Accounts Payable
        balance_data['accounts_payable'] = (
            self._get_latest_financial_value(yf_balance, 'Accounts Payable') or
            'N/A'
        )
        
        # Long-term Debt
        balance_data['long_term_debt'] = (
            self._get_latest_financial_value(yf_balance, 'Long Term Debt') or
            'N/A'
        )
        
        # Total Debt
        balance_data['total_debt'] = (
            yf_info.get('totalDebt') or
            'N/A'
        )
        
        # Stockholders Equity
        balance_data['stockholders_equity'] = (
            self._get_latest_financial_value(yf_balance, 'Stockholders Equity') or
            'N/A'
        )
        
        # Retained Earnings
        balance_data['retained_earnings'] = (
            self._get_latest_financial_value(yf_balance, 'Retained Earnings') or
            'N/A'
        )
        
        # Working Capital (calculate if possible)
        if (balance_data['current_assets'] != 'N/A' and 
            balance_data['current_liabilities'] != 'N/A'):
            try:
                balance_data['working_capital'] = float(balance_data['current_assets']) - float(balance_data['current_liabilities'])
            except (ValueError, TypeError):
                balance_data['working_capital'] = 'N/A'
        else:
            balance_data['working_capital'] = 'N/A'
        
        # Try to fetch missing fields from Finnhub if available
        if FINNHUB_AVAILABLE:
            missing_fields = [k for k, v in balance_data.items() if v == 'N/A']
            if missing_fields and ('goodwill' in missing_fields or 'intangible_assets' in missing_fields):
                ticker = raw_data.get('ticker', '')
                logger.info(f"Attempting to supplement balance sheet data from Finnhub for {ticker}")
                try:
                    finnhub_data = fetch_balance_sheet_supplement(ticker)
                    if finnhub_data:
                        for field, value in finnhub_data.items():
                            if field in balance_data and balance_data[field] == 'N/A':
                                balance_data[field] = value
                                logger.info(f"Filled {field} from Finnhub: {value}")
                except Exception as e:
                    logger.warning(f"Could not fetch Finnhub supplement: {str(e)}")
        
        return balance_data
    
    def _process_cash_flow(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process cash flow statement data using ONLY yfinance"""
        cashflow_data = {}
        sources = raw_data.get('data_sources', {})
        
        yf_cashflow = self._safe_get(sources, ['yfinance', 'data', 'quarterly_cashflow'])
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        
        # Operating Cash Flow
        cashflow_data['operating_cash_flow'] = (
            self._get_latest_financial_value(yf_cashflow, 'Operating Cash Flow') or
            yf_info.get('operatingCashflow') or
            'N/A'
        )
        
        # Investing Cash Flow
        cashflow_data['net_cash_investing'] = (
            self._get_latest_financial_value(yf_cashflow, 'Investing Cash Flow') or
            'N/A'
        )
        
        # Financing Cash Flow
        cashflow_data['net_cash_financing'] = (
            self._get_latest_financial_value(yf_cashflow, 'Financing Cash Flow') or
            'N/A'
        )
        
        # Free Cash Flow
        cashflow_data['free_cash_flow'] = (
            self._get_latest_financial_value(yf_cashflow, 'Free Cash Flow') or
            yf_info.get('freeCashflow') or
            'N/A'
        )
        
        # Capital Expenditures
        cashflow_data['capital_expenditures'] = (
            self._get_latest_financial_value(yf_cashflow, 'Capital Expenditure') or
            'N/A'
        )
        
        # Dividends Paid
        cashflow_data['dividends_paid'] = (
            self._get_latest_financial_value(yf_cashflow, 'Cash Dividends Paid') or
            'N/A'
        )
        
        # Share Repurchases
        cashflow_data['share_repurchases'] = (
            self._get_latest_financial_value(yf_cashflow, 'Repurchase Of Capital Stock') or
            'N/A'
        )
        
        return cashflow_data
    
    def _process_analyst_estimates(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process analyst estimate data using ONLY yfinance"""
        estimates_data = {}
        sources = raw_data.get('data_sources', {})
        
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        analyst_info = self._safe_get(sources, ['analyst', 'data']) or {}
        recommendations = self._safe_get(sources, ['yfinance', 'data', 'recommendations']) or {}
        
        # EPS Estimates from yfinance
        estimates_data['estimated_eps'] = yf_info.get('forwardEps') or 'N/A'
        estimates_data['estimated_eps_high'] = analyst_info.get('target_high_price') or 'N/A'
        estimates_data['estimated_eps_low'] = analyst_info.get('target_low_price') or 'N/A'
        estimates_data['number_of_analysts'] = yf_info.get('numberOfAnalystOpinions') or analyst_info.get('number_of_analyst_opinions') or 'N/A'
        
        # Revenue Estimates
        estimates_data['estimated_revenue'] = yf_info.get('targetMeanPrice') or 'N/A'  # Proxy
        estimates_data['estimated_revenue_high'] = 'N/A'
        estimates_data['estimated_revenue_low'] = 'N/A'
        
        # Year ago estimate (use previous year EPS)
        estimates_data['estimate_year_ago'] = yf_info.get('trailingEps') or 'N/A'
        
        # Analyst Recommendations - extract from recommendations dict
        # Format after serialization: {field: {index: value}}
        # Note: Keys can be integers (fresh data) or strings (from JSON cache)
        if recommendations and isinstance(recommendations, dict):
            # Get most recent (index 0 or '0')
            def get_rating_value(rating_dict, idx=0):
                """Get rating value, trying both int and string keys"""
                if not isinstance(rating_dict, dict):
                    return 0
                # Try integer key first, then string key
                return rating_dict.get(idx, rating_dict.get(str(idx), 0))
            
            strong_buy = get_rating_value(recommendations.get('strongBuy', {}))
            buy = get_rating_value(recommendations.get('buy', {}))
            hold = get_rating_value(recommendations.get('hold', {}))
            sell = get_rating_value(recommendations.get('sell', {}))
            strong_sell = get_rating_value(recommendations.get('strongSell', {}))
            
            logger.info(f"Analyst recommendations - strongBuy: {strong_buy}, buy: {buy}, hold: {hold}, sell: {sell}, strongSell: {strong_sell}")
            
            estimates_data['analysts_recommending_buy'] = int(strong_buy + buy)
            estimates_data['analysts_recommending_hold'] = int(hold)
            estimates_data['analysts_recommending_sell'] = int(sell + strong_sell)
        else:
            logger.warning(f"Recommendations not available or invalid format: {type(recommendations)}")
            estimates_data['analysts_recommending_buy'] = 'N/A'
            estimates_data['analysts_recommending_hold'] = 'N/A'
            estimates_data['analysts_recommending_sell'] = 'N/A'
        
        estimates_data['recommendation'] = yf_info.get('recommendationKey') or 'N/A'
        
        return estimates_data
    
    def _process_actual_vs_estimate(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process actual vs estimate data using ONLY yfinance"""
        actual_data = {}
        sources = raw_data.get('data_sources', {})
        
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        yf_quarterly_earnings = self._safe_get(sources, ['yfinance', 'data', 'quarterly_earnings'])
        
        # Get actual EPS from quarterly earnings
        actual_eps = yf_info.get('trailingEps') or 'N/A'
        estimated_eps = yf_info.get('forwardEps') or 'N/A'
        
        actual_data['eps_actual'] = actual_eps
        actual_data['estimated_eps_prior'] = estimated_eps
        actual_data['eps_surprise'] = 'N/A'
        actual_data['eps_surprise_percent'] = 'N/A'
        
        # Calculate surprise if both values available
        if actual_eps != 'N/A' and estimated_eps != 'N/A':
            try:
                actual_val = float(actual_eps)
                estimate_val = float(estimated_eps)
                if estimate_val != 0:
                    surprise = actual_val - estimate_val
                    surprise_pct = (surprise / abs(estimate_val)) * 100
                    actual_data['eps_surprise'] = f"{surprise:.4f}"
                    actual_data['eps_surprise_percent'] = f"{surprise_pct:.2f}%"
            except (ValueError, TypeError):
                pass
        
        # Revenue Actual vs Estimate
        actual_data['revenue_actual'] = yf_info.get('totalRevenue') or 'N/A'
        actual_data['estimated_revenue_prior'] = 'N/A'
        actual_data['revenue_surprise'] = 'N/A'
        actual_data['revenue_surprise_percent'] = 'N/A'
        
        return actual_data
    
    def _process_stock_price(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stock price data with comprehensive fields"""
        price_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Latest price info from yfinance
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        latest_price = self._safe_get(sources, ['yfinance', 'data', 'latest_price'])
        
        # Current Price - prioritize multiple sources
        price_data['current_price'] = (
            self._safe_get(sources, ['yfinance', 'data', 'info', 'currentPrice']) or
            self._safe_get(sources, ['yfinance', 'data', 'info', 'regularMarketPrice']) or
            (latest_price.get('close') if latest_price else None) or
            'N/A'
        )
        
        # Previous Close
        price_data['previous_close'] = yf_info.get('previousClose', 'N/A')
        
        # Open Price
        price_data['open_price'] = (
            yf_info.get('open') or
            yf_info.get('regularMarketOpen') or
            (latest_price.get('open') if latest_price else None) or
            'N/A'
        )
        
        # Day High
        price_data['day_high'] = (
            yf_info.get('dayHigh') or
            yf_info.get('regularMarketDayHigh') or
            (latest_price.get('high') if latest_price else None) or
            'N/A'
        )
        
        # Day Low
        price_data['day_low'] = (
            yf_info.get('dayLow') or
            yf_info.get('regularMarketDayLow') or
            (latest_price.get('low') if latest_price else None) or
            'N/A'
        )
        
        # Volume
        price_data['volume'] = (
            yf_info.get('volume') or
            yf_info.get('regularMarketVolume') or
            (latest_price.get('volume') if latest_price else None) or
            'N/A'
        )
        
        # Average Volume
        price_data['average_volume'] = (
            yf_info.get('averageVolume') or
            yf_info.get('averageVolume10days') or
            yf_info.get('averageDailyVolume10Day') or
            'N/A'
        )
        
        # 52 Week High/Low
        price_data['52_week_high'] = yf_info.get('fiftyTwoWeekHigh', 'N/A')
        price_data['52_week_low'] = yf_info.get('fiftyTwoWeekLow', 'N/A')
        
        # Price Change (1 day)
        if price_data['previous_close'] != 'N/A' and price_data['current_price'] != 'N/A':
            try:
                current = float(price_data['current_price'])
                prev = float(price_data['previous_close'])
                change = current - prev
                change_pct = (change / prev) * 100
                price_data['price_change_1d'] = round(change, 2)
                price_data['price_change_percent_1d'] = round(change_pct, 2)
            except (ValueError, TypeError):
                price_data['price_change_1d'] = 'N/A'
                price_data['price_change_percent_1d'] = 'N/A'
        else:
            price_data['price_change_1d'] = 'N/A'
            price_data['price_change_percent_1d'] = 'N/A'
        
        return price_data
        
        return price_data
    
    def _process_guidance(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process company guidance data using ONLY yfinance"""
        guidance_data = {}
        sources = raw_data.get('data_sources', {})\
        
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        
        # Guidance (limited in yfinance - use forward estimates as proxy)
        guidance_data['guidance_eps_low'] = 'N/A'
        guidance_data['guidance_eps_high'] = 'N/A'
        guidance_data['guidance_revenue_low'] = 'N/A'
        guidance_data['guidance_revenue_high'] = 'N/A'
        
        # Next year estimate
        guidance_data['next_year_estimate'] = yf_info.get('forwardEps') or 'N/A'
        
        return guidance_data
    
    def _process_analyst_sentiment(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process analyst sentiment including ratings and price targets"""
        sentiment_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Get analyst data
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info']) or {}
        yf_recommendations = self._safe_get(sources, ['yfinance', 'data', 'recommendations'])
        
        # Number of analysts
        sentiment_data['number_of_analysts'] = yf_info.get('numberOfAnalystOpinions', 'N/A')
        
        # Buy/Hold/Sell counts from recommendations DataFrame
        if yf_recommendations is not None and isinstance(yf_recommendations, dict) and yf_recommendations:
            try:
                # Recommendations is stored as dict after serialization
                # Find the most recent entry (first key)
                keys = list(yf_recommendations.keys())
                if keys:
                    first_key = keys[0]
                    if isinstance(yf_recommendations[first_key], dict):
                        latest = yf_recommendations[first_key]
                        sentiment_data['buy_ratings'] = int(latest.get('strongBuy', 0)) + int(latest.get('buy', 0))
                        sentiment_data['hold_ratings'] = int(latest.get('hold', 0))
                        sentiment_data['sell_ratings'] = int(latest.get('sell', 0)) + int(latest.get('strongSell', 0))
                    else:
                        sentiment_data['buy_ratings'] = 'N/A'
                        sentiment_data['hold_ratings'] = 'N/A'
                        sentiment_data['sell_ratings'] = 'N/A'
                else:
                    sentiment_data['buy_ratings'] = 'N/A'
                    sentiment_data['hold_ratings'] = 'N/A'
                    sentiment_data['sell_ratings'] = 'N/A'
            except:
                sentiment_data['buy_ratings'] = 'N/A'
                sentiment_data['hold_ratings'] = 'N/A'
                sentiment_data['sell_ratings'] = 'N/A'
        else:
            sentiment_data['buy_ratings'] = 'N/A'
            sentiment_data['hold_ratings'] = 'N/A'
            sentiment_data['sell_ratings'] = 'N/A'
        
        # Price targets from info dict
        sentiment_data['target_mean_price'] = yf_info.get('targetMeanPrice', 'N/A')
        sentiment_data['target_median_price'] = yf_info.get('targetMedianPrice', 'N/A')
        sentiment_data['target_high_price'] = yf_info.get('targetHighPrice', 'N/A')
        sentiment_data['target_low_price'] = yf_info.get('targetLowPrice', 'N/A')
        
        # Overall recommendation
        sentiment_data['recommendation'] = yf_info.get('recommendationKey', 'N/A')
        
        return sentiment_data
    
    def _process_valuation_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process comprehensive valuation metrics"""
        valuation_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Get valuation data
        valuation_info = self._safe_get(sources, ['valuation', 'data'])
        
        if valuation_info:
            valuation_data['market_cap'] = valuation_info.get('market_cap', 'N/A')
            valuation_data['trailing_pe'] = valuation_info.get('trailing_pe', 'N/A')
            valuation_data['forward_pe'] = valuation_info.get('forward_pe', 'N/A')
            valuation_data['peg_ratio'] = valuation_info.get('peg_ratio', 'N/A')
            valuation_data['price_to_sales'] = valuation_info.get('price_to_sales', 'N/A')
            valuation_data['price_to_book'] = valuation_info.get('price_to_book', 'N/A')
            valuation_data['enterprise_value'] = valuation_info.get('enterprise_value', 'N/A')
            valuation_data['ev_to_revenue'] = valuation_info.get('ev_to_revenue', 'N/A')
            valuation_data['ev_to_ebitda'] = valuation_info.get('ev_to_ebitda', 'N/A')
            valuation_data['dividend_yield'] = valuation_info.get('dividend_yield', 'N/A')
            valuation_data['sector'] = valuation_info.get('sector', 'N/A')
            valuation_data['industry'] = valuation_info.get('industry', 'N/A')
        else:
            # Fallback to yfinance info
            yf_info = self._safe_get(sources, ['yfinance', 'data', 'info'])
            if yf_info:
                valuation_data['market_cap'] = yf_info.get('marketCap', 'N/A')
                valuation_data['trailing_pe'] = yf_info.get('trailingPE', 'N/A')
                valuation_data['forward_pe'] = yf_info.get('forwardPE', 'N/A')
                valuation_data['peg_ratio'] = yf_info.get('pegRatio', 'N/A')
                valuation_data['price_to_sales'] = yf_info.get('priceToSalesTrailing12Months', 'N/A')
                valuation_data['price_to_book'] = yf_info.get('priceToBook', 'N/A')
                valuation_data['enterprise_value'] = yf_info.get('enterpriseValue', 'N/A')
                valuation_data['ev_to_revenue'] = yf_info.get('enterpriseToRevenue', 'N/A')
                valuation_data['ev_to_ebitda'] = yf_info.get('enterpriseToEbitda', 'N/A')
                valuation_data['dividend_yield'] = yf_info.get('dividendYield', 'N/A')
                valuation_data['sector'] = yf_info.get('sector', 'N/A')
                valuation_data['industry'] = yf_info.get('industry', 'N/A')
        
        return valuation_data
    
    def _process_performance_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stock performance metrics"""
        performance_data = {}
        sources = raw_data.get('data_sources', {})
        
        # Get performance data
        performance_info = self._safe_get(sources, ['performance', 'data'])
        
        if performance_info:
            performance_data['1_month_return'] = performance_info.get('1_month_return', 'N/A')
            performance_data['3_month_return'] = performance_info.get('3_month_return', 'N/A')
            performance_data['ytd_return'] = performance_info.get('ytd_return', 'N/A')
            performance_data['1_year_return'] = performance_info.get('1_year_return', 'N/A')
            performance_data['volatility_1y'] = performance_info.get('volatility_1y', 'N/A')
            performance_data['volume_trend'] = performance_info.get('volume_trend', 'N/A')
            performance_data['avg_volume_3m'] = performance_info.get('avg_volume_3m', 'N/A')
            performance_data['beta'] = performance_info.get('beta', 'N/A')
        else:
            performance_data['1_month_return'] = 'N/A'
            performance_data['3_month_return'] = 'N/A'
            performance_data['ytd_return'] = 'N/A'
            performance_data['1_year_return'] = 'N/A'
            performance_data['volatility_1y'] = 'N/A'
            performance_data['volume_trend'] = 'N/A'
            performance_data['avg_volume_3m'] = 'N/A'
            
            # Try to get beta from yfinance
            yf_info = self._safe_get(sources, ['yfinance', 'data', 'info'])
            performance_data['beta'] = yf_info.get('beta', 'N/A') if yf_info else 'N/A'
        
        return performance_data
    
    def _identify_key_focus_areas(self, raw_data: Dict[str, Any]) -> List[str]:
        """Identify company-specific key focus areas based on industry and business"""
        focus_areas = []
        sources = raw_data.get('data_sources', {})
        
        # Get company info
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info'])
        sector = yf_info.get('sector', '') if yf_info else ''
        industry = yf_info.get('industry', '') if yf_info else ''
        ticker = raw_data.get('ticker', '')
        
        # Define focus areas based on sector/industry/ticker
        if 'Technology' in sector:
            focus_areas.extend([
                'Revenue growth and market share trends',
                'Product innovation and new releases',
                'Cloud and subscription services growth',
                'Margin expansion and operating leverage',
                'R&D spending and future product pipeline'
            ])
        
        if ticker in ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA']:
            # Tech giants - add specific areas
            if ticker == 'AAPL':
                focus_areas = [
                    'iPhone revenue and unit sales trends',
                    'Services revenue growth (App Store, iCloud, Apple Music)',
                    'Mac and iPad performance',
                    'Wearables and Accessories growth',
                    'Greater China revenue trends',
                    'Gross margin outlook and product mix'
                ]
            elif ticker == 'MSFT':
                focus_areas = [
                    'Azure cloud revenue growth',
                    'Microsoft 365 commercial and consumer adoption',
                    'LinkedIn revenue trends',
                    'Gaming division performance (Xbox, Game Pass)',
                    'AI integration and Copilot adoption',
                    'Operating margin expansion'
                ]
            elif ticker in ['GOOGL', 'GOOG']:
                focus_areas = [
                    'Search advertising revenue trends',
                    'YouTube advertising and subscription growth',
                    'Google Cloud revenue and profitability',
                    'Traffic acquisition costs (TAC)',
                    'Other Bets performance',
                    'AI investments and integration'
                ]
            elif ticker == 'AMZN':
                focus_areas = [
                    'AWS revenue growth and operating income',
                    'North America e-commerce sales',
                    'International segment performance',
                    'Advertising services revenue',
                    'Prime membership trends',
                    'Operating margin improvement'
                ]
            elif ticker == 'TSLA':
                focus_areas = [
                    'Vehicle deliveries and production capacity',
                    'Average selling price trends',
                    'Energy generation and storage revenue',
                    'Automotive gross margin (ex-credits)',
                    'Full Self-Driving (FSD) adoption',
                    'New product launches and timeline'
                ]
        
        elif 'Financial' in sector or 'Bank' in industry:
            focus_areas.extend([
                'Net interest income and margin trends',
                'Loan growth and credit quality',
                'Non-interest income sources',
                'Expense management and efficiency ratio',
                'Capital return (dividends and buybacks)',
                'Regulatory environment impact'
            ])
        
        elif 'Healthcare' in sector or 'Pharmaceuticals' in industry:
            focus_areas.extend([
                'Drug pipeline and FDA approvals',
                'Patent expirations and generic competition',
                'Clinical trial results',
                'Market share in key therapeutic areas',
                'Pricing pressure and reimbursement trends',
                'M&A activity'
            ])
        
        elif 'Consumer' in sector or 'Retail' in industry:
            focus_areas.extend([
                'Same-store sales growth',
                'E-commerce penetration and growth',
                'Gross margin trends',
                'Inventory management',
                'Customer acquisition and retention',
                'Store expansion or optimization plans'
            ])
        
        elif 'Energy' in sector:
            focus_areas.extend([
                'Production volumes and growth',
                'Commodity price realization',
                'Operating costs per unit',
                'Capital expenditure plans',
                'Inventory levels',
                'Renewable energy initiatives'
            ])
        
        # Generic focus areas if no specific match
        if not focus_areas:
            focus_areas = [
                'Revenue growth trends',
                'Profitability and margin performance',
                'Market share dynamics',
                'Cost management initiatives',
                'Capital allocation strategy',
                'Guidance and outlook commentary'
            ]
        
        return focus_areas[:6]  # Limit to 6 key areas
    
    def _assess_risks(self, raw_data: Dict[str, Any]) -> List[str]:
        """Assess and list key risks based on company, sector, and market conditions"""
        risks = []
        sources = raw_data.get('data_sources', {})
        
        # Get company info
        yf_info = self._safe_get(sources, ['yfinance', 'data', 'info'])
        sector = yf_info.get('sector', '') if yf_info else ''
        industry = yf_info.get('industry', '') if yf_info else ''
        
        # Financial health risks
        balance_sheet = self._safe_get(sources, ['yfinance', 'data', 'quarterly_balance_sheet'])
        if balance_sheet:
            debt_to_equity = self._to_float(yf_info.get('debtToEquity')) if yf_info else None
            if debt_to_equity and debt_to_equity > 2.0:
                risks.append('High debt levels relative to equity')
        
        # Sector-specific risks
        if 'Technology' in sector:
            risks.extend([
                'Rapid technological change and innovation pressure',
                'Cybersecurity threats and data privacy concerns',
                'Intense competition from established and emerging players'
            ])
        
        if 'Financial' in sector:
            risks.extend([
                'Interest rate sensitivity and Federal Reserve policy',
                'Credit risk and loan portfolio quality',
                'Regulatory changes and compliance costs'
            ])
        
        if 'Healthcare' in sector:
            risks.extend([
                'Drug pricing pressure and regulatory scrutiny',
                'Clinical trial failures or delays',
                'Patent expirations and generic competition'
            ])
        
        if 'Consumer' in sector:
            risks.extend([
                'Consumer spending weakness or recession',
                'Input cost inflation (labor, materials, shipping)',
                'Supply chain disruptions'
            ])
        
        if 'Energy' in sector:
            risks.extend([
                'Commodity price volatility',
                'Geopolitical tensions affecting supply',
                'Climate policy and ESG pressures'
            ])
        
        # Add generic market risks
        risks.extend([
            'Macroeconomic uncertainty and recession risk',
            'Foreign exchange fluctuations',
            'Geopolitical instability'
        ])
        
        return risks[:5]  # Limit to 5 key risks
    
    def _calculate_ratios(self, earnings_data: Dict[str, Any], yf_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate financial ratios from processed data"""
        ratios = {}
        
        if yf_info is None:
            yf_info = {}
        
        # Extract needed values
        net_income = self._to_float(earnings_data.get('income_statement', {}).get('net_income'))
        total_revenue = self._to_float(earnings_data.get('income_statement', {}).get('total_revenue'))
        operating_income = self._to_float(earnings_data.get('income_statement', {}).get('operating_income'))
        gross_profit = self._to_float(earnings_data.get('income_statement', {}).get('gross_profit'))
        
        total_assets = self._to_float(earnings_data.get('balance_sheet', {}).get('total_assets'))
        stockholders_equity = self._to_float(earnings_data.get('balance_sheet', {}).get('stockholders_equity'))
        total_debt = self._to_float(earnings_data.get('balance_sheet', {}).get('total_debt'))
        current_assets = self._to_float(earnings_data.get('balance_sheet', {}).get('current_assets'))
        current_liabilities = self._to_float(earnings_data.get('balance_sheet', {}).get('current_liabilities'))
        
        price = self._to_float(earnings_data.get('stock_price', {}).get('current_price'))
        eps = self._to_float(earnings_data.get('income_statement', {}).get('earnings_per_share_diluted'))
        
        # Use yf_info values when available (these are more reliable)
        # Gross Margin
        ratios['gross_margin'] = yf_info.get('grossMargins')
        if ratios['gross_margin'] and isinstance(ratios['gross_margin'], (int, float)):
            ratios['gross_margin'] = round(ratios['gross_margin'] * 100, 2)
        elif gross_profit and total_revenue and total_revenue != 0:
            ratios['gross_margin'] = round((gross_profit / total_revenue) * 100, 2)
        else:
            ratios['gross_margin'] = 'N/A'
        
        # Operating Margin
        ratios['operating_margin'] = yf_info.get('operatingMargins')
        if ratios['operating_margin'] and isinstance(ratios['operating_margin'], (int, float)):
            ratios['operating_margin'] = round(ratios['operating_margin'] * 100, 2)
        elif operating_income and total_revenue and total_revenue != 0:
            ratios['operating_margin'] = round((operating_income / total_revenue) * 100, 2)
        else:
            ratios['operating_margin'] = 'N/A'
        
        # Profit Margin
        ratios['profit_margin'] = yf_info.get('profitMargins')
        if ratios['profit_margin'] and isinstance(ratios['profit_margin'], (int, float)):
            ratios['profit_margin'] = round(ratios['profit_margin'] * 100, 2)
        elif net_income and total_revenue and total_revenue != 0:
            ratios['profit_margin'] = round((net_income / total_revenue) * 100, 2)
        else:
            ratios['profit_margin'] = 'N/A'
        
        # Return on Equity (ROE)
        ratios['return_on_equity'] = yf_info.get('returnOnEquity')
        if ratios['return_on_equity'] and isinstance(ratios['return_on_equity'], (int, float)):
            ratios['return_on_equity'] = round(ratios['return_on_equity'] * 100, 2)
        elif net_income and stockholders_equity and stockholders_equity != 0:
            ratios['return_on_equity'] = round((net_income / stockholders_equity) * 100, 2)
        else:
            ratios['return_on_equity'] = 'N/A'
        
        # Return on Assets (ROA)
        ratios['return_on_assets'] = yf_info.get('returnOnAssets')
        if ratios['return_on_assets'] and isinstance(ratios['return_on_assets'], (int, float)):
            ratios['return_on_assets'] = round(ratios['return_on_assets'] * 100, 2)
        elif net_income and total_assets and total_assets != 0:
            ratios['return_on_assets'] = round((net_income / total_assets) * 100, 2)
        else:
            ratios['return_on_assets'] = 'N/A'
        
        # Debt to Equity
        ratios['debt_to_equity'] = yf_info.get('debtToEquity')
        if ratios['debt_to_equity'] and isinstance(ratios['debt_to_equity'], (int, float)):
            ratios['debt_to_equity'] = round(ratios['debt_to_equity'], 2)
        elif total_debt and stockholders_equity and stockholders_equity != 0:
            ratios['debt_to_equity'] = round(total_debt / stockholders_equity, 2)
        else:
            ratios['debt_to_equity'] = 'N/A'
        
        # Current Ratio
        ratios['current_ratio'] = yf_info.get('currentRatio')
        if ratios['current_ratio'] and isinstance(ratios['current_ratio'], (int, float)):
            ratios['current_ratio'] = round(ratios['current_ratio'], 2)
        elif current_assets and current_liabilities and current_liabilities != 0:
            ratios['current_ratio'] = round(current_assets / current_liabilities, 2)
        else:
            ratios['current_ratio'] = 'N/A'
        
        # P/E Ratio
        ratios['pe_ratio'] = yf_info.get('trailingPE')
        if ratios['pe_ratio'] and isinstance(ratios['pe_ratio'], (int, float)):
            ratios['pe_ratio'] = round(ratios['pe_ratio'], 2)
        elif price and eps and eps != 0:
            ratios['pe_ratio'] = round(price / eps, 2)
        else:
            ratios['pe_ratio'] = 'N/A'
        
        return ratios
    
    def _validate_data_quality(self, earnings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data quality and completeness - ENHANCED VERSION"""
        quality = {
            'completeness_score': 0,
            'missing_critical_fields': [],
            'data_age': 'N/A',
            'source_coverage': {},
            'field_completeness': {}
        }
        
        # Critical fields with flexible field mapping
        critical_fields_mapping = {
            'company_identification': {
                'ticker': ['ticker', 'symbol'],
                'company_name': ['company_name', 'longName', 'name']
            },
            'income_statement': {
                'revenue': ['total_revenue', 'revenue', 'net_sales'],
                'net_income': ['net_income', 'netIncome'],
                'eps_diluted': ['earnings_per_share_diluted', 'eps_diluted', 'trailingEps']
            },
            'balance_sheet': {
                'total_assets': ['total_assets', 'totalAssets'],
                'total_liabilities': ['total_liabilities', 'totalLiabilities']
            },
            'stock_price': {
                'current_price': ['current_price', 'currentPrice', 'price']
            }
        }
        
        total_fields = 0
        present_fields = 0
        
        for category, field_mappings in critical_fields_mapping.items():
            category_data = earnings_data.get(category, {})
            
            for logical_field, possible_field_names in field_mappings.items():
                found = False
                
                # Try each possible field name
                for field_name in possible_field_names:
                    value = category_data.get(field_name)
                    if value is not None and value != 'N/A' and value != '':
                        found = True
                        present_fields += 1
                        break
                
                if not found:
                    quality['missing_critical_fields'].append(f"{category}.{logical_field}")
                
                total_fields += 1
        
        # Calculate overall completeness
        quality['completeness_score'] = round((present_fields / total_fields) * 100, 2)
        
        # Calculate section-wise completeness
        for section in ['company_identification', 'income_statement', 'balance_sheet', 'cash_flow', 'stock_price']:
            section_data = earnings_data.get(section, {})
            if section_data:
                non_na_count = sum(1 for v in section_data.values() if v not in [None, 'N/A', ''])
                total_count = len(section_data)
                if total_count > 0:
                    quality['field_completeness'][section] = round((non_na_count / total_count) * 100, 2)
        
        return quality
    
    # Helper methods
    def _safe_get(self, data: Dict, keys: List[str], default: Any = None) -> Any:
        """Safely navigate nested dictionary"""
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
                if data is None:
                    return default
            else:
                return default
        return data if data is not None else default
    
    def _get_latest_financial_value(self, df_dict: Any, key: str) -> Any:
        """Extract latest value from financial dataframe dictionary"""
        if not df_dict or not isinstance(df_dict, dict):
            return None
        
        try:
            # df_dict format is {date: {field: value}} after pandas to_dict()
            # Get sorted dates (most recent first)
            dates = sorted(df_dict.keys(), reverse=True)
            
            if not dates:
                return None
            
            # Look through dates starting with most recent
            for date in dates:
                if key in df_dict[date]:
                    value = df_dict[date][key]
                    # Return if not None or NaN
                    if value is not None and not (isinstance(value, float) and value != value):
                        return value
            
            return None
            
        except (KeyError, IndexError, TypeError):
            pass
        
        return None
    
    def _get_latest_av_value(self, reports: Any, key: str) -> Any:
        """Extract latest value from Alpha Vantage quarterly reports"""
        if not reports or not isinstance(reports, list) or len(reports) == 0:
            return None
        
        try:
            latest = reports[0]
            return latest.get(key)
        except (KeyError, IndexError, TypeError):
            return None
    
    def _to_float(self, value: Any) -> Optional[float]:
        """Convert value to float, return None if not possible"""
        if value == 'N/A' or value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _extract_quarter_from_date(self, date_str: str) -> str:
        """Extract quarter (Q1-Q4) from a date string"""
        if not date_str or date_str == 'N/A':
            return 'N/A'
        
        try:
            # Parse date (format: YYYY-MM-DD)
            date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
            month = date_obj.month
            
            if 1 <= month <= 3:
                return 'Q1'
            elif 4 <= month <= 6:
                return 'Q2'
            elif 7 <= month <= 9:
                return 'Q3'
            else:
                return 'Q4'
        except (ValueError, TypeError):
            return 'N/A'
    
    def _process_enhanced_analytics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process enhanced analytics data including one-time items, adjusted earnings, and cash sustainability.
        
        Args:
            raw_data: Raw data from EarningsDataCollector including enhanced analytics
            
        Returns:
            Processed enhanced analytics data for reporting
        """
        enhanced_analytics = {
            'one_time_items': {},  # Changed from 'one_time_items_analysis' to match expected structure
            'adjusted_earnings': {},  # Changed from 'adjusted_earnings_analysis' to match expected structure
            'cash_sustainability': {},  # Changed from 'cash_sustainability_analysis' to match expected structure
            'summary_insights': [],
            'critical_flags': []
        }
        
        try:
            # Get enhanced analytics from raw data
            raw_enhanced = raw_data.get('enhanced_analytics', {})
            
            # Process one-time items analysis
            one_time_data = raw_enhanced.get('one_time_items', {})
            if one_time_data:
                # Pass through the raw one-time items data structure for the comprehensive test
                enhanced_analytics['one_time_items'] = one_time_data
                
                # Add insights
                if len(one_time_data.get('items_found', {})) > 0:
                    impact_millions = one_time_data.get('total_one_time_impact', 0) / 1000000
                    enhanced_analytics['summary_insights'].append(
                        f"Identified ${impact_millions:.1f}M in one-time items affecting reported earnings"
                    )
            
            # Process adjusted earnings analysis
            adjusted_data = raw_enhanced.get('adjusted_earnings', {})
            if adjusted_data:
                # Pass through the adjusted earnings data with expected structure
                enhanced_analytics['adjusted_earnings'] = adjusted_data
                
                # Add insights if there are meaningful adjustments
                if 'metrics' in adjusted_data:
                    metrics = adjusted_data['metrics']
                    adjusted_income = metrics.get('adjusted_net_income', {})
                    
                    if adjusted_income:
                        latest_period = max(adjusted_income.keys()) if adjusted_income.keys() else None
                        if latest_period:
                            latest_data = adjusted_income[latest_period]
                            improvement = latest_data.get('improvement', 0)
                            if improvement > 1000000:  # $1M improvement
                                enhanced_analytics['summary_insights'].append(
                                    f"Adjusted earnings show ${improvement/1000000:.1f}M improvement after removing one-time items"
                                )
            
            # Process cash sustainability analysis
            cash_data = raw_enhanced.get('cash_sustainability', {})
            if cash_data:
                # Pass through the cash sustainability data with expected structure
                enhanced_analytics['cash_sustainability'] = cash_data
                
                # Add critical flags and insights
                if 'metrics' in cash_data:
                    cash_metrics = cash_data['metrics']
                    runway_data = cash_metrics.get('cash_runway', {})
                    
                    risk_level = cash_data.get('risk_level', 'unknown')
                    runway_scenario = runway_data.get('runway_scenario', 'unknown')
                    
                    if risk_level in ['critical', 'high']:
                        enhanced_analytics['critical_flags'].append(f"Cash sustainability risk: {risk_level}")
                    
                    if runway_scenario == 'critical':
                        enhanced_analytics['critical_flags'].append("Cash runway critically short")
                
                # Add insights
                runway_months = runway_data.get('cash_runway_months')
                if isinstance(runway_months, (int, float)):
                    if runway_months < 12:
                        enhanced_analytics['summary_insights'].append(
                            f"Company has {runway_months:.1f} months of cash runway - financing may be needed"
                        )
                    else:
                        enhanced_analytics['summary_insights'].append(
                            f"Company has {runway_months:.1f} months of cash runway"
                        )
            
            logger.info("Successfully processed enhanced analytics")
            
        except Exception as e:
            logger.error(f"Error processing enhanced analytics: {e}")
            enhanced_analytics['error'] = str(e)
        
        return enhanced_analytics
    
    def _extract_one_time_categories(self, one_time_data: Dict[str, Any]) -> List[str]:
        """Extract major categories of one-time items."""
        categories = set()
        
        try:
            items_found = one_time_data.get('items_found', {})
            for item_key, item_data in items_found.items():
                category = item_data.get('category', 'other')
                categories.add(category)
        except Exception as e:
            logger.warning(f"Error extracting one-time categories: {e}")
        
        return list(categories)
