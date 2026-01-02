"""
Working Test Script for Enhanced Earnings Reports

Tests the enhanced earnings report system with proper import handling.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def test_enhanced_earnings_system():
    """Test the enhanced earnings system with proper error handling."""
    logger.info("Starting Enhanced Earnings System Test")
    logger.info("="*50)
    
    test_results = {
        'test_timestamp': datetime.now().isoformat(),
        'test_results': {},
        'summary': {}
    }
    
    # Test tickers
    test_tickers = ['AAPL', 'FWDI', 'TSLA']
    
    for ticker in test_tickers:
        logger.info(f"\nTesting {ticker}...")
        ticker_result = test_single_ticker(ticker)
        test_results['test_results'][ticker] = ticker_result
    
    # Generate summary
    successful_tests = sum(1 for result in test_results['test_results'].values() if result.get('overall_success', False))
    total_tests = len(test_tickers)
    
    test_results['summary'] = {
        'total_tickers_tested': total_tests,
        'successful_tests': successful_tests,
        'success_rate': f"{(successful_tests/total_tests*100):.1f}%",
        'failed_tickers': [ticker for ticker, result in test_results['test_results'].items() if not result.get('overall_success', False)]
    }
    
    # Save results
    results_dir = os.path.join(current_dir, 'test_results')
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(results_dir, f'working_test_results_{timestamp}.json')
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Total Tickers Tested: {total_tests}")
    logger.info(f"Successful Tests: {successful_tests}")
    logger.info(f"Success Rate: {test_results['summary']['success_rate']}")
    if test_results['summary']['failed_tickers']:
        logger.info(f"Failed Tickers: {', '.join(test_results['summary']['failed_tickers'])}")
    logger.info(f"Results saved to: {results_file}")
    logger.info(f"{'='*50}")
    
    return test_results

def test_single_ticker(ticker):
    """Test data collection for a single ticker."""
    result = {
        'ticker': ticker,
        'data_collection': {'success': False, 'errors': []},
        'enhanced_analytics': {'success': False, 'errors': []},
        'data_processing': {'success': False, 'errors': []},
        'overall_success': False
    }
    
    try:
        # Import modules dynamically
        logger.info(f"Importing modules for {ticker}...")
        
        from data_collector import EarningsDataCollector
        from data_processor import EarningsDataProcessor
        from earnings_config import EarningsConfig
        
        logger.info(f"✅ Modules imported successfully for {ticker}")
        
        # Initialize components
        config = EarningsConfig()
        collector = EarningsDataCollector(config)
        processor = EarningsDataProcessor(config)
        
        # Test data collection
        logger.info(f"Collecting data for {ticker}...")
        raw_data = collector.collect_all_data(ticker, use_cache=False)
        
        if raw_data and 'data_sources' in raw_data:
            result['data_collection']['success'] = True
            logger.info(f"✅ Data collection successful for {ticker}")
            
            # Check for enhanced analytics
            if 'enhanced_analytics' in raw_data:
                result['enhanced_analytics']['success'] = True
                
                # Check components
                enhanced = raw_data['enhanced_analytics']
                result['enhanced_analytics']['one_time_items'] = 'one_time_items' in enhanced
                result['enhanced_analytics']['adjusted_earnings'] = 'adjusted_earnings' in enhanced
                result['enhanced_analytics']['cash_sustainability'] = 'cash_sustainability' in enhanced
                
                logger.info(f"✅ Enhanced analytics found for {ticker}")
                
                # Log some details
                if enhanced.get('one_time_items', {}).get('items_found'):
                    items_count = len(enhanced['one_time_items']['items_found'])
                    logger.info(f"  📊 One-time items found: {items_count}")
                
                if enhanced.get('cash_sustainability', {}).get('metrics', {}).get('cash_runway'):
                    runway = enhanced['cash_sustainability']['metrics']['cash_runway'].get('cash_runway_months')
                    if isinstance(runway, (int, float)):
                        logger.info(f"  💰 Cash runway: {runway:.1f} months")
                
            else:
                result['enhanced_analytics']['errors'].append("No enhanced analytics in raw data")
                logger.warning(f"⚠️ No enhanced analytics found for {ticker}")
            
            # Test data processing
            logger.info(f"Processing data for {ticker}...")
            processed_data = processor.process_earnings_data(raw_data)
            
            if processed_data and 'earnings_data' in processed_data:
                result['data_processing']['success'] = True
                logger.info(f"✅ Data processing successful for {ticker}")
                
                # Save individual ticker data (actual earnings data)
                save_success = save_ticker_data(ticker, raw_data, processed_data)
                if not save_success:
                    result['data_processing']['errors'].append("Failed to save ticker data to files")
                
            else:
                result['data_processing']['errors'].append("Data processing returned no earnings data")
                logger.error(f"❌ Data processing failed for {ticker}")
        
        else:
            result['data_collection']['errors'].append("No data sources returned from collection")
            logger.error(f"❌ Data collection failed for {ticker}")
    
    except Exception as e:
        error_msg = f"Error testing {ticker}: {str(e)}"
        result['data_collection']['errors'].append(error_msg)
        logger.error(f"❌ {error_msg}")
        # Don't log full traceback for JSON serialization errors as they're not critical
        if "keys must be str" not in str(e):
            import traceback
            logger.error(traceback.format_exc())
    
    # Determine overall success
    result['overall_success'] = (
        result['data_collection']['success'] and 
        result['enhanced_analytics']['success'] and 
        result['data_processing']['success']
    )
    
    return result

def save_ticker_data(ticker, raw_data, processed_data):
    """Save ticker data to JSON files with proper serialization."""
    # Create collected_data directory for actual earnings data
    collected_data_dir = os.path.join(os.path.dirname(__file__), 'collected_data')
    os.makedirs(collected_data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def convert_for_json(obj):
        """Convert pandas/numpy objects to JSON-serializable formats including keys."""
        if isinstance(obj, dict):
            # Convert keys and values
            new_dict = {}
            for k, v in obj.items():
                # Convert key to string if it's a Timestamp or other non-serializable type
                if hasattr(k, 'isoformat'):  # Pandas Timestamp
                    new_key = k.isoformat()
                elif hasattr(k, '__str__') and not isinstance(k, (str, int, float, bool, type(None))):
                    new_key = str(k)
                else:
                    new_key = k
                
                # Convert value recursively
                new_dict[new_key] = convert_for_json(v)
            return new_dict
        elif isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime/Timestamp
            return obj.isoformat()
        elif hasattr(obj, 'item'):  # numpy types
            return obj.item()
        elif hasattr(obj, 'tolist'):  # numpy arrays
            return obj.tolist()
        elif str(obj) == 'nan' or (hasattr(obj, '__ne__') and obj != obj):  # NaN
            return None
        else:
            return obj
    
    try:
        # Convert data to JSON-serializable format
        serializable_raw = convert_for_json(raw_data)
        serializable_processed = convert_for_json(processed_data)
        
        # Save raw earnings data
        raw_file = os.path.join(collected_data_dir, f"{ticker}_earnings_raw_{timestamp}.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_raw, f, indent=2)
        
        # Save processed earnings data  
        processed_file = os.path.join(collected_data_dir, f"{ticker}_earnings_processed_{timestamp}.json")
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_processed, f, indent=2)
        
        logger.info(f"💾 Saved {ticker} earnings data to collected_data/ directory")
        
        # Also create a summary file for this ticker
        summary_data = {
            'ticker': ticker,
            'collection_timestamp': timestamp,
            'data_summary': {
                'raw_data_size_kb': round(len(json.dumps(serializable_raw)) / 1024, 2),
                'processed_data_size_kb': round(len(json.dumps(serializable_processed)) / 1024, 2),
                'enhanced_analytics_included': 'enhanced_analytics' in raw_data,
                'data_sources': list(raw_data.get('data_sources', {}).keys()),
                'processing_completed': 'earnings_data' in processed_data
            }
        }
        
        # Extract key metrics for quick reference
        if 'enhanced_analytics' in raw_data:
            enhanced = raw_data['enhanced_analytics']
            summary_data['enhanced_summary'] = {
                'one_time_items_found': len(enhanced.get('one_time_items', {}).get('items_found', {})),
                'has_adjusted_earnings': 'adjusted_earnings' in enhanced,
                'cash_runway_months': enhanced.get('cash_sustainability', {}).get('metrics', {}).get('cash_runway', {}).get('cash_runway_months'),
                'risk_level': enhanced.get('cash_sustainability', {}).get('risk_level')
            }
        
        summary_file = os.path.join(collected_data_dir, f"{ticker}_summary_{timestamp}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save {ticker} data: {e}")
        return False

if __name__ == "__main__":
    results = test_enhanced_earnings_system()