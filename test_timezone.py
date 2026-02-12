#!/usr/bin/env python3
from database.smart_updater import SmartStockUpdater
import pytz
from datetime import datetime

# Test timezone logic
updater = SmartStockUpdater()
et = pytz.timezone('US/Eastern')
now_et = datetime.now(et)

print(f'Current ET time: {now_et.strftime("%H:%M %Z")}')
print('Testing should_update_today for AAPL...')

# Check what's in database first
stock = updater.db.get_stock_by_symbol('AAPL') 
last_sync = stock.get('last_sync_date')
print(f'Raw last_sync_date from DB: {last_sync}')
print(f'Type: {type(last_sync)}')

# Parse the timestamp like the code does
if isinstance(last_sync, str):
    try:
        last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
        print(f'Parsed datetime: {last_sync_dt}')
        print(f'Timezone info: {last_sync_dt.tzinfo}')
        
        # Convert to ET like the code does
        last_sync_dt_utc = last_sync_dt.astimezone(pytz.UTC)
        last_sync_et = last_sync_dt_utc.astimezone(et)
        print(f'Converted to ET: {last_sync_et}')
        
        # Calculate hours difference
        hours_since_update = (now_et - last_sync_et).total_seconds() / 3600
        print(f'Hours since update: {hours_since_update:.1f}h')
        
    except Exception as e:
        print(f'Parse error: {e}')

print('\n' + '='*50)
should_update, reason = updater.should_update_today('AAPL', force_intraday=True)
print(f'Should update: {should_update}')
print(f'Reason: {reason}')

if should_update:
    print("✅ Would trigger intraday update!")
else:
    print("❌ Skipping intraday update")