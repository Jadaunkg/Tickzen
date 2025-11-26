# Duplicate Content Prevention Fix

## Problem Description

When multiple site profiles were configured to publish articles simultaneously, the same ticker (e.g., AAPL) would generate and publish **duplicate articles across multiple sites**, causing:

❌ **Duplicate Content** - Same article published to multiple sites
❌ **SEO Issues** - Google penalizes duplicate content
❌ **Resource Waste** - Generating same article multiple times
❌ **User Confusion** - Same content appearing on different sites

### Root Cause

The previous implementation used **per-profile ticker tracking**:

```python
# OLD - Per-profile tracking only
state['published_tickers_log_by_profile'][profile_id] = set(['AAPL', 'MSFT'])
```

This meant:
- **Profile 1** (Site A) tracks: `['AAPL', 'MSFT']`
- **Profile 2** (Site B) tracks: `['GOOGL', 'TSLA']`

When both profiles try to publish AAPL:
1. Profile 1 checks: "AAPL not in my set" ✅ Proceeds
2. Profile 2 checks: "AAPL not in my set" ✅ Proceeds
3. **RESULT**: AAPL published to BOTH sites! ❌

## Solution Implemented

### Global Ticker Tracking

Added a **global published tickers tracker** that prevents the same ticker from being published to ANY site on the same day:

```python
# NEW - Global tracking across ALL profiles
state['global_published_tickers_today'] = set(['AAPL', 'MSFT', 'GOOGL'])
```

### How It Works

```
Day 1 - 8:00 AM:
┌─────────────────────────────────────────────────────┐
│ Profile 1 (Site A) wants to publish: AAPL, MSFT    │
│ Profile 2 (Site B) wants to publish: AAPL, GOOGL   │
└─────────────────────────────────────────────────────┘

Profile 1 Processing:
  ├─ Check AAPL: Not in global set ✅ → Publish to Site A
  │  └─ Add AAPL to global_published_tickers_today
  └─ Check MSFT: Not in global set ✅ → Publish to Site A
     └─ Add MSFT to global_published_tickers_today

global_published_tickers_today = {'AAPL', 'MSFT'}

Profile 2 Processing:
  ├─ Check AAPL: Already in global set ❌ → SKIP (prevent duplicate)
  └─ Check GOOGL: Not in global set ✅ → Publish to Site B
     └─ Add GOOGL to global_published_tickers_today

global_published_tickers_today = {'AAPL', 'MSFT', 'GOOGL'}

RESULT: 
✅ AAPL published ONLY to Site A
✅ MSFT published ONLY to Site A
✅ GOOGL published ONLY to Site B
✅ NO DUPLICATES!
```

### Daily Reset

The global tracker resets every day at midnight UTC:

```python
# New day detected
if state.get('last_run_date') != current_date_str:
    state['global_published_tickers_today'] = set()  # Reset for new day
```

This ensures:
- Each ticker can be published once per day across ALL sites
- Fresh start every day
- No carryover blocking

## Code Changes

### 1. State Initialization (`auto_publisher.py`)

```python
# Added global tracker to default state
default_state['global_published_tickers_today'] = set()
```

### 2. Daily Reset (`auto_publisher.py`)

```python
# Reset on new day
if state.get('last_run_date') != current_date_str:
    # ... existing resets ...
    state['global_published_tickers_today'] = set()  # NEW
```

### 3. Duplicate Check (`auto_publisher.py`)

```python
# Check global tracker BEFORE per-profile check
state.setdefault('global_published_tickers_today', set())
if ticker_to_process in state['global_published_tickers_today']:
    # SKIP - Already published globally today
    msg = f"Ticker '{ticker_to_process}' already published globally today"
    final_post_status = "Skipped - Already Published Globally"
    continue  # Don't generate article

# Then check per-profile (for same-profile duplicates)
if ticker_to_process in state['published_tickers_log_by_profile'][profile_id]:
    # SKIP - Already published on this specific profile
```

### 4. Add to Global Set on Success (`auto_publisher.py`)

```python
if created_post_id:  # Post successfully scheduled
    # Add to per-profile tracker
    state['published_tickers_log_by_profile'][profile_id].add(ticker_to_process)
    
    # Add to GLOBAL tracker (NEW)
    state['global_published_tickers_today'].add(ticker_to_process)
    logger.info(f"Added {ticker_to_process} to global published list")
```

