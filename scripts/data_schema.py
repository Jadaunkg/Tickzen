#!/usr/bin/env python3
"""
Data Schema and Dictionary for Ticker Data Export
=================================================

This module defines the complete schema for all variables exported by
the ticker_data_exporter.py script. It provides metadata, descriptions,
data types, and tab groupings for all 220+ variables.

Usage:
    from data_schema import VARIABLE_SCHEMA, get_variables_by_tab
    
    # Get all variables for a specific tab
    overview_vars = get_variables_by_tab('Overview')
    
    # Get variable metadata
    var_info = VARIABLE_SCHEMA['current_price']
"""

# Complete variable schema
VARIABLE_SCHEMA = {
    # OVERVIEW TAB - Market Price
    'ticker': {'tab': 'Overview', 'category': 'Identifier', 'type': 'string', 'description': 'Stock ticker symbol'},
    'current_price': {'tab': 'Overview', 'category': 'Market Price', 'type': 'float', 'description': 'Current stock price'},
    'regularMarketPrice': {'tab': 'Overview', 'category': 'Market Price', 'type': 'float', 'description': 'Regular market price'},
    'open_price': {'tab': 'Overview', 'category': 'Market Price', 'type': 'float', 'description': 'Opening price'},
    'high_price': {'tab': 'Overview', 'category': 'Market Price', 'type': 'float', 'description': 'Daily high price'},
    'low_price': {'tab': 'Overview', 'category': 'Market Price', 'type': 'float', 'description': 'Daily low price'},
    'close_price': {'tab': 'Overview', 'category': 'Market Price', 'type': 'float', 'description': 'Closing price'},
    'volume': {'tab': 'Overview', 'category': 'Market Price', 'type': 'int', 'description': 'Trading volume'},
    
    # OVERVIEW TAB - Market Size
    'market_cap': {'tab': 'Overview', 'category': 'Market Size', 'type': 'float', 'description': 'Market capitalization'},
    'enterprise_value': {'tab': 'Overview', 'category': 'Market Size', 'type': 'float', 'description': 'Enterprise value'},
    'shares_outstanding': {'tab': 'Overview', 'category': 'Market Size', 'type': 'float', 'description': 'Shares outstanding'},
    'float_shares': {'tab': 'Overview', 'category': 'Market Size', 'type': 'float', 'description': 'Float shares'},
    
    # OVERVIEW TAB - Performance
    'daily_return_pct': {'tab': 'Overview', 'category': 'Performance', 'type': 'float', 'description': 'Daily return percentage'},
    'change_15d_pct': {'tab': 'Overview', 'category': 'Performance', 'type': 'float', 'description': '15-day change percentage'},
    'change_52w_pct': {'tab': 'Overview', 'category': 'Performance', 'type': 'float', 'description': '52-week change percentage'},
    'performance_1y_pct': {'tab': 'Overview', 'category': 'Performance', 'type': 'float', 'description': '1-year performance percentage'},
    'high_52w': {'tab': 'Overview', 'category': 'Performance', 'type': 'float', 'description': '52-week high'},
    'low_52w': {'tab': 'Overview', 'category': 'Performance', 'type': 'float', 'description': '52-week low'},
    
    # OVERVIEW TAB - Market Context
    'exchange': {'tab': 'Overview', 'category': 'Market Context', 'type': 'string', 'description': 'Stock exchange'},
    'country': {'tab': 'Overview', 'category': 'Market Context', 'type': 'string', 'description': 'Company country'},
    'sp500_index': {'tab': 'Overview', 'category': 'Market Context', 'type': 'float', 'description': 'S&P 500 index value'},
    'interest_rate': {'tab': 'Overview', 'category': 'Market Context', 'type': 'float', 'description': 'Interest rate'},
    
    # FORECAST TAB - Analyst Targets
    'target_price_mean': {'tab': 'Forecast', 'category': 'Analyst Targets', 'type': 'float', 'description': 'Mean analyst target price'},
    'target_price_median': {'tab': 'Forecast', 'category': 'Analyst Targets', 'type': 'float', 'description': 'Median analyst target price'},
    'target_price_high': {'tab': 'Forecast', 'category': 'Analyst Targets', 'type': 'float', 'description': 'Highest analyst target price'},
    'target_price_low': {'tab': 'Forecast', 'category': 'Analyst Targets', 'type': 'float', 'description': 'Lowest analyst target price'},
    'analyst_rating': {'tab': 'Forecast', 'category': 'Analyst Targets', 'type': 'string', 'description': 'Analyst recommendation'},
    'analyst_count': {'tab': 'Forecast', 'category': 'Analyst Targets', 'type': 'int', 'description': 'Number of analysts'},
    
    # FORECAST TAB - Earnings Timing
    'next_earnings_date': {'tab': 'Forecast', 'category': 'Earnings Timing', 'type': 'date', 'description': 'Next earnings report date'},
    'earningsTimestamp': {'tab': 'Forecast', 'category': 'Earnings Timing', 'type': 'int', 'description': 'Earnings timestamp'},
    'earnings_call_time': {'tab': 'Forecast', 'category': 'Earnings Timing', 'type': 'datetime', 'description': 'Earnings call time'},
    'earningsCallTimestampStart': {'tab': 'Forecast', 'category': 'Earnings Timing', 'type': 'int', 'description': 'Earnings call start timestamp'},
    
    # FORECAST TAB - Price Forecast
    'forecast_price_1y': {'tab': 'Forecast', 'category': 'Price Forecast', 'type': 'float', 'description': '1-year forecast price'},
    'forecast_avg_price': {'tab': 'Forecast', 'category': 'Price Forecast', 'type': 'float', 'description': 'Average forecast price'},
    'forecast_range_width': {'tab': 'Forecast', 'category': 'Price Forecast', 'type': 'float', 'description': 'Forecast range width'},
    'forecast_period': {'tab': 'Forecast', 'category': 'Price Forecast', 'type': 'string', 'description': 'Forecast period'},
    
    # TECHNICALS TAB - Trend
    'sma_7': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '7-day simple moving average'},
    'sma_20': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '20-day simple moving average'},
    'sma_50': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '50-day simple moving average'},
    'sma_100': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '100-day simple moving average'},
    'sma_200': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '200-day simple moving average'},
    'ema_12': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '12-day exponential moving average'},
    'ema_26': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': '26-day exponential moving average'},
    'adx': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': 'Average Directional Index'},
    'parabolic_sar': {'tab': 'Technicals', 'category': 'Trend', 'type': 'float', 'description': 'Parabolic SAR'},
    
    # TECHNICALS TAB - Momentum
    'rsi_14': {'tab': 'Technicals', 'category': 'Momentum', 'type': 'float', 'description': '14-day RSI'},
    'macd_line': {'tab': 'Technicals', 'category': 'Momentum', 'type': 'float', 'description': 'MACD line'},
    'macd_signal': {'tab': 'Technicals', 'category': 'Momentum', 'type': 'float', 'description': 'MACD signal line'},
    'macd_hist': {'tab': 'Technicals', 'category': 'Momentum', 'type': 'float', 'description': 'MACD histogram'},
    'stochastic_osc': {'tab': 'Technicals', 'category': 'Momentum', 'type': 'float', 'description': 'Stochastic oscillator'},
    'williams_r': {'tab': 'Technicals', 'category': 'Momentum', 'type': 'float', 'description': 'Williams %R'},
    
    # TECHNICALS TAB - Volatility
    'bb_upper': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': 'Bollinger band upper'},
    'bb_middle': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': 'Bollinger band middle'},
    'bb_lower': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': 'Bollinger band lower'},
    'atr_14': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': '14-day ATR'},
    'volatility_7d': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': '7-day volatility'},
    'volatility_30d_annual': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': '30-day annualized volatility'},
    'keltner_upper': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': 'Keltner channel upper'},
    'keltner_lower': {'tab': 'Technicals', 'category': 'Volatility', 'type': 'float', 'description': 'Keltner channel lower'},
    
    # TECHNICALS TAB - Volume
    'volume_sma_20': {'tab': 'Technicals', 'category': 'Volume', 'type': 'float', 'description': '20-day volume SMA'},
    'volume_sma_ratio': {'tab': 'Technicals', 'category': 'Volume', 'type': 'float', 'description': 'Volume to SMA ratio'},
    'volume_trend_5d': {'tab': 'Technicals', 'category': 'Volume', 'type': 'string', 'description': '5-day volume trend'},
    'obv': {'tab': 'Technicals', 'category': 'Volume', 'type': 'float', 'description': 'On-Balance Volume'},
    'vpt': {'tab': 'Technicals', 'category': 'Volume', 'type': 'float', 'description': 'Volume Price Trend'},
    'chaikin_money_flow': {'tab': 'Technicals', 'category': 'Volume', 'type': 'float', 'description': 'Chaikin Money Flow'},
    'green_days_count': {'tab': 'Technicals', 'category': 'Volume', 'type': 'int', 'description': 'Green days count'},
    
    # TECHNICALS TAB - Support & Resistance
    'support_30d': {'tab': 'Technicals', 'category': 'Support & Resistance', 'type': 'float', 'description': '30-day support level'},
    'resistance_30d': {'tab': 'Technicals', 'category': 'Support & Resistance', 'type': 'float', 'description': '30-day resistance level'},
    
    # FUNDAMENTALS TAB - Valuation
    'pe_trailing': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'Trailing P/E ratio'},
    'pe_forward': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'Forward P/E ratio'},
    'price_to_sales': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'Price to sales ratio'},
    'price_to_book': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'Price to book ratio'},
    'peg_ratio': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'PEG ratio'},
    'ev_to_revenue': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'EV to revenue ratio'},
    'ev_to_ebitda': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'EV to EBITDA ratio'},
    'price_to_fcf': {'tab': 'Fundamentals', 'category': 'Valuation', 'type': 'float', 'description': 'Price to free cash flow'},
    
    # FUNDAMENTALS TAB - Profitability
    'net_margin': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'Net profit margin'},
    'operating_margin': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'Operating margin'},
    'gross_margin': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'Gross margin'},
    'ebitda_margin': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'EBITDA margin'},
    'roe': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'Return on equity'},
    'roa': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'Return on assets'},
    'roic': {'tab': 'Fundamentals', 'category': 'Profitability', 'type': 'float', 'description': 'Return on invested capital'},
    
    # FUNDAMENTALS TAB - Financial Health
    'debt_to_equity': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Debt to equity ratio'},
    'total_cash': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Total cash'},
    'totalCash': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Total cash (duplicate)'},
    'total_debt': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Total debt'},
    'free_cash_flow': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Free cash flow'},
    'freeCashflow': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Free cash flow (duplicate)'},
    'operating_cash_flow': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Operating cash flow'},
    'current_ratio': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Current ratio'},
    'quick_ratio': {'tab': 'Fundamentals', 'category': 'Financial Health', 'type': 'float', 'description': 'Quick ratio'},
    
    # FUNDAMENTALS TAB - Growth
    'revenue_ttm': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'Revenue TTM'},
    'revenue_growth_yoy': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'YoY revenue growth'},
    'net_income_ttm': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'Net income TTM'},
    'netIncomeToCommon': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'Net income to common'},
    'earnings_growth_yoy': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'YoY earnings growth'},
    'ebitda_ttm': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'EBITDA TTM'},
    'gross_profit_ttm': {'tab': 'Fundamentals', 'category': 'Growth', 'type': 'float', 'description': 'Gross profit TTM'},
    
    # FUNDAMENTALS TAB - Efficiency
    'asset_turnover': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Asset turnover ratio'},
    'inventory_turnover': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Inventory turnover'},
    'receivables_turnover': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Receivables turnover'},
    'working_capital_turnover': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Working capital turnover'},
    'dso': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Days sales outstanding'},
    'dio': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Days inventory outstanding'},
    'ccc': {'tab': 'Fundamentals', 'category': 'Efficiency', 'type': 'float', 'description': 'Cash conversion cycle'},
    
    # FUNDAMENTALS TAB - Dividends
    'dividend_rate': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Annual dividend rate'},
    'dividend_yield_pct': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Dividend yield percentage'},
    'payout_ratio': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Dividend payout ratio'},
    'avg_dividend_yield_5y': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': '5-year average dividend yield'},
    'dividend_forward_rate': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Forward dividend rate'},
    'dividend_forward_yield': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Forward dividend yield'},
    'dividend_trailing_rate': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Trailing dividend rate'},
    'dividend_trailing_yield': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'float', 'description': 'Trailing dividend yield'},
    'ex_dividend_date': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'date', 'description': 'Ex-dividend date'},
    'last_split_date': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'date', 'description': 'Last stock split date'},
    'last_split_factor': {'tab': 'Fundamentals', 'category': 'Dividends', 'type': 'string', 'description': 'Last split factor'},
    
    # RISK & SENTIMENT TAB - Risk
    'var_95': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Value at Risk (95%)'},
    'var_99': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Value at Risk (99%)'},
    'sharpe_ratio': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Sharpe ratio'},
    'sortino_ratio': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Sortino ratio'},
    'calmar_ratio': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Calmar ratio'},
    'max_drawdown': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Maximum drawdown'},
    'beta': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Beta coefficient'},
    'market_correlation': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Market correlation'},
    'skewness': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Return skewness'},
    'kurtosis': {'tab': 'Risk & Sentiment', 'category': 'Risk', 'type': 'float', 'description': 'Return kurtosis'},
    
    # RISK & SENTIMENT TAB - Sentiment
    'sentiment_score': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'float', 'description': 'Composite sentiment score'},
    'sentiment_label': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'string', 'description': 'Sentiment classification'},
    'sentiment_confidence': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'float', 'description': 'Sentiment confidence'},
    'news_sentiment': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'float', 'description': 'News sentiment score'},
    'analyst_sentiment': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'float', 'description': 'Analyst sentiment score'},
    'options_sentiment': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'float', 'description': 'Options sentiment score'},
    'put_call_ratio': {'tab': 'Risk & Sentiment', 'category': 'Sentiment', 'type': 'float', 'description': 'Put/call ratio'},
    
    # RISK & SENTIMENT TAB - Insider Activity Summary
    'total_transactions': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Total insider transactions'},
    'buy_count': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Insider buy count'},
    'sell_count': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Insider sell count'},
    'net_shares': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Net shares from insider activity'},
    'net_sentiment': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'string', 'description': 'Net insider sentiment'},
    'market_transactions': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Market transactions count'},
    'option_exercises': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Option exercises count'},
    'awards': {'tab': 'Risk & Sentiment', 'category': 'Insider Activity', 'type': 'int', 'description': 'Stock awards count'},
    
    # COMPANY TAB - Profile
    'company_name': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Company name'},
    'shortName': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Short company name'},
    'longName': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Long company name'},
    'symbol': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Stock symbol'},
    'sector': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Business sector'},
    'industry': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Industry classification'},
    'website_url': {'tab': 'Company', 'category': 'Profile', 'type': 'string', 'description': 'Company website'},
    'employee_count': {'tab': 'Company', 'category': 'Profile', 'type': 'int', 'description': 'Number of employees'},
    'business_summary': {'tab': 'Company', 'category': 'Profile', 'type': 'text', 'description': 'Business description'},
    'longBusinessSummary': {'tab': 'Company', 'category': 'Profile', 'type': 'text', 'description': 'Detailed business summary'},
    'firstTradeDateEpochUtc': {'tab': 'Company', 'category': 'Profile', 'type': 'int', 'description': 'First trade date timestamp'},
    'first_trade_date': {'tab': 'Company', 'category': 'Profile', 'type': 'date', 'description': 'First trade date'},
    
    # COMPANY TAB - Ownership
    'sharesOutstanding': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Shares outstanding'},
    'shares_outstanding_diluted': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Diluted shares outstanding'},
    'insider_ownership_pct': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Insider ownership percentage'},
    'institutional_ownership_pct': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Institutional ownership percentage'},
    'shares_short': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Shares sold short'},
    'short_ratio_days': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Short ratio (days to cover)'},
    'short_pct_float': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Short percentage of float'},
    'shares_short_prev': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'Previous month short shares'},
    'shares_change_yoy': {'tab': 'Company', 'category': 'Ownership', 'type': 'float', 'description': 'YoY shares change'},
    
    # QUARTERLY EARNINGS
    'q1_date': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 quarter end date'},
    'q1_total_revenue': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 total revenue'},
    'q1_net_income': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 net income'},
    'q1_gross_profit': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 gross profit'},
    'q1_operating_income': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 operating income'},
    'q1_eps_basic': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 basic EPS'},
    'q1_eps_diluted': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 diluted EPS'},
    'q1_gross_margin': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'Q1 gross margin'},
    'qoq_revenue_growth': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'QoQ revenue growth'},
    'qoq_net_income_growth': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'QoQ net income growth'},
    'yoy_revenue_growth': {'tab': 'Fundamentals', 'category': 'Quarterly Earnings', 'type': 'string', 'description': 'YoY revenue growth'},
    
    # METADATA
    'data_collection_date': {'tab': 'Metadata', 'category': 'System', 'type': 'datetime', 'description': 'Data collection timestamp'},
    'data_source': {'tab': 'Metadata', 'category': 'System', 'type': 'string', 'description': 'Data source identifier'},
    'errors': {'tab': 'Metadata', 'category': 'System', 'type': 'text', 'description': 'Collection errors log'},
}


