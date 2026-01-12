---
description: "Code quality standards, linting, formatting, and best practices for TickZen"
alwaysApply: true
globs: []
---

# TickZen Code Quality Standards

## Python Style Guide (PEP 8 Compliance)

### Naming Conventions
```python
# Classes: PascalCase
class StockAnalyzer:
    pass

class EarningsReportGenerator:
    pass

# Functions and variables: snake_case
def calculate_pe_ratio(price, earnings):
    return price / earnings

user_profile = get_user_profile(user_id)
ticker_list = ['AAPL', 'GOOGL', 'MSFT']

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = 'https://api.example.com'

# Private methods/attributes: leading underscore
class DataProcessor:
    def __init__(self):
        self._cache = {}
    
    def _internal_method(self):
        pass

# Protected (module-level): single leading underscore
_internal_config = {}

def _helper_function():
    pass
```

### Import Organization
```python
# Standard library imports
import os
import sys
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

# Third-party imports
import pandas as pd
import numpy as np
import yfinance as yf
from flask import Flask, request, jsonify
from flask_socketio import SocketIO

# Local application imports
from config.config import Config
from analysis_scripts.technical_analysis import calculate_indicators
from data_processing_scripts.data_collection import fetch_stock_data

# Avoid wildcard imports
from module import *  # ❌ NEVER DO THIS

# Use explicit imports
from module import specific_function, SpecificClass  # ✅ CORRECT
```

### Line Length and Formatting
```python
# Maximum line length: 88 characters (Black formatter default)

# Break long lines properly
def create_comprehensive_stock_report(
    ticker: str,
    include_technical: bool = True,
    include_fundamental: bool = True,
    include_sentiment: bool = False,
    time_period: str = '1y'
) -> Dict:
    """Function with many parameters - one per line"""
    pass

# Long method chains
result = (
    df.groupby('ticker')
    .agg({'price': 'mean', 'volume': 'sum'})
    .reset_index()
    .sort_values('price', ascending=False)
)

# Long string concatenation
error_message = (
    f"Failed to process ticker {ticker} "
    f"after {max_retries} attempts. "
    f"Last error: {str(error)}"
)
```

## Type Hints

### Function Signatures
```python
from typing import List, Dict, Optional, Union, Tuple, Any

# Always use type hints for function parameters and return values
def get_stock_price(ticker: str) -> Optional[float]:
    """Get current stock price"""
    try:
        return yf.Ticker(ticker).info['currentPrice']
    except Exception:
        return None

def process_tickers(
    tickers: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """Process multiple tickers"""
    results = {}
    for ticker in tickers:
        results[ticker] = fetch_data(ticker, start_date, end_date)
    return results

# Complex return types
def analyze_portfolio(
    holdings: Dict[str, float]
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Analyze portfolio
    
    Returns:
        Tuple of (total_value, total_return, detailed_analysis)
    """
    total_value = sum(holdings.values())
    total_return = calculate_return(holdings)
    details = generate_analysis(holdings)
    
    return total_value, total_return, details

# Union types for multiple possible types
def format_date(date: Union[str, datetime]) -> str:
    """Accept string or datetime object"""
    if isinstance(date, str):
        return date
    return date.strftime('%Y-%m-%d')
```

### Class Type Hints
```python
from typing import ClassVar, Protocol
from dataclasses import dataclass

@dataclass
class StockData:
    """Type-safe stock data container"""
    ticker: str
    price: float
    volume: int
    timestamp: datetime
    metadata: Dict[str, Any] = None

class StockAnalyzer:
    """Stock analyzer with type hints"""
    
    # Class variable
    DEFAULT_PERIOD: ClassVar[str] = '1y'
    
    def __init__(self, ticker: str) -> None:
        self.ticker: str = ticker
        self.data: Optional[pd.DataFrame] = None
        self.indicators: Dict[str, pd.Series] = {}
    
    def fetch_data(self, period: str = '1y') -> pd.DataFrame:
        """Fetch stock data"""
        self.data = yf.Ticker(self.ticker).history(period=period)
        return self.data
    
    def calculate_rsi(self, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        if self.data is None:
            raise ValueError("Must fetch data first")
        
        delta = self.data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        self.indicators['rsi'] = rsi
        return rsi
```

