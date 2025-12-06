"""
Earnings Configuration Module

Defines all configuration settings for the earnings report pipeline.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

class EarningsConfig:
    """Configuration settings for earnings reports pipeline"""
    
    # API Keys
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_API_KEY')
    
    # Cache Settings
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated_data', 'earnings_cache')
    CACHE_EXPIRY_HOURS = 6  # Cache expires after 6 hours
    
    # Report Output Settings
    REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated_data', 'earnings_reports')
    
    # Data Collection Settings
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 30  # seconds
    RATE_LIMIT_DELAY = 1.0  # seconds between API calls
    
    # Earnings Data Keys Configuration
    # All required data keys organized by category
    
    COMPANY_IDENTIFICATION_KEYS = [
        'ticker',
        'company_name',
        'cik',
        'exchange',
        'sector',
        'market_cap'
    ]
    
    EARNINGS_TIMELINE_KEYS = [
        'earnings_date',
        'fiscal_quarter',
        'fiscal_year',
        'filing_date',
        'period_end_date',
        'filing_type'
    ]
    
    INCOME_STATEMENT_KEYS = [
        'total_revenue',
        'cost_of_revenue',
        'gross_profit',
        'operating_income',
        'net_income',
        'earnings_per_share_basic',
        'earnings_per_share_diluted',
        'research_and_development',
        'sales_and_marketing',
        'general_and_administrative',
        'depreciation_and_amortization',
        'interest_expense',
        'tax_provision',
        'stock_based_compensation',
        'weighted_average_shares_basic',
        'weighted_average_shares_diluted'
    ]
    
    BALANCE_SHEET_KEYS = [
        'total_assets',
        'current_assets',
        'cash_and_equivalents',
        'accounts_receivable',
        'inventory',
        'property_plant_equipment',
        'goodwill',
        'intangible_assets',
        'total_liabilities',
        'current_liabilities',
        'accounts_payable',
        'long_term_debt',
        'total_debt',
        'stockholders_equity',
        'retained_earnings',
        'working_capital'
    ]
    
    CASH_FLOW_KEYS = [
        'operating_cash_flow',
        'net_cash_investing',
        'net_cash_financing',
        'free_cash_flow',
        'capital_expenditures',
        'dividends_paid',
        'share_repurchases'
    ]
    
    ANALYST_ESTIMATE_KEYS = [
        'estimated_revenue',
        'estimated_eps',
        'estimate_high',
        'estimate_low',
        'number_of_analysts',
        'estimate_year_ago'
    ]
    
    ACTUAL_VS_ESTIMATE_KEYS = [
        'revenue_surprise',
        'eps_surprise',
        'revenue_actual',
        'eps_actual'
    ]
    
    STOCK_PRICE_KEYS = [
        'price',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'price_change',
        'price_change_percent',
        '52_week_high',
        '52_week_low'
    ]
    
    GUIDANCE_KEYS = [
        'guidance_revenue_low',
        'guidance_revenue_high',
        'guidance_eps_low',
        'guidance_eps_high',
        'next_year_estimate'
    ]
    
    CALCULATED_RATIO_KEYS = [
        'profit_margin',
        'operating_margin',
        'gross_margin',
        'return_on_equity',
        'return_on_assets',
        'debt_to_equity',
        'current_ratio',
        'pe_ratio'
    ]
    
    # Combine all keys
    ALL_EARNINGS_KEYS = (
        COMPANY_IDENTIFICATION_KEYS +
        EARNINGS_TIMELINE_KEYS +
        INCOME_STATEMENT_KEYS +
        BALANCE_SHEET_KEYS +
        CASH_FLOW_KEYS +
        ANALYST_ESTIMATE_KEYS +
        ACTUAL_VS_ESTIMATE_KEYS +
        STOCK_PRICE_KEYS +
        GUIDANCE_KEYS +
        CALCULATED_RATIO_KEYS
    )
    
    # Data source priority (order matters)
    DATA_SOURCE_PRIORITY = ['yfinance', 'alpha_vantage', 'finnhub']
    
    # yfinance field mappings
    YFINANCE_FIELD_MAPPING = {
        'ticker': 'symbol',
        'company_name': 'longName',
        'sector': 'sector',
        'market_cap': 'marketCap',
        'earnings_date': 'earningsDate',
        'fiscal_quarter': 'currentQuarterEstimate',
        'total_revenue': 'totalRevenue',
        'gross_profit': 'grossProfit',
        'operating_income': 'operatingIncome',
        'net_income': 'netIncome',
        'earnings_per_share_basic': 'trailingEps',
        'earnings_per_share_diluted': 'trailingEps',
        'total_assets': 'totalAssets',
        'total_liabilities': 'totalLiabilities',
        'stockholders_equity': 'totalStockholderEquity',
        'cash_and_equivalents': 'totalCash',
        'total_debt': 'totalDebt',
        'operating_cash_flow': 'operatingCashflow',
        'free_cash_flow': 'freeCashflow',
        'price': 'currentPrice',
        'pe_ratio': 'trailingPE',
        'profit_margin': 'profitMargins',
        'operating_margin': 'operatingMargins',
        'return_on_equity': 'returnOnEquity',
        'return_on_assets': 'returnOnAssets',
        'debt_to_equity': 'debtToEquity',
        'current_ratio': 'currentRatio',
        '52_week_high': 'fiftyTwoWeekHigh',
        '52_week_low': 'fiftyTwoWeekLow'
    }
    
    # Finnhub field mappings
    FINNHUB_FIELD_MAPPING = {
        'ticker': 'symbol',
        'company_name': 'name',
        'market_cap': 'marketCapitalization',
        'earnings_date': 'earningsDate',
        'earnings_per_share_actual': 'actual',
        'earnings_per_share_estimate': 'estimate',
        'eps_surprise': 'surprise',
        'revenue_actual': 'revenueActual',
        'revenue_estimate': 'revenueEstimate'
    }
    
    # Alpha Vantage field mappings
    ALPHA_VANTAGE_FIELD_MAPPING = {
        'ticker': 'symbol',
        'fiscal_year': 'fiscalDateEnding',
        'total_revenue': 'totalRevenue',
        'cost_of_revenue': 'costOfRevenue',
        'gross_profit': 'grossProfit',
        'operating_income': 'operatingIncome',
        'net_income': 'netIncome',
        'earnings_per_share_diluted': 'reportedEPS',
        'total_assets': 'totalAssets',
        'total_liabilities': 'totalLiabilities',
        'stockholders_equity': 'totalShareholderEquity',
        'operating_cash_flow': 'operatingCashflow',
        'capital_expenditures': 'capitalExpenditures'
    }
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all necessary directories exist"""
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def get_cache_path(cls, ticker: str, data_type: str) -> str:
        """Get cache file path for a specific ticker and data type"""
        cls.ensure_directories()
        timestamp = datetime.now().strftime('%Y%m%d')
        return os.path.join(cls.CACHE_DIR, f"{ticker}_{data_type}_{timestamp}.json")
    
    @classmethod
    def get_report_path(cls, ticker: str, report_type: str) -> str:
        """Get report file path for a specific ticker and report type"""
        cls.ensure_directories()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(cls.REPORTS_DIR, f"{ticker}_{report_type}_{timestamp}.html")
    
    @classmethod
    def is_cache_valid(cls, cache_path: str) -> bool:
        """Check if cache file is still valid"""
        if not os.path.exists(cache_path):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        expiry_time = datetime.now() - timedelta(hours=cls.CACHE_EXPIRY_HOURS)
        
        return file_time > expiry_time
