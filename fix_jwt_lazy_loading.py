#!/usr/bin/env python3
"""
Script to add lazy loading for JWT in main_portal_app.py
"""

import re

def fix_jwt_lazy_loading():
    file_path = "app/main_portal_app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find jwt.decode or jwt.encode usage
    patterns = [
        # Pattern for lines like "decoded = jwt.decode(...)"
        (r'(\s+)(decoded = jwt\.decode\()', r'\1jwt = get_jwt()  # Lazy load JWT\n\1\2'),
        # Pattern for lines like "mock_token = jwt.encode(...)"
        (r'(\s+)(.*?= jwt\.encode\()', r'\1jwt = get_jwt()  # Lazy load JWT\n\1\2'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ JWT lazy loading fixes applied")

if __name__ == "__main__":
    fix_jwt_lazy_loading()
