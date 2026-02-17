import json
import os
import threading
import logging
import time
from app.core.config import Config

logger = logging.getLogger(__name__)

class EventBus:
    _instance = None
    _redis = None
    _handlers = {}
    _listening = False
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._init_redis()
        
    def _init_redis(self):
        # Ensure env is loaded
        Config.load_env() 
        try:
            REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            USE_REDIS = os.getenv('USE_REDIS', 'False').lower() == 'true'
            
            if USE_REDIS:
                import redis
                self._redis = redis.from_url(REDIS_URL)
                logger.info(f"EventBus connected to Redis at {REDIS_URL}")
            else:
                self._redis = None
                # No warning needed for default local dev

        except Exception as e:
            logger.error(f"EventBus failed to connect to Redis: {e}")
            self._redis = None

    def publish(self, channel, data):
        """Publish an event to a channel."""
        try:
            message = json.dumps(data)
            if self._redis:
                self._redis.publish(channel, message)
                logger.debug(f"Published to Redis channel {channel}: {message}")
            else:
                # Local fallback mechanism (simple direct callback for same process)
                self._handle_local_message(channel, message)
        except Exception as e:
            logger.error(f"Failed to publish event to {channel}: {e}")

    def subscribe(self, channel, callback):
        """Subscribe to a channel with a callback function."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(callback)
        
        if self._redis and not self._listening:
            self._start_listener()

    def _start_listener(self):
        """Start a background thread to listen for Redis messages."""
        self._listening = True
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()
        
    def _listen_loop(self):
        pubsub = self._redis.pubsub()
        # Subscribe to all registered channels
        # Note: Logic to update subscriptions dynamically is complex, 
        # so for simplicity we subscribe to a pattern or fixed set.
        # Here we subscribe to everything under tickzen:* prefix for simplicity
        # or just specific channels if known.
        
        # Better approach: Subscribe to all channels currently in _handlers
        for channel in self._handlers:
            pubsub.subscribe(channel)
            
        logger.info("EventBus listener started.")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = message['data'].decode('utf-8')
                    self._dispatch(channel, data)
        except Exception as e:
            logger.error(f"EventBus listener error: {e}")
            self._listening = False # Needs restart logic in real robust app

    def _handle_local_message(self, channel, data_str):
        """Handle message locally without Redis."""
        self._dispatch(channel, data_str)

    def _dispatch(self, channel, data_str):
        try:
            data = json.loads(data_str)
            if channel in self._handlers:
                for callback in self._handlers[channel]:
                    try:
                        callback(data)
                    except Exception as cb_err:
                        logger.error(f"Error in event handler for {channel}: {cb_err}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in event on {channel}")


# Global accessor
_event_bus = None

def get_event_bus():
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus.get_instance()
    return _event_bus

def publish_event(event_type, payload):
    """Refined helper to publish standard events"""
    bus = get_event_bus()
    bus.publish(f"tickzen:{event_type}", payload)

def subscribe_event(event_type, callback):
    """Refined helper to subscribe to standard events"""
    bus = get_event_bus()
    bus.subscribe(f"tickzen:{event_type}", callback)
