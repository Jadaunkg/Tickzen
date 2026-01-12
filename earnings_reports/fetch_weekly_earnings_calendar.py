import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import finnhub


# Load environment variables from .env
load_dotenv()
API_KEY = os.getenv('FINNHUB_API_KEY')

import requests

def fetch_weekly_earnings_calendar():
    """Fetch earnings calendar for the next 7 days and save with metadata"""
    results = {}
    base_url = "https://finnhub.io/api/v1/calendar/earnings"
    start_date = datetime.now()
    
    # Request session with timeout configuration
    session = requests.Session()
    session.timeout = 10  # 10 second timeout
    
    for i in range(7):
        day = start_date + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        params = {
            'from': day_str,
            'to': day_str,
            'token': API_KEY
        }
        
        try:
            response = session.get(base_url, params=params, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
            
            daily_list = []
            for entry in data.get('earningsCalendar', []):
                daily_list.append({
                    'ticker': entry.get('symbol'),
                    'name': entry.get('company'),
                    'date': entry.get('date')
                })
            results[day_str] = daily_list
            
        except (requests.RequestException, requests.Timeout, requests.ConnectTimeout) as e:
            print(f"Error fetching data for {day_str}: {e}")
            # Use empty list for failed dates
            results[day_str] = []
    
    # Create the final data structure with metadata
    calendar_data = {
        'last_refreshed': datetime.now().isoformat(),
        'last_refreshed_date': datetime.now().strftime('%Y-%m-%d'),
        'calendar': results
    }
    
    # Determine file path (save in project root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(project_root, 'data', 'weekly_earnings_calendar.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(calendar_data, f, indent=2)
    
    print(f"Saved weekly earnings calendar to {output_path}")
    print(f"Last refreshed: {calendar_data['last_refreshed']}")
    
    # Count total tickers
    total_tickers = sum(len(daily_list) for daily_list in results.values())
    print(f"Total tickers with earnings in next 7 days: {total_tickers}")
    
    return calendar_data

if __name__ == '__main__':
    fetch_weekly_earnings_calendar()