def get_variables_by_tab(tab_name):
    """Get all variables for a specific tab."""
    return {k: v for k, v in VARIABLE_SCHEMA.items() if v['tab'] == tab_name}


def get_variables_by_category(category_name):
    """Get all variables for a specific category."""
    return {k: v for k, v in VARIABLE_SCHEMA.items() if v['category'] == category_name}


def get_all_tabs():
    """Get list of all unique tabs."""
    return sorted(list(set(v['tab'] for v in VARIABLE_SCHEMA.values())))


def get_all_categories():
    """Get list of all unique categories."""
    return sorted(list(set(v['category'] for v in VARIABLE_SCHEMA.values())))


def export_schema_to_csv(output_path='variable_schema.csv'):
    """Export schema to CSV file."""
    import pandas as pd
    
    data = []
    for var_name, var_info in VARIABLE_SCHEMA.items():
        data.append({
            'Variable': var_name,
            'Tab': var_info['tab'],
            'Category': var_info['category'],
            'Data Type': var_info['type'],
            'Description': var_info['description']
        })
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Schema exported to: {output_path}")


if __name__ == "__main__":
    print("TickZen2 Data Schema")
    print("=" * 60)
    print(f"Total variables: {len(VARIABLE_SCHEMA)}")
    print(f"\nTabs ({len(get_all_tabs())}):")
    for tab in get_all_tabs():
        count = len(get_variables_by_tab(tab))
        print(f"  - {tab}: {count} variables")
    
    print(f"\nCategories ({len(get_all_categories())}):")
    for cat in get_all_categories():
        count = len(get_variables_by_category(cat))
        print(f"  - {cat}: {count} variables")
    
    # Export to CSV
    export_schema_to_csv()
