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
"""

import base64
import json
import logging
import os
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


def publish_job_article(
    *,
    profile_id: str,
    title: str,
    content: str,
    status: str = "draft",
    category_id: Optional[int] = None,
    dry_run: bool = False,
    site_url: Optional[str] = None,
    author: Optional[Dict[str, Any]] = None,
) -> str:
    """Publish a job article to WordPress or simulate when dry_run.

    Args:
        profile_id: Profile ID for reference
        title: Post title
        content: HTML content
        status: WordPress post status (publish, draft, future)
        category_id: Optional category id to assign
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
        simulated = f"{site_url.rstrip('/')}/drafts/{title.replace(' ', '-').lower()}"
        logger.info(f"Dry-run publish for profile {profile_id}: {simulated}")
        return simulated

    if not username or not app_password:
        raise WPJobPublishingError("WordPress credentials missing for profile")

    headers = {
        "Authorization": _basic_auth_header(username, app_password),
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "title": title,
        "content": content,
        "status": status,
    }
    if category_id:
        payload["categories"] = [category_id]

    url = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("link") or data.get("guid", {}).get("rendered") or url
    except Exception as exc:
        raise WPJobPublishingError(f"Failed to publish to {url}: {exc}")
