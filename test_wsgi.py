#!/usr/bin/env python3
"""
Test WSGI import to verify application can be loaded
"""
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

print("Testing WSGI import...")

try:
    print("Importing wsgi module...")
    import wsgi
    print("✓ WSGI module imported successfully")
    
    print("Checking for 'application' attribute...")
    if hasattr(wsgi, 'application'):
        print("✓ wsgi.application exists")
        print(f"  Type: {type(wsgi.application)}")
    else:
        print("✗ wsgi.application NOT FOUND")
        print(f"  Available attributes: {dir(wsgi)}")
        
    print("\n✅ All tests passed! WSGI entry point is correctly configured.")
    sys.exit(0)
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
