"""
Quota Plan Definitions
Defines quota limits for different subscription tiers
"""

from datetime import datetime
from typing import Dict, Any

# Quota Plan Definitions
QUOTA_PLANS = {
    "free": {
        "plan_id": "free",
        "display_name": "Free Plan",
        "limits": {
            "stock_reports_monthly": 10,
        },
        "features": [
            "10 stock analysis reports per month",
            "Basic stock analysis",
            "Limited automation",
            "Standard support"
        ],
        "price_monthly": 0,
        "is_active": True
    },
    "pro": {
        "plan_id": "pro",
        "display_name": "Pro Plan",
        "limits": {
            "stock_reports_monthly": 45,
        },
        "features": [
            "45 stock analysis reports per month",
            "Advanced stock analysis",
            "Priority support",
            "Custom alerts"
        ],
        "price_monthly": 29,
        "is_active": True
    },
    "pro_plus": {
        "plan_id": "pro_plus",
        "display_name": "Pro+ Plan",
        "limits": {
            "stock_reports_monthly": 100,
        },
        "features": [
            "100 stock analysis reports per month",
            "Advanced stock analysis",
            "Premium support",
            "Custom alerts",
            "API access"
        ],
        "price_monthly": 79,
        "is_active": True
    },
    "enterprise": {
        "plan_id": "enterprise",
        "display_name": "Enterprise Plan",
        "limits": {
            "stock_reports_monthly": -1,  # -1 means unlimited
        },
        "features": [
            "Unlimited stock analysis reports",
            "All Pro+ features",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantees"
        ],
        "price_monthly": 299,
        "is_active": True
    }
}

# Default plan for new users
DEFAULT_PLAN = "free"

# Resource types
RESOURCE_TYPES = {
    "stock_report": "stock_reports_monthly",
}

def get_plan_limits(plan_id: str) -> Dict[str, int]:
    """Get quota limits for a specific plan"""
    plan = QUOTA_PLANS.get(plan_id, QUOTA_PLANS[DEFAULT_PLAN])
    return plan["limits"]

def get_plan_info(plan_id: str) -> Dict[str, Any]:
    """Get full plan information"""
    return QUOTA_PLANS.get(plan_id, QUOTA_PLANS[DEFAULT_PLAN])

def is_unlimited(limit: int) -> bool:
    """Check if a limit is unlimited (-1)"""
    return limit == -1

def get_all_plans() -> Dict[str, Dict[str, Any]]:
    """Get all available plans"""
    return QUOTA_PLANS
