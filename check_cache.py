#!/usr/bin/env python3
"""
Cache checking utility for Tickzen application
This module provides functions to check and manage application cache
"""

import os
import json
import time
from datetime import datetime, timedelta

def check_cache_status(cache_dir=None):
    """
    Check the status of application cache
    
    Args:
        cache_dir (str): Directory to check for cache files
        
    Returns:
        dict: Cache status information
    """
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'generated_data')
    
    status = {
        'cache_dir': cache_dir,
        'exists': os.path.exists(cache_dir),
        'files': [],
        'total_size': 0,
        'oldest_file': None,
        'newest_file': None,
        'timestamp': datetime.now().isoformat()
    }
    
    if not status['exists']:
        return status
    
    try:
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            if os.path.isfile(file_path):
                file_stat = os.stat(file_path)
                file_info = {
                    'name': filename,
                    'size': file_stat.st_size,
                    'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    'age_days': (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
                }
                status['files'].append(file_info)
                status['total_size'] += file_stat.st_size
                
                if status['oldest_file'] is None or file_info['age_days'] > status['oldest_file']['age_days']:
                    status['oldest_file'] = file_info
                
                if status['newest_file'] is None or file_info['age_days'] < status['newest_file']['age_days']:
                    status['newest_file'] = file_info
    except Exception as e:
        status['error'] = str(e)
    
    return status

def cleanup_old_cache(cache_dir=None, max_age_days=7):
    """
    Clean up old cache files
    
    Args:
        cache_dir (str): Directory to clean
        max_age_days (int): Maximum age in days before deletion
        
    Returns:
        dict: Cleanup results
    """
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'generated_data')
    
    results = {
        'cache_dir': cache_dir,
        'files_removed': 0,
        'bytes_freed': 0,
        'errors': [],
        'timestamp': datetime.now().isoformat()
    }
    
    if not os.path.exists(cache_dir):
        results['error'] = f"Cache directory does not exist: {cache_dir}"
        return results
    
    try:
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            if os.path.isfile(file_path):
                file_age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))).days
                
                if file_age > max_age_days:
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        results['files_removed'] += 1
                        results['bytes_freed'] += file_size
                    except Exception as e:
                        results['errors'].append(f"Failed to remove {filename}: {e}")
    except Exception as e:
        results['error'] = str(e)
    
    return results

if __name__ == "__main__":
    # Test cache checking functionality
    print("Checking cache status...")
    status = check_cache_status()
    print(json.dumps(status, indent=2))
    
    print("\nCleaning up old cache...")
    cleanup_results = cleanup_old_cache()
    print(json.dumps(cleanup_results, indent=2))
