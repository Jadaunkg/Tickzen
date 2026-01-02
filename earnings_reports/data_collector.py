"""
Earnings Data Collector Module

Collects comprehensive earnings data from multiple sources:
- yfinance: Company fundamentals, financial statements, stock prices
- Alpha Vantage: SEC filing data, detailed financials
- Finnhub: Earnings calendar, estimates, surprises

This module handles API calls, caching, rate limiting, and error handling.
"""

import json
import logging
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import os

import yfinance as yf
import requests
import pandas as pd
import numpy as np

try:
    import finnhub
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False
    logging.warning("finnhub-python not available. Finnhub data collection will be disabled.")

try:
    # Try relative imports first (when used as module)
    from .earnings_config import EarningsConfig
    from .one_time_items_extractor import extract_one_time_items_for_ticker
    from .adjusted_earnings_calculator import calculate_adjusted_earnings_for_ticker
    from .cash_sustainability_analyzer import analyze_cash_sustainability_for_ticker
except ImportError:
    # Fallback to direct imports (when used standalone)
    from earnings_config import EarningsConfig
    from one_time_items_extractor import extract_one_time_items_for_ticker
    from adjusted_earnings_calculator import calculate_adjusted_earnings_for_ticker
    from cash_sustainability_analyzer import analyze_cash_sustainability_for_ticker

# Configure logging
logger = logging.getLogger(__name__)


