"""
Job Automation Processor Module
================================

Background job processor for handling automation runs.
Processes items, generates content, publishes articles, and manages state.
"""

import logging
import threading
import time
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from Job_Portal_Automation.job_automation_helpers import JobAutomationManager
from Job_Portal_Automation.state_management.job_publishing_state_manager import JobPublishingStateManager, RunStatus
from Job_Portal_Automation.job_article_pipeline import JobArticlePipeline, GeminiArticleGenerator
from Job_Portal_Automation.publishers.wp_job_publisher import publish_job_article, WPJobPublishingError
from Job_Portal_Automation.utilities.feature_image_generator import FeatureImageGenerator
from Job_Portal_Automation.utilities.internal_linking import JobPortalInternalLinker

logger = logging.getLogger(__name__)


class ProcessorState(str, Enum):
    """States for the background processor"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class JobAutomationProcessor:
    """
    Background processor for automation runs.
    
    Responsibilities:
    - Execute automation runs
    - Process items sequentially
    - Generate content
    - Publish to WordPress
    - Track progress
    - Handle errors gracefully
    """
    
    def __init__(self, automation_manager: JobAutomationManager,
                 state_manager: JobPublishingStateManager):
        """
        Initialize processor
        
        Args:
            automation_manager: JobAutomationManager instance
            state_manager: JobPublishingStateManager instance
        """
        self.automation_manager = automation_manager
        self.state_manager = state_manager
        
        self.state = ProcessorState.IDLE
        self.current_run_id: Optional[str] = None
        self.thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Callback functions
        self.on_progress: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None

        # Content generation pipeline
        self.pipeline = JobArticlePipeline(
            perplexity_client=self.automation_manager.research_client,
            gemini_client=GeminiArticleGenerator()
        )
        
        # Feature image generator
        self.feature_image_generator = FeatureImageGenerator()
        
        # Internal linking system
        self.internal_linker = JobPortalInternalLinker()
    
    # ===================== LIFECYCLE METHODS =====================
    
    def start_run(self, run_id: str, blocking: bool = False) -> bool:
        """
        Start processing a run
        
        Args:
            run_id: Run ID to process
            blocking: If True, wait for completion before returning
            
        Returns:
            True if processing started successfully
        """
        try:
            # Validate run exists
            run = self.state_manager.get_run(run_id)
            if not run:
                self.logger.error(f"Run {run_id} not found")
                return False
            
            # Check if already processing
            if self.state in [ProcessorState.RUNNING, ProcessorState.PAUSED]:
                self.logger.warning(f"Processor already {self.state.value}")
                return False
            
            # Set current run
            self.current_run_id = run_id
            self.state = ProcessorState.RUNNING
            
            self.logger.info(f"Starting processor for run {run_id}")
            
            # Update run status
            self.state_manager.update_run_status(run_id, RunStatus.RUNNING)
            
            # Create and start thread
            self.thread = threading.Thread(
                target=self._process_run,
                args=(run_id,),
                daemon=False
            )
            self.thread.start()
            
            # Block if requested
            if blocking:
                self.thread.join()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start run: {e}")
            self.state = ProcessorState.IDLE
            return False
    
    def pause_run(self) -> bool:
        """
        Pause the current run
        
        Returns:
            True if paused successfully
        """
        if self.state != ProcessorState.RUNNING:
            self.logger.warning(f"Cannot pause: processor is {self.state.value}")
            return False
        
        self.state = ProcessorState.PAUSED
        
        if self.current_run_id:
            self.state_manager.update_run_status(
                self.current_run_id,
                RunStatus.PAUSED
            )
            self.logger.info(f"Paused run {self.current_run_id}")
        
        return True
    
    def resume_run(self) -> bool:
        """
        Resume the paused run
        
        Returns:
            True if resumed successfully
        """
        if self.state != ProcessorState.PAUSED:
            self.logger.warning(f"Cannot resume: processor is {self.state.value}")
            return False
        
        self.state = ProcessorState.RUNNING
        
        if self.current_run_id:
            self.state_manager.update_run_status(
                self.current_run_id,
                RunStatus.RUNNING
            )
            self.logger.info(f"Resumed run {self.current_run_id}")
        
        return True
    
    def stop_run(self) -> bool:
        """
        Stop the current run
        
        Returns:
            True if stopped successfully
        """
        if self.state == ProcessorState.IDLE:
            self.logger.warning("No run to stop")
            return False
        
        self.state = ProcessorState.STOPPED
        
        if self.current_run_id:
            self.state_manager.update_run_status(
                self.current_run_id,
                RunStatus.CANCELLED
            )
            self.logger.info(f"Stopped run {self.current_run_id}")
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.state = ProcessorState.IDLE
        self.current_run_id = None
        
        return True
    
    # ===================== PROCESSING LOGIC =====================
    
    def _process_run(self, run_id: str):
        """
        Internal method to process a run (runs in background thread)
        
        Args:
            run_id: Run ID to process
        """
        try:
            self.logger.info(f"Processing run {run_id}")
            
            # Get run details
            run = self.state_manager.get_run(run_id)
            if not run:
                self._handle_error(run_id, "Run not found")
                return
            
            # Extract configuration
            content_type = run.get('content_type')
            selected_items = run.get('selected_items', [])
            target_profiles = run.get('target_profiles', [])
            config = run.get('config', {})
            
            # Process each item
            total_items = len(selected_items)
            published_count = 0
            error_count = 0
            
            for idx, item in enumerate(selected_items):
                # Check for pause/stop signals
                if self.state == ProcessorState.PAUSED:
                    self._emit_progress(
                        run_id=run_id,
                        status="paused",
                        processed=idx,
                        total=total_items,
                        message=f"Paused at item {idx + 1}/{total_items}"
                    )
                    # Wait while paused
                    while self.state == ProcessorState.PAUSED:
                        time.sleep(0.5)
                
                if self.state == ProcessorState.STOPPED:
                    break
                
                # Update progress
                self._emit_progress(
                    run_id=run_id,
                    status="processing",
                    processed=idx,
                    total=total_items,
                    message=f"Processing item {idx + 1}/{total_items}: {item.get('title', 'Unknown')}"
                )
                
                # Process item
                success = self._process_item(
                    run_id=run_id,
                    item=item,
                    content_type=content_type,
                    target_profiles=target_profiles,
                    config=config,
                    item_index=idx + 1
                )
                
                if success:
                    published_count += 1
                else:
                    error_count += 1
                
                # Brief delay to avoid overwhelming resources
                time.sleep(0.5)
            
            # Determine final status
            if self.state == ProcessorState.STOPPED:
                final_status = RunStatus.CANCELLED
                message = f"Cancelled: processed {published_count} of {total_items} items"
            elif error_count == total_items:
                final_status = RunStatus.FAILED
                message = f"Failed: all {total_items} items encountered errors"
            else:
                final_status = RunStatus.COMPLETED
                message = f"Completed: {published_count} published, {error_count} failed"
            
            # Update run status
            self.state_manager.update_run_status(run_id, final_status)
            
            # Final progress emission
            self._emit_progress(
                run_id=run_id,
                status="completed" if final_status == RunStatus.COMPLETED else "failed",
                processed=total_items,
                total=total_items,
                message=message
            )
            
            # Call completion callback
            if self.on_complete:
                self.on_complete(run_id, final_status.value, message)
            
            self.logger.info(f"Run {run_id} processing complete: {message}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error processing run {run_id}: {e}")
            self._handle_error(run_id, str(e))
        
        finally:
            self.state = ProcessorState.IDLE
            self.current_run_id = None
    
    def _process_item(self, run_id: str, item: Dict[str, Any],
                     content_type: str, target_profiles: List[str],
                     config: Dict[str, Any], item_index: int) -> bool:
        """
        Process a single item
        
        Args:
            run_id: Run ID
            item: Item to process
            content_type: Type of content
            target_profiles: Target WordPress profiles
            config: Automation config
            item_index: Item index (1-based)
            
        Returns:
            True if item processed successfully
        """
        try:
            item_id = item.get('id')
            item_title = item.get('title', 'Unknown')
            item_url = item.get('url')
            
            self.logger.info(f"Processing item {item_index}: {item_id} - {item_title}")
            
            # Step 1: Fetch full details
            details_result = self.automation_manager.fetch_item_details(
                item_url,
                content_type=content_type.rstrip('s')  # Remove 's' from 'jobs', 'results', etc.
            )
            
            if not details_result.get('success'):
                error_msg = f"Failed to fetch details: {details_result.get('error')}"
                self.state_manager.add_run_error(
                    run_id,
                    item_id=item_id,
                    item_title=item_title,
                    error_message=error_msg,
                    step='detail_fetching'
                )
                self._emit_error(run_id, f"Item {item_index}: {error_msg}")
                return False
            
            # Step 2: Generate content (Article Pipeline: API Details + Perplexity Research + Gemini Generation)
            article_data = self._generate_article(
                item=item,
                details=details_result.get('details', {}),
                content_type=content_type,
                config=config
            )
            
            if not article_data or not article_data.get('content'):
                error_msg = "Failed to generate article"
                self.state_manager.add_run_error(
                    run_id,
                    item_id=item_id,
                    item_title=item_title,
                    error_message=error_msg,
                    step='article_generation'
                )
                self._emit_error(run_id, f"Item {item_index}: {error_msg}")
                return False
            
            # Step 3: Add internal links (optional - integrate with existing internal linking system)
            article_content = article_data.get('content', '')
            try:
                article_content = self._add_internal_links(
                    content=article_content,
                    title=article_data.get('title', item_title),
                    target_profiles=target_profiles,
                    config=config
                )
                self.logger.info(f"Internal links added to article")
            except Exception as e:
                self.logger.warning(f"Failed to add internal links: {e}. Continuing with original content.")
                # Continue with original content if internal linking fails
            
            # Step 4: Publish to target profiles (with feature image generation per profile)
            article_slug = article_data.get('slug')
            self.logger.info(f"📝 Publishing with slug: '{article_slug}' (type: {type(article_slug).__name__})")
            published_urls = self._publish_to_profiles(
                item_id=item_id,
                title=article_data.get('title', item_title),
                slug=article_slug,  # Pass SEO-optimized slug
                content=article_content,
                content_type=content_type,  # Pass content type for feature image generation
                target_profiles=target_profiles,
                config=config
            )
            
            if not published_urls:
                error_msg = "Failed to publish to any profile"
                self.state_manager.add_run_error(
                    run_id,
                    item_id=item_id,
                    item_title=item_title,
                    error_message=error_msg,
                    step='publishing'
                )
                self._emit_error(run_id, f"Item {item_index}: {error_msg}")
                return False
            
            # Step 5: Record success
            # Record each published URL with profile mapping
            for idx, url in enumerate(published_urls):
                profile_name = target_profiles[idx] if idx < len(target_profiles) else (target_profiles[0] if target_profiles else 'unknown')
                self.state_manager.add_run_result(
                    run_id,
                    item_id=item_id,
                    item_title=item_title,
                    published_url=url,
                    profile_name=profile_name
                )
            
            self.logger.info(f"Item {item_index} processed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing item {item_index}: {e}")
            self.state_manager.add_run_error(
                run_id,
                item_id=item.get('id'),
                item_title=item.get('title'),
                error_message=str(e),
                step='unknown'
            )
            self._emit_error(run_id, f"Item {item_index}: {str(e)}")
            return False
    
    def _generate_article(self, item: Dict[str, Any], details: Dict[str, Any],
                         content_type: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate article content via the Phase 3 pipeline.
        
        Process:
        1. Fetch details from API
        2. Collect research from Perplexity
        3. Generate comprehensive article with Gemini
        4. Returns article with title, content, keywords, metadata
        """
        try:
            return self.pipeline.generate_article(
                item=item,
                details=details,
                content_type=content_type,
                config=config
            )
        except Exception as e:
            self.logger.error(f"Error generating article: {e}")
            return None
    
    def _generate_feature_image(self, title: str, content_type: str, website_name: str = "Stockdunia") -> Optional[str]:
        """
        Generate feature image for the article.
        
        Args:
            title: Article title
            content_type: Content type (jobs, results, admit_cards)
            website_name: Website name for watermark
            
        Returns:
            Path to generated feature image, or None if generation failed
        """
        try:
            self.logger.info(f"🎨 Generating feature image for: {title[:60]}...")
            
            # Normalize content_type (remove trailing 's' if present)
            normalized_type = content_type.rstrip('s')
            
            # Generate the feature image
            image_path = self.feature_image_generator.generate(
                title=title,
                content_type=normalized_type,
                site_name=website_name,
                site_url='',
                template='professional'
            )
            
            return str(image_path) if image_path else None
            
        except Exception as e:
            self.logger.error(f"Feature image generation failed: {e}")
            return None
    
    def _extract_website_name(self, profile_data: Dict[str, Any]) -> str:
        """
        Extract website name from profile data for watermarking.
        
        Args:
            profile_data: Profile configuration dictionary
            
        Returns:
            Website name string
        """
        import re
        
        # Try profile_name first (most explicit)
        profile_name = profile_data.get('profile_name', '')
        if profile_name:
            return profile_name
        
        # Try to extract from site_url
        site_url = profile_data.get('site_url', '')
        if site_url:
            # Extract domain name from URL (e.g., "https://stockdunia.com" -> "Stockdunia")
            domain_match = re.search(r'https?://(?:www\.)?([^./]+)', site_url)
            if domain_match:
                domain = domain_match.group(1)
                # Capitalize first letter
                return domain.capitalize()
        
        # Fallback to profile_id
        profile_id = profile_data.get('profile_id', 'Job Portal')
        return profile_id.replace('_', ' ').title()
    
    def _add_internal_links(self, content: str, title: str, target_profiles: List[str], 
                          config: Dict[str, Any]) -> str:
        """Add internal links section at end of article from existing website articles.
        
        Fetches 4-5 random articles from each WordPress site and adds a 
        'More from [Site]' section at the end of the article.
        
        Args:
            content: Article HTML content
            title: Article title
            target_profiles: List of profile IDs (strings)
            config: Automation configuration
            
        Returns:
            Content with internal links section added (or original if linking fails)
        """
        try:
            self.logger.info(f"🔗 Adding internal links section for: {title[:60]}...")
            
            # Add internal links for the first profile (they all go to same content)
            # If multiple profiles, each will get its own links during per-profile publishing
            if not target_profiles:
                self.logger.warning("No target profiles for internal linking")
                return content
            
            # Get first profile ID and fetch its configuration
            first_profile_id = target_profiles[0]
            profiles = config.get('profiles', [])
            
            # Find the profile configuration
            profile = None
            for p in profiles:
                if p.get('profile_id') == first_profile_id:
                    profile = p
                    break
            
            if not profile:
                self.logger.warning(f"Profile configuration not found for ID: {first_profile_id}")
                return content
            
            # Use profile to get site details
            site_url = profile.get('site_url')
            
            if not site_url:
                self.logger.warning("No site_url in profile for internal linking")
                return content
            
            # Extract website name from profile
            site_name = self._extract_website_name(profile)
            
            # Get credentials for API access
            authors = profile.get('authors', [])
            username = None
            app_password = None
            
            if authors and len(authors) > 0:
                author = authors[0]
                username = author.get('wp_username')
                app_password = author.get('app_password')
            
            # Add internal links section
            enhanced_content = self.internal_linker.add_internal_links_section(
                content=content,
                site_url=site_url,
                site_name=site_name,
                username=username,
                app_password=app_password,
                num_links=5  # Add 5 random articles
            )
            
            return enhanced_content
            
        except Exception as e:
            self.logger.warning(f"Internal linking failed: {e}. Returning original content.")
            return content
    
    def _publish_to_profiles(self, item_id: str, title: str, slug: Optional[str],
                            content: str, content_type: str,
                            target_profiles: List[str],
                            config: Dict[str, Any]) -> List[str]:
        """Publish article to WordPress profiles using standalone publisher."""
        published_urls: List[str] = []
        
        # Get full profile configurations from config
        profiles = config.get('profiles', [])
        
        # If no profiles in config, fall back to basic publishing
        if not profiles:
            dry_run = getattr(self.automation_manager.config, 'WORDPRESS_DRY_RUN', True)
            default_category = getattr(self.automation_manager.config, 'WORDPRESS_DEFAULT_CATEGORY_ID', None)
            status = getattr(self.automation_manager.config, 'WORDPRESS_DEFAULT_STATUS', 'draft')
            
            # Generate feature image with generic watermark for fallback
            feature_image_path = self._generate_feature_image(
                title=title,
                content_type=content_type,
                website_name="Job Portal"
            )
            
            for profile_id in target_profiles:
                try:
                    url = publish_job_article(
                        profile_id=profile_id,
                        title=title,
                        slug=slug,
                        content=content,
                        status=status,
                        category_id=default_category,
                        feature_image_path=feature_image_path,
                        dry_run=dry_run
                    )
                    if url:
                        published_urls.append(url)
                        self.logger.info(f"Published item {item_id} to profile {profile_id}: {url}")
                except Exception as e:
                    self.logger.error(f"Publishing failed for profile {profile_id}: {e}")
            return published_urls
        
        # Use profile-specific configurations
        for profile_data in profiles:
            profile_id = profile_data.get('profile_id')
            if not profile_id:
                continue
            
            # Extract profile-specific settings
            category_id = profile_data.get('category_id')
            publish_status = profile_data.get('publish_status', 'draft')
            
            # For scheduled publishing, use 'draft' status initially
            # The scheduler will handle publishing at the scheduled time
            if publish_status == 'schedule':
                publish_status = 'draft'
                # TODO: Add to scheduler queue with min/max intervals
                self.logger.info(f"Scheduling disabled for now, publishing as draft")
            
            try:
                # Get WordPress credentials from profile (same format as sports automation)
                site_url = profile_data.get('site_url')
                authors = profile_data.get('authors', [])
                
                # Get author from authors array (use first author)
                author = None
                if authors and len(authors) > 0:
                    author = authors[0]
                
                if not author:
                    self.logger.error(f"No author found for profile {profile_id}. Available fields: {list(profile_data.keys())}")
                    self.state_manager.add_run_error(
                        self.current_run_id or "unknown",
                        item_id=item_id,
                        item_title=title,
                        error_message=f"Profile {profile_id} has no author configured",
                        step='publishing'
                    )
                    continue
                
                # Extract credentials from author
                username = author.get('wp_username')
                app_password = author.get('app_password')
                
                # Log credentials status
                self.logger.info(f"Profile {profile_id}: site_url={site_url}, author_username={'***' if username else None}, app_password={'***' if app_password else None}")
                
                if not all([site_url, username, app_password]):
                    self.logger.error(f"Missing credentials for profile {profile_id}: site_url={bool(site_url)}, username={bool(username)}, app_password={bool(app_password)}")
                    self.state_manager.add_run_error(
                        self.current_run_id or "unknown",
                        item_id=item_id,
                        item_title=title,
                        error_message=f"Incomplete credentials for profile {profile_id}",
                        step='publishing'
                    )
                    continue
                
                # Generate feature image with THIS profile's website name
                website_name = self._extract_website_name(profile_data)
                self.logger.info(f"🏷️  Generating feature image with watermark: '{website_name}'")
                
                feature_image_path = self._generate_feature_image(
                    title=title,
                    content_type=content_type,
                    website_name=website_name
                )
                
                if not feature_image_path:
                    self.logger.warning(f"⚠️  Feature image generation failed for profile {profile_id}")
                
                # Publish article using author credentials (same as sports automation)
                url = publish_job_article(
                    profile_id=profile_id,
                    title=title,
                    slug=slug,  # Pass SEO-optimized slug
                    content=content,
                    status=publish_status,
                    category_id=category_id,
                    feature_image_path=feature_image_path,  # Pass profile-specific feature image
                    dry_run=False,
                    site_url=site_url,
                    author=author  # Pass author dict with wp_username and app_password
                )
                
                if url:
                    published_urls.append(url)
                    profile_name = profile_data.get('profile_name', profile_id)
                    self.logger.info(f"Published item {item_id} to profile '{profile_name}': {url}")
                else:
                    raise WPJobPublishingError("No URL returned from publisher")
                    
            except Exception as e:
                self.logger.error(f"Publishing failed for profile {profile_id}: {e}")
                self.state_manager.add_run_error(
                    self.current_run_id or "unknown",
                    item_id=item_id,
                    item_title=title,
                    error_message=str(e),
                    step='publishing'
                )
                
        return published_urls
    
    # ===================== PROGRESS & ERROR REPORTING =====================
    
    def _emit_progress(self, run_id: str, status: str, processed: int,
                      total: int, message: str):
        """
        Emit progress update
        
        Args:
            run_id: Run ID
            status: Current status (processing, paused, completed, failed)
            processed: Number of items processed
            total: Total items
            message: Status message
        """
        try:
            # Update state manager using existing signature (completed, failed, current_item)
            failed = max(total - processed, 0)
            self.state_manager.update_run_progress(
                run_id,
                completed=processed,
                failed=failed,
                current_item=message
            )
            
            self.logger.info(f"Progress: {processed}/{total} - {message}")
            
        except Exception as e:
            self.logger.error(f"Error emitting progress: {e}")
    
    def _emit_error(self, run_id: str, message: str):
        """
        Emit error event
        
        Args:
            run_id: Run ID
            message: Error message
        """
        try:
            if self.on_error:
                self.on_error(run_id, message)
            
            self.logger.warning(f"Error: {message}")
            
        except Exception as e:
            self.logger.error(f"Error emitting error event: {e}")
    
    def _handle_error(self, run_id: str, error: str):
        """
        Handle a critical error
        
        Args:
            run_id: Run ID
            error: Error message
        """
        try:
            self.state_manager.update_run_status(run_id, RunStatus.FAILED)
            self.state_manager.add_run_error(
                run_id,
                item_id='unknown',
                item_title='unknown',
                error_message=error,
                step='processing'
            )
            
            self._emit_error(run_id, error)
            
            if self.on_complete:
                self.on_complete(run_id, RunStatus.FAILED.value, error)
            
        except Exception as e:
            self.logger.error(f"Error handling critical error: {e}")
        
        finally:
            self.state = ProcessorState.IDLE
            self.current_run_id = None
    
    # ===================== STATUS & MONITORING =====================
    
    def get_processor_status(self) -> Dict[str, Any]:
        """
        Get current processor status
        
        Returns:
            Dictionary with processor status
        """
        run_data = {}
        
        if self.current_run_id:
            run = self.state_manager.get_run(self.current_run_id)
            if run:
                run_data = {
                    'run_id': self.current_run_id,
                    'status': run.get('status'),
                    'progress': run.get('progress')
                }
        
        return {
            'processor_state': self.state.value,
            'current_run': run_data
        }
    
    # ===================== CLEANUP =====================
    
    def shutdown(self):
        """Shutdown processor gracefully"""
        try:
            if self.state != ProcessorState.IDLE:
                self.stop_run()
            
            self.logger.info("JobAutomationProcessor shutdown")
            
        except Exception as e:
            self.logger.warning(f"Error during shutdown: {e}")
