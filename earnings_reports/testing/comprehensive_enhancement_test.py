"""
Comprehensive Earnings Enhancement Test

Tests all enhanced functionality after cleanup:
- Enhanced data extraction
- Data quality improvements  
- Missing value filling
- Analyst sentiment mapping
- Interest expense calculation
- PEG ratio calculation
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the project path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from earnings_reports.data_collector import EarningsDataCollector
from earnings_reports.data_processor import EarningsDataProcessor
from earnings_reports.earnings_config import EarningsConfig


def convert_for_json(obj):
    """Convert objects for JSON serialization"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, 'timestamp'):
        return obj.isoformat()
    elif str(type(obj).__name__) == 'Timestamp':
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return [convert_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
    else:
        try:
            return str(obj) if obj is not None else None
        except:
            return "Unable to serialize"


def analyze_enhancements(earnings_data, ticker):
    """Analyze the enhancements made to the data"""
    print(f"\n{'='*60}")
    print(f"🔍 ENHANCEMENT ANALYSIS FOR {ticker}")
    print(f"{'='*60}")
    
    # Data Quality Metrics
    na_count = count_na_values(earnings_data)
    total_fields = count_total_fields(earnings_data)
    completeness = ((total_fields - na_count) / total_fields * 100) if total_fields > 0 else 0
    
    print(f"📊 DATA QUALITY METRICS:")
    print(f"   • Total Fields: {total_fields}")
    print(f"   • N/A Values: {na_count}")
    print(f"   • Completeness: {completeness:.1f}%")
    
    # Enhanced Field Analysis
    print(f"\n🚀 ENHANCED FIELDS:")
    
    # Company Identification
    company = earnings_data.get('company_identification', {})
    print(f"   • CIK: {company.get('cik', 'N/A')}")
    
    # Balance Sheet Enhancements
    balance = earnings_data.get('balance_sheet', {})
    goodwill = balance.get('goodwill', 'N/A')
    intangible = balance.get('intangible_assets', 'N/A')
    print(f"   • Goodwill: {format_currency(goodwill)}")
    print(f"   • Intangible Assets: {format_currency(intangible)}")
    
    # Income Statement Enhancements  
    income = earnings_data.get('income_statement', {})
    interest_exp = income.get('interest_expense', 'N/A')
    print(f"   • Interest Expense: {format_currency(interest_exp)}")
    
    # Valuation Enhancements
    valuation = earnings_data.get('valuation_metrics', {})
    peg_ratio = valuation.get('peg_ratio', 'N/A')
    print(f"   • PEG Ratio: {peg_ratio}")
    if valuation.get('peg_ratio_estimated'):
        print(f"     (Calculated from PE ratio and growth rate)")
    
    # Analyst Sentiment Enhancements
    analyst = earnings_data.get('analyst_sentiment', {})
    buy_ratings = analyst.get('buy_ratings', 'N/A')
    hold_ratings = analyst.get('hold_ratings', 'N/A')  
    sell_ratings = analyst.get('sell_ratings', 'N/A')
    
    print(f"   • Analyst Buy Ratings: {buy_ratings}")
    print(f"   • Analyst Hold Ratings: {hold_ratings}")
    print(f"   • Analyst Sell Ratings: {sell_ratings}")
    
    # Enhanced Analytics
    if 'enhanced_analytics' in earnings_data:
        enhanced = earnings_data['enhanced_analytics']
        print(f"\n🎯 ENHANCED ANALYTICS:")
        
        # One-time Items
        one_time = enhanced.get('one_time_items', {})
        items_count = len(one_time.get('items_found', {}))  # Fixed: was 'items', now 'items_found' 
        total_impact = one_time.get('total_one_time_impact', 0)  # Fixed: was 'total_impact', now 'total_one_time_impact'
        print(f"   • One-time Items: {items_count} identified")
        print(f"   • Total Impact: {format_currency(total_impact)}")
        
        # Adjusted Earnings
        adjusted = enhanced.get('adjusted_earnings', {})
        adj_eps = adjusted.get('adjusted_eps', 'N/A')
        print(f"   • Adjusted EPS: ${adj_eps}")
        
        # Cash Sustainability
        cash_analysis = enhanced.get('cash_sustainability', {})
        runway = cash_analysis.get('cash_runway_months', 'N/A')
        burn_rate = cash_analysis.get('monthly_burn_rate', 'N/A')
        print(f"   • Cash Runway: {runway} months")
        print(f"   • Monthly Burn Rate: {format_currency(burn_rate)}")
    
    return {
        'completeness_score': completeness,
        'na_count': na_count,
        'total_fields': total_fields,
        'enhanced_fields_populated': sum([
            1 for field in [goodwill, intangible, interest_exp, peg_ratio, buy_ratings, hold_ratings, sell_ratings]
            if field != 'N/A' and field != 0
        ])
    }


def format_currency(value):
    """Format currency values"""
    if value == 'N/A' or value is None:
        return 'N/A'
    try:
        num_value = float(value)
        if num_value == 0:
            return '$0'
        elif abs(num_value) >= 1e9:
            return f"${num_value/1e9:.1f}B"
        elif abs(num_value) >= 1e6:
            return f"${num_value/1e6:.1f}M"
        elif abs(num_value) >= 1e3:
            return f"${num_value/1e3:.1f}K"
        else:
            return f"${num_value:.2f}"
    except (ValueError, TypeError):
        return str(value)


def count_na_values(data):
    """Count N/A values recursively"""
    count = 0
    if isinstance(data, dict):
        for value in data.values():
            if value == 'N/A':
                count += 1
            elif isinstance(value, (dict, list)):
                count += count_na_values(value)
    elif isinstance(data, list):
        for item in data:
            if item == 'N/A':
                count += 1
            elif isinstance(item, (dict, list)):
                count += count_na_values(item)
    return count


def count_total_fields(data):
    """Count total fields recursively"""
    count = 0
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, (dict, list)):
                count += count_total_fields(value)
            else:
                count += 1
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                count += count_total_fields(item)
            else:
                count += 1
    return count


