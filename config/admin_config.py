"""
Admin Configuration
Stores admin-specific settings and permissions
"""

# Admin email addresses
# These users have full admin access to quota management and system settings
ADMIN_EMAILS = [
    'jadaunkg@gmail.com',
    'admin@tickzen.app',
]

# Admin permissions
ADMIN_PERMISSIONS = {
    'quota_management': True,
    'user_management': True,
    'system_settings': True,
}

def is_admin_user(email: str) -> bool:
    """
    Check if email belongs to an admin user
    
    Args:
        email: User email address
    
    Returns:
        True if user is admin, False otherwise
    """
    if not email:
        return False
    
    return email.lower().strip() in [e.lower() for e in ADMIN_EMAILS]


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
