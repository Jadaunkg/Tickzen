#!/usr/bin/env python3
"""
Production startup script for Flask app with Celery worker
"""
import os
import sys
import subprocess
import signal
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ProductionServer:
    """Manages production server processes"""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_redis(self):
        """Start Redis server if not running"""
        try:
            # Check if Redis is running
            result = subprocess.run(['redis-cli', 'ping'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and 'PONG' in result.stdout:
                logger.info("Redis is already running")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        logger.warning("Redis not found or not running. Please start Redis manually:")
        logger.warning("  - Install Redis: https://redis.io/download")
        logger.warning("  - Start Redis: redis-server")
        return False
    
    def start_celery_worker(self):
        """Start Celery worker process"""
        try:
            logger.info("Starting Celery worker...")
            worker_process = subprocess.Popen([
                sys.executable, 'celery_worker.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(('Celery Worker', worker_process))
            logger.info(f"Celery worker started with PID: {worker_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Celery worker: {e}")
            return False
    
    def start_flask_app(self):
        """Start Flask application"""
        try:
            logger.info("Starting Flask application...")
            
            # Set production environment
            env = os.environ.copy()
            env['APP_ENV'] = 'production'
            env['FLASK_DEBUG'] = 'False'
            
            flask_process = subprocess.Popen([
                sys.executable, 'app/main_portal_app.py'
            ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(('Flask App', flask_process))
            logger.info(f"Flask app started with PID: {flask_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Flask app: {e}")
            return False
    
    def start_celery_beat(self):
        """Start Celery beat scheduler (for periodic tasks)"""
        try:
            logger.info("Starting Celery beat scheduler...")
            beat_process = subprocess.Popen([
                sys.executable, '-m', 'celery', 'beat',
                '--app=app.celery_config.celery_app',
                '--loglevel=info',
                '--scheduler=celery.beat.PersistentScheduler'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(('Celery Beat', beat_process))
            logger.info(f"Celery beat started with PID: {beat_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Celery beat: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.shutdown()
    
    def shutdown(self):
        """Shutdown all processes"""
        logger.info("Shutting down all processes...")
        
        for name, process in self.processes:
            try:
                logger.info(f"Stopping {name} (PID: {process.pid})...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                    logger.info(f"{name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} did not stop gracefully, forcing...")
                    process.kill()
                    process.wait()
                    
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("All processes stopped")
    
    def monitor_processes(self):
        """Monitor running processes"""
        while self.running:
            for name, process in self.processes[:]:
                if process.poll() is not None:
                    logger.error(f"{name} process died unexpectedly (exit code: {process.returncode})")
                    self.processes.remove((name, process))
                    
                    # Restart the process
                    if name == 'Celery Worker':
                        self.start_celery_worker()
                    elif name == 'Flask App':
                        self.start_flask_app()
                    elif name == 'Celery Beat':
                        self.start_celery_beat()
            
            time.sleep(5)
    
    def run(self):
        """Run the production server"""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Starting production server...")
        
        # Check Redis
        if not self.start_redis():
            logger.error("Redis is required but not available. Exiting.")
            return False
        
        # Start processes
        success = True
        success &= self.start_celery_worker()
        success &= self.start_flask_app()
        success &= self.start_celery_beat()
        
        if not success:
            logger.error("Failed to start one or more processes. Exiting.")
            self.shutdown()
            return False
        
        logger.info("All processes started successfully")
        logger.info("Production server is running...")
        logger.info("Press Ctrl+C to stop")
        
        # Monitor processes
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.shutdown()
        
        return True

def main():
    """Main entry point"""
    server = ProductionServer()
    return server.run()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 