class EarningsDataCollector:
    """
    Collects earnings report data from multiple sources.
    
    This class coordinates data collection from yfinance, Alpha Vantage, and Finnhub,
    implementing caching, rate limiting, and error handling.
    """
    
    def __init__(self, config: Optional[EarningsConfig] = None):
        """
        Initialize the data collector.
        
        Args:
            config: Optional EarningsConfig instance. If None, uses default config.
        """
        self.config = config or EarningsConfig()
        self.config.ensure_directories()
        
        # Initialize Finnhub client if available
        self.finnhub_client = None
        if FINNHUB_AVAILABLE and self.config.FINNHUB_API_KEY:
            try:
                self.finnhub_client = finnhub.Client(api_key=self.config.FINNHUB_API_KEY)
                logger.info("Finnhub client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Finnhub client: {e}")
        else:
            logger.warning("Finnhub client not initialized - API key missing or library unavailable")
        
        self.last_api_call = {}  # Track last API call time for rate limiting
    
    def _convert_to_serializable(self, obj):
        """
        Convert pandas/numpy objects to JSON-serializable formats.
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable version of the object
        """
        if isinstance(obj, dict):
            return {self._convert_to_serializable(k): self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def collect_all_data(self, ticker: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Collect all earnings data for a ticker using ONLY yfinance.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary containing all collected earnings data
        """
        logger.info(f"Starting comprehensive data collection for {ticker} (yfinance only)")
        
        # Check cache first
        if use_cache:
            cached_data = self._load_from_cache(ticker)
            if cached_data:
                logger.info(f"Using cached data for {ticker}")
                return cached_data
        
        # Collect ONLY from yfinance
        earnings_data = {
            'ticker': ticker,
            'collection_timestamp': datetime.now().isoformat(),
            'data_sources': {}
        }
        
        # Collect comprehensive yfinance data
        logger.info(f"Collecting comprehensive yfinance data for {ticker}")
        yf_data = self._collect_yfinance_data(ticker)
        earnings_data['data_sources']['yfinance'] = yf_data
        
        # Collect additional yfinance-based data
        logger.info(f"Collecting analyst data from yfinance for {ticker}")
        analyst_data = self.collect_analyst_data(ticker)
        earnings_data['data_sources']['analyst'] = analyst_data
        
        logger.info(f"Collecting valuation metrics from yfinance for {ticker}")
        valuation_data = self.collect_valuation_metrics(ticker)
        earnings_data['data_sources']['valuation'] = valuation_data
        
        logger.info(f"Collecting performance data from yfinance for {ticker}")
        performance_data = self.collect_performance_data(ticker)
        earnings_data['data_sources']['performance'] = performance_data
        
        logger.info(f"Collecting segment revenue data from yfinance for {ticker}")
        segment_data = self.collect_segment_revenue(ticker)
        earnings_data['data_sources']['segment'] = segment_data
        
        # ENHANCED ANALYTICS - Phase 1 Implementation
        logger.info(f"Extracting one-time items for {ticker}")
        one_time_items = extract_one_time_items_for_ticker(ticker, yf_data)
        earnings_data['enhanced_analytics'] = {
            'one_time_items': one_time_items
        }
        
        logger.info(f"Calculating adjusted earnings for {ticker}")
        adjusted_earnings = calculate_adjusted_earnings_for_ticker(ticker, yf_data, one_time_items)
        earnings_data['enhanced_analytics']['adjusted_earnings'] = adjusted_earnings
        
        logger.info(f"Analyzing cash sustainability for {ticker}")
        cash_sustainability = analyze_cash_sustainability_for_ticker(ticker, yf_data)
        earnings_data['enhanced_analytics']['cash_sustainability'] = cash_sustainability
        
        # Save to cache
        self._save_to_cache(ticker, earnings_data)
        
        logger.info(f"Completed data collection for {ticker}")
        return earnings_data
    
    def _collect_yfinance_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect data from yfinance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing yfinance data
        """
        yf_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        try:
            stock = yf.Ticker(ticker)
            
            # Company identification and profile
            info = stock.info
            yf_data['data']['info'] = info
            
            # Financial statements (income statement)
            try:
                yf_data['data']['income_stmt'] = stock.income_stmt.to_dict() if hasattr(stock, 'income_stmt') and stock.income_stmt is not None else {}
                yf_data['data']['quarterly_income_stmt'] = stock.quarterly_income_stmt.to_dict() if hasattr(stock, 'quarterly_income_stmt') and stock.quarterly_income_stmt is not None else {}
            except Exception as e:
                logger.warning(f"Could not fetch income statement from yfinance for {ticker}: {e}")
                yf_data['data']['income_stmt'] = {}
                yf_data['data']['quarterly_income_stmt'] = {}
            
            # Balance sheet
            try:
                yf_data['data']['balance_sheet'] = stock.balance_sheet.to_dict() if hasattr(stock, 'balance_sheet') and stock.balance_sheet is not None else {}
                yf_data['data']['quarterly_balance_sheet'] = stock.quarterly_balance_sheet.to_dict() if hasattr(stock, 'quarterly_balance_sheet') and stock.quarterly_balance_sheet is not None else {}
            except Exception as e:
                logger.warning(f"Could not fetch balance sheet from yfinance for {ticker}: {e}")
                yf_data['data']['balance_sheet'] = {}
                yf_data['data']['quarterly_balance_sheet'] = {}
            
            # Cash flow
            try:
                yf_data['data']['cashflow'] = stock.cashflow.to_dict() if hasattr(stock, 'cashflow') and stock.cashflow is not None else {}
                yf_data['data']['quarterly_cashflow'] = stock.quarterly_cashflow.to_dict() if hasattr(stock, 'quarterly_cashflow') and stock.quarterly_cashflow is not None else {}
            except Exception as e:
                logger.warning(f"Could not fetch cashflow from yfinance for {ticker}: {e}")
                yf_data['data']['cashflow'] = {}
                yf_data['data']['quarterly_cashflow'] = {}
            
            # Earnings data
            try:
                yf_data['data']['earnings'] = stock.earnings.to_dict() if hasattr(stock, 'earnings') and stock.earnings is not None else {}
                yf_data['data']['quarterly_earnings'] = stock.quarterly_earnings.to_dict() if hasattr(stock, 'quarterly_earnings') and stock.quarterly_earnings is not None else {}
            except Exception as e:
                logger.warning(f"Could not fetch earnings from yfinance for {ticker}: {e}")
                yf_data['data']['earnings'] = {}
                yf_data['data']['quarterly_earnings'] = {}
            
            # Earnings calendar
            try:
                if hasattr(stock, 'calendar') and stock.calendar is not None:
                    # Handle both DataFrame and dict types
                    if hasattr(stock.calendar, 'to_dict'):
                        yf_data['data']['calendar'] = stock.calendar.to_dict()
                    elif isinstance(stock.calendar, dict):
                        yf_data['data']['calendar'] = stock.calendar
                    else:
                        yf_data['data']['calendar'] = {}
                else:
                    yf_data['data']['calendar'] = {}
            except Exception as e:
                logger.warning(f"Could not fetch calendar from yfinance for {ticker}: {e}")
                yf_data['data']['calendar'] = {}
            
            # Analyst recommendations and estimates
            try:
                yf_data['data']['recommendations'] = stock.recommendations.to_dict() if hasattr(stock, 'recommendations') and stock.recommendations is not None else {}
                yf_data['data']['analyst_price_target'] = stock.analyst_price_target if hasattr(stock, 'analyst_price_target') else {}
            except Exception as e:
                logger.warning(f"Could not fetch recommendations from yfinance for {ticker}: {e}")
                yf_data['data']['recommendations'] = {}
                yf_data['data']['analyst_price_target'] = {}
            
            # Historical price data (last 60 days for context)
            try:
                hist = stock.history(period='60d')
                if not hist.empty:
                    yf_data['data']['price_history'] = hist.to_dict()
                    
                    # Latest price data
                    latest = hist.iloc[-1]
                    yf_data['data']['latest_price'] = {
                        'date': hist.index[-1].strftime('%Y-%m-%d'),
                        'open': float(latest['Open']),
                        'high': float(latest['High']),
                        'low': float(latest['Low']),
                        'close': float(latest['Close']),
                        'volume': int(latest['Volume'])
                    }
            except Exception as e:
                logger.warning(f"Could not fetch price history from yfinance for {ticker}: {e}")
                yf_data['data']['price_history'] = {}
                yf_data['data']['latest_price'] = {}
            
            yf_data['success'] = True
            logger.info(f"Successfully collected yfinance data for {ticker}")
            
        except Exception as e:
            yf_data['error'] = str(e)
            logger.error(f"Error collecting yfinance data for {ticker}: {e}")
        
        return yf_data
    
    def _collect_alpha_vantage_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect data from Alpha Vantage API.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing Alpha Vantage data
        """
        av_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        if not self.config.ALPHA_VANTAGE_API_KEY:
            av_data['error'] = "Alpha Vantage API key not configured"
            logger.warning(av_data['error'])
            return av_data
        
        try:
            base_url = "https://www.alphavantage.co/query"
            
            # Rate limiting
            self._wait_for_rate_limit('alpha_vantage')
            
            # Get earnings data
            try:
                params = {
                    'function': 'EARNINGS',
                    'symbol': ticker,
                    'apikey': self.config.ALPHA_VANTAGE_API_KEY
                }
                response = requests.get(base_url, params=params, timeout=self.config.REQUEST_TIMEOUT)
                response.raise_for_status()
                earnings_data = response.json()
                
                if 'Information' in earnings_data:
                    logger.warning(f"Alpha Vantage API limit message: {earnings_data['Information']}")
                    av_data['data']['earnings'] = {}
                else:
                    av_data['data']['earnings'] = earnings_data
                
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch earnings from Alpha Vantage for {ticker}: {e}")
                av_data['data']['earnings'] = {}
            
            # Get income statement
            try:
                params = {
                    'function': 'INCOME_STATEMENT',
                    'symbol': ticker,
                    'apikey': self.config.ALPHA_VANTAGE_API_KEY
                }
                response = requests.get(base_url, params=params, timeout=self.config.REQUEST_TIMEOUT)
                response.raise_for_status()
                income_data = response.json()
                
                if 'Information' not in income_data:
                    av_data['data']['income_statement'] = income_data
                else:
                    av_data['data']['income_statement'] = {}
                
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch income statement from Alpha Vantage for {ticker}: {e}")
                av_data['data']['income_statement'] = {}
            
            # Get balance sheet
            try:
                params = {
                    'function': 'BALANCE_SHEET',
                    'symbol': ticker,
                    'apikey': self.config.ALPHA_VANTAGE_API_KEY
                }
                response = requests.get(base_url, params=params, timeout=self.config.REQUEST_TIMEOUT)
                response.raise_for_status()
                balance_data = response.json()
                
                if 'Information' not in balance_data:
                    av_data['data']['balance_sheet'] = balance_data
                else:
                    av_data['data']['balance_sheet'] = {}
                
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch balance sheet from Alpha Vantage for {ticker}: {e}")
                av_data['data']['balance_sheet'] = {}
            
            # Get cash flow
            try:
                params = {
                    'function': 'CASH_FLOW',
                    'symbol': ticker,
                    'apikey': self.config.ALPHA_VANTAGE_API_KEY
                }
                response = requests.get(base_url, params=params, timeout=self.config.REQUEST_TIMEOUT)
                response.raise_for_status()
                cashflow_data = response.json()
                
                if 'Information' not in cashflow_data:
                    av_data['data']['cash_flow'] = cashflow_data
                else:
                    av_data['data']['cash_flow'] = {}
                
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch cash flow from Alpha Vantage for {ticker}: {e}")
                av_data['data']['cash_flow'] = {}
            
            # Get company overview
            try:
                params = {
                    'function': 'OVERVIEW',
                    'symbol': ticker,
                    'apikey': self.config.ALPHA_VANTAGE_API_KEY
                }
                response = requests.get(base_url, params=params, timeout=self.config.REQUEST_TIMEOUT)
                response.raise_for_status()
                overview_data = response.json()
                
                if 'Information' not in overview_data:
                    av_data['data']['overview'] = overview_data
                else:
                    av_data['data']['overview'] = {}
            except Exception as e:
                logger.warning(f"Could not fetch overview from Alpha Vantage for {ticker}: {e}")
                av_data['data']['overview'] = {}
            
            av_data['success'] = True
            logger.info(f"Successfully collected Alpha Vantage data for {ticker}")
            
        except Exception as e:
            av_data['error'] = str(e)
            logger.error(f"Error collecting Alpha Vantage data for {ticker}: {e}")
        
        return av_data
    
    def _collect_finnhub_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect data from Finnhub API.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing Finnhub data
        """
        fh_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        if not self.finnhub_client:
            fh_data['error'] = "Finnhub client not initialized"
            logger.warning(fh_data['error'])
            return fh_data
        
        try:
            # Rate limiting
            self._wait_for_rate_limit('finnhub')
            
            # Get company profile
            try:
                profile = self.finnhub_client.company_profile2(symbol=ticker)
                fh_data['data']['profile'] = profile
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch profile from Finnhub for {ticker}: {e}")
                fh_data['data']['profile'] = {}
            
            # Get earnings calendar
            try:
                # Get earnings for next 30 days and past 30 days
                today = datetime.now()
                from_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
                to_date = (today + timedelta(days=90)).strftime('%Y-%m-%d')
                
                earnings_calendar = self.finnhub_client.earnings_calendar(
                    _from=from_date,
                    to=to_date,
                    symbol=ticker,
                    international=False
                )
                fh_data['data']['earnings_calendar'] = earnings_calendar
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch earnings calendar from Finnhub for {ticker}: {e}")
                fh_data['data']['earnings_calendar'] = {}
            
            # Get earnings surprises (historical)
            try:
                surprises = self.finnhub_client.company_earnings(ticker, limit=8)
                fh_data['data']['earnings_surprises'] = surprises
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch earnings surprises from Finnhub for {ticker}: {e}")
                fh_data['data']['earnings_surprises'] = []
            
            # Get analyst estimates
            try:
                estimates = self.finnhub_client.company_eps_estimates(ticker)
                fh_data['data']['eps_estimates'] = estimates
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch EPS estimates from Finnhub for {ticker}: {e}")
                fh_data['data']['eps_estimates'] = {}
            
            # Get revenue estimates
            try:
                revenue_estimates = self.finnhub_client.company_revenue_estimates(ticker)
                fh_data['data']['revenue_estimates'] = revenue_estimates
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch revenue estimates from Finnhub for {ticker}: {e}")
                fh_data['data']['revenue_estimates'] = {}
            
            # Get basic financials
            try:
                financials = self.finnhub_client.company_basic_financials(ticker, 'all')
                fh_data['data']['basic_financials'] = financials
                time.sleep(self.config.RATE_LIMIT_DELAY)
            except Exception as e:
                logger.warning(f"Could not fetch basic financials from Finnhub for {ticker}: {e}")
                fh_data['data']['basic_financials'] = {}
            
            # Get recommendation trends
            try:
                recommendations = self.finnhub_client.recommendation_trends(ticker)
                fh_data['data']['recommendations'] = recommendations
            except Exception as e:
                logger.warning(f"Could not fetch recommendations from Finnhub for {ticker}: {e}")
                fh_data['data']['recommendations'] = []
            
            fh_data['success'] = True
            logger.info(f"Successfully collected Finnhub data for {ticker}")
            
        except Exception as e:
            fh_data['error'] = str(e)
            logger.error(f"Error collecting Finnhub data for {ticker}: {e}")
        
        return fh_data
    
    def _wait_for_rate_limit(self, api_name: str):
        """
        Implement rate limiting for API calls.
        
        Args:
            api_name: Name of the API (for tracking)
        """
        if api_name in self.last_api_call:
            elapsed = time.time() - self.last_api_call[api_name]
            if elapsed < self.config.RATE_LIMIT_DELAY:
                time.sleep(self.config.RATE_LIMIT_DELAY - elapsed)
        
        self.last_api_call[api_name] = time.time()
    
    def _load_from_cache(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Load data from cache if available and valid.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Cached data or None if not available
        """
        cache_path = self.config.get_cache_path(ticker, 'earnings_data')
        
        if not self.config.is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in cache for {ticker}: {e}. Removing corrupted cache.")
            try:
                os.remove(cache_path)
            except:
                pass
            return None
        except Exception as e:
            logger.warning(f"Could not load cache for {ticker}: {e}")
            return None
    
    def _save_to_cache(self, ticker: str, data: Dict[str, Any]):
        """
        Save data to cache.
        
        Args:
            ticker: Stock ticker symbol
            data: Data to cache
        """
        cache_path = self.config.get_cache_path(ticker, 'earnings_data')
        
        try:
            # Convert all data to serializable format
            serializable_data = self._convert_to_serializable(data)
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2)
            logger.info(f"Saved data to cache: {cache_path}")
        except Exception as e:
            logger.error(f"Could not save cache for {ticker}: {e}")
    
    def get_upcoming_earnings(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Get list of upcoming earnings dates.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of tickers with upcoming earnings
        """
        # This would typically query a database or API
        # For now, returns empty list as a placeholder
        logger.info(f"Getting upcoming earnings for next {days_ahead} days")
        return []
    
    def collect_analyst_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect comprehensive analyst ratings, recommendations, and price targets.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing analyst data
        """
        analyst_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        try:
            stock = yf.Ticker(ticker)
            
            # Get analyst recommendations
            try:
                if hasattr(stock, 'recommendations') and stock.recommendations is not None:
                    analyst_data['data']['recommendations'] = stock.recommendations.to_dict()
                else:
                    analyst_data['data']['recommendations'] = {}
            except Exception as e:
                logger.warning(f"Could not fetch recommendations for {ticker}: {e}")
                analyst_data['data']['recommendations'] = {}
            
            # Get recommendation summary from info
            info = stock.info
            analyst_data['data']['recommendation_key'] = info.get('recommendationKey', 'N/A')
            analyst_data['data']['recommendation_mean'] = info.get('recommendationMean', 'N/A')
            analyst_data['data']['number_of_analyst_opinions'] = info.get('numberOfAnalystOpinions', 'N/A')
            
            # Price targets
            analyst_data['data']['target_mean_price'] = info.get('targetMeanPrice', 'N/A')
            analyst_data['data']['target_median_price'] = info.get('targetMedianPrice', 'N/A')
            analyst_data['data']['target_high_price'] = info.get('targetHighPrice', 'N/A')
            analyst_data['data']['target_low_price'] = info.get('targetLowPrice', 'N/A')
            
            # Upgrades/Downgrades
            try:
                if hasattr(stock, 'upgrades_downgrades') and stock.upgrades_downgrades is not None:
                    analyst_data['data']['upgrades_downgrades'] = stock.upgrades_downgrades.to_dict()
                else:
                    analyst_data['data']['upgrades_downgrades'] = {}
            except Exception as e:
                logger.warning(f"Could not fetch upgrades/downgrades for {ticker}: {e}")
                analyst_data['data']['upgrades_downgrades'] = {}
            
            analyst_data['success'] = True
            logger.info(f"Successfully collected analyst data for {ticker}")
            
        except Exception as e:
            analyst_data['error'] = str(e)
            logger.error(f"Error collecting analyst data for {ticker}: {e}")
        
        return analyst_data
    
    def collect_valuation_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Collect comprehensive valuation metrics.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing valuation metrics
        """
        valuation_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Market Cap
            valuation_data['data']['market_cap'] = info.get('marketCap', 'N/A')
            
            # P/E Ratios
            valuation_data['data']['trailing_pe'] = info.get('trailingPE', 'N/A')
            valuation_data['data']['forward_pe'] = info.get('forwardPE', 'N/A')
            
            # PEG Ratio
            valuation_data['data']['peg_ratio'] = info.get('pegRatio', 'N/A')
            
            # Price to Sales
            valuation_data['data']['price_to_sales'] = info.get('priceToSalesTrailing12Months', 'N/A')
            
            # Price to Book
            valuation_data['data']['price_to_book'] = info.get('priceToBook', 'N/A')
            
            # Enterprise Value metrics
            valuation_data['data']['enterprise_value'] = info.get('enterpriseValue', 'N/A')
            valuation_data['data']['ev_to_revenue'] = info.get('enterpriseToRevenue', 'N/A')
            valuation_data['data']['ev_to_ebitda'] = info.get('enterpriseToEbitda', 'N/A')
            
            # Dividend metrics
            valuation_data['data']['dividend_rate'] = info.get('dividendRate', 'N/A')
            valuation_data['data']['dividend_yield'] = info.get('dividendYield', 'N/A')
            valuation_data['data']['payout_ratio'] = info.get('payoutRatio', 'N/A')
            
            # Sector/Industry for comparison
            valuation_data['data']['sector'] = info.get('sector', 'N/A')
            valuation_data['data']['industry'] = info.get('industry', 'N/A')
            
            valuation_data['success'] = True
            logger.info(f"Successfully collected valuation metrics for {ticker}")
            
        except Exception as e:
            valuation_data['error'] = str(e)
            logger.error(f"Error collecting valuation metrics for {ticker}: {e}")
        
        return valuation_data
    
    def collect_performance_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect stock performance data including historical returns.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing performance data
        """
        performance_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        try:
            stock = yf.Ticker(ticker)
            
            # Get historical data for various periods
            hist_1m = stock.history(period='1mo')
            hist_3m = stock.history(period='3mo')
            hist_ytd = stock.history(start=f"{datetime.now().year}-01-01")
            hist_1y = stock.history(period='1y')
            
            # Calculate returns
            if not hist_1m.empty:
                price_1m_ago = hist_1m['Close'].iloc[0]
                current_price = hist_1m['Close'].iloc[-1]
                performance_data['data']['1_month_return'] = ((current_price - price_1m_ago) / price_1m_ago) * 100
            else:
                performance_data['data']['1_month_return'] = 'N/A'
            
            if not hist_3m.empty:
                price_3m_ago = hist_3m['Close'].iloc[0]
                current_price = hist_3m['Close'].iloc[-1]
                performance_data['data']['3_month_return'] = ((current_price - price_3m_ago) / price_3m_ago) * 100
            else:
                performance_data['data']['3_month_return'] = 'N/A'
            
            if not hist_ytd.empty:
                price_ytd_start = hist_ytd['Close'].iloc[0]
                current_price = hist_ytd['Close'].iloc[-1]
                performance_data['data']['ytd_return'] = ((current_price - price_ytd_start) / price_ytd_start) * 100
            else:
                performance_data['data']['ytd_return'] = 'N/A'
            
            if not hist_1y.empty:
                price_1y_ago = hist_1y['Close'].iloc[0]
                current_price = hist_1y['Close'].iloc[-1]
                performance_data['data']['1_year_return'] = ((current_price - price_1y_ago) / price_1y_ago) * 100
                
                # Calculate volatility (annualized)
                returns = hist_1y['Close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized
                performance_data['data']['volatility_1y'] = volatility * 100
            else:
                performance_data['data']['1_year_return'] = 'N/A'
                performance_data['data']['volatility_1y'] = 'N/A'
            
            # Average volume trends
            if not hist_3m.empty:
                avg_volume_3m = hist_3m['Volume'].mean()
                recent_volume = hist_3m['Volume'].iloc[-5:].mean()  # Last 5 days
                volume_trend = ((recent_volume - avg_volume_3m) / avg_volume_3m) * 100
                performance_data['data']['volume_trend'] = volume_trend
                performance_data['data']['avg_volume_3m'] = avg_volume_3m
            else:
                performance_data['data']['volume_trend'] = 'N/A'
                performance_data['data']['avg_volume_3m'] = 'N/A'
            
            # Beta
            info = stock.info
            performance_data['data']['beta'] = info.get('beta', 'N/A')
            
            performance_data['success'] = True
            logger.info(f"Successfully collected performance data for {ticker}")
            
        except Exception as e:
            performance_data['error'] = str(e)
            logger.error(f"Error collecting performance data for {ticker}: {e}")
        
        return performance_data
    
    def collect_segment_revenue(self, ticker: str) -> Dict[str, Any]:
        """
        Collect business segment revenue data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing segment revenue data
        """
        segment_data = {
            'success': False,
            'error': None,
            'data': {}
        }
        
        try:
            stock = yf.Ticker(ticker)
            
            # Try to get segment data from financials
            # Note: Segment breakdown is limited in yfinance
            info = stock.info
            
            # Get geographic revenue breakdown if available
            segment_data['data']['business_summary'] = info.get('longBusinessSummary', 'N/A')
            
            # Some basic segment indicators
            segment_data['data']['total_revenue'] = info.get('totalRevenue', 'N/A')
            segment_data['data']['revenue_per_share'] = info.get('revenuePerShare', 'N/A')
            
            segment_data['success'] = True
            logger.info(f"Successfully collected segment data for {ticker}")
            
        except Exception as e:
            segment_data['error'] = str(e)
            logger.error(f"Error collecting segment data for {ticker}: {e}")
        
        return segment_data