## Docstrings (Google Style)

### Module Docstring
```python
"""Stock analysis automation module.

This module provides functionality for automated stock analysis,
including technical indicators, fundamental metrics, and report generation.

Example:
    analyzer = StockAnalyzer('AAPL')
    analyzer.fetch_data(period='1y')
    report = analyzer.generate_report()

Author: TickZen Development Team
"""
```

### Function Docstring
```python
def calculate_moving_average(
    data: pd.Series,
    window: int,
    min_periods: Optional[int] = None
) -> pd.Series:
    """Calculate simple moving average.
    
    Computes the simple moving average (SMA) of a time series
    using a rolling window approach.
    
    Args:
        data: Time series data (e.g., stock prices)
        window: Number of periods for the moving average
        min_periods: Minimum number of observations required.
            If None, defaults to window size.
    
    Returns:
        Series containing the moving average values.
        NaN values for insufficient data points.
    
    Raises:
        ValueError: If window is less than 1
        TypeError: If data is not a pandas Series
    
    Example:
        >>> prices = pd.Series([100, 102, 101, 105, 107])
        >>> sma = calculate_moving_average(prices, window=3)
        >>> print(sma)
        0      NaN
        1      NaN
        2    101.0
        3    102.67
        4    104.33
    """
    if window < 1:
        raise ValueError("Window must be at least 1")
    
    if not isinstance(data, pd.Series):
        raise TypeError("Data must be a pandas Series")
    
    return data.rolling(window=window, min_periods=min_periods).mean()
```

### Class Docstring
```python
class EarningsAnalyzer:
    """Analyze company earnings reports.
    
    This class provides comprehensive earnings analysis including
    revenue trends, margin calculations, and year-over-year comparisons.
    
    Attributes:
        ticker: Stock ticker symbol
        quarters: Number of quarters to analyze
        data: DataFrame containing earnings data
        metrics: Calculated financial metrics
    
    Example:
        >>> analyzer = EarningsAnalyzer('AAPL', quarters=8)
        >>> analyzer.load_earnings_data()
        >>> metrics = analyzer.calculate_metrics()
        >>> print(metrics['revenue_growth'])
    """
    
    def __init__(self, ticker: str, quarters: int = 8) -> None:
        """Initialize earnings analyzer.
        
        Args:
            ticker: Stock ticker symbol
            quarters: Number of quarters to analyze (default: 8)
        """
        self.ticker = ticker
        self.quarters = quarters
        self.data: Optional[pd.DataFrame] = None
        self.metrics: Dict[str, Any] = {}
```

## Error Handling

### Specific Exceptions
```python
# Catch specific exceptions, not generic Exception
try:
    data = yf.Ticker(ticker).history(period='1y')
except KeyError as e:
    app.logger.error(f"Ticker {ticker} not found: {e}")
    raise ValueError(f"Invalid ticker: {ticker}")
except requests.exceptions.RequestException as e:
    app.logger.error(f"Network error: {e}")
    raise ConnectionError("Failed to fetch data")
except Exception as e:
    app.logger.error(f"Unexpected error: {e}", exc_info=True)
    raise

# Don't use bare except
try:
    risky_operation()
except:  # ❌ NEVER DO THIS
    pass

# At minimum, catch Exception and log it
try:
    risky_operation()
except Exception as e:  # ✅ ACCEPTABLE (but specific is better)
    app.logger.error(f"Error: {e}", exc_info=True)
    raise
```

### Custom Exceptions
```python
class TickZenError(Exception):
    """Base exception for TickZen"""
    pass

class DataFetchError(TickZenError):
    """Error fetching data from external API"""
    pass

class ReportGenerationError(TickZenError):
    """Error generating report"""
    pass

class PublishingError(TickZenError):
    """Error publishing to WordPress"""
    pass

# Usage
def fetch_stock_data(ticker: str) -> pd.DataFrame:
    """Fetch stock data"""
    try:
        return yf.Ticker(ticker).history(period='1y')
    except Exception as e:
        raise DataFetchError(f"Failed to fetch {ticker}: {e}") from e
```

