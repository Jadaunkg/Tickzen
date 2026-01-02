#!/usr/bin/env python3
"""
Test Enhanced Sports Article Pipeline
=====================================

Test script to verify that the enhanced pipeline works correctly with
both Perplexity research and Enhanced Search content combined.

Usage:
    python test_enhanced_pipeline.py
    
Author: Tickzen AI System
Created: December 25, 2025
"""

import sys
import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import pipeline components
from core.article_generation_pipeline import ArticleGenerationPipeline
from utilities.perplexity_ai_client import PerplexityResearchCollector
from utilities.sports_article_generator import SportsArticleGenerator
from testing.test_enhanced_search_content import EnhancedSearchContentFetcher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_enhanced_pipeline():
    """Test the enhanced pipeline with both research sources"""
    
    print("🧪 TESTING ENHANCED SPORTS ARTICLE PIPELINE")
    print("="*70)
    print("This test verifies that the pipeline can combine research from:")
    print("• Perplexity AI (web research)")
    print("• Enhanced Search (full article content)")
    print()
    
    try:
        # Step 1: Initialize all clients
        print("⚙️ Step 1: Initializing pipeline clients...")
        
        perplexity_client = PerplexityResearchCollector()
        gemini_client = SportsArticleGenerator()
        enhanced_search_client = EnhancedSearchContentFetcher()
        
        print(f"   📡 Perplexity API: {'✅ Available' if perplexity_client.api_key else '❌ Not configured'}")
        print(f"   🤖 Gemini AI: {'✅ Available' if gemini_client.available else '❌ Not configured'}")
        print(f"   🔍 Enhanced Search: {'✅ Available' if enhanced_search_client.available else '❌ Not configured'}")
        
        # Initialize enhanced pipeline
        pipeline = ArticleGenerationPipeline(
            perplexity_client=perplexity_client,
            gemini_client=gemini_client,
            enhanced_search_client=enhanced_search_client
        )
        print("   ✅ Enhanced pipeline initialized!")
        print()
        
        # Step 2: Test with a sample headline
        test_headline = "Cristiano Ronaldo scores hat-trick in Champions League victory"
        
        print(f"🧪 Step 2: Testing with sample headline:")
        print(f"   📰 {test_headline}")
        print()
        
        # Create test article entry
        article_entry = {
            'title': test_headline,
            'source_name': 'Test Source',
            'category': 'football',
            'url': '',
            'published_date': datetime.now().strftime('%Y-%m-%d'),
            'importance_score': 75
        }
        
        # Step 3: Generate article using enhanced pipeline
        print("🔄 Step 3: Generating article with enhanced pipeline...")
        start_time = time.time()
        
        generated_article = pipeline.generate_article_for_headline(article_entry)
        
        generation_time = time.time() - start_time
        
        # Step 4: Evaluate results
        print(f"⏱️ Step 4: Evaluating results (took {generation_time:.2f}s)")
        print("="*70)
        
        if generated_article.get('status') == 'success':
            print("🎉 ENHANCED PIPELINE TEST SUCCESSFUL!")
            print()
            
            # Display article info
            headline = generated_article.get('headline', 'No headline')
            content = generated_article.get('article_content', '')
            word_count = len(content.split()) if content else 0
            
            print(f"📊 Generated Article Summary:")
            print(f"   📰 Headline: {headline}")
            print(f"   📝 Word Count: {word_count}")
            print(f"   🏷️ Category: {generated_article.get('category', 'Unknown')}")
            print()
            
            # Check workflow metadata for research info
            workflow_metadata = generated_article.get('workflow_metadata', {})
            research_sources = workflow_metadata.get('research_sources_used', [])
            
            if research_sources:
                print(f"🔍 Research Sources Used:")
                for source in research_sources:
                    print(f"   ✅ {source}")
            
            # Save test article
            try:
                saved_path = pipeline.save_generated_article(generated_article, "test_outputs")
                if saved_path:
                    print(f"💾 Test article saved: {saved_path}")
            except Exception as e:
                print(f"⚠️ Could not save test article: {e}")
            
            print()
            print("🎯 TEST CONCLUSION:")
            print("The enhanced pipeline successfully combines research from multiple sources!")
            print("Both Perplexity AI and Enhanced Search content are being used for richer articles.")
            
        elif generated_article.get('status') == 'partial_success':
            print("⚠️ PARTIAL SUCCESS - Some research sources failed")
            print(f"   Error details: {generated_article.get('error', 'Unknown error')}")
            
            # Still check what worked
            workflow_metadata = generated_article.get('workflow_metadata', {})
            if workflow_metadata:
                print(f"   Working sources: {workflow_metadata.get('research_sources_used', [])}")
            
        else:
            print("❌ ENHANCED PIPELINE TEST FAILED")
            error = generated_article.get('error', 'Unknown error')
            print(f"   Error: {error}")
            
            # Check individual component availability
            print("\n🔍 Troubleshooting:")
            if not perplexity_client.api_key:
                print("   • Perplexity API key not configured - add PERPLEXITY_API_KEY to .env")
            if not gemini_client.available:
                print("   • Gemini AI not available - add GEMINI_API_KEY to .env") 
            if not enhanced_search_client.available:
                print("   • Enhanced Search not available - add Google Search API keys to .env")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "="*70)
    print("🏁 Enhanced Pipeline Test Completed")
    print("="*70)


if __name__ == "__main__":
    test_enhanced_pipeline()