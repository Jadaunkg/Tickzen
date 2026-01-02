# Real-time Data Configuration
# Configuration settings for real-time stock data fetching

import os
from datetime import datetime

# Real-time data fetching settings
REALTIME_CONFIG = {
    # Enable real-time data fetching (vs. cached data only)
    'enable_realtime_fetch': True,
    
    # Cache validity periods (in hours)
    'daily_cache_validity_hours': 24,
    'intraday_cache_validity_hours': 1,
    'current_price_cache_validity_minutes': 15,
    
    # Data intervals for different analysis types
    'default_interval': '1d',           # Daily data for standard analysis
    'intraday_interval': '5m',          # 5-minute data for intraday analysis
    'realtime_interval': '1m',          # 1-minute data for real-time tracking
    
    # Market hours settings
    'respect_market_hours': True,       # More aggressive caching during off-hours
    'weekend_cache_extension_days': 3,  # Allow older data on weekends
    
    # Performance settings
    'max_intraday_days': 7,            # Limit intraday data to last 7 days
    'throttle_seconds': 0.3,           # Delay between API calls
    'timeout_seconds': 30,             # API timeout
    
    # Feature flags
    'enable_current_price_fetch': True, # Fetch current market price
    'enable_intraday_analysis': True,   # Include intraday data in analysis
    'enable_market_hours_check': True,  # Check if market is open
    
    # Data quality settings
    'min_data_points_required': 30,    # Minimum data points for analysis
    'max_missing_days_allowed': 5,     # Maximum gaps in data
}

def get_realtime_config():
    """
    Get real-time configuration with environment variable overrides.
    """
    config = REALTIME_CONFIG.copy()
    
    # Allow environment variable overrides
    env_overrides = {
        'TICKZEN_ENABLE_REALTIME': 'enable_realtime_fetch',
        'TICKZEN_RESPECT_MARKET_HOURS': 'respect_market_hours',
        'TICKZEN_ENABLE_INTRADAY': 'enable_intraday_analysis',
        'TICKZEN_THROTTLE_SECONDS': 'throttle_seconds',
    }
    
    for env_var, config_key in env_overrides.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            if config_key in ['enable_realtime_fetch', 'respect_market_hours', 'enable_intraday_analysis']:
                config[config_key] = env_value.lower() in ('true', '1', 'yes', 'on')
            elif config_key in ['throttle_seconds']:
                try:
                    config[config_key] = float(env_value)
                except ValueError:
                    pass
    
    return config

def is_realtime_enabled():
    """Quick check if real-time fetching is enabled."""
    return get_realtime_config()['enable_realtime_fetch']

def get_cache_validity_hours(data_type='daily'):
    """Get cache validity period for different data types."""
    config = get_realtime_config()
    cache_key = f'{data_type}_cache_validity_hours'
    return config.get(cache_key, 24)

def should_use_intraday():
    """Check if intraday data should be used."""
    config = get_realtime_config()
    return config['enable_intraday_analysis']

# Development vs Production settings
if os.getenv('APP_ENV', 'development').lower() == 'production':
    # Production: More conservative caching to reduce API costs
    REALTIME_CONFIG.update({
        'daily_cache_validity_hours': 6,    # Refresh daily data every 6 hours
        'intraday_cache_validity_hours': 2, # Refresh intraday data every 2 hours
        'throttle_seconds': 0.5,            # Slower throttling
    })
else:
    # Development: More aggressive real-time fetching for testing
    REALTIME_CONFIG.update({
        'daily_cache_validity_hours': 1,    # Refresh daily data every hour
        'intraday_cache_validity_hours': 0.5, # Refresh intraday data every 30 minutes
        'throttle_seconds': 0.1,            # Faster throttling
    })