## Logging Best Practices

### Structured Logging
```python
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Log levels hierarchy: DEBUG < INFO < WARNING < ERROR < CRITICAL

# DEBUG: Detailed diagnostic information
logger.debug(f"Processing ticker {ticker} with params: {params}")

# INFO: Confirmation that things are working as expected
logger.info(f"Successfully fetched data for {ticker}")

# WARNING: Something unexpected but not critical
logger.warning(f"Using cached data for {ticker} (API unavailable)")

# ERROR: Error that prevents specific operation
logger.error(f"Failed to publish {ticker}: {error}", exc_info=True)

# CRITICAL: Serious error, application may crash
logger.critical("Database connection lost", exc_info=True)
```

### Contextual Logging
```python
# Include context in log messages
logger.info(
    f"Report generated",
    extra={
        'ticker': ticker,
        'user_id': user_id,
        'sections': 32,
        'word_count': 4500,
        'generation_time': 45.3
    }
)

# Use exc_info=True for exceptions
try:
    process_data(ticker)
except Exception as e:
    logger.error(
        f"Processing failed for {ticker}",
        exc_info=True,  # Includes full traceback
        extra={'user_id': user_id}
    )
```

## Code Organization

### File Structure
```python
# Each file should have a clear purpose and reasonable size (<500 lines)

# Good: Separate concerns
# data_collection.py - Data fetching logic
# data_preprocessing.py - Data cleaning/transformation
# feature_engineering.py - Feature calculation
# technical_analysis.py - Technical indicators

# Bad: Everything in one file
# analysis.py (3000 lines) - Everything mixed together
```

### Function Size
```python
# Keep functions small and focused (< 50 lines)

# Good: Single responsibility
def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

# Bad: Too many responsibilities
def analyze_stock(ticker):  # ❌ Does too much
    data = fetch_data(ticker)
    data = clean_data(data)
    indicators = calculate_all_indicators(data)
    fundamentals = fetch_fundamentals(ticker)
    sentiment = analyze_sentiment(ticker)
    report = generate_report(data, indicators, fundamentals, sentiment)
    post_id = publish_report(report)
    send_notification(user, post_id)
    return post_id
```

## Testing Standards

### Test File Naming
```python
# Test files mirror source files with test_ prefix
# Source: analysis_scripts/technical_analysis.py
# Tests:  testing/test_technical_analysis.py

# Test functions describe what they test
def test_calculate_rsi_returns_correct_values():
    """RSI calculation returns expected values"""
    pass

def test_calculate_rsi_handles_empty_data():
    """RSI calculation handles empty DataFrame"""
    pass

def test_calculate_rsi_raises_error_for_invalid_window():
    """RSI raises ValueError for window < 1"""
    pass
```

### Assertion Messages
```python
import pytest

def test_stock_price_positive():
    """Stock price should always be positive"""
    price = get_stock_price('AAPL')
    
    # Good: Clear assertion message
    assert price > 0, f"Price should be positive, got {price}"
    
    # Better: Use pytest for better error messages
    assert price > 0  # pytest shows actual value automatically
```

## Code Comments

### When to Comment
```python
# ✅ GOOD: Explain WHY, not WHAT
# We multiply by 100 because the API returns decimal values (e.g., 0.05 for 5%)
percentage_value = api_value * 100

# ✅ GOOD: Document non-obvious logic
# Prophet requires a specific column naming convention
df = df.rename(columns={'date': 'ds', 'price': 'y'})

# ❌ BAD: Stating the obvious
# Get the user's name
user_name = user.get_name()

# ✅ GOOD: TODO comments with context
# TODO(username): Implement caching to reduce API calls (Issue #123)

# ❌ BAD: Vague TODO
# TODO: Fix this
```

