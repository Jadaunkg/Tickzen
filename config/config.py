#!/usr/bin/env python3
"""
TickZen Configuration Management
===============================

Central configuration management for the TickZen platform. Defines system-wide
settings, supported tickers, analysis parameters, and environment-specific
configurations used across all modules.

Configuration Categories:
------------------------
1. **Ticker Management**: Supported stock symbols and validation
2. **Date Ranges**: Historical data collection parameters
3. **Forecast Options**: Prophet model forecasting horizons
4. **Analysis Settings**: Default parameters for various analysis types
5. **Performance Limits**: System performance and resource constraints

Supported Tickers:
-----------------
Configurable list of stock symbols for analysis:
- Default: Tesla (TSLA) for initial setup
- Expandable: Easy addition of new tickers
- Validation: Automatic ticker symbol validation
- Categories: Grouping by sector, market cap, etc.

Forecast Configuration:
----------------------
Prophet model forecasting parameters:
- **Short-term**: 15 days for immediate trends
- **Medium-term**: 1 month for tactical decisions
- **Long-term**: 3+ months for strategic planning
- **Custom**: User-defined forecast periods

Data Collection Settings:
------------------------
- **Historical Range**: Maximum historical data (from 2012)
- **Update Frequency**: Data refresh intervals
- **Quality Thresholds**: Minimum data quality requirements
- **Cache Settings**: Data caching TTL and strategies

Analysis Parameters:
-------------------
- **Technical Analysis**: Default indicator periods and parameters
- **Fundamental Analysis**: Ratio calculation settings
- **Risk Analysis**: VaR confidence levels and time horizons
- **Sentiment Analysis**: Source weights and scoring algorithms

Performance Configuration:
-------------------------
- **Concurrency**: Maximum parallel analysis processes
- **Memory Limits**: Analysis pipeline memory constraints
- **Timeout Settings**: API call and analysis timeouts
- **Cache Sizes**: Memory and disk cache limitations

Environment Integration:
-----------------------
Supports multiple deployment environments:
- **Development**: Local development settings
- **Staging**: Pre-production testing configuration
- **Production**: Live deployment optimization
- **Testing**: Unit and integration test settings

Usage Pattern:
-------------
```python
from config.config import TICKERS, FORECAST_OPTIONS

# Use configured tickers for analysis
for ticker in TICKERS:
    run_analysis(ticker)

# Apply forecast settings
forecast_days = FORECAST_OPTIONS['1 month']
```

Configuration Validation:
------------------------
- **Type Checking**: Ensure correct data types
- **Range Validation**: Verify numeric ranges
- **Format Validation**: Check date formats and patterns
- **Dependency Verification**: Validate inter-config dependencies

Dynamic Configuration:
---------------------
- **Environment Variables**: Override via env vars
- **Runtime Updates**: Modify settings during execution
- **User Preferences**: Per-user configuration overrides
- **A/B Testing**: Feature flag support

Security Considerations:
-----------------------
- **Sensitive Data**: No API keys or secrets in this file
- **Environment Separation**: Clear dev/prod boundaries
- **Access Control**: Configuration access restrictions
- **Audit Trail**: Configuration change tracking

Author: TickZen Development Team
Version: 1.4
Last Updated: January 2026
"""

from datetime import datetime, timedelta
import os

# List of tickers; you can later add more.
TICKERS = ["TSLA"]  # e.g., ["AAPL", "GOOGL", "MSFT"]

# Date range for data collection
START_DATE = "2012-01-01"  # Earliest practical date
END_DATE = datetime.today().strftime("%Y-%m-%d")  # Current date

# --- Forecast Horizon Options ---
# Keys are the display options and values are the corresponding forecast period in days.
FORECAST_OPTIONS = {
    "15 days": 15,
    "1 month": 30,
    "3 month": 90,
    "6 month": 180,
    "1 year": 365,
    "2 year": 730,
    "5 year": 1825
}


FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')

# ============================================================================
# CACHING CONFIGURATION
# ============================================================================

# Cache configuration for Flask-Caching
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',  # Use SimpleCache for development, Redis for production
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
    'CACHE_KEY_PREFIX': 'tickzen_',
    'CACHE_THRESHOLD': 500  # Maximum number of items in cache
}

# Redis configuration (for production)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Production cache config
PRODUCTION_CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': REDIS_URL,
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'tickzen_',
    'CACHE_OPTIONS': {
        'socket_connect_timeout': 2,
        'socket_timeout': 2,
        'retry_on_timeout': True,
        'max_connections': 50
    }
}

# Different TTL for different data types (in seconds)
CACHE_TTL = {
    'user_profile': 600,           # 10 minutes - rarely changes
    'site_profiles': 300,          # 5 minutes - moderate changes
    'site_profiles_list': 180,     # 3 minutes - for profile listings
    'report_count': 60,            # 1 minute - changes frequently
    'report_history': 120,         # 2 minutes - moderate frequency
    'dashboard_stats': 120,        # 2 minutes - frequently updated
    'admin_analytics': 180,        # 3 minutes - not critical to be real-time
    'storage_check': 3600,         # 1 hour - expensive operation
    'published_articles': 300,     # 5 minutes
    'automation_state': 60,        # 1 minute - needs to be fresh
    'counter_values': 30,          # 30 seconds - frequently updated
}
