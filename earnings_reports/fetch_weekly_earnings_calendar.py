import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import finnhub


# Load environment variables from .env
load_dotenv()
API_KEY = os.getenv('FINNHUB_API_KEY')

import requests
results = {}
base_url = "https://finnhub.io/api/v1/calendar/earnings"
start_date = datetime.now()
for i in range(7):
    day = start_date + timedelta(days=i)
    day_str = day.strftime('%Y-%m-%d')
    params = {
        'from': day_str,
        'to': day_str,
        'token': API_KEY
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    daily_list = []
    for entry in data.get('earningsCalendar', []):
        daily_list.append({
            'ticker': entry.get('symbol'),
            'name': entry.get('company'),
            'date': entry.get('date')
        })
    results[day_str] = daily_list

with open('weekly_earnings_calendar.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f"Saved weekly earnings calendar to weekly_earnings_calendar.json")
