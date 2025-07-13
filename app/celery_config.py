"""
Celery configuration for background task processing
"""
import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Create Celery instance
celery_app = Celery(
    'tempautomate',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['app.celery_tasks']
)

# Celery configuration - Optimized for small scale (10-15 concurrent users)
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution - Optimized for small scale
    task_track_started=True,
    task_time_limit=15 * 60,  # 15 minutes (reduced from 30)
    task_soft_time_limit=12 * 60,  # 12 minutes (reduced from 25)
    
    # Worker configuration - Optimized for small scale
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,  # Reduced from 1000
    
    # Result backend configuration - Optimized for memory
    result_expires=900,  # 15 minutes (reduced from 1 hour)
    
    # Beat schedule (for periodic tasks)
    beat_schedule={},
    
    # Broker connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=5,  # Reduced from 10
    
    # Task routing settings
    task_always_eager=False,
    task_eager_propagates=True,
    
    # Task routing - disabled to avoid conflicts
    # task_routes={},
    
    # Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
)

# Optional: Configure logging
celery_app.conf.update(
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

if __name__ == '__main__':
    celery_app.start() 