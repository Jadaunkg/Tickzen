"""
Test Perplexity AI Research Collection for Bangladesh Cricket Headline
This script tests the story-focused Perplexity research collection for a specific sports headline
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directories to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))
sys.path.append(str(parent_dir / "utilities"))

# Import the Perplexity AI client
from utilities.perplexity_ai_client import PerplexityResearchCollector

def test_perplexity_research():
    """Test Perplexity research collection with Bangladesh cricket headline"""
    
    # Initialize the headline
    test_headline = "Bangladesh bring back Taskin, drop Jaker from T20 World Cup squad"
    
    print("🏏 Testing Perplexity AI Research Collection")
    print("=" * 70)
    print(f"📰 Headline: {test_headline}")
    print(f"🕐 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        # Initialize Perplexity Research Collector
        print("🚀 Initializing Perplexity Research Collector...")
        collector = PerplexityResearchCollector()
        
        if not collector.api_key:
            print("❌ Error: PERPLEXITY_API_KEY not found!")
            print("   Please set the PERPLEXITY_API_KEY environment variable")
            return None
            
        print("✅ Perplexity client initialized successfully")
        
        # Collect research using the enhanced method (story-focused approach)
        print(f"\n🔍 Starting story-focused research collection...")
        print(f"   Using enhanced single-request method with story focus")
        
        research_result = collector.collect_enhanced_research_for_headline(
            headline=test_headline,
            source="Bangladesh Cricket",
            category="cricket"
        )
        
        # Check if research was successful
        if research_result.get('status') == 'success':
            print("✅ Research collection completed successfully!")
            
            # Display key metrics
            research_data = research_result.get('research_data', {})
            content_length = len(research_data.get('comprehensive_research', ''))
            sources_count = len(research_result.get('compiled_sources', []))
            
            print(f"\n📊 Research Results Summary:")
            print(f"   📝 Research content length: {content_length:,} characters")
            print(f"   🔗 Sources collected: {sources_count}")
            print(f"   🎯 Collection method: {research_result.get('collection_method', 'unknown')}")
            print(f"   ⏱️ Research timestamp: {research_result.get('collection_timestamp', 'unknown')}")
            
            # Display source citations
            if research_result.get('compiled_citations'):
                print(f"\n📚 Source Citations:")
                for i, citation in enumerate(research_result['compiled_citations'][:5], 1):
                    print(f"   {i}. {citation}")
                if len(research_result['compiled_citations']) > 5:
                    print(f"   ... and {len(research_result['compiled_citations']) - 5} more sources")
            
            # Save results to file
            save_results_to_file(research_result, test_headline)
            
            return research_result
            
        else:
            print(f"❌ Research collection failed!")
            print(f"   Error: {research_result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Exception during research collection: {str(e)}")
        return None

def save_results_to_file(research_result: dict, headline: str):
    """Save research results to a text file"""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path(__file__).parent / "testing_output"
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_headline = "".join(c for c in headline if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_headline = clean_headline.replace(' ', '_')[:50]
        filename = f"perplexity_research_{clean_headline}_{timestamp}.txt"
        filepath = output_dir / filename
        
        # Write detailed results to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("PERPLEXITY AI RESEARCH COLLECTION RESULTS\n")
            f.write("=" * 80 + "\n\n")
            
            # Header information
            f.write(f"Headline: {headline}\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Collection Method: {research_result.get('collection_method', 'unknown')}\n")
            f.write(f"Status: {research_result.get('status', 'unknown')}\n\n")
            
            # Research data
            research_data = research_result.get('research_data', {})
            if research_data:
                f.write("-" * 50 + "\n")
                f.write("COMPREHENSIVE RESEARCH DATA\n")
                f.write("-" * 50 + "\n\n")
                
                comprehensive_research = research_data.get('comprehensive_research', '')
                if comprehensive_research:
                    f.write(comprehensive_research)
                    f.write("\n\n")
                
            # Source information
            if research_result.get('compiled_sources'):
                f.write("-" * 50 + "\n")
                f.write("SOURCE URLS\n")
                f.write("-" * 50 + "\n\n")
                for i, source in enumerate(research_result['compiled_sources'], 1):
                    f.write(f"{i}. {source}\n")
                f.write("\n")
                
            # Citations
            if research_result.get('compiled_citations'):
                f.write("-" * 50 + "\n")
                f.write("SOURCE CITATIONS\n")
                f.write("-" * 50 + "\n\n")
                for i, citation in enumerate(research_result['compiled_citations'], 1):
                    f.write(f"{i}. {citation}\n")
                f.write("\n")
                
            # Content freshness information
            if research_result.get('freshness_validation'):
                freshness = research_result['freshness_validation']
                f.write("-" * 50 + "\n")
                f.write("CONTENT FRESHNESS VALIDATION\n")
                f.write("-" * 50 + "\n\n")
                f.write(f"Fresh articles count: {freshness.get('fresh_count', 'N/A')}\n")
                f.write(f"Filtered articles count: {freshness.get('filtered_count', 'N/A')}\n")
                f.write(f"Content age compliance: {freshness.get('all_fresh', 'N/A')}\n\n")
                
            # Raw JSON data (for debugging)
            f.write("-" * 50 + "\n")
            f.write("RAW JSON DATA (FOR DEBUGGING)\n")
            f.write("-" * 50 + "\n\n")
            f.write(json.dumps(research_result, indent=2, ensure_ascii=False))
            
        print(f"\n💾 Research results saved to: {filepath}")
        
    except Exception as e:
        print(f"❌ Error saving results to file: {str(e)}")

def main():
    """Main function to run the test"""
    print("🏏 Perplexity AI Research Collection Test")
    print("Testing story-focused research for Bangladesh Cricket headline\n")
    
    # Run the test
    result = test_perplexity_research()
    
    if result:
        print("\n✅ Test completed successfully!")
        print("   Check the testing_output directory for detailed results.")
    else:
        print("\n❌ Test failed!")
        print("   Please check your API configuration and try again.")
    
    print("\n" + "=" * 70)
    print("Test session ended.")

if __name__ == "__main__":
    main()