### Docstring vs Comment
```python
# Use docstrings for public API documentation
def calculate_pe_ratio(price: float, earnings: float) -> float:
    """Calculate Price-to-Earnings ratio.
    
    Args:
        price: Current stock price
        earnings: Earnings per share
    
    Returns:
        P/E ratio, or None if earnings are zero
    """
    if earnings == 0:
        return None
    return price / earnings

# Use comments for internal implementation details
def _complex_internal_calculation(data):
    # First pass: Remove outliers using IQR method
    q1, q3 = data.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)
    
    filtered = data[(data >= lower_bound) & (data <= upper_bound)]
    
    # Second pass: Apply exponential smoothing
    # Alpha=0.3 chosen based on backtesting results
    smoothed = filtered.ewm(alpha=0.3).mean()
    
    return smoothed
```

## Performance Best Practices

### Use Built-in Functions
```python
# ❌ Slow: Manual loop
total = 0
for value in values:
    total += value

# ✅ Fast: Built-in function
total = sum(values)

# ❌ Slow: List comprehension for existence check
if ticker in [t for t in all_tickers]:
    pass

# ✅ Fast: Use sets for membership testing
ticker_set = set(all_tickers)
if ticker in ticker_set:
    pass
```

### Avoid Premature Optimization
```python
# First: Write clear, correct code
def calculate_metrics(data):
    """Calculate metrics - readable version"""
    mean = data.mean()
    std = data.std()
    percentiles = data.quantile([0.25, 0.5, 0.75])
    return {
        'mean': mean,
        'std': std,
        'q25': percentiles[0.25],
        'median': percentiles[0.5],
        'q75': percentiles[0.75]
    }

# Then: Profile and optimize bottlenecks if needed
# Use cProfile, line_profiler, etc. to identify slow code
```

## Linting Configuration

### flake8 (.flake8)
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    .git,
    __pycache__,
    venv,
    .venv,
    build,
    dist
```

### Black (pyproject.toml)
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  | venv
  | .venv
  | build
  | dist
)/
'''
```

### isort (pyproject.toml)
```toml
[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

## Pre-commit Hooks

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## Code Review Checklist

Before committing code:
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Imports are organized (standard, third-party, local)
- [ ] No unused imports or variables
- [ ] Error handling is specific and logged
- [ ] Code is formatted with Black
- [ ] No hardcoded credentials or API keys
- [ ] Tests written for new functionality
- [ ] Comments explain WHY, not WHAT
- [ ] Variable/function names are descriptive
- [ ] Line length ≤ 88 characters
- [ ] No print statements (use logging)
- [ ] No TODO comments without context/issue number
- [ ] Complex logic is broken into smaller functions
- [ ] No code duplication (DRY principle)

## Quick Reference

```python
# ✅ GOOD CODE EXAMPLE
import logging
from typing import List, Optional, Dict
from datetime import datetime

import pandas as pd
import yfinance as yf

from config.config import Config

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """Analyze stock data and generate insights.
    
    Attributes:
        ticker: Stock ticker symbol
        data: Historical price data
    """
    
    DEFAULT_PERIOD: str = '1y'
    
    def __init__(self, ticker: str) -> None:
        """Initialize analyzer.
        
        Args:
            ticker: Stock ticker symbol
        """
        self.ticker = ticker
        self.data: Optional[pd.DataFrame] = None
    
    def fetch_data(self, period: str = '1y') -> pd.DataFrame:
        """Fetch historical stock data.
        
        Args:
            period: Time period (e.g., '1y', '6mo')
        
        Returns:
            DataFrame with historical prices
        
        Raises:
            DataFetchError: If data fetch fails
        """
        try:
            stock = yf.Ticker(self.ticker)
            self.data = stock.history(period=period)
            
            if self.data.empty:
                raise ValueError(f"No data for {self.ticker}")
            
            logger.info(f"Fetched {len(self.data)} rows for {self.ticker}")
            return self.data
            
        except Exception as e:
            logger.error(f"Data fetch failed: {e}", exc_info=True)
            raise DataFetchError(f"Failed to fetch {self.ticker}") from e
```
