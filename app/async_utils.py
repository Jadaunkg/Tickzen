"""
Async utilities for handling synchronous operations in a non-blocking way
"""
import asyncio
import concurrent.futures
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')

# Global thread pool executor
_thread_pool_executor = None


def get_thread_pool_executor(max_workers: int = 10) -> concurrent.futures.ThreadPoolExecutor:
    """Get or create a thread pool executor"""
    global _thread_pool_executor
    if _thread_pool_executor is None:
        _thread_pool_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="AsyncUtils"
        )
    return _thread_pool_executor


def run_in_thread_pool(func: Callable[..., T], *args, **kwargs) -> concurrent.futures.Future[T]:
    """
    Run a function in a thread pool executor
    
    Args:
        func: Function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    
    Returns:
        Future object that will contain the result
    """
    executor = get_thread_pool_executor()
    return executor.submit(func, *args, **kwargs)


def run_sync_in_thread(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in a thread pool and wait for result
    
    Args:
        func: Function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function execution
    """
    future = run_in_thread_pool(func, *args, **kwargs)
    return future.result()


async def run_sync_async(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function asynchronously using thread pool
    
    Args:
        func: Function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function execution
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        get_thread_pool_executor(),
        functools.partial(func, *args, **kwargs)
    )


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry async functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                                     f"Retrying in {current_delay} seconds...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        return wrapper
    return decorator


def sync_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry synchronous functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                                     f"Retrying in {current_delay} seconds...")
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        return wrapper
    return decorator


class AsyncFirestoreWrapper:
    """Wrapper for Firestore operations to make them async-friendly"""
    
    def __init__(self, firestore_client):
        self.client = firestore_client
    
    async def get_document(self, collection_path: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document asynchronously"""
        def _get_doc():
            doc_ref = self.client.collection(collection_path).document(document_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        
        return await run_sync_async(_get_doc)
    
    async def set_document(self, collection_path: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Set a document asynchronously"""
        def _set_doc():
            doc_ref = self.client.collection(collection_path).document(document_id)
            doc_ref.set(data)
            return True
        
        return await run_sync_async(_set_doc)
    
    async def update_document(self, collection_path: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Update a document asynchronously"""
        def _update_doc():
            doc_ref = self.client.collection(collection_path).document(document_id)
            doc_ref.update(data)
            return True
        
        return await run_sync_async(_update_doc)
    
    async def delete_document(self, collection_path: str, document_id: str) -> bool:
        """Delete a document asynchronously"""
        def _delete_doc():
            doc_ref = self.client.collection(collection_path).document(document_id)
            doc_ref.delete()
            return True
        
        return await run_sync_async(_delete_doc)
    
    async def get_collection(self, collection_path: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get documents from a collection asynchronously"""
        def _get_collection():
            query = self.client.collection(collection_path)
            if limit:
                query = query.limit(limit)
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        
        return await run_sync_async(_get_collection)


class AsyncStorageWrapper:
    """Wrapper for Firebase Storage operations to make them async-friendly"""
    
    def __init__(self, storage_bucket):
        self.bucket = storage_bucket
    
    async def upload_file(self, file_bytes: bytes, storage_path: str, content_type: str = None) -> bool:
        """Upload a file asynchronously"""
        def _upload():
            blob = self.bucket.blob(storage_path)
            if content_type:
                blob.content_type = content_type
            blob.upload_from_string(file_bytes)
            return True
        
        return await run_sync_async(_upload)
    
    async def download_file(self, storage_path: str) -> Optional[bytes]:
        """Download a file asynchronously"""
        def _download():
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                return blob.download_as_bytes()
            return None
        
        return await run_sync_async(_download)
    
    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file asynchronously"""
        def _delete():
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.delete()
            return True
        
        return await run_sync_async(_delete)
    
    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists asynchronously"""
        def _exists():
            blob = self.bucket.blob(storage_path)
            return blob.exists()
        
        return await run_sync_async(_exists)


def cleanup_thread_pool():
    """Clean up the thread pool executor"""
    global _thread_pool_executor
    if _thread_pool_executor:
        _thread_pool_executor.shutdown(wait=True)
        _thread_pool_executor = None


# Context manager for thread pool
class ThreadPoolContext:
    """Context manager for thread pool operations"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = None
    
    def __enter__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="ThreadPoolContext"
        )
        return self.executor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.executor:
            self.executor.shutdown(wait=True)


# Utility functions for common async patterns
async def batch_process(items: List[Any], processor: Callable[[Any], T], 
                       batch_size: int = 10, max_concurrent: int = 5) -> List[T]:
    """
    Process items in batches asynchronously
    
    Args:
        items: List of items to process
        processor: Function to process each item
        batch_size: Number of items to process in each batch
        max_concurrent: Maximum number of concurrent batches
    
    Returns:
        List of processed results
    """
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(batch):
        async with semaphore:
            tasks = [run_sync_async(processor, item) for item in batch]
            return await asyncio.gather(*tasks)
    
    # Split items into batches
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    # Process batches concurrently
    batch_tasks = [process_batch(batch) for batch in batches]
    batch_results = await asyncio.gather(*batch_tasks)
    
    # Flatten results
    for batch_result in batch_results:
        results.extend(batch_result)
    
    return results


def create_task_status(task_id: str, status: str = "PENDING", 
                      progress: int = 0, message: str = "", 
                      result: Any = None, error: str = None) -> Dict[str, Any]:
    """
    Create a standardized task status object
    
    Args:
        task_id: Unique task identifier
        status: Task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
        progress: Progress percentage (0-100)
        message: Status message
        result: Task result (if completed)
        error: Error message (if failed)
    
    Returns:
        Task status dictionary
    """
    return {
        'task_id': task_id,
        'status': status,
        'progress': progress,
        'message': message,
        'result': result,
        'error': error,
        'timestamp': datetime.now(timezone.utc).isoformat()
    } 