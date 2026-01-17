"""
Job Portal Automation API Module
=================================

Handles all external API integrations:
- Job Crawler API client
- Perplexity AI research client
"""

from .job_api_client import JobAPIClient
from .perplexity_client import PerplexityResearchCollector

__all__ = ["JobAPIClient", "PerplexityResearchCollector"]
