"""
WordPress Job Publisher (Phase 4)
---------------------------------
Standalone publisher that posts generated job articles to WordPress using
Basic Auth. Designed to reuse existing profile configuration without
impacting other automation flows.

Features:
- Loads profile credentials from config/profiles_config.json
- Dry-run mode for tests/offline environments
- Minimal dependency surface (requests only)
- Graceful fallback when credentials/config missing
- Feature image upload and attachment
"""

import base64
import json
import logging
import os
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # tickzen2/
PROFILES_CONFIG_PATH = PROJECT_ROOT / "config" / "profiles_config.json"


class WPJobPublishingError(Exception):
    """Custom exception for WordPress publishing failures."""


def _load_profiles() -> Dict[str, Dict[str, Any]]:
    if not PROFILES_CONFIG_PATH.exists():
        raise WPJobPublishingError(f"profiles_config.json not found at {PROFILES_CONFIG_PATH}")
    try:
        with PROFILES_CONFIG_PATH.open("r", encoding="utf-8") as f:
            profiles = json.load(f)
    except Exception as exc:  # pragma: no cover - defensive
        raise WPJobPublishingError(f"Failed to read profiles_config.json: {exc}")

    # Index by profile_id
    return {p.get("profile_id") or p.get("id") or p.get("name"): p for p in profiles if isinstance(p, dict)}


def _basic_auth_header(username: str, app_password: str) -> str:
    token = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    return f"Basic {token}"


def _upload_feature_image(
    site_url: str,
    username: str,
    app_password: str,
    image_path: str,
    title: str,
    content_type: str = 'job'
) -> Optional[int]:
    """
    Upload feature image to WordPress media library with SEO-optimized alt text.
    
    Args:
        site_url: WordPress site URL
        username: WordPress username
        app_password: WordPress application password
        image_path: Path to the image file
        title: Article title (used to generate alt text)
        content_type: Content type (job, result, admit_card) for descriptive alt text
        
    Returns:
        Media ID if successful, None otherwise
    """
    try:
        image_file = Path(image_path)
        if not image_file.exists():
            logger.error(f"Feature image not found: {image_path}")
            return None
        
        # Generate SEO-optimized alt text using exact headline
        # Use the exact title/headline for maximum SEO value
        alt_text = title
        
        # Limit alt text to 125 characters for optimal SEO (Google recommendation)
        if len(alt_text) > 125:
            alt_text = title[:122] + "..."
        
        logger.info(f"🏷️  Alt text: {alt_text[:80]}...")
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(image_file))
        if not mime_type:
            mime_type = 'image/jpeg'  # Default
        
        # Prepare upload
        headers = {
            "Authorization": _basic_auth_header(username, app_password),
            "Content-Disposition": f'attachment; filename="{image_file.name}"',
            "Content-Type": mime_type
        }
        
        url = f"{site_url.rstrip('/')}/wp-json/wp/v2/media"
        
        with open(image_file, 'rb') as f:
            image_data = f.read()
        
        logger.info(f"📤 Uploading feature image: {image_file.name} ({len(image_data)} bytes)")
        
        response = requests.post(url, headers=headers, data=image_data, timeout=120)
        response.raise_for_status()
        
        media_data = response.json()
        media_id = media_data.get('id')
        
        if media_id:
            # Update media metadata with alt text (using exact headline)
            try:
                update_url = f"{site_url.rstrip('/')}/wp-json/wp/v2/media/{media_id}"
                
                # Generate content-specific description for metadata
                content_labels = {
                    'job': 'Job Notification',
                    'result': 'Result Declaration',
                    'admit_card': 'Admit Card Download'
                }
                content_label = content_labels.get(content_type, 'Notification')
                
                update_payload = {
                    "alt_text": alt_text,  # Exact headline for SEO
                    "caption": title,       # Full title as caption
                    "description": f"{content_label} for {title}"
                }
                update_headers = {
                    "Authorization": _basic_auth_header(username, app_password),
                    "Content-Type": "application/json"
                }
                update_response = requests.post(update_url, headers=update_headers, json=update_payload, timeout=60)
                update_response.raise_for_status()
                logger.info(f"✅ Feature image uploaded with alt text. Media ID: {media_id}")
            except Exception as e:
                logger.warning(f"Alt text update failed (image still uploaded): {e}")
            
            return media_id
        else:
            logger.error(f"Failed to get media ID from response: {media_data}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to upload feature image: {e}")
        return None


