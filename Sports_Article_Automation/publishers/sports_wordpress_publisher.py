"""
Sports Article WordPress Publisher
Publishes SEO-optimized sports articles to WordPress

Two-Stage Article Generation Process:
1. Perplexity AI: Research collection from internet sources
2. Gemini AI: SEO-optimized article generation from research

WordPress Publishing:
- Follows same pattern as stock analysis auto_publisher.py
- Supports scheduling, featured images, categories
- Tracks publishing state and prevents duplicates
"""

import json
import logging
import os
import sys
import re
import time
import random
import base64
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure console can handle UTF-8 output
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Setup logging (prevent duplicate handlers completely)
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

root_logger = logging.getLogger()
if not root_logger.handlers:
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(LOG_DIR / 'sports_wordpress_publisher.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)


class SportsWordPressPublisher:
    """
    WordPress publisher for sports articles
    Integrates two-stage article generation with WordPress publishing
    """
    
    def __init__(self, 
                 wp_site_url: str,
                 wp_username: str,
                 wp_app_password: str,
                 wp_user_id: int,
                 wp_category_id: Optional[int] = None):
        """
        Initialize WordPress publisher for sports articles
        
        Args:
            wp_site_url (str): WordPress site URL (e.g., https://yoursite.com)
            wp_username (str): WordPress username
            wp_app_password (str): WordPress application password
            wp_user_id (int): WordPress user ID
            wp_category_id (int): WordPress category ID for sports articles
        """
        self.wp_site_url = wp_site_url.rstrip('/')
        self.wp_username = wp_username
        self.wp_app_password = wp_app_password
        self.wp_user_id = wp_user_id
        self.wp_category_id = wp_category_id
        
        # Publishing state tracking
        self.published_articles = set()
        self.publishing_stats = {
            'total_processed': 0,
            'articles_published': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def publish_article_to_wordpress(self,
                                    article_data: Dict,
                                    schedule_time: Optional[datetime] = None,
                                    status: str = "future") -> Optional[int]:
        """
        Publish generated article to WordPress
        
        Args:
            article_data (Dict): Generated article data from Gemini
            schedule_time (datetime): When to publish (None = now)
            status (str): WordPress post status (future, publish, draft)
            
        Returns:
            int: WordPress post ID or None if failed
        """
        try:
            # Extract article data
            headline = article_data.get('headline', '')
            article_content = article_data.get('article_content', '')
            category = article_data.get('category', 'General')
            seo_metadata = article_data.get('seo_metadata', {})
            
            if not headline or not article_content:
                logging.error("❌ Missing headline or content for WordPress publishing")
                self.publishing_stats['failed'] += 1
                return None
            
            logging.info(f"\n{'='*70}")
            logging.info(f"📤 PUBLISHING TO WORDPRESS")
            logging.info(f"{'='*70}")
            logging.info(f"📰 Original Headline: {headline}")
            logging.info(f"🏷️  Category: {category}")
            logging.info(f"📊 Content Length: {len(article_content)} characters")
            
            # Convert markdown to HTML for WordPress
            html_content = self._markdown_to_html(article_content)
            
            # Extract rewritten title from SEO metadata (from AI-generated headline)
            wp_title = seo_metadata.get('title', headline) if seo_metadata else headline
            
            # Log which title is being used
            if wp_title != headline:
                logging.info(f"✏️  Using Rewritten Title: {wp_title}")
            else:
                logging.warning(f"⚠️  No rewritten headline found, using original: {wp_title}")
            
            # Remove h1 from content (it becomes the WordPress title)
            html_content = re.sub(r'<h1[^>]*>.*?</h1>', '', html_content, count=1, flags=re.DOTALL | re.IGNORECASE)
            
            # Also remove any remaining markdown H1 (in case conversion didn't catch it)
            html_content = re.sub(r'^# .*$', '', html_content, count=1, flags=re.MULTILINE)
            
            # Create slug for SEO-friendly URL (use pre-generated if available)
            if seo_metadata and 'slug' in seo_metadata and seo_metadata['slug']:
                slug = seo_metadata['slug']
                logging.info(f"🔗 Using pre-generated SEO slug: {slug} ({len(slug)}/75 chars)")
            else:
                slug = self._create_seo_slug(wp_title, category)
                logging.info(f"🔗 Generated new SEO slug: {slug} ({len(slug)}/75 chars)")
            
            # Set schedule time
            if not schedule_time:
                schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(5, 15))
            
            # Ensure schedule time is in the future
            if schedule_time < datetime.now(timezone.utc):
                schedule_time = datetime.now(timezone.utc) + timedelta(minutes=5)
            
            # Generate featured image
            feature_image_id = self._generate_and_upload_featured_image(wp_title, category)
            
            # Create WordPress post
            post_id = self._create_wordpress_post(
                title=wp_title,
                content=html_content,
                slug=slug,
                schedule_time=schedule_time,
                status=status,
                category_id=self.wp_category_id,
                featured_media_id=feature_image_id
            )
            
            if post_id:
                logging.info(f"✅ Article published to WordPress!")
                logging.info(f"📝 Post ID: {post_id}")
                logging.info(f"🔗 URL: {self.wp_site_url}/{slug}")
                if schedule_time:
                    logging.info(f"⏰ Scheduled for: {schedule_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                self.published_articles.add(headline)
                self.publishing_stats['articles_published'] += 1
                self.publishing_stats['total_processed'] += 1
                
                return post_id
            else:
                logging.error(f"❌ WordPress post creation failed")
                self.publishing_stats['failed'] += 1
                self.publishing_stats['total_processed'] += 1
                return None
                
        except Exception as e:
            logging.error(f"❌ Error publishing to WordPress: {e}")
            self.publishing_stats['failed'] += 1
            self.publishing_stats['total_processed'] += 1
            return None
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown to HTML for WordPress
        Handles both markdown syntax and already-formatted HTML
        ALWAYS converts markdown headings to proper HTML
        
        Args:
            markdown_text (str): Markdown/HTML content
            
        Returns:
            str: HTML content
        """
        html = markdown_text
        
        # ALWAYS convert markdown headings to HTML (regardless of existing HTML)
        # Order matters: convert H4 first, then H3, H2, H1 to avoid partial matches
        logging.info("Converting markdown headings to HTML...")
        
        # H4 (####)
        html = re.sub(r"^#### (.*)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        # H3 (###) - must not match ####
        html = re.sub(r"^### (.*)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        # H2 (##) - must not match ### or ####
        html = re.sub(r"^## (.*)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        # H1 (#) - must not match ##, ###, or ####
        html = re.sub(r"^# (.*)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        
        # Convert markdown bold and italics
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
        
        # Convert markdown links [text](url) - only if not already HTML
        html = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"<a href='\2' target='_blank' rel='noopener noreferrer'>\1</a>", html)
        
        # Check if content needs paragraph wrapping
        if '<div class="article-overview"' in html or '<p>' in html:
            # Content already has proper HTML structure, minimal processing
            logging.info("Content has semantic HTML structure, skipping paragraph wrapping")
        else:
            # Wrap non-heading, non-HTML lines in paragraphs
            lines = html.split('\n')
            processed_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('<') and not stripped.startswith('#'):
                    processed_lines.append(f"<p>{stripped}</p>")
                elif stripped:
                    processed_lines.append(line)
            html = '\n'.join(processed_lines)
        
        logging.info(f"Markdown to HTML conversion complete. Output length: {len(html)} chars")
        return html
    
    def _create_seo_slug(self, title: str, category: str) -> str:
        """
        Create SEO-friendly URL slug (max 75 characters for optimal SEO)
        
        Args:
            title (str): Article title
            category (str): Article category
            
        Returns:
            str: SEO slug (max 75 characters)
        """
        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[\s]+', '-', slug).strip('-')
        
        # Build category prefix if available
        category_prefix = ""
        if category and category.lower() not in ['general', 'uncategorized']:
            category_prefix = f"{category.lower()}-"
        
        # Calculate available length for title part (75 chars max total - category prefix)
        max_title_length = 75 - len(category_prefix)
        
        # Limit title slug to available length, breaking at word boundaries
        if len(slug) > max_title_length:
            slug = slug[:max_title_length].rsplit('-', 1)[0]
        
        # Combine category prefix + title slug
        final_slug = category_prefix + slug
        
        # Final safety check - ensure it never exceeds 75 characters
        if len(final_slug) > 75:
            # If still over 75, trim from the end with word boundary respect
            # This properly accounts for the category prefix length
            final_slug = final_slug[:75].rsplit('-', 1)[0]
        
        # Ensure no trailing hyphens or empty strings
        final_slug = final_slug.strip('-')
        
        # Verify the final length and log any issues
        if len(final_slug) > 75:
            # Emergency fallback - should never reach here, but if it does, force truncate
            logging.warning(f"⚠️  SEO slug exceeded 75 chars even after trimming: {final_slug[:80]}... Forcing truncation.")
            final_slug = final_slug[:75].rsplit('-', 1)[0].strip('-')
        
        # Log slug creation for SEO monitoring
        if len(final_slug) > 60:
            logging.info(f"📝 Created SEO slug ({len(final_slug)}/75 chars): {final_slug}")
        
        return final_slug
    
    def _create_wordpress_post(self,
                              title: str,
                              content: str,
                              slug: str,
                              schedule_time: datetime,
                              status: str = "future",
                              category_id: Optional[int] = None,
                              featured_media_id: Optional[int] = None) -> Optional[int]:
        """
        Create WordPress post via REST API
        
        Args:
            title (str): Post title
            content (str): Post content (HTML)
            slug (str): Post slug
            schedule_time (datetime): Scheduled publish time
            status (str): Post status (future, publish, draft)
            category_id (int): Category ID
            featured_media_id (int): Featured image media ID
            
        Returns:
            int: Post ID or None if failed
        """
        try:
            url = f"{self.wp_site_url}/wp-json/wp/v2/posts"
            
            # Create authorization header
            credentials = base64.b64encode(
                f"{self.wp_username}:{self.wp_app_password}".encode()
            ).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json"
            }
            
            # Build post payload (let WordPress use authenticated user as author by default)
            payload = {
                "title": title,
                "content": content,
                "status": status,
                "slug": slug
            }
            
            logging.info(f"📤 Sending Post Payload: Title='{title[:30]}...', Slug='{slug}'")

            # Don't specify author - let WordPress use the authenticated user
            # This avoids "rest_cannot_edit_others" permission errors
            logging.info(f"📝 Creating post as authenticated user: {self.wp_username}")
            
            # Add scheduled time for future posts
            if status == "future":
                payload["date_gmt"] = schedule_time.isoformat()
            
            # Add category if provided
            if category_id:
                payload["categories"] = [category_id]
            
            # Add featured image if provided
            if featured_media_id:
                payload["featured_media"] = featured_media_id
            
            # Make API request
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            
            post_data = response.json()
            post_id = post_data.get('id')
            returned_slug = post_data.get('slug')
            
            if returned_slug != slug:
                logging.warning(f"⚠️  Slug Mismatch! Requested: '{slug}', Got: '{returned_slug}'")
                logging.warning(f"ℹ️  This usually happens if the slug already exists or contains invalid characters.")
            else:
                logging.info(f"✅ Slug verified: '{returned_slug}'")
            
            return post_id
            
        except requests.exceptions.RequestException as e:
            logging.error(f"WordPress API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                    logging.error(f"Response: {error_response}")
                    # Check for specific authentication/authorization errors
                    if error_response.get('code') in ['rest_cannot_edit_others', 'rest_cannot_create']:
                        logging.error("❌ User permissions issue - try removing explicit author assignment")
                        logging.error(f"❌ Current user ID: {self.wp_user_id}, Username: {self.wp_username}")
                except:
                    logging.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"Error creating WordPress post: {e}")
            return None
    
    def _generate_and_upload_featured_image(self, title: str, category: str) -> Optional[int]:
        """
        Generate featured image and upload to WordPress
        
        Args:
            title (str): Article title
            category (str): Article category
            
        Returns:
            int: WordPress media ID or None
        """
        try:
            # Create temporary directory for images
            temp_dir = Path(__file__).parent / "temp_images"
            temp_dir.mkdir(exist_ok=True)
            
            # Generate unique filename
            timestamp = int(time.time())
            safe_title = re.sub(r'[^\w]', '_', title)[:30]
            image_filename = f"{category}_{safe_title}_{timestamp}.png"
            image_path = temp_dir / image_filename
            
            # Generate image
            self._create_featured_image(title, category, str(image_path))
            
            # Upload to WordPress
            media_id = self._upload_image_to_wordpress(str(image_path), title)
            
            # Clean up temporary file
            try:
                os.remove(image_path)
            except Exception as e:
                logging.warning(f"Failed to remove temp image: {e}")
            
            return media_id
            
        except Exception as e:
            logging.warning(f"Featured image generation failed: {e}")
            return None
    
    def _create_featured_image(self, title: str, category: str, output_path: str):
        """
        Create a featured image for the article
        
        Args:
            title (str): Article title
            category (str): Article category
            output_path (str): Where to save the image
        """
        try:
            # Image dimensions
            width, height = 1200, 630
            
            # Category colors
            category_colors = {
                'cricket': ('#1e40af', '#dbeafe'),
                'football': ('#15803d', '#dcfce7'),
                'basketball': ('#dc2626', '#fee2e2'),
                'uncategorized': ('#6b7280', '#f3f4f6')
            }
            
            bg_color, text_color = category_colors.get(
                category.lower(),
                category_colors['uncategorized']
            )
            
            # Create image
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Try to load font, fallback to default
            try:
                title_font = ImageFont.truetype("arial.ttf", 60)
                category_font = ImageFont.truetype("arial.ttf", 36)
            except:
                title_font = ImageFont.load_default()
                category_font = ImageFont.load_default()
            
            # Draw category badge
            category_text = category.upper()
            draw.text((60, 60), category_text, fill=text_color, font=category_font)
            
            # Draw title (wrapped)
            title_wrapped = self._wrap_text(title, width - 120, draw, title_font)
            draw.text((60, 150), title_wrapped, fill='#ffffff', font=title_font)
            
            # Save image
            img.save(output_path, 'PNG', quality=95)
            
        except Exception as e:
            logging.error(f"Error creating featured image: {e}")
            raise
    
    def _wrap_text(self, text: str, max_width: int, draw, font) -> str:
        """Wrap text to fit within max width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines[:3])  # Limit to 3 lines
    
    def _upload_image_to_wordpress(self, image_path: str, title: str) -> Optional[int]:
        """
        Upload image to WordPress media library
        
        Args:
            image_path (str): Path to image file
            title (str): Image title
            
        Returns:
            int: WordPress media ID or None
        """
        try:
            url = f"{self.wp_site_url}/wp-json/wp/v2/media"
            
            credentials = base64.b64encode(
                f"{self.wp_username}:{self.wp_app_password}".encode()
            ).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Disposition": f'attachment; filename="{Path(image_path).name}"'
            }
            
            with open(image_path, 'rb') as img_file:
                files = {'file': img_file}
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    timeout=60
                )
            
            response.raise_for_status()
            media_data = response.json()
            media_id = media_data.get('id')
            
            logging.info(f"✅ Featured image uploaded - Media ID: {media_id}")
            return media_id
            
        except Exception as e:
            logging.error(f"Image upload error: {e}")
            return None
    
    def print_publishing_stats(self):
        """Print publishing statistics"""
        logging.info(f"\n{'='*70}")
        logging.info(f"📊 PUBLISHING STATISTICS")
        logging.info(f"{'='*70}")
        logging.info(f"Total Processed: {self.publishing_stats['total_processed']}")
        logging.info(f"Successfully Published: {self.publishing_stats['articles_published']}")
        logging.info(f"Failed: {self.publishing_stats['failed']}")
        logging.info(f"Skipped: {self.publishing_stats['skipped']}")


