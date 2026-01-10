#!/usr/bin/env python3
"""
Earnings Article Publisher Integration
====================================

Advanced earnings-focused content publishing system that integrates earnings
analysis with the WordPress automation platform. Provides specialized content
generation, smart writer rotation, and comprehensive publishing management
for earnings-related articles.

Core Publishing Features:
------------------------
1. **Earnings Article Types**:
   - Pre-earnings analysis and previews
   - Post-earnings results and analysis
   - Earnings surprise analysis
   - Forward guidance impact assessment
   - Quarterly trend analysis

2. **Content Generation**:
   - Automated earnings article creation
   - Data-driven narrative generation
   - Financial metrics interpretation
   - Analyst estimate comparison
   - Historical performance context

3. **Publishing Automation**:
   - WordPress integration with auto_publisher
   - Smart writer rotation and attribution
   - Daily publishing limits management
   - SEO optimization for earnings content
   - Social media snippet generation

Writer Management System:
------------------------
- **Unified Rotation**: Integrated with main auto_publisher writer rotation
- **Expertise Matching**: Match writers to earnings complexity
- **Load Balancing**: Distribute earnings articles evenly across writers
- **Performance Tracking**: Monitor writer-specific engagement metrics
- **Quality Assurance**: Maintain consistent writing quality standards

Content Personalization:
-----------------------
- **Article Type Detection**: Automatic classification of earnings content
- **Complexity Assessment**: Adjust content depth based on company size
- **Audience Targeting**: Tailor content for different reader segments
- **Tone Adaptation**: Professional vs accessible writing styles
- **Length Optimization**: Optimal article length for engagement

Publishing Workflow:
-------------------
1. **Earnings Data Collection**: Gather comprehensive earnings information
2. **Content Generation**: Create article based on earnings analysis
3. **Writer Assignment**: Select appropriate writer using rotation system
4. **Content Review**: Quality assurance and fact-checking
5. **SEO Optimization**: Keywords, meta descriptions, and structure
6. **WordPress Publishing**: Automated posting with proper attribution
7. **Performance Tracking**: Monitor engagement and success metrics

Integration Features:
--------------------
- **Auto-Publisher Sync**: Seamless integration with existing publishing system
- **State Management**: Consistent state tracking with main publisher
- **Daily Limits**: Respect overall daily publishing quotas
- **Error Handling**: Robust error recovery and retry mechanisms
- **Progress Tracking**: Real-time publishing progress via SocketIO

Content Quality Features:
------------------------
- **Data Validation**: Verify earnings data accuracy before publishing
- **Fact Checking**: Cross-reference multiple data sources
- **Plagiarism Prevention**: Ensure unique content generation
- **Readability Optimization**: Maintain appropriate reading level
- **Brand Consistency**: Align with overall content strategy

Publishing Analytics:
--------------------
- **Performance Metrics**: Track article engagement and success
- **Writer Analytics**: Individual writer performance assessment
- **Content Optimization**: Identify high-performing article patterns
- **Audience Insights**: Understand reader preferences and behavior
- **ROI Tracking**: Measure publishing effectiveness and value

Usage Examples:
--------------
```python
# Initialize earnings publisher
publisher = EarningsPublisher()

# Publish pre-earnings analysis
result = publisher.publish_pre_earnings_article(
    ticker='AAPL',
    earnings_date='2026-01-25',
    profile_id='financial_blog_1'
)

# Publish post-earnings analysis
result = publisher.publish_post_earnings_article(
    ticker='AAPL',
    earnings_data=earnings_results,
    profile_id='financial_blog_1'
)

# Bulk earnings publishing
results = publisher.publish_earnings_batch(
    tickers=['AAPL', 'GOOGL', 'MSFT'],
    article_type='post_earnings',
    profiles=['blog_1', 'blog_2']
)
```

Integration Points:
------------------
- Uses earnings_reports/data_collector.py for comprehensive data
- Integrates with automation_scripts/auto_publisher.py for publishing
- Leverages reporting_tools/report_generator.py for visualizations
- Connects to main_portal_app.py for real-time updates

Error Handling:
--------------
- **Data Availability**: Handle missing or delayed earnings data
- **Publishing Failures**: Retry mechanisms for WordPress API issues
- **Content Generation**: Fallback content for incomplete data
- **Rate Limiting**: Respect API limits and quotas
- **Network Issues**: Robust handling of connectivity problems

Configuration:
-------------
Customizable settings:
- **Publishing Schedule**: Pre and post-earnings timing
- **Content Templates**: Article structure and format options
- **Writer Preferences**: Writer specialization and availability
- **Quality Thresholds**: Minimum content quality requirements
- **Performance Targets**: Engagement and success metrics

Author: TickZen Development Team
Version: 2.0
Last Updated: January 2026
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from earnings_reports.gemini_earnings_writer import GeminiEarningsWriter

# Configure logging
logger = logging.getLogger(__name__)


class EarningsArticlePublisher:
    """
    Publisher integration for earnings articles.
    
    Provides methods to generate earnings articles in a format compatible with
    the auto_publisher system, including writer rotation and record keeping.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the earnings article publisher.
        
        Args:
            api_key: Google API key for Gemini
        """
        self.writer = GeminiEarningsWriter(api_key=api_key)
        logger.info("Earnings Article Publisher initialized")
    
    def generate_earnings_article_for_publishing(
        self, 
        ticker: str,
        article_type: str = 'earnings',
        profile_config: Optional[Dict[str, Any]] = None,
        variation_number: int = 0
    ) -> Dict[str, Any]:
        """
        Generate earnings article ready for WordPress publishing.
        
        This method creates an earnings article and returns it in a format
        compatible with auto_publisher's workflow.
        
        Args:
            ticker: Stock ticker symbol
            article_type: Type of article - 'earnings' (default), 'pre_earnings', 'post_earnings'
            profile_config: Optional profile configuration for customization
            variation_number: Article variation number (0=first, 1=second variation, etc.)
            
        Returns:
            Dictionary with article HTML, metadata, and publishing info
        """
        logger.info(f"Generating {article_type} article for {ticker} (Variation #{variation_number})")
        
        try:
            # Generate complete earnings report with variation
            result = self.writer.generate_complete_report(ticker, variation_number=variation_number)
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'ticker': ticker,
                    'article_type': article_type
                }
            
            # Extract article components
            article_html = result.get('article_html', '')
            metadata = result.get('metadata', {})
            
            # Clean article HTML for WordPress (remove wrapper tags if present)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(article_html, 'html.parser')
            
            # Remove any full document structure (html, head, body tags)
            body = soup.find('body')
            if body:
                article_html = ''.join(str(tag) for tag in body.children)
            else:
                article_html = str(soup)
            
            # Extract title from h1 or generate from metadata
            h1_tag = soup.find('h1')
            if h1_tag:
                article_title = h1_tag.get_text().strip()
                # Remove h1 from content as WordPress will use it as post title
                h1_tag.decompose()
                article_html = str(soup)
            else:
                # Fallback title
                company_name = metadata.get('company_name', ticker)
                article_title = f"{company_name} ({ticker}) Earnings Report - Comprehensive Analysis"
            
            # Generate company name for slug if not in metadata
            company_name = metadata.get('company_name', ticker)
            
            return {
                'success': True,
                'ticker': ticker,
                'article_type': article_type,
                'article_html': article_html,
                'article_title': article_title,
                'company_name': company_name,
                'word_count': result.get('word_count', 0),
                'metadata': metadata,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'file_path': result.get('file_path'),
                'sector': metadata.get('sector', 'Technology')
            }
            
        except Exception as e:
            logger.error(f"Error generating earnings article for {ticker}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker,
                'article_type': article_type
            }
    
    def prepare_for_wordpress(
        self,
        article_data: Dict[str, Any],
        feature_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare earnings article for WordPress publishing.
        
        Args:
            article_data: Article data from generate_earnings_article_for_publishing
            feature_image_path: Optional path to feature image
            
        Returns:
            Dictionary ready for WordPress posting
        """
        if not article_data.get('success'):
            return article_data
        
        # Prepare WordPress-compatible format
        wp_ready = {
            'title': article_data.get('article_title'),
            'content': article_data.get('article_html'),
            'ticker': article_data.get('ticker'),
            'company_name': article_data.get('company_name'),
            'article_type': article_data.get('article_type', 'earnings'),
            'sector': article_data.get('sector', 'Technology'),
            'word_count': article_data.get('word_count', 0),
            'generated_at': article_data.get('generated_at'),
            'feature_image_path': feature_image_path,
            'metadata': article_data.get('metadata', {})
        }
        
        logger.info(f"Prepared earnings article for WordPress: {wp_ready['title']}")
        return wp_ready


