"""
Earnings Reports Pipeline

A comprehensive system for collecting, processing, and generating earnings reports
using data from yfinance, Alpha Vantage, and Finnhub.

Modules:
    - data_collector: Fetches earnings data from multiple sources
    - data_processor: Normalizes and validates earnings data
    - report_generator: Generates pre-earnings and post-earnings articles
    - pipeline: Main orchestrator for the earnings pipeline
    - config: Configuration settings for the pipeline
    - utils: Helper utilities
"""

from .data_collector import EarningsDataCollector
from .data_processor import EarningsDataProcessor
# from .report_generator import EarningsReportGenerator  # Temporarily disabled
from .earnings_config import EarningsConfig
# from .pipeline import EarningsPipeline, quick_generate  # Temporarily disabled

__all__ = [
    'EarningsDataCollector',
    'EarningsDataProcessor', 
    # 'EarningsReportGenerator',  # Temporarily disabled
    'EarningsConfig',
    # 'EarningsPipeline',  # Temporarily disabled
    # 'quick_generate'  # Temporarily disabled
]

__version__ = '1.0.0'
