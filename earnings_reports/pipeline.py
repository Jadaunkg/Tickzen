"""
Earnings Pipeline Orchestrator

Main pipeline class that coordinates the entire earnings report workflow.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .data_collector import EarningsDataCollector
from .data_processor import EarningsDataProcessor
from .report_generator import EarningsReportGenerator
from .earnings_config import EarningsConfig
from .utils import (
    setup_logging, 
    format_ticker, 
    validate_ticker,
    create_earnings_summary,
    get_missing_data_report
)

logger = logging.getLogger(__name__)


class EarningsPipeline:
    """
    Main orchestrator for the earnings report pipeline.
    
    This class coordinates data collection, processing, and report generation
    for earnings reports.
    """
    
    def __init__(self, config: Optional[EarningsConfig] = None, log_level: str = 'INFO'):
        """
        Initialize the earnings pipeline.
        
        Args:
            config: Optional EarningsConfig instance
            log_level: Logging level
        """
        # Setup logging
        setup_logging(log_level)
        
        self.config = config or EarningsConfig()
        self.config.ensure_directories()
        
        # Initialize components
        self.collector = EarningsDataCollector(self.config)
        self.processor = EarningsDataProcessor(self.config)
        self.generator = EarningsReportGenerator(self.config)
        
        logger.info("Earnings pipeline initialized")
    
    def generate_pre_earnings_report(self, ticker: str, use_cache: bool = True, 
                                     save_report: bool = True) -> Dict[str, Any]:
        """
        Generate a complete pre-earnings report for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            save_report: Whether to save the report to file
            
        Returns:
            Dictionary containing report info and status
        """
        ticker = format_ticker(ticker)
        logger.info(f"Starting pre-earnings report generation for {ticker}")
        
        # Validate ticker
        if not validate_ticker(ticker):
            logger.error(f"Invalid ticker: {ticker}")
            return {
                'success': False,
                'error': f"Invalid ticker symbol: {ticker}",
                'ticker': ticker
            }
        
        try:
            # Step 1: Collect data
            logger.info(f"Step 1/3: Collecting data for {ticker}")
            raw_data = self.collector.collect_all_data(ticker, use_cache=use_cache)
            
            # Step 2: Process data
            logger.info(f"Step 2/3: Processing data for {ticker}")
            processed_data = self.processor.process_earnings_data(raw_data)
            
            # Step 3: Generate report
            logger.info(f"Step 3/3: Generating pre-earnings report for {ticker}")
            html_content = self.generator.generate_pre_earnings_report(
                processed_data, 
                save_to_file=save_report
            )
            
            # Create summary
            summary = create_earnings_summary(processed_data)
            
            result = {
                'success': True,
                'ticker': ticker,
                'report_type': 'pre_earnings',
                'html_content': html_content,
                'summary': summary,
                'data_quality': processed_data.get('data_quality', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            if save_report:
                result['report_path'] = self.config.get_report_path(ticker, 'pre_earnings')
            
            logger.info(f"Successfully generated pre-earnings report for {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating pre-earnings report for {ticker}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker,
                'report_type': 'pre_earnings'
            }
    
    def generate_post_earnings_report(self, ticker: str, use_cache: bool = True, 
                                      save_report: bool = True) -> Dict[str, Any]:
        """
        Generate a complete post-earnings report for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            save_report: Whether to save the report to file
            
        Returns:
            Dictionary containing report info and status
        """
        ticker = format_ticker(ticker)
        logger.info(f"Starting post-earnings report generation for {ticker}")
        
        # Validate ticker
        if not validate_ticker(ticker):
            logger.error(f"Invalid ticker: {ticker}")
            return {
                'success': False,
                'error': f"Invalid ticker symbol: {ticker}",
                'ticker': ticker
            }
        
        try:
            # Step 1: Collect data
            logger.info(f"Step 1/3: Collecting data for {ticker}")
            raw_data = self.collector.collect_all_data(ticker, use_cache=use_cache)
            
            # Step 2: Process data
            logger.info(f"Step 2/3: Processing data for {ticker}")
            processed_data = self.processor.process_earnings_data(raw_data)
            
            # Step 3: Generate report
            logger.info(f"Step 3/3: Generating post-earnings report for {ticker}")
            html_content = self.generator.generate_post_earnings_report(
                processed_data, 
                save_to_file=save_report
            )
            
            # Create summary
            summary = create_earnings_summary(processed_data)
            
            result = {
                'success': True,
                'ticker': ticker,
                'report_type': 'post_earnings',
                'html_content': html_content,
                'summary': summary,
                'data_quality': processed_data.get('data_quality', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            if save_report:
                result['report_path'] = self.config.get_report_path(ticker, 'post_earnings')
            
            logger.info(f"Successfully generated post-earnings report for {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating post-earnings report for {ticker}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker,
                'report_type': 'post_earnings'
            }
    
    def generate_both_reports(self, ticker: str, use_cache: bool = True, 
                            save_reports: bool = True) -> Dict[str, Any]:
        """
        Generate both pre and post earnings reports.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            save_reports: Whether to save reports to file
            
        Returns:
            Dictionary containing both report results
        """
        ticker = format_ticker(ticker)
        logger.info(f"Generating both pre and post earnings reports for {ticker}")
        
        pre_result = self.generate_pre_earnings_report(ticker, use_cache, save_reports)
        post_result = self.generate_post_earnings_report(ticker, use_cache, save_reports)
        
        return {
            'ticker': ticker,
            'pre_earnings': pre_result,
            'post_earnings': post_result,
            'overall_success': pre_result['success'] and post_result['success']
        }
    
    def batch_generate_reports(self, tickers: List[str], report_type: str = 'both',
                               use_cache: bool = True, save_reports: bool = True) -> List[Dict[str, Any]]:
        """
        Generate reports for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            report_type: 'pre', 'post', or 'both'
            use_cache: Whether to use cached data
            save_reports: Whether to save reports to file
            
        Returns:
            List of result dictionaries
        """
        logger.info(f"Starting batch report generation for {len(tickers)} tickers")
        results = []
        
        for ticker in tickers:
            ticker = format_ticker(ticker)
            logger.info(f"Processing {ticker} ({tickers.index(ticker)+1}/{len(tickers)})")
            
            if report_type == 'pre':
                result = self.generate_pre_earnings_report(ticker, use_cache, save_reports)
            elif report_type == 'post':
                result = self.generate_post_earnings_report(ticker, use_cache, save_reports)
            else:  # both
                result = self.generate_both_reports(ticker, use_cache, save_reports)
            
            results.append(result)
        
        # Summary
        if report_type == 'both':
            successful = sum(1 for r in results if r.get('overall_success'))
        else:
            successful = sum(1 for r in results if r.get('success'))
        
        logger.info(f"Batch processing complete: {successful}/{len(tickers)} successful")
        
        return results
    
    def get_data_only(self, ticker: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Collect and process data without generating a report.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            
        Returns:
            Processed earnings data
        """
        ticker = format_ticker(ticker)
        logger.info(f"Collecting and processing data for {ticker}")
        
        try:
            raw_data = self.collector.collect_all_data(ticker, use_cache=use_cache)
            processed_data = self.processor.process_earnings_data(raw_data)
            
            return {
                'success': True,
                'ticker': ticker,
                'data': processed_data,
                'summary': create_earnings_summary(processed_data),
                'missing_fields': get_missing_data_report(processed_data)
            }
        except Exception as e:
            logger.error(f"Error collecting data for {ticker}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker
            }
    
    def validate_and_report_data_quality(self, ticker: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Validate data quality for a ticker and generate a quality report.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            
        Returns:
            Data quality report
        """
        ticker = format_ticker(ticker)
        logger.info(f"Validating data quality for {ticker}")
        
        data_result = self.get_data_only(ticker, use_cache)
        
        if not data_result['success']:
            return data_result
        
        processed_data = data_result['data']
        
        quality_report = {
            'ticker': ticker,
            'completeness_score': processed_data.get('data_quality', {}).get('completeness_score', 0),
            'missing_critical_fields': processed_data.get('data_quality', {}).get('missing_critical_fields', []),
            'all_missing_fields': data_result['missing_fields'],
            'data_sources_used': list(processed_data.get('data_sources', {}).keys()),
            'recommendation': self._get_quality_recommendation(
                processed_data.get('data_quality', {}).get('completeness_score', 0)
            )
        }
        
        return quality_report
    
    def _get_quality_recommendation(self, score: float) -> str:
        """Get recommendation based on data quality score"""
        if score >= 90:
            return "Excellent - Report can be generated with high confidence"
        elif score >= 75:
            return "Good - Report can be generated, some fields may be missing"
        elif score >= 60:
            return "Fair - Report can be generated but may have significant gaps"
        else:
            return "Poor - Consider refreshing data or using alternative sources"


def quick_generate(ticker: str, report_type: str = 'both') -> Dict[str, Any]:
    """
    Quick function to generate earnings report(s) with default settings.
    
    Args:
        ticker: Stock ticker symbol
        report_type: 'pre', 'post', or 'both'
        
    Returns:
        Report result(s)
    """
    pipeline = EarningsPipeline()
    
    if report_type == 'pre':
        return pipeline.generate_pre_earnings_report(ticker)
    elif report_type == 'post':
        return pipeline.generate_post_earnings_report(ticker)
    else:
        return pipeline.generate_both_reports(ticker)