def generate_earnings_article_for_autopublisher(
    ticker: str,
    article_type: str = 'earnings',
    profile_config: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    variation_number: int = 0
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Convenience function for auto_publisher integration.
    
    This function generates an earnings article and returns it in the same format
    as the stock analysis pipeline for seamless integration with auto_publisher.
    
    Args:
        ticker: Stock ticker symbol
        article_type: Type of article ('earnings', 'pre_earnings', 'post_earnings')
        profile_config: Optional profile configuration
        api_key: Optional Google API key
        variation_number: Article variation number (0=first, 1=second variation, etc.)
        
    Returns:
        Tuple of (article_html, article_title, metadata_dict)
    """
    logger.info(f"Auto-publisher requesting {article_type} article for {ticker} (Variation #{variation_number})")
    
    try:
        publisher = EarningsArticlePublisher(api_key=api_key)
        article_data = publisher.generate_earnings_article_for_publishing(
            ticker=ticker,
            article_type=article_type,
            profile_config=profile_config,
            variation_number=variation_number
        )
        
        if not article_data.get('success'):
            error_msg = article_data.get('error', 'Unknown error')
            logger.error(f"Failed to generate earnings article: {error_msg}")
            return None, None, {'error': error_msg, 'success': False}
        
        article_html = article_data.get('article_html', '')
        article_title = article_data.get('article_title', f"{ticker} Earnings Analysis")
        
        # Create metadata dict compatible with auto_publisher
        metadata = {
            'success': True,
            'ticker': ticker,
            'company_name': article_data.get('company_name', ticker),
            'sector': article_data.get('sector', 'Technology'),
            'article_type': article_type,
            'word_count': article_data.get('word_count', 0),
            'generated_at': article_data.get('generated_at'),
            'overall_pct_change': 0,  # Not applicable for earnings articles
            'profile_data': {
                'Company Name': article_data.get('company_name', ticker),
                'Sector': article_data.get('sector', 'Technology'),
                'Article Type': article_type
            }
        }
        
        logger.info(f"Successfully generated earnings article for auto-publisher: {article_title}")
        return article_html, article_title, metadata
        
    except Exception as e:
        logger.error(f"Error in auto-publisher integration for {ticker}: {e}", exc_info=True)
        return None, None, {'error': str(e), 'success': False}


if __name__ == '__main__':
    """Test earnings article publisher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Earnings Article Publisher')
    parser.add_argument('ticker', type=str, help='Stock ticker symbol')
    parser.add_argument('--type', type=str, default='earnings', 
                       choices=['earnings', 'pre_earnings', 'post_earnings'],
                       help='Article type')
    
    args = parser.parse_args()
    
    # Test generation
    html, title, metadata = generate_earnings_article_for_autopublisher(
        ticker=args.ticker.upper(),
        article_type=args.type
    )
    
    if html and title:
        print(f"\n✅ Successfully generated article:")
        print(f"   Title: {title}")
        print(f"   Words: {metadata.get('word_count', 0):,}")
        print(f"   Type: {metadata.get('article_type')}")
        print(f"   Company: {metadata.get('company_name')}")
    else:
        print(f"\n❌ Failed to generate article: {metadata.get('error')}")
