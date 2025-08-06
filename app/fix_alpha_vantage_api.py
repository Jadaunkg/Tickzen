"""
This script checks and fixes issues with the Alpha Vantage API implementation
in the market_news.py file to properly handle API limits and information messages.
"""

import os
import requests
import json

# Check what Alpha Vantage is returning for our API key
def check_alpha_vantage_response():
    api_key = os.environ.get('ALPHA_API_KEY')
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            api_key = os.environ.get('ALPHA_API_KEY')
        except ImportError:
            print("dotenv not available")
    
    if not api_key:
        print("API key not found in environment variables")
        return
    
    print(f"Using API key: {api_key[:4]}...{api_key[-4:]}")
    
    # Make a test request
    base_url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
        "limit": 200
    }
    
    try:
        print("Sending request to Alpha Vantage...")
        response = requests.get(base_url, params=params, timeout=10)
        print(f"Response status code: {response.status_code}")
        
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        
        if "Information" in data:
            print("\nInformation message from Alpha Vantage:")
            print(data["Information"])
            print("\nThis typically means you've hit a usage limit or there's an issue with your API key.")
            print("Free tier keys are limited to 25 API calls per day.")
            
            # Add recommendation
            print("\nRecommendations:")
            print("1. Upgrade to a premium Alpha Vantage plan for higher limits")
            print("2. Enable aggressive caching (increase NEWS_CACHE_TIMEOUT to 24+ hours)")
            print("3. Check if your API key has been used elsewhere")
            
        elif "feed" in data:
            print(f"\nSuccess! API returned {len(data['feed'])} news items")
            if len(data['feed']) > 0:
                print("\nSample news item:")
                print(json.dumps(data['feed'][0], indent=2)[:500] + "...")
        else:
            print("\nUnexpected response format. All keys in response:")
            print(json.dumps(data, indent=2))
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_alpha_vantage_response()