def publish_job_article(
    *,
    profile_id: str,
    title: str,
    content: str,
    slug: Optional[str] = None,
    status: str = "draft",
    category_id: Optional[int] = None,
    feature_image_path: Optional[str] = None,
    dry_run: bool = False,
    site_url: Optional[str] = None,
    author: Optional[Dict[str, Any]] = None,
) -> str:
    """Publish a job article to WordPress or simulate when dry_run.

    Args:
        profile_id: Profile ID for reference
        title: Post title
        content: HTML content
        slug: URL slug (SEO-optimized, 60-70 chars recommended)
        status: WordPress post status (publish, draft, future)
        category_id: Optional category id to assign
        feature_image_path: Path to feature image file (will be uploaded and set as featured media)
        dry_run: When True, do not call WordPress; return simulated URL
        site_url: WordPress site URL (if not provided, loads from config file)
        author: Author dict with wp_username and app_password (if not provided, loads from config file)

    Returns:
        The published (or simulated) URL string.
    """
    # If site_url and author are provided directly, use them (Firestore mode)
    if site_url and author:
        username = author.get("wp_username")
        app_password = author.get("app_password")
    else:
        # Fall back to loading from config file
        profiles = _load_profiles()
        profile = profiles.get(profile_id)
        if not profile:
            raise WPJobPublishingError(f"Profile '{profile_id}' not found in profiles_config.json")

        site_url = profile.get("site_url")
        
        # Handle both old format (author dict) and new format (direct fields)
        if "author" in profile:
            author = profile.get("author", {})
            username = author.get("wp_username") or author.get("username")
            app_password = author.get("app_password")
        else:
            username = profile.get("username")
            app_password = profile.get("app_password")

    if not site_url:
        raise WPJobPublishingError("site_url missing in profile config")
    
    if dry_run:
        # Use slug if provided, otherwise generate from title
        url_slug = slug if slug else title.replace(' ', '-').lower()
        simulated = f"{site_url.rstrip('/')}/drafts/{url_slug}"
        logger.info(f"Dry-run publish for profile {profile_id}: {simulated}")
        return simulated

    if not username or not app_password:
        raise WPJobPublishingError("WordPress credentials missing for profile")

    # Upload feature image first (if provided)
    featured_media_id = None
    if feature_image_path and not dry_run:
        try:
            # Extract content type from title or default to 'job'
            content_type = 'job'  # Default
            title_lower = title.lower()
            if 'result' in title_lower or 'merit' in title_lower:
                content_type = 'result'
            elif 'admit card' in title_lower or 'hall ticket' in title_lower:
                content_type = 'admit_card'
            
            featured_media_id = _upload_feature_image(
                site_url=site_url,
                username=username,
                app_password=app_password,
                image_path=feature_image_path,
                title=title,
                content_type=content_type
            )
            if featured_media_id:
                logger.info(f"🖼️  Feature image will be attached to post (Media ID: {featured_media_id})")
        except Exception as e:
            logger.warning(f"Feature image upload failed: {e}. Continuing without feature image.")

    headers = {
        "Authorization": _basic_auth_header(username, app_password),
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "title": title,
        "content": content,
        "status": status,
    }
    
    # Add featured media if uploaded
    if featured_media_id:
        payload["featured_media"] = featured_media_id
        logger.info(f"✅ Featured media ID added to payload: {featured_media_id}")
    
    # Add slug if provided (WordPress will auto-generate if not)
    logger.info(f"🔍 WordPress Publisher - Received slug: '{slug}' (type: {type(slug).__name__ if slug else 'None'})")
    if slug:
        payload["slug"] = slug
        logger.info(f"✅ Slug added to WordPress payload: '{slug}'")
    else:
        logger.warning(f"⚠️  No slug provided - WordPress will auto-generate from title: '{title}'")
    
    if category_id:
        payload["categories"] = [category_id]

    # Log the complete payload for debugging
    logger.info(f"📤 WordPress API Payload:")
    logger.info(f"   - title: '{title[:60]}...' ({len(title)} chars)")
    logger.info(f"   - slug: '{payload.get('slug', 'NOT SET')}'")
    logger.info(f"   - status: '{status}'")
    logger.info(f"   - content length: {len(content)} chars")
    logger.info(f"   - categories: {payload.get('categories', 'None')}")

    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("link") or data.get("guid", {}).get("rendered") or url
    except Exception as exc:
        raise WPJobPublishingError(f"Failed to publish to {url}: {exc}")
