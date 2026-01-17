"""
Job Portal Automation State Management Module
==============================================

Handles state persistence, tracking, and recovery.
"""

from .job_publishing_state_manager import JobPublishingStateManager

__all__ = ["JobPublishingStateManager"]
