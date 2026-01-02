#!/usr/bin/env python3
"""
Sports Article Generation Pipeline
==================================

Complete pipeline that:
1. Takes a sports headline as input
2. Performs enhanced search to collect comprehensive information
3. Generates human-style article using Gemini AI
4. Saves final article to final_article folder

Usage:
    python sports_article_pipeline.py
    
    Or with command line argument:
    python sports_article_pipeline.py "Your headline here"
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import our existing components
from test_enhanced_search_content import EnhancedSearchContentFetcher
from test_gemini_article_generation import GeminiArticleTester

class SportsArticlePipeline:
    """Complete pipeline for sports article generation"""
    
    def __init__(self):
        """Initialize the pipeline with both components"""
        print("🚀 Initializing Sports Article Generation Pipeline")
        print("="*70)
        
        # Initialize enhanced search component
        self.search_fetcher = EnhancedSearchContentFetcher()
        
        # Initialize Gemini article generator
        self.article_generator = GeminiArticleTester()
        
        # Setup directories
        self.final_article_dir = Path(__file__).parent / "final_article"
        self.final_article_dir.mkdir(exist_ok=True)
        
        print("✅ Pipeline ready!")
        print(f"   📂 Articles will be saved to: {self.final_article_dir}")
        print()
    
    def generate_article_from_headline(self, headline: str, max_sources: int = 10) -> dict:
        """
        Complete pipeline: headline → research → article generation
        
        Args:
            headline (str): Sports headline to research and write about
            max_sources (int): Maximum sources to collect (default: 10)
            
        Returns:
            dict: Pipeline result with status, timing, and file paths
        """
        pipeline_start = time.time()
        
        print(f"📰 SPORTS ARTICLE PIPELINE")
        print(f"   Headline: {headline}")
        print(f"   Max Sources: {max_sources}")
        print("="*70)
        
        try:
            # Step 1: Enhanced Search & Content Collection
            print("🔍 STEP 1: Enhanced Search & Content Collection")
            print("-"*50)
            
            search_start = time.time()
            search_result = self.search_fetcher.collect_comprehensive_research(
                headline=headline,
                max_sources=max_sources
            )
            search_time = time.time() - search_start
            
            if search_result.get('status') != 'success':
                return {
                    'status': 'error',
                    'error': f"Search failed: {search_result.get('error', 'Unknown error')}",
                    'search_time': search_time
                }
            
            print(f"✅ Search completed in {search_time:.2f}s")
            print(f"   📊 Sources found: {search_result.get('total_sources_processed', 0)}")
            print(f"   📝 Total words: {search_result.get('total_words_collected', 0)}")
            print()
            
            # Step 2: Article Generation with Gemini AI
            print("🤖 STEP 2: Human-Style Article Generation")
            print("-"*50)
            
            generation_start = time.time()
            article_result = self.article_generator.generate_human_article_from_sources(search_result)
            generation_time = time.time() - generation_start
            
            if article_result.get('status') != 'success':
                return {
                    'status': 'error',
                    'error': f"Article generation failed: {article_result.get('error', 'Unknown error')}",
                    'search_time': search_time,
                    'generation_time': generation_time
                }
            
            # Step 3: Save Generated Article
            print("💾 STEP 3: Saving Generated Article")
            print("-"*50)
            
            saved_file_path = self.article_generator.save_generated_article(
                article_result, headline
            )
            
            if not saved_file_path:
                return {
                    'status': 'error',
                    'error': 'Failed to save generated article',
                    'search_time': search_time,
                    'generation_time': generation_time,
                    'article_result': article_result
                }
            
            print(f"✅ Article generated in {generation_time:.2f}s")
            print(f"   📝 Word count: {article_result.get('word_count', 0)}")
            print(f"   💾 Saved to: {saved_file_path}")
            print()
            
            # Step 4: Results Summary
            total_time = time.time() - pipeline_start
            
            print("🎯 PIPELINE COMPLETED SUCCESSFULLY!")
            print("="*70)
            print(f"📊 PERFORMANCE SUMMARY:")
            print(f"   🔍 Search Time: {search_time:.2f}s")
            print(f"   🤖 Generation Time: {generation_time:.2f}s") 
            print(f"   ⏱️  Total Time: {total_time:.2f}s")
            print()
            print(f"📄 ARTICLE DETAILS:")
            print(f"   📰 Headline: {headline}")
            print(f"   📝 Word Count: {article_result.get('word_count', 0)}")
            print(f"   📊 Sources Used: {search_result.get('total_sources_processed', 0)}")
            print(f"   💾 Saved to: {saved_file_path}")
            print()
            
            return {
                'status': 'success',
                'headline': headline,
                'search_result': search_result,
                'article_result': article_result,
                'timing': {
                    'search_time': search_time,
                    'generation_time': generation_time,
                    'total_time': total_time
                },
                'file_paths': {
                    'article_file': saved_file_path,
                    'data_file': saved_file_path.replace('.txt', '.json') if saved_file_path else None
                }
            }
            
        except Exception as e:
            total_time = time.time() - pipeline_start
            error_msg = f"Pipeline error: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'status': 'error',
                'error': error_msg,
                'total_time': total_time
            }
    
    def interactive_mode(self):
        """Interactive mode for manual headline input"""
        print("🎮 INTERACTIVE MODE")
        print("="*70)
        print("Enter sports headlines to generate articles")
        print("Type 'quit' or 'exit' to stop")
        print()
        
        while True:
            try:
                headline = input("📰 Enter sports headline: ").strip()
                
                if headline.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not headline:
                    print("❌ Please enter a headline")
                    continue
                
                print()
                result = self.generate_article_from_headline(headline)
                
                if result['status'] == 'success':
                    print("🎉 Article generated successfully!")
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
                print("\n" + "="*70 + "\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue

def main():
    """Main function - handles command line arguments or interactive mode"""
    
    # Create pipeline
    pipeline = SportsArticlePipeline()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Use command line headline
        headline = " ".join(sys.argv[1:])
        result = pipeline.generate_article_from_headline(headline)
        
        if result['status'] == 'success':
            print("🎉 Pipeline completed successfully!")
            sys.exit(0)
        else:
            print(f"❌ Pipeline failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    else:
        # Interactive mode
        pipeline.interactive_mode()

if __name__ == "__main__":
    main()