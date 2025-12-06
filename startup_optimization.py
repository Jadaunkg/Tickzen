# startup_optimization.py
"""
Azure App Service startup optimization for Tickzen
This module implements lazy loading and startup performance improvements
"""

import os
import sys
import time
from functools import lru_cache

# Enable lazy loading for heavy imports
LAZY_IMPORTS = {
    'matplotlib': None,
    'plotly': None,
    'prophet': None,
    'pandas': None,
    'numpy': None
}

def optimize_matplotlib():
    """Optimize matplotlib for faster loading"""
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    # Set matplotlib to use system fonts to avoid font building
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'
    return matplotlib

def optimize_environment():
    """Set environment variables for faster startup"""
    # Disable matplotlib font cache rebuilding
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
    
    # Disable numba JIT compilation for faster imports
    os.environ['NUMBA_DISABLE_JIT'] = '1'
    
    # Optimize Python startup
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    # Optimize pandas
    os.environ['PANDAS_PLOTTING_BACKEND'] = 'matplotlib'

@lru_cache(maxsize=1)
def get_heavy_imports():
    """Lazy load heavy dependencies only when needed"""
    start_time = time.time()
    
    try:
        # Load matplotlib with optimizations
        matplotlib = optimize_matplotlib()
        LAZY_IMPORTS['matplotlib'] = matplotlib
        
        # Load other heavy packages
        import pandas as pd
        LAZY_IMPORTS['pandas'] = pd
        
        import numpy as np
        LAZY_IMPORTS['numpy'] = np
        
        print(f"Heavy imports loaded in {time.time() - start_time:.2f} seconds")
        
    except Exception as e:
        print(f"Error loading heavy imports: {e}")
    
    return LAZY_IMPORTS

def quick_health_check():
    """Quick health check without heavy operations"""
    try:
        # Basic Flask import test
        from flask import Flask
        
        # Basic system check
        import socket
        socket.gethostname()
        
        return True
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def initialize_minimal_app():
    """Initialize minimal Flask app for quick startup"""
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'timestamp': time.time()}
    
    return app

# Initialize optimizations
optimize_environment()

def optimize_startup_environment():
    """Apply comprehensive startup optimizations for Azure deployment"""
    print("🚀 Applying startup optimizations...")
    
    # Apply environment optimizations
    optimize_environment()
    
    # Pre-optimize matplotlib
    try:
        optimize_matplotlib()
        print("✅ Matplotlib pre-optimized")
    except Exception as e:
        print(f"⚠️  Matplotlib optimization failed: {e}")
    
    print("✅ Startup optimizations completed")
