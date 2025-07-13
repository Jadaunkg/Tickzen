#!/usr/bin/env python3
"""
Celery worker startup script for background task processing
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('celery_worker.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start Celery worker"""
    try:
        # Import Celery app
        from app.celery_config import celery_app
        
        logger.info("Starting Celery worker...")
        logger.info(f"Broker URL: {celery_app.conf.broker_url}")
        logger.info(f"Result Backend: {celery_app.conf.result_backend}")
        
        # Start the worker
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=4',  # Number of worker processes
            '--queues=default,file_processing,database,automation',  # Queues to process
            '--hostname=worker@%h',  # Worker hostname
            '--without-gossip',  # Disable gossip for single worker
            '--without-mingle',  # Disable mingle for single worker
            '--without-heartbeat'  # Disable heartbeat for single worker
        ])
        
    except KeyboardInterrupt:
        logger.info("Celery worker stopped by user")
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 