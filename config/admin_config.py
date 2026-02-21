"""
Admin Configuration
Stores admin-specific settings and permissions

Admin emails are loaded from the ADMIN_EMAILS environment variable as a
comma-separated list.  Example .env entry:
    ADMIN_EMAILS=admin@tickzen.app,youremail@example.com
If the variable is not set, no admin access is granted in production.
"""

import os

# Admin email addresses — read from env var; NEVER hard-code in source.
_raw = os.getenv('ADMIN_EMAILS', '')
ADMIN_EMAILS: list[str] = [e.strip().lower() for e in _raw.split(',') if e.strip()]

# Admin permissions
ADMIN_PERMISSIONS = {
    'quota_management': True,
    'user_management': True,
    'system_settings': True,
}

def is_admin_user(email: str) -> bool:
    """
    Check if email belongs to an admin user.

    Admin emails are loaded from the ADMIN_EMAILS environment variable
    (comma-separated).  Returns False if ADMIN_EMAILS is not configured.

    Args:
        email: User email address

    Returns:
        True if user is admin, False otherwise
    """
    if not email or not ADMIN_EMAILS:
        return False

    return email.lower().strip() in ADMIN_EMAILS


def has_admin_permission(email: str, permission: str) -> bool:
    """
    Check if admin user has specific permission
    
    Args:
        email: User email address
        permission: Permission name to check
    
    Returns:
        True if user has permission, False otherwise
    """
    if not is_admin_user(email):
        return False
    
    return ADMIN_PERMISSIONS.get(permission, False)
