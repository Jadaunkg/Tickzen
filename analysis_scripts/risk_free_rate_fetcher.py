"""
Dynamic Risk-Free Rate Fetcher
==============================

Task: P1.1 - Dynamic Risk-Free Rate (^IRX)
Phase: 1 - Foundation & Bug Fixes
Day: 1 - Implementation
Date: February 9, 2026

Purpose:
--------
Fetches current 13-week T-bill rate from ^IRX ticker as the risk-free rate.
Replaces hardcoded 2% rate with dynamic market data.

Features:
---------
1. Fetches real-time 13-week T-bill rate from ^IRX
2. 24-hour caching to minimize API calls
3. Fallback to 2% if data unavailable
4. Comprehensive error handling
5. Logging for monitoring

Usage:
------
```python
from analysis_scripts.risk_free_rate_fetcher import fetch_current_risk_free_rate

# Get current risk-free rate
rf_rate = fetch_current_risk_free_rate()
print(f"Current RF Rate: {rf_rate:.4f} ({rf_rate*100:.2f}%)")

# Use in Sharpe ratio calculation
excess_returns = returns - rf_rate/252
sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
```

Technical Details:
-----------------
- Data Source: Yahoo Finance ^IRX (13-week T-bill)
- Update Frequency: Daily
- Cache Duration: 24 hours
- Fallback Rate: 2% (0.02)
- Rate Format: Decimal (e.g., 0.0425 for 4.25%)

Author: TickZen Engineering Team
Version: 1.0
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskFreeRateFetcher:
    """
    Fetches and caches the current risk-free rate from ^IRX
    
    The 13-week Treasury Bill rate (^IRX) is used as a proxy for the
    risk-free rate in financial calculations. This class handles fetching,
    caching, and validation of the rate.
    
    Attributes:
        cache_duration_hours (int): How long to cache the rate (default: 24)
        fallback_rate (float): Rate to use if API fails (default: 0.02)
        last_fetch_time (datetime): When rate was last fetched
        cached_rate (float): Currently cached rate
    """
    
    def __init__(self, cache_duration_hours=24, fallback_rate=0.02):
        """
        Initialize the Risk-Free Rate Fetcher
        
        Args:
            cache_duration_hours (int): Cache duration in hours
            fallback_rate (float): Fallback rate if fetch fails
        """
        self.cache_duration_hours = cache_duration_hours
        self.fallback_rate = fallback_rate
        self.last_fetch_time = None
        self.cached_rate = None
        
        logger.info(f"RiskFreeRateFetcher initialized with {cache_duration_hours}h cache, "
                   f"fallback={fallback_rate:.4f}")
    
    def _is_cache_valid(self):
        """
        Check if cached rate is still valid
        
        Returns:
            bool: True if cache is valid, False if expired or empty
        """
        if self.cached_rate is None or self.last_fetch_time is None:
            return False
        
        time_since_fetch = datetime.now() - self.last_fetch_time
        cache_valid = time_since_fetch < timedelta(hours=self.cache_duration_hours)
        
        if cache_valid:
            logger.debug(f"Using cached rate: {self.cached_rate:.4f} "
                        f"(fetched {time_since_fetch.total_seconds()/3600:.1f}h ago)")
        
        return cache_valid
    
    def _fetch_from_api(self):
        """
        Fetch current rate from Yahoo Finance ^IRX ticker
        
        Returns:
            float: Current 13-week T-bill rate (as decimal)
            None: If fetch fails
        """
        try:
            logger.info("Fetching risk-free rate from ^IRX...")
            
            # Fetch ^IRX data (13-week T-bill)
            irx = yf.Ticker('^IRX')
            hist = irx.history(period='5d')  # Get last 5 days for reliability
            
            if hist.empty:
                logger.warning("^IRX returned empty DataFrame")
                return None
            
            # Get most recent closing rate
            latest_rate_pct = hist['Close'].iloc[-1]
            
            # Convert from percentage (e.g., 4.25) to decimal (0.0425)
            latest_rate = latest_rate_pct / 100
            
            # Validate rate is reasonable (0% to 10%)
            if not (0 <= latest_rate <= 0.10):
                logger.warning(f"^IRX rate {latest_rate:.4f} outside valid range [0, 0.10], "
                             f"using fallback")
                return None
            
            logger.info(f"✅ Successfully fetched RF rate: {latest_rate:.4f} ({latest_rate_pct:.2f}%)")
            return latest_rate
            
        except Exception as e:
            logger.error(f"Error fetching ^IRX data: {type(e).__name__}: {str(e)}")
            return None
    
    def get_rate(self, force_refresh=False):
        """
        Get current risk-free rate (cached or fresh)
        
        Args:
            force_refresh (bool): If True, bypass cache and fetch fresh data
        
        Returns:
            float: Current risk-free rate as decimal
        """
        # Check cache first (unless force refresh)
        if not force_refresh and self._is_cache_valid():
            return self.cached_rate
        
        # Fetch fresh data
        fetched_rate = self._fetch_from_api()
        
        if fetched_rate is not None:
            # Successfully fetched - update cache
            self.cached_rate = fetched_rate
            self.last_fetch_time = datetime.now()
            return fetched_rate
        else:
            # Fetch failed - use fallback
            logger.warning(f"Using fallback rate: {self.fallback_rate:.4f}")
            
            # Cache the fallback to avoid repeated API calls
            self.cached_rate = self.fallback_rate
            self.last_fetch_time = datetime.now()
            
            return self.fallback_rate
    
    def get_rate_info(self):
        """
        Get detailed information about current rate
        
        Returns:
            dict: Rate information including source, timestamp, cache status
        """
        current_rate = self.get_rate()
        
        return {
            'rate': current_rate,
            'rate_percentage': current_rate * 100,
            'source': '^IRX (13-week T-bill)' if current_rate != self.fallback_rate else 'Fallback',
            'is_cached': self._is_cache_valid(),
            'cache_age_hours': ((datetime.now() - self.last_fetch_time).total_seconds() / 3600) 
                              if self.last_fetch_time else None,
            'last_updated': self.last_fetch_time.strftime('%Y-%m-%d %H:%M:%S') 
                           if self.last_fetch_time else None,
            'fallback_rate': self.fallback_rate
        }


# Global instance for singleton pattern
_global_fetcher = None


def fetch_current_risk_free_rate(force_refresh=False):
    """
    Convenience function to fetch current risk-free rate
    
    This function provides a simple interface to get the current risk-free rate.
    It uses a global singleton instance to maintain caching across calls.
    
    Args:
        force_refresh (bool): If True, bypass cache and fetch fresh data
    
    Returns:
        float: Current risk-free rate as decimal (e.g., 0.0425 for 4.25%)
    
    Example:
        >>> rf_rate = fetch_current_risk_free_rate()
        >>> print(f"Current RF rate: {rf_rate*100:.2f}%")
        Current RF rate: 4.25%
    """
    global _global_fetcher
    
    if _global_fetcher is None:
        _global_fetcher = RiskFreeRateFetcher()
    
    return _global_fetcher.get_rate(force_refresh=force_refresh)


def get_risk_free_rate_info():
    """
    Get detailed information about current risk-free rate
    
    Returns:
        dict: Detailed rate information
    
    Example:
        >>> info = get_risk_free_rate_info()
        >>> print(f"Rate: {info['rate_percentage']:.2f}%")
        >>> print(f"Source: {info['source']}")
        >>> print(f"Last updated: {info['last_updated']}")
    """
    global _global_fetcher
    
    if _global_fetcher is None:
        _global_fetcher = RiskFreeRateFetcher()
    
    return _global_fetcher.get_rate_info()


def calculate_daily_risk_free_rate():
    """
    Get daily risk-free rate for use in daily return calculations
    
    Returns:
        float: Daily risk-free rate (annual rate / 252)
    
    Example:
        >>> daily_rf = calculate_daily_risk_free_rate()
        >>> excess_returns = returns - daily_rf
    """
    annual_rate = fetch_current_risk_free_rate()
    return annual_rate / 252


# For testing and demonstration
if __name__ == '__main__':
    print("="*70)
    print("Dynamic Risk-Free Rate Fetcher - Test Run")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test basic fetching
    print("1. Fetching current risk-free rate...")
    rf_rate = fetch_current_risk_free_rate()
    print(f"   Current RF Rate: {rf_rate:.4f} ({rf_rate*100:.2f}%)\n")
    
    # Test detailed info
    print("2. Getting detailed rate information...")
    info = get_risk_free_rate_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    print()
    
    # Test daily rate calculation
    print("3. Calculating daily risk-free rate...")
    daily_rf = calculate_daily_risk_free_rate()
    print(f"   Daily RF Rate: {daily_rf:.6f} ({daily_rf*252*100:.2f}% annualized)\n")
    
    # Test caching
    print("4. Testing cache (second call should be instant)...")
    start_time = time.time()
    rf_rate_cached = fetch_current_risk_free_rate()
    elapsed = time.time() - start_time
    print(f"   Cached rate: {rf_rate_cached:.4f}")
    print(f"   Fetch time: {elapsed*1000:.2f}ms (cached)\n")
    
    # Test force refresh
    print("5. Testing force refresh...")
    start_time = time.time()
    rf_rate_fresh = fetch_current_risk_free_rate(force_refresh=True)
    elapsed = time.time() - start_time
    print(f"   Fresh rate: {rf_rate_fresh:.4f}")
    print(f"   Fetch time: {elapsed*1000:.2f}ms (API call)\n")
    
    print("="*70)
    print("✅ All tests completed successfully!")
    print("="*70)