def run_complete_sports_publishing_workflow(
    category: Optional[str] = None,
    num_articles: int = 1,
    wp_site_url: Optional[str] = None,
    wp_username: Optional[str] = None,
    wp_app_password: Optional[str] = None,
    wp_user_id: Optional[int] = None,
    wp_category_id: Optional[int] = None,
    publish_status: str = "future",
    min_interval_minutes: int = 45,
    max_interval_minutes: int = 90
) -> Dict:
    """
    Run complete sports article publishing workflow
    
    Steps:
    1. Load articles from database
    2. Select headlines by importance
    3. Collect research using Perplexity AI
    4. Generate articles using Gemini AI
    5. Publish to WordPress
    
    Args:
        category (str): Sports category (cricket, football, basketball)
        num_articles (int): Number of articles to publish
        wp_site_url (str): WordPress site URL
        wp_username (str): WordPress username
        wp_app_password (str): WordPress app password
        wp_user_id (int): WordPress user ID
        wp_category_id (int): WordPress category ID
        publish_status (str): Post status (publish, draft, future)
        min_interval_minutes (int): Minimum time between scheduled posts
        max_interval_minutes (int): Maximum time between scheduled posts
        
    Returns:
        Dict: Publishing results
    """
    try:
        logging.info("\n" + "="*70)
        logging.info("🚀 SPORTS ARTICLE PUBLISHING WORKFLOW")
        logging.info("="*70)
        
        # Import required modules
        from Sports_Article_Automation.core.article_generation_pipeline import ArticleGenerationPipeline
        from Sports_Article_Automation.utilities.perplexity_ai_client import PerplexityResearchCollector
        from Sports_Article_Automation.utilities.sports_article_generator import SportsArticleGenerator
        
        # Initialize AI clients
        logging.info("🔧 Initializing AI clients...")
        perplexity_client = PerplexityResearchCollector()
        gemini_client = SportsArticleGenerator()
        
        # Initialize article generation pipeline
        pipeline = ArticleGenerationPipeline(
            perplexity_client=perplexity_client,
            gemini_client=gemini_client
        )
        
        # Load WordPress credentials from environment if not provided
        wp_site_url = wp_site_url or os.getenv('WP_SITE_URL')
        wp_username = wp_username or os.getenv('WP_USERNAME')
        wp_app_password = wp_app_password or os.getenv('WP_APP_PASSWORD')
        wp_user_id = wp_user_id or int(os.getenv('WP_USER_ID', 0))
        wp_category_id = wp_category_id or int(os.getenv('WP_SPORTS_CATEGORY_ID', 0))
        
        if not all([wp_site_url, wp_username, wp_app_password, wp_user_id]):
            raise ValueError("WordPress credentials not configured")
        
        # Initialize WordPress publisher
        logging.info("🔧 Initializing WordPress publisher...")
        wp_publisher = SportsWordPressPublisher(
            wp_site_url=wp_site_url,
            wp_username=wp_username,
            wp_app_password=wp_app_password,
            wp_user_id=wp_user_id,
            wp_category_id=wp_category_id
        )
        
        # Load articles
        logging.info(f"📂 Loading {category or 'mixed'} articles...")
        articles = pipeline.load_articles_from_database(
            category=category,
            limit=num_articles * 2  # Get extra in case some fail
        )
        
        if not articles:
            logging.error("❌ No articles found to process")
            return {'status': 'error', 'message': 'No articles found'}
        
        # Process and publish articles with enhanced scheduling
        published_posts = []
        schedule_time = None
        
        # Initialize first schedule time for future posts
        if publish_status == "future":
            schedule_time = datetime.now(timezone.utc) + timedelta(minutes=random.randint(2, 5))
        
        for i in range(min(num_articles, len(articles))):
            article_entry = articles[i]
            
            logging.info(f"\n{'='*70}")
            logging.info(f"Processing Article {i+1}/{num_articles}")
            logging.info(f"Status: {publish_status}, Category: {wp_category_id}")
            logging.info(f"{'='*70}")
            
            # Step 1 & 2: Research collection + Article generation
            generated_article = pipeline.generate_article_for_headline(article_entry)
            
            if generated_article.get('status') not in ['success', 'placeholder']:
                logging.warning(f"⚠️  Article generation failed, skipping...")
                wp_publisher.publishing_stats['skipped'] += 1
                continue
            
            # Step 3: Publish to WordPress with enhanced parameters
            post_id = wp_publisher.publish_article_to_wordpress(
                article_data=generated_article,
                schedule_time=schedule_time if publish_status == "future" else None,
                status=publish_status
            )
            
            if post_id:
                post_result = {
                    'post_id': post_id,
                    'title': generated_article.get('headline'),
                    'category': generated_article.get('category'),
                    'status': publish_status
                }
                
                if schedule_time and publish_status == "future":
                    post_result['scheduled_time'] = schedule_time.isoformat()
                    
                published_posts.append(post_result)
                
                # Calculate next schedule time for future posts
                if publish_status == "future" and i < num_articles - 1:  # Not the last article
                    random_interval = random.randint(min_interval_minutes, max_interval_minutes)
                    schedule_time += timedelta(minutes=random_interval)
                    logging.info(f"Next article scheduled in {random_interval} minutes: {schedule_time}")
            
            # Add small delay between processing articles to avoid rate limits
            if i < num_articles - 1:  # Not the last article
                time.sleep(2)
        
        # Print summary
        wp_publisher.print_publishing_stats()
        
        return {
            'status': 'success',
            'published_posts': published_posts,
            'stats': wp_publisher.publishing_stats
        }
        
    except Exception as e:
        logging.error(f"❌ Workflow error: {e}")
        return {'status': 'error', 'message': str(e)}


if __name__ == "__main__":
    # Example usage
    results = run_complete_sports_publishing_workflow(
        category="football",  # or 'cricket', 'basketball', None for mixed
        num_articles=1,
        # WordPress credentials loaded from .env file
    )
    
    logging.info(f"\n{'='*70}")
    logging.info(f"FINAL RESULTS")
    logging.info(f"{'='*70}")
    logging.info(json.dumps(results, indent=2))