def test_comprehensive_enhancements():
    """Run comprehensive enhancement testing"""
    test_tickers = ['AAPL', 'MSFT', 'TSLA']
    
    print(f"🧪 STARTING COMPREHENSIVE ENHANCEMENT TEST")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Testing Enhanced Data Extraction & Quality Improvements")
    print(f"📊 Test Tickers: {', '.join(test_tickers)}")
    
    config = EarningsConfig()
    collector = EarningsDataCollector(config)
    processor = EarningsDataProcessor(config)
    
    results = {}
    
    for ticker in test_tickers:
        print(f"\n{'='*80}")
        print(f"🔄 PROCESSING {ticker}")
        print(f"{'='*80}")
        
        try:
            # Step 1: Collect Data
            print(f"1️⃣ Collecting raw data for {ticker}...")
            raw_data = collector.collect_all_data(ticker)
            
            if not raw_data or 'data_sources' not in raw_data:
                print(f"❌ Failed to collect data for {ticker}")
                results[ticker] = {'status': 'failed', 'stage': 'collection'}
                continue
            
            print(f"✅ Raw data collection successful")
            
            # Step 2: Process & Enhance Data
            print(f"2️⃣ Processing and enhancing data...")
            processed_data = processor.process_earnings_data(raw_data)
            
            if not processed_data or 'earnings_data' not in processed_data:
                print(f"❌ Failed to process data for {ticker}")
                results[ticker] = {'status': 'failed', 'stage': 'processing'}
                continue
            
            print(f"✅ Data processing and enhancement successful")
            
            # Step 3: Analyze Enhancements
            print(f"3️⃣ Analyzing enhancements...")
            enhancement_metrics = analyze_enhancements(processed_data['earnings_data'], ticker)
            
            # Step 4: Save Results
            print(f"4️⃣ Saving enhanced data...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"test_results/comprehensive_test_{ticker}_{timestamp}.json"
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(processed_data, f, default=convert_for_json, indent=2)
            
            print(f"💾 Results saved to {output_file}")
            
            # Store test results
            results[ticker] = {
                'status': 'success',
                'file': output_file,
                'metrics': enhancement_metrics,
                'data_quality_score': processed_data.get('data_quality', {}).get('completeness_score', 0)
            }
            
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            logger.exception(f"Error in comprehensive test for {ticker}")
            results[ticker] = {
                'status': 'error', 
                'error': str(e),
                'stage': 'unknown'
            }
    
    # Final Summary
    print_test_summary(results)
    
    return results


def print_test_summary(results):
    """Print comprehensive test summary"""
    print(f"\n{'='*80}")
    print(f"📋 COMPREHENSIVE ENHANCEMENT TEST SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results.values() if r['status'] == 'success')
    total = len(results)
    
    print(f"📊 OVERALL RESULTS:")
    print(f"   • Total Tests: {total}")
    print(f"   • Successful: {successful}")
    print(f"   • Success Rate: {(successful/total*100):.1f}%")
    
    if successful > 0:
        print(f"\n🏆 SUCCESSFUL ENHANCEMENTS:")
        for ticker, result in results.items():
            if result['status'] == 'success':
                metrics = result.get('metrics', {})
                quality_score = result.get('data_quality_score', 0)
                
                print(f"   • {ticker}:")
                print(f"     - Data Quality Score: {quality_score}%")
                print(f"     - Completeness: {metrics.get('completeness_score', 0):.1f}%")
                print(f"     - Enhanced Fields: {metrics.get('enhanced_fields_populated', 0)}")
                print(f"     - N/A Values: {metrics.get('na_count', 0)}")
    
    if successful < total:
        print(f"\n❌ FAILED TESTS:")
        for ticker, result in results.items():
            if result['status'] != 'success':
                stage = result.get('stage', 'unknown')
                error = result.get('error', 'Unknown error')
                print(f"   • {ticker}: Failed at {stage} - {error}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    print("🚀 Starting Comprehensive Enhancement Test...")
    test_results = test_comprehensive_enhancements()
    print("✅ Comprehensive test completed!")