#!/usr/bin/env python3
"""
Startup script to diagnose and test the Flask application
"""
import sys
import os

def test_imports():
    """Test all critical imports"""
    print("Testing critical imports...")
    
    # Test basic Python modules
    try:
        import flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False
    
    try:
        import redis
        print("✓ Redis imported successfully")
    except ImportError as e:
        print(f"✗ Redis import failed: {e}")
    
    try:
        import firebase_admin
        print("✓ Firebase Admin imported successfully")
    except ImportError as e:
        print(f"✗ Firebase Admin import failed: {e}")
    
    try:
        import celery
        print("✓ Celery imported successfully")
    except ImportError as e:
        print(f"✗ Celery import failed: {e}")
    
    try:
        import magic
        print("✓ Python-magic imported successfully")
    except ImportError as e:
        print(f"✗ Python-magic import failed: {e}")
    
    return True

def test_environment():
    """Test environment variables"""
    print("\nTesting environment variables...")
    
    env_vars = [
        'APP_ENV',
        'FLASK_ENV',
        'REDIS_URL',
        'FLASK_SECRET_KEY'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} = {value[:10]}..." if len(str(value)) > 10 else f"✓ {var} = {value}")
        else:
            print(f"✗ {var} not set")
    
    # Set defaults if not present
    os.environ.setdefault('APP_ENV', 'production')
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')

def test_app_import():
    """Test importing the main app"""
    print("\nTesting app import...")
    
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from app.main_portal_app import app
        print("✓ Main app imported successfully")
        print(f"  App name: {app.name}")
        print(f"  App config: {app.config.get('ENV', 'Not set')}")
        return app
    except ImportError as e:
        print(f"✗ Main app import failed: {e}")
        print(f"  Current directory: {os.getcwd()}")
        print(f"  Python path: {sys.path[:3]}...")  # Show first 3 entries
        if os.path.exists('app'):
            print(f"  App directory contents: {os.listdir('app')[:5]}...")  # Show first 5 files
        return None

def main():
    """Main diagnostic function"""
    print("=== Flask App Startup Diagnostics ===")
    
    # Test basic imports
    if not test_imports():
        print("Critical imports failed. Exiting.")
        sys.exit(1)
    
    # Test environment
    test_environment()
    
    # Test app import
    app = test_app_import()
    
    if app:
        print("\n✓ All tests passed! App is ready to run.")
        return app
    else:
        print("\n✗ App import failed. Check the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main() 