### 5. Firestore Persistence (`firestore_state_manager.py`)

```python
# Default state includes global tracker
state['global_published_tickers_today'] = []  # List for Firestore

# Convert list to set when loading
if 'global_published_tickers_today' in state_data:
    state_data['global_published_tickers_today'] = set(state_data['global_published_tickers_today'])

# Convert set to list when saving (automatic in _sanitize_state_for_firestore)
```

## Benefits

✅ **No Duplicate Content** - Same ticker published to only ONE site per day
✅ **SEO Protection** - No duplicate content penalties from Google
✅ **Resource Efficiency** - Each article generated only once
✅ **Better Distribution** - Different sites get different content
✅ **Scalable** - Works with unlimited number of profiles/sites

## Testing

### Test Case 1: Same Ticker, Multiple Sites

```python
# Setup
profiles = [
    {"profile_id": "site_a", "article_type": "earnings"},
    {"profile_id": "site_b", "article_type": "earnings"}
]

custom_tickers = {
    "site_a": ["AAPL", "MSFT"],
    "site_b": ["AAPL", "GOOGL"]  # AAPL overlaps
}

# Run
trigger_publishing_run(...)

# Expected Result
# Site A: AAPL ✅, MSFT ✅
# Site B: AAPL ❌ (skipped), GOOGL ✅
```

### Test Case 2: Sequential Processing

```python
# Day 1
Profile 1 publishes: AAPL, MSFT, GOOGL
global_set = {'AAPL', 'MSFT', 'GOOGL'}

# Day 1 (later)
Profile 2 tries to publish: AAPL, TSLA
Result: 
  - AAPL skipped (already in global set)
  - TSLA published ✅
global_set = {'AAPL', 'MSFT', 'GOOGL', 'TSLA'}

# Day 2 (new day - reset)
global_set = {}  # Reset
Profile 1 can now publish: AAPL ✅ (fresh day)
```

### Test Case 3: Firestore Persistence

```python
# Session 1
publish AAPL to Site A
Save to Firestore: global_published_tickers_today = ['AAPL']

# Session 2 (app restart)
Load from Firestore
Convert to set: global_published_tickers_today = {'AAPL'}
Try to publish AAPL to Site B
Result: SKIPPED ✅ (global tracker persisted)
```

## Monitoring

### Logs to Watch

```
[GLOBAL_TRACKER] Added AAPL to global published list. Total global: 1
[DUPLICATE_PREVENTION] Ticker 'AAPL' already published globally today (on another site)
```

### State Inspection

```python
# Check current global state
state['global_published_tickers_today']
# Output: {'AAPL', 'MSFT', 'GOOGL', 'TSLA'}

# Check per-profile state
state['published_tickers_log_by_profile']['site_a']
# Output: {'AAPL', 'MSFT'}

state['published_tickers_log_by_profile']['site_b']
# Output: {'GOOGL', 'TSLA'}
```

## Migration Notes

### Existing States

- Old states without `global_published_tickers_today` will auto-initialize to empty set
- No manual migration required
- First run will create the field automatically

### Backward Compatibility

- ✅ Works with existing per-profile tracking
- ✅ Compatible with Firestore and pickle state files
- ✅ No breaking changes to API or configuration

## Additional Fix

### Duplicate `elif` Bug

Also fixed a code bug where `elif GEMINI_ARTICLE_SYSTEM_AVAILABLE:` appeared twice in succession, which could cause unexpected behavior.

**Before:**
```python
elif GEMINI_ARTICLE_SYSTEM_AVAILABLE:
    # Stock analysis
elif GEMINI_ARTICLE_SYSTEM_AVAILABLE:  # DUPLICATE!
    # Stock analysis (again)
```

**After:**
```python
elif GEMINI_ARTICLE_SYSTEM_AVAILABLE:
    # Stock analysis (once)
```

## Summary

This fix ensures that when multiple sites are configured:
1. ✅ Each ticker is published to **ONLY ONE SITE per day**
2. ✅ No duplicate content across sites
3. ✅ Sequential processing completes one profile before starting next
4. ✅ Global tracking persists across sessions (Firestore)
5. ✅ Automatic daily reset for fresh content distribution

The implementation maintains **full backward compatibility** while adding robust duplicate prevention.
