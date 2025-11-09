#!/usr/bin/env python3
"""
Comprehensive Content Uniqueness Test for All Report Sections
Tests content generation uniqueness across all 21 report sections for TSLA stock.
Generates 8 variations per section and analyzes similarity patterns.
"""

import os
import sys
import json
import hashlib
import re
from datetime import datetime
import time

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Import WordPress reporter and related modules
    from reporting_tools.wordpress_reporter import (
        generate_wordpress_report,
        load_content_library,
        generate_wordpress_introduction_html,
        generate_wordpress_metrics_summary_html,
        generate_wordpress_company_profile_html,
        generate_wordpress_valuation_metrics_html,
        generate_wordpress_total_valuation_html,
        generate_wordpress_detailed_forecast_table_html,
        generate_wordpress_financial_health_html,
        generate_wordpress_financial_efficiency_html,
        generate_wordpress_profitability_growth_html,
        generate_wordpress_dividends_shareholder_returns_html,
        generate_wordpress_share_statistics_html,
        generate_wordpress_stock_price_statistics_html,
        generate_wordpress_short_selling_info_html,
        generate_wordpress_analyst_insights_html,
        generate_wordpress_technical_analysis_summary_html,
        generate_wordpress_historical_performance_html,
        generate_wordpress_conclusion_outlook_html,
        ALL_REPORT_SECTIONS
    )
    import app.html_components as hc
    from data_processing_scripts.data_collection import fetch_stock_data
    from data_processing_scripts.macro_data import fetch_macro_indicators
    from data_processing_scripts.data_preprocessing import preprocess_data
    from Models.prophet_model import train_prophet_model
    import analysis_scripts.fundamental_analysis as fa
    from config.config import START_DATE, END_DATE
    import yfinance as yf
    import pandas as pd
    
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class ComprehensiveContentTester:
    def __init__(self, ticker="TSLA", app_root=None):
        self.ticker = ticker
        self.app_root = app_root or project_root
        self.content_library = None
        self.rdata = None
        self.test_results = {}
        self.output_dir = os.path.join(project_root, "comprehensive_content_test_outputs")
        
        # All 21 sections with their handlers
        self.section_handlers = {
            # WordPress-Enhanced Sections (17)
            "introduction": generate_wordpress_introduction_html,
            "metrics_summary": generate_wordpress_metrics_summary_html,
            "company_profile": generate_wordpress_company_profile_html,
            "valuation_metrics": generate_wordpress_valuation_metrics_html,
            "total_valuation": generate_wordpress_total_valuation_html,
            "detailed_forecast_table": generate_wordpress_detailed_forecast_table_html,
            "financial_health": generate_wordpress_financial_health_html,
            "financial_efficiency": generate_wordpress_financial_efficiency_html,
            "profitability_growth": generate_wordpress_profitability_growth_html,
            "dividends_shareholder_returns": generate_wordpress_dividends_shareholder_returns_html,
            "share_statistics": generate_wordpress_share_statistics_html,
            "stock_price_statistics": generate_wordpress_stock_price_statistics_html,
            "short_selling_info": generate_wordpress_short_selling_info_html,
            "analyst_insights": generate_wordpress_analyst_insights_html,
            "technical_analysis_summary": generate_wordpress_technical_analysis_summary_html,
            "historical_performance": generate_wordpress_historical_performance_html,
            "conclusion_outlook": generate_wordpress_conclusion_outlook_html,
            
            # Standard Sections (4)
            "peer_comparison": hc.generate_peer_comparison_html,
            "risk_factors": hc.generate_risk_factors_html,
            "faq": hc.generate_faq_html,
            "report_info_disclaimer": hc.generate_report_info_disclaimer_html
        }
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
    def setup_data(self):
        """Setup the data and content library needed for testing."""
        print(f"🔄 Setting up data for {self.ticker}...")
        
        # Load content library
        self.content_library = load_content_library(self.app_root)
        if not self.content_library:
            print("⚠️  Content library not loaded - using fallback variations")
        else:
            print("✅ Content library loaded successfully")
        
        # Fetch stock data
        print("📊 Fetching stock data...")
        stock_data = fetch_stock_data(self.ticker, app_root=self.app_root, start_date=START_DATE, end_date=END_DATE, timeout=30)
        if stock_data is None or stock_data.empty:
            raise ValueError(f"Could not fetch stock data for {self.ticker}")
        
        # Fetch macro data
        print("📈 Fetching macro data...")
        macro_data = fetch_macro_indicators(app_root=self.app_root, start_date=START_DATE, end_date=END_DATE)
        if macro_data is None or macro_data.empty:
            print("⚠️  Using fallback macro data")
            date_range_stock = pd.date_range(start=stock_data['Date'].min(), end=stock_data['Date'].max(), freq='D')
            macro_data = pd.DataFrame({'Date': date_range_stock})
            for col_macro in ['Interest_Rate', 'SP500', 'Interest_Rate_MA30', 'SP500_MA30']:
                macro_data[col_macro] = 0.0
        
        # Preprocess data
        print("🔧 Preprocessing data...")
        processed_data = preprocess_data(stock_data, macro_data)
        if processed_data is None or processed_data.empty:
            raise ValueError("Preprocessing resulted in empty data.")
        
        # Train Prophet model (with fallback for Windows issues)
        print("🤖 Training Prophet model...")
        ts = str(int(time.time()))
        try:
            model, forecast_raw, actual_df, forecast_df = train_prophet_model(
                processed_data.copy(), self.ticker, forecast_horizon='1y', timestamp=ts
            )
        except Exception as e:
            print(f"⚠️  Prophet model training failed: {e}")
            print("📊 Using mock forecast data for testing...")
            
            # Create mock forecast data for testing purposes
            actual_df = processed_data.copy()
            dates = pd.date_range(start=processed_data['Date'].max(), periods=365, freq='D')
            forecast_df = pd.DataFrame({
                'ds': dates,
                'yhat': [processed_data['Close'].iloc[-1] * (1 + i*0.001) for i in range(365)],
                'yhat_lower': [processed_data['Close'].iloc[-1] * (1 + i*0.001 - 0.1) for i in range(365)],
                'yhat_upper': [processed_data['Close'].iloc[-1] * (1 + i*0.001 + 0.1) for i in range(365)]
            })
            forecast_raw = forecast_df.copy()
            model = None
        
        # Fetch fundamentals
        print("💼 Fetching fundamentals...")
        yf_ticker_obj = yf.Ticker(self.ticker)
        fundamentals = {
            'info': yf_ticker_obj.info or {},
            'recommendations': yf_ticker_obj.recommendations if hasattr(yf_ticker_obj, 'recommendations') and yf_ticker_obj.recommendations is not None else pd.DataFrame(),
            'news': yf_ticker_obj.news if hasattr(yf_ticker_obj, 'news') and yf_ticker_obj.news is not None else []
        }
        
        # Generate comprehensive rdata
        print("📋 Generating rdata...")
        
        # Initialize rdata
        self.rdata = {}
        self.rdata['ticker'] = self.ticker
        self.rdata['current_price'] = processed_data['Close'].iloc[-1] if not processed_data.empty else None
        self.rdata['last_date'] = processed_data['Date'].iloc[-1] if not processed_data.empty else datetime.now()
        self.rdata['historical_data'] = processed_data
        self.rdata['actual_data'] = actual_df
        self.rdata['monthly_forecast_table_data'] = forecast_df
        
        # Set up forecast data
        if not forecast_df.empty:
            self.rdata['forecast_1m'] = forecast_df['yhat'].iloc[30] if len(forecast_df) > 30 else forecast_df['yhat'].iloc[-1]
            self.rdata['forecast_1y'] = forecast_df['yhat'].iloc[-1]
            
            if self.rdata['forecast_1y'] and self.rdata['current_price'] and self.rdata['current_price'] > 0:
                self.rdata['overall_pct_change'] = ((self.rdata['forecast_1y'] - self.rdata['current_price']) / self.rdata['current_price']) * 100
            else:
                self.rdata['overall_pct_change'] = 0.0
        else:
            self.rdata['forecast_1m'] = None
            self.rdata['forecast_1y'] = None
            self.rdata['overall_pct_change'] = 0.0
        
        # Extract fundamental data using the functions from fundamental_analysis
        current_price_for_fa = self.rdata.get('current_price')
        self.rdata['profile_data'] = fa.extract_company_profile(fundamentals)
        self.rdata['valuation_data'] = fa.extract_valuation_metrics(fundamentals)
        self.rdata['total_valuation_data'] = fa.extract_total_valuation_data(fundamentals, current_price_for_fa)
        self.rdata['share_statistics_data'] = fa.extract_share_statistics_data(fundamentals, current_price_for_fa)
        self.rdata['financial_health_data'] = fa.extract_financial_health(fundamentals)
        self.rdata['financial_efficiency_data'] = fa.extract_financial_efficiency_data(fundamentals)
        self.rdata['profitability_data'] = fa.extract_profitability(fundamentals)
        self.rdata['dividends_data'] = fa.extract_dividends_splits(fundamentals)
        self.rdata['analyst_info_data'] = fa.extract_analyst_info(fundamentals)
        self.rdata['stock_price_stats_data'] = fa.extract_stock_price_stats_data(fundamentals)
        self.rdata['short_selling_data'] = fa.extract_short_selling_data(fundamentals)
        self.rdata['peer_comparison_data'] = fa.extract_peer_comparison_data(self.ticker)
        self.rdata['industry'] = fundamentals.get('info', {}).get('industry', 'N/A')
        self.rdata['sector'] = fundamentals.get('info', {}).get('sector', 'N/A')
        
        # Technical analysis data
        import analysis_scripts.technical_analysis as ta_module
        self.rdata['detailed_ta_data'] = ta_module.calculate_detailed_ta(processed_data)
        self.rdata['sma_50'] = self.rdata['detailed_ta_data'].get('SMA_50')
        self.rdata['sma_200'] = self.rdata['detailed_ta_data'].get('SMA_200')
        self.rdata['latest_rsi'] = self.rdata['detailed_ta_data'].get('RSI_14')
        
        # Calculate volatility
        if 'Close' in processed_data.columns and len(processed_data) > 30:
            log_returns = pd.Series(processed_data['Close']).pct_change()
            self.rdata['volatility'] = log_returns.iloc[-30:].std() * (252 ** 0.5) * 100
        else:
            self.rdata['volatility'] = None
        
        # Calculate green days
        if 'Close' in processed_data.columns and 'Open' in processed_data.columns and len(processed_data) >= 30:
            last_30_days = processed_data.iloc[-30:]
            self.rdata['green_days'] = (last_30_days['Close'] > last_30_days['Open']).sum()
            self.rdata['total_days'] = 30
        else:
            self.rdata['green_days'] = None
            self.rdata['total_days'] = None
        
        # Calculate sentiment
        sentiment_score = 0
        if self.rdata.get('current_price') and self.rdata.get('sma_50') and self.rdata['current_price'] > self.rdata['sma_50']:
            sentiment_score += 1
        if self.rdata.get('current_price') and self.rdata.get('sma_200') and self.rdata['current_price'] > self.rdata['sma_200']:
            sentiment_score += 2
        if self.rdata.get('latest_rsi') and self.rdata['latest_rsi'] < 70:
            sentiment_score += 0.5
        if self.rdata.get('latest_rsi') and self.rdata['latest_rsi'] < 30:
            sentiment_score += 1
        
        if sentiment_score >= 4:
            self.rdata['sentiment'] = 'Bullish'
        elif sentiment_score >= 2:
            self.rdata['sentiment'] = 'Neutral-Bullish'
        elif sentiment_score >= 0:
            self.rdata['sentiment'] = 'Neutral'
        else:
            self.rdata['sentiment'] = 'Bearish'
        
        print("✅ Data setup complete!")
        
    def clean_html_content(self, html_content):
        """Clean HTML content for text comparison."""
        if not html_content:
            return ""
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', ' ', html_content)
        # Remove extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text)
        # Remove special characters and normalize
        clean_text = re.sub(r'[^\w\s]', ' ', clean_text)
        # Convert to lowercase and strip
        clean_text = clean_text.lower().strip()
        
        return clean_text
    
    def calculate_similarity(self, text1, text2):
        """Calculate similarity between two texts using word overlap."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) * 100
    
    def generate_section_variations(self, section_name, variations=8):
        """Generate multiple variations of a section."""
        print(f"  🔄 Generating {variations} variations for {section_name}...")
        
        section_variations = []
        handler = self.section_handlers.get(section_name)
        
        if not handler:
            print(f"  ❌ No handler found for section: {section_name}")
            return []
        
        for i in range(variations):
            try:
                # Generate content based on section type
                if section_name == "report_info_disclaimer":
                    # Special case: requires datetime parameter
                    content = handler(datetime.now())
                elif section_name in ["peer_comparison", "risk_factors", "faq"]:
                    # Standard sections without content library
                    content = handler(self.ticker, self.rdata)
                else:
                    # WordPress sections with content library
                    content = handler(self.ticker, self.rdata, self.content_library)
                
                # Clean content for analysis
                clean_content = self.clean_html_content(content)
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                
                variation_data = {
                    'iteration': i + 1,
                    'content': content,
                    'clean_content': clean_content,
                    'hash': content_hash,
                    'word_count': len(clean_content.split()) if clean_content else 0,
                    'char_count': len(content) if content else 0,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                section_variations.append(variation_data)
                
                # Save individual variation to file
                filename = f"{section_name}_variation_{i+1}.html"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{section_name.title()} Content - Variation {i+1}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metadata {{ background: #f5f5f5; padding: 10px; margin-bottom: 20px; }}
        .content {{ background: white; padding: 20px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="metadata">
        <h3>Test Metadata</h3>
        <p><strong>Section:</strong> {section_name}</p>
        <p><strong>Variation:</strong> {i+1}</p>
        <p><strong>Generated:</strong> {variation_data['timestamp']}</p>
        <p><strong>Content Hash:</strong> {content_hash}</p>
        <p><strong>Word Count:</strong> {variation_data['word_count']}</p>
        <p><strong>Character Count:</strong> {variation_data['char_count']}</p>
    </div>
    
    <div class="content">
        {content}
    </div>
</body>
</html>""")
                
                print(f"    ✅ Variation {i+1} generated (Hash: {content_hash[:8]}...)")
                
            except Exception as e:
                print(f"    ❌ Error generating variation {i+1}: {e}")
                variation_data = {
                    'iteration': i + 1,
                    'error': str(e),
                    'content': None,
                    'clean_content': "",
                    'hash': None,
                    'word_count': 0,
                    'char_count': 0,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                section_variations.append(variation_data)
        
        return section_variations
    
    def analyze_section_uniqueness(self, section_name, variations):
        """Analyze uniqueness within a section's variations."""
        print(f"  📊 Analyzing uniqueness for {section_name}...")
        
        valid_variations = [v for v in variations if v.get('content') and v.get('hash')]
        
        if len(valid_variations) < 2:
            return {
                'unique_hashes': len(valid_variations),
                'total_variations': len(variations),
                'uniqueness_percentage': 100.0 if len(valid_variations) <= 1 else 0.0,
                'average_similarity': 0.0,
                'max_similarity': 0.0,
                'min_similarity': 0.0,
                'similarity_matrix': [],
                'errors': len(variations) - len(valid_variations)
            }
        
        # Check hash uniqueness
        unique_hashes = len(set(v['hash'] for v in valid_variations))
        
        # Calculate pairwise similarities
        similarities = []
        similarity_matrix = []
        
        for i, var1 in enumerate(valid_variations):
            row = []
            for j, var2 in enumerate(valid_variations):
                if i != j:
                    similarity = self.calculate_similarity(var1['clean_content'], var2['clean_content'])
                    similarities.append(similarity)
                    row.append(similarity)
                else:
                    row.append(100.0)  # Self-similarity
            similarity_matrix.append(row)
        
        analysis = {
            'unique_hashes': unique_hashes,
            'total_variations': len(variations),
            'uniqueness_percentage': (unique_hashes / len(valid_variations)) * 100,
            'average_similarity': sum(similarities) / len(similarities) if similarities else 0.0,
            'max_similarity': max(similarities) if similarities else 0.0,
            'min_similarity': min(similarities) if similarities else 0.0,
            'similarity_matrix': similarity_matrix,
            'errors': len(variations) - len(valid_variations)
        }
        
        return analysis
    
    def analyze_cross_section_similarity(self, all_results):
        """Analyze similarity between different sections."""
        print("🔍 Analyzing cross-section similarities...")
        
        section_samples = {}
        
        # Get first valid variation from each section
        for section_name, results in all_results.items():
            variations = results.get('variations', [])
            for var in variations:
                if var.get('content') and var.get('clean_content'):
                    section_samples[section_name] = var['clean_content']
                    break
        
        cross_similarities = {}
        
        for section1_name, content1 in section_samples.items():
            cross_similarities[section1_name] = {}
            for section2_name, content2 in section_samples.items():
                if section1_name != section2_name:
                    similarity = self.calculate_similarity(content1, content2)
                    cross_similarities[section1_name][section2_name] = similarity
        
        return cross_similarities
    
    def run_comprehensive_test(self, variations_per_section=8):
        """Run the comprehensive test across all sections."""
        print(f"🚀 Starting comprehensive content uniqueness test for {self.ticker}")
        print(f"📋 Testing {len(self.section_handlers)} sections with {variations_per_section} variations each")
        print("=" * 70)
        
        # Setup data
        self.setup_data()
        
        # Test each section
        for i, section_name in enumerate(self.section_handlers.keys(), 1):
            print(f"\n📝 [{i}/{len(self.section_handlers)}] Testing section: {section_name}")
            
            # Generate variations
            variations = self.generate_section_variations(section_name, variations_per_section)
            
            # Analyze uniqueness
            analysis = self.analyze_section_uniqueness(section_name, variations)
            
            # Store results
            self.test_results[section_name] = {
                'variations': variations,
                'analysis': analysis
            }
            
            # Print summary
            print(f"  📊 Results: {analysis['unique_hashes']}/{analysis['total_variations']} unique hashes")
            print(f"  🎯 Uniqueness: {analysis['uniqueness_percentage']:.1f}%")
            print(f"  📈 Avg Similarity: {analysis['average_similarity']:.1f}%")
            print(f"  🔺 Max Similarity: {analysis['max_similarity']:.1f}%")
            if analysis['errors'] > 0:
                print(f"  ⚠️  Errors: {analysis['errors']}")
        
        # Cross-section analysis
        cross_similarities = self.analyze_cross_section_similarity(self.test_results)
        
        # Generate comprehensive report
        self.generate_comprehensive_report(cross_similarities)
        
        print(f"\n✅ Comprehensive test completed!")
        print(f"📁 Results saved to: {self.output_dir}")
        
        return self.test_results
    
    def generate_comprehensive_report(self, cross_similarities):
        """Generate a comprehensive analysis report."""
        print("📊 Generating comprehensive report...")
        
        # Calculate overall statistics
        total_sections = len(self.test_results)
        sections_with_good_uniqueness = 0
        sections_with_moderate_uniqueness = 0
        sections_with_poor_uniqueness = 0
        
        overall_stats = {
            'total_sections_tested': total_sections,
            'total_variations_generated': 0,
            'total_successful_generations': 0,
            'total_errors': 0,
            'sections_summary': []
        }
        
        for section_name, results in self.test_results.items():
            analysis = results['analysis']
            variations = results['variations']
            
            overall_stats['total_variations_generated'] += len(variations)
            overall_stats['total_successful_generations'] += analysis['unique_hashes']
            overall_stats['total_errors'] += analysis['errors']
            
            # Categorize sections by uniqueness
            if analysis['max_similarity'] < 70:
                sections_with_good_uniqueness += 1
                uniqueness_category = "Good"
            elif analysis['max_similarity'] < 85:
                sections_with_moderate_uniqueness += 1
                uniqueness_category = "Moderate"
            else:
                sections_with_poor_uniqueness += 1
                uniqueness_category = "Poor"
            
            section_summary = {
                'section_name': section_name,
                'unique_hashes': analysis['unique_hashes'],
                'total_variations': analysis['total_variations'],
                'uniqueness_percentage': analysis['uniqueness_percentage'],
                'max_similarity': analysis['max_similarity'],
                'average_similarity': analysis['average_similarity'],
                'uniqueness_category': uniqueness_category,
                'errors': analysis['errors']
            }
            
            overall_stats['sections_summary'].append(section_summary)
        
        # Add categorization summary
        overall_stats['uniqueness_distribution'] = {
            'good_uniqueness': sections_with_good_uniqueness,
            'moderate_uniqueness': sections_with_moderate_uniqueness,
            'poor_uniqueness': sections_with_poor_uniqueness
        }
        
        # Save detailed JSON report
        report_data = {
            'test_metadata': {
                'ticker': self.ticker,
                'test_date': datetime.now().isoformat(),
                'variations_per_section': 8,
                'total_sections': total_sections
            },
            'overall_statistics': overall_stats,
            'detailed_results': self.test_results,
            'cross_section_similarities': cross_similarities
        }
        
        json_report_path = os.path.join(self.output_dir, 'comprehensive_test_report.json')
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Generate human-readable summary report
        summary_report_path = os.path.join(self.output_dir, 'test_summary_report.txt')
        with open(summary_report_path, 'w', encoding='utf-8') as f:
            f.write(f"""
COMPREHENSIVE CONTENT UNIQUENESS TEST REPORT
===========================================

Test Details:
- Ticker: {self.ticker}
- Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Sections Tested: {total_sections}
- Variations per Section: 8
- Total Variations Generated: {overall_stats['total_variations_generated']}

OVERALL RESULTS:
===============
✅ Successful Generations: {overall_stats['total_successful_generations']}/{overall_stats['total_variations_generated']} ({overall_stats['total_successful_generations']/overall_stats['total_variations_generated']*100:.1f}%)
❌ Errors: {overall_stats['total_errors']}

UNIQUENESS DISTRIBUTION:
=======================
🟢 Good Uniqueness (< 70% max similarity): {sections_with_good_uniqueness} sections
🟡 Moderate Uniqueness (70-85% max similarity): {sections_with_moderate_uniqueness} sections  
🔴 Poor Uniqueness (> 85% max similarity): {sections_with_poor_uniqueness} sections

SECTION-BY-SECTION ANALYSIS:
============================
""")
            
            for section_summary in overall_stats['sections_summary']:
                status_emoji = "🟢" if section_summary['uniqueness_category'] == "Good" else "🟡" if section_summary['uniqueness_category'] == "Moderate" else "🔴"
                f.write(f"{status_emoji} {section_summary['section_name']}:\n")
                f.write(f"   Unique Hashes: {section_summary['unique_hashes']}/{section_summary['total_variations']}\n")
                f.write(f"   Uniqueness: {section_summary['uniqueness_percentage']:.1f}%\n")
                f.write(f"   Max Similarity: {section_summary['max_similarity']:.1f}%\n")
                f.write(f"   Avg Similarity: {section_summary['average_similarity']:.1f}%\n")
                if section_summary['errors'] > 0:
                    f.write(f"   Errors: {section_summary['errors']}\n")
                f.write(f"\n")
            
            # Cross-section similarity summary
            f.write("\nCROSS-SECTION SIMILARITY ANALYSIS:\n")
            f.write("==================================\n")
            f.write("(Average similarity between different sections)\n\n")
            
            if cross_similarities:
                # Calculate average cross-section similarity
                all_cross_sims = []
                for section1, sims in cross_similarities.items():
                    for section2, sim in sims.items():
                        all_cross_sims.append(sim)
                
                if all_cross_sims:
                    avg_cross_sim = sum(all_cross_sims) / len(all_cross_sims)
                    max_cross_sim = max(all_cross_sims)
                    min_cross_sim = min(all_cross_sims)
                    
                    f.write(f"Average Cross-Section Similarity: {avg_cross_sim:.1f}%\n")
                    f.write(f"Maximum Cross-Section Similarity: {max_cross_sim:.1f}%\n")
                    f.write(f"Minimum Cross-Section Similarity: {min_cross_sim:.1f}%\n")
        
        print(f"✅ Comprehensive report saved to: {summary_report_path}")

def main():
    """Main function to run the comprehensive test."""
    print("🔬 Comprehensive Content Uniqueness Test")
    print("=======================================")
    
    try:
        tester = ComprehensiveContentTester(ticker="TSLA")
        results = tester.run_comprehensive_test(variations_per_section=8)
        
        print("\n🎉 Test completed successfully!")
        print(f"📁 Check results in: {tester.output_dir}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)