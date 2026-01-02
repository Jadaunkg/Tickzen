"""
Quick Test Runner for Enhanced Earnings Reports

Simple script to run the enhanced earnings test suite.
"""

import sys
import os
import logging

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from test_enhanced_earnings import run_enhanced_earnings_tests

if __name__ == "__main__":
    print("Starting Enhanced Earnings Reports Test Suite...")
    print("This will test data collection, enhanced analytics, and compatibility.")
    print("Results will be saved to test_results/ directory.")
    print("-" * 60)
    
    # Set logging level for cleaner output during testing
    logging.getLogger().setLevel(logging.WARNING)  # Reduce noise during testing
    
    try:
        results = run_enhanced_earnings_tests()
        
        if results:
            print("\n✅ Testing completed successfully!")
            print(f"📊 Results saved with timestamp: {results['test_timestamp']}")
        else:
            print("\n❌ Testing failed - check logs for details")
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        print(traceback.format_exc())