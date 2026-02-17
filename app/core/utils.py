import os
import re
from datetime import datetime, timezone, date, timedelta
import dateutil.parser
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def is_reloader_process():
    """Check if this is the parent reloader process (not the actual worker)"""
    return os.environ.get('WERKZEUG_RUN_MAIN') != 'true'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_url(url_string):
    if not url_string: return False
    if not (url_string.startswith('http://') or url_string.startswith('https://')): return False
    try:
        domain_part = url_string.split('//')[1].split('/')[0]
        if '.' not in domain_part or len(domain_part) < 3: 
            return False
    except IndexError: return False
    return True

def format_datetime_filter(value, fmt="%Y-%m-%d %H:%M:%S"):
    if not value: return "N/A"
    try:
        # Handle string inputs
        if isinstance(value, str):
            # Check for Z suffix and handle timezone
            if value.endswith('Z'):
                value = value.replace('Z', '+00:00')
            try:
                dt_obj = datetime.fromisoformat(value)
            except ValueError:
                dt_obj = dateutil.parser.parse(value)
                
        # Handle numeric timestamps (seconds or milliseconds)
        elif isinstance(value, (int, float)):
            # Heuristic to detect milliseconds (timestamp > 10 billion)
            if value > 10**10: 
                 dt_obj = datetime.fromtimestamp(value / 1000, timezone.utc)
            else: 
                 dt_obj = datetime.fromtimestamp(value, timezone.utc)
                 
        # Handle datetime objects
        elif isinstance(value, datetime):
            dt_obj = value
            
        # Handle Firestore Timestamp objects (duck typing)
        elif hasattr(value, 'seconds') and hasattr(value, 'nanoseconds'): 
            seconds = value.seconds
            nanoseconds = value.nanoseconds
            # Construct timestamp
            dt_obj = datetime.fromtimestamp(seconds + nanoseconds / 1e9, timezone.utc)
        else:
            return value 

        # Ensure timezone awareness (assume UTC if naive)
        if dt_obj.tzinfo is None: 
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)

        return dt_obj.strftime(fmt)
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning(f"Could not format datetime value '{value}' (type: {type(value)}): {e}")
        return value

def format_earnings_date_filter(value):
    """Format earnings calendar date into readable format with day name"""
    if not value: return "N/A"
    try:
        # Parse logic
        if isinstance(value, str):
             dt_obj = datetime.strptime(value, "%Y-%m-%d")
        elif isinstance(value, datetime):
             dt_obj = value
        elif isinstance(value, date):
             dt_obj = datetime.combine(value, datetime.min.time())
        else:
             return str(value)
        
        # Get day name and formatted date
        day_name = dt_obj.strftime("%A")
        formatted_date = dt_obj.strftime("%B %d, %Y")
        
        # Check if it's today, tomorrow, or show day name
        today = date.today()
        tomorrow = today + timedelta(days=1)
        target_date = dt_obj.date()
        
        if target_date == today:
            return f"Today - {formatted_date}"
        elif target_date == tomorrow:
            return f"Tomorrow - {formatted_date}"
        else:
            return f"{day_name} - {formatted_date}"
    except (ValueError, AttributeError, TypeError) as e:
        return str(value)
