# Quota System - Phase 1 Implementation

## Overview

Phase 1 of the quota system implements user quota tracking and limits for **stock analysis reports** only. This provides the foundational infrastructure that can be extended for other resource types (automation, articles) in future phases.

## Subscription Plans

| Plan | Stock Reports/Month | Price |
|------|---------------------|-------|
| **Free** | 10 | $0 |
| **Pro** | 45 | $29/month |
| **Pro+** | 100 | $79/month |
| **Enterprise** | Unlimited | $299/month |

## What's Included

### ✅ Core Components

1. **QuotaService** - Main service for quota management
   - Check quota availability
   - Consume quota atomically
   - Track usage history
   - Monthly quota resets
   - In-memory caching for performance

2. **Data Models** - Firestore document schemas
   - `UserQuota` - User quota limits and current usage
   - `UsageHistory` - Detailed usage tracking per month
   - `QuotaLimits` - Quota limit configurations
   - `CurrentUsage` - Real-time usage counters

3. **Firestore Integration**
   - Security rules (users can only read their own quotas)
   - Composite indexes for efficient queries
   - Atomic transactions for quota consumption

4. **Migration Scripts**
   - Initialize quotas for existing users
   - Monthly quota reset automation
   - Firestore index deployment

5. **Unit Tests**
   - 90%+ test coverage
   - Tests for all core functionality
   - Performance tests

## Installation & Setup

### Step 1: Install Dependencies

All required dependencies should already be installed in your project. The quota system uses:
- `firebase-admin` (for Firestore)
- Standard Python libraries

### Step 2: Deploy Firestore Configuration

Deploy the Firestore indexes and security rules:

```bash
# Option 1: Use the init script
cd tickzen2
python scripts/init_quota_indexes.py

# Option 2: Deploy manually
firebase deploy --only firestore:indexes
firebase deploy --only firestore:rules
```

### Step 3: Migrate Existing Users

Initialize quota documents for all existing users:

```bash
# Dry run first (shows what would be done)
python scripts/migrate_user_quotas.py

# Execute the migration
python scripts/migrate_user_quotas.py --execute

# Verify migration
python scripts/migrate_user_quotas.py --verify
```

### Step 4: Test the System

Run the unit tests to ensure everything is working:

```bash
cd testing/test_quota
python test_quota_service.py
```

## Usage

### Basic Usage in Your Application

```python
from app.services.quota_service import get_quota_service, QuotaExceededException
from app.models.quota_models import ResourceType

# Get the quota service
quota_service = get_quota_service()

# Check if user has quota available
user_uid = "user_123"
has_quota, quota_info = quota_service.check_quota(
    user_uid, 
    ResourceType.STOCK_REPORT.value
)

if has_quota:
    print(f"User has {quota_info['remaining']} reports remaining")
    
    # Generate the stock report
    # ... your report generation code ...
    
    # Consume the quota
    metadata = {
        'ticker': 'AAPL',
        'status': 'success',
        'generation_time_ms': 1234,
        'report_id': 'report_xyz'
    }
    
    try:
        result = quota_service.consume_quota(
            user_uid,
            ResourceType.STOCK_REPORT.value,
            metadata
        )
        print(f"Quota consumed successfully: {result}")
    except QuotaExceededException as e:
        print(f"Quota exceeded: {e}")
else:
    print(f"Quota exceeded. Used: {quota_info['used']}/{quota_info['limit']}")
```

### Integration with Flask Routes

Example integration with a stock analysis route:

```python
from flask import Blueprint, request, jsonify, g
from app.services.quota_service import get_quota_service, QuotaExceededException
from app.models.quota_models import ResourceType

stock_bp = Blueprint('stock', __name__)
quota_service = get_quota_service()

@stock_bp.route('/start-analysis', methods=['POST'])
def start_analysis():
    # Get user ID (from session/auth)
    user_uid = g.current_user.uid
    ticker = request.json.get('ticker')
    
    # Check quota BEFORE generating report
    has_quota, quota_info = quota_service.check_quota(
        user_uid,
        ResourceType.STOCK_REPORT.value
    )
    
    if not has_quota:
        return jsonify({
            'error': 'Quota exceeded',
            'quota_info': quota_info,
            'message': f"You've used all {quota_info['limit']} reports this month. "
                      f"Upgrade your plan for more reports."
        }), 403
    
    try:
        # Generate the stock report
        report = generate_stock_report(ticker)
        
        # Consume quota AFTER successful generation
        metadata = {
            'ticker': ticker,
            'status': 'success',
            'report_id': report.id,
            'generation_time_ms': report.generation_time
        }
        
        quota_service.consume_quota(
            user_uid,
            ResourceType.STOCK_REPORT.value,
            metadata
        )
        
        # Return success with quota info
        return jsonify({
            'success': True,
            'report': report.to_dict(),
            'quota_remaining': quota_info['remaining'] - 1
        })
        
    except QuotaExceededException as e:
        # Race condition: quota was consumed between check and consume
        return jsonify({
            'error': 'Quota exceeded',
            'message': 'Quota limit reached'
        }), 403
    except Exception as e:
        # Report generation failed - don't consume quota
        return jsonify({
            'error': 'Report generation failed',
            'message': str(e)
        }), 500
```

## API Reference

### QuotaService Methods

#### `check_quota(user_uid: str, resource_type: str) -> Tuple[bool, Dict]`

Check if user has quota available.

**Parameters:**
- `user_uid`: User's unique identifier
- `resource_type`: Type of resource (use `ResourceType.STOCK_REPORT.value`)

**Returns:**
- `has_quota`: Boolean indicating if quota is available
- `quota_info`: Dictionary with quota details:
  ```python
  {
      'has_quota': True,
      'limit': 10,
      'used': 5,
      'remaining': 5,
      'unlimited': False,
      'plan_type': 'free',
      'period_end': '2026-01-31T23:59:59+00:00',
      'check_time_ms': 45
  }
  ```

#### `consume_quota(user_uid: str, resource_type: str, metadata: Dict) -> Dict`

Consume quota for a resource (atomic operation).

**Parameters:**
- `user_uid`: User's unique identifier
- `resource_type`: Type of resource
- `metadata`: Additional metadata about the usage
  ```python
  {
      'ticker': 'AAPL',
      'status': 'success',
      'report_id': 'xyz',
      'generation_time_ms': 1234
  }
  ```

**Returns:**
```python
{
    'success': True,
    'user_uid': 'user_123',
    'resource_type': 'stock_report',
    'quota_used': {'stock_reports': 6},
    'quota_limits': {'stock_reports_monthly': 10},
    'consumption_time_ms': 150
}
```

**Raises:**
- `QuotaExceededException`: If quota is exceeded

#### `get_usage_stats(user_uid: str, period: str = None) -> Dict`

Get detailed usage statistics for a user.

**Parameters:**
- `user_uid`: User's unique identifier
- `period`: Period in 'YYYY-MM' format (defaults to current month)

**Returns:**
```python
{
    'user_uid': 'user_123',
    'plan_type': 'free',
    'period': '2026-01',
    'quota_limits': {'stock_reports_monthly': 10},
    'current_usage': {'stock_reports': 5},
    'period_start': '2026-01-01T00:00:00+00:00',
    'period_end': '2026-01-31T23:59:59+00:00',
    'lifetime_stats': {
        'total_stock_reports': 25,
        'member_since': '2025-12-01T00:00:00+00:00'
    },
    'history': {
        'daily_stats': {
            '2026-01-13': {'stock_reports': 2},
            '2026-01-14': {'stock_reports': 3}
        },
        'summary': {
            'total_stock_reports': 5,
            'peak_usage_day': '2026-01-14',
            'avg_daily_usage': 2.5
        }
    }
}
```

#### `get_remaining_quota(user_uid: str, resource_type: str) -> int`

Get remaining quota count.

**Returns:**
- Remaining quota count (or -1 if unlimited)

#### `reset_monthly_quota(user_uid: str) -> bool`

Reset monthly quota for a user. This is automatically called at the start of each month.

#### `update_user_plan(user_uid: str, new_plan: str) -> bool`

Update user's subscription plan.

**Parameters:**
- `user_uid`: User's unique identifier
- `new_plan`: New plan type ('free', 'pro', 'pro_plus', 'enterprise')

#### `initialize_user_quota(user_uid: str, plan_type: str = None) -> UserQuota`

Initialize quota for a new user (automatically called during user registration).

## Database Schema

### Collection: `userQuotas/{userId}`

```javascript
{
  user_uid: "string",
  plan_type: "free" | "pro" | "pro_plus" | "enterprise",
  plan_updated_at: timestamp,
  
  quota_limits: {
    stock_reports_monthly: 10
  },
  
  current_usage: {
    stock_reports: 5
  },
  
  current_period_start: timestamp,
  current_period_end: timestamp,
  last_reset: timestamp,
  
  created_at: timestamp,
  updated_at: timestamp,
  
  is_suspended: false,
  suspension_reason: null,
  
  lifetime_stats: {
    total_stock_reports: 25,
    member_since: timestamp
  }
}
```

### SubCollection: `userQuotas/{userId}/usage_history/{year_month}`

```javascript
{
  period: "2026-01",
  user_uid: "string",
  
  stock_reports: [
    {
      ticker: "AAPL",
      timestamp: timestamp,
      report_id: "string",
      status: "success",
      generation_time_ms: 1234
    }
  ],
  
  daily_stats: {
    "2026-01-13": {
      stock_reports: 2
    }
  },
  
  summary: {
    total_stock_reports: 5,
    peak_usage_day: "2026-01-13",
    avg_daily_usage: 2.5
  }
}
```

## Performance

The quota system is designed for high performance:

- **< 50ms** average quota check latency (with caching)
- **In-memory caching** for frequently accessed quotas (60s TTL)
- **Atomic transactions** prevent race conditions
- **Efficient Firestore indexes** for fast queries

## Monthly Reset

Quotas automatically reset at the start of each month. To manually reset all quotas:

```bash
# Dry run
python scripts/reset_monthly_quotas.py

# Execute reset
python scripts/reset_monthly_quotas.py --execute
```

**Recommended**: Set up a cron job or Cloud Scheduler to run this monthly:
```
0 0 1 * * python /path/to/tickzen2/scripts/reset_monthly_quotas.py --execute
```

## Error Handling

### QuotaExceededException

Raised when user attempts to consume quota that isn't available:

```python
try:
    quota_service.consume_quota(user_uid, resource_type, metadata)
except QuotaExceededException as e:
    print(f"Quota exceeded: {e}")
    print(f"Quota info: {e.quota_info}")
    # Show upgrade prompt to user
```

### QuotaServiceError

General quota service errors:

```python
try:
    quota_service.check_quota(user_uid, resource_type)
except QuotaServiceError as e:
    print(f"Quota service error: {e}")
    # Log error and show user a friendly message
```

## Security

- ✅ Users can only read their own quota data
- ✅ Only server (Admin SDK) can write quota data
- ✅ All quota consumption is atomic (prevents race conditions)
- ✅ Complete audit trail in usage_history
- ✅ Firestore security rules enforced

## Monitoring

### Check Quota Status for a User

```python
quota_service = get_quota_service()
stats = quota_service.get_usage_stats("user_123")
print(f"User has used {stats['current_usage']['stock_reports']} of "
      f"{stats['quota_limits']['stock_reports_monthly']} reports")
```

### Find High-Usage Users

```python
from firebase_admin import firestore

db = firestore.client()
high_usage = db.collection('userQuotas').where('current_usage.stock_reports', '>=', 8).get()

for doc in high_usage:
    data = doc.to_dict()
    print(f"User {data['user_uid']} has used {data['current_usage']['stock_reports']} reports")
```

## Next Steps (Future Phases)

Phase 1 focuses on stock analysis reports. Future phases will add:

- **Phase 2**: Stock analysis integration with UI
- **Phase 3**: Automation quotas (earnings, sports, general articles)
- **Phase 4**: User dashboard and quota widgets
- **Phase 5**: Admin dashboard and monitoring

## Troubleshooting

### User doesn't have quota document

If a user doesn't have a quota document, it will be automatically created with the default (free) plan when they first check or consume quota.

### Quota not resetting monthly

Ensure the monthly reset script is scheduled to run. Quotas are also automatically reset if accessed after the period end date.

### Cache issues

If you notice stale quota data, invalidate the cache:

```python
quota_service._invalidate_cache(user_uid)
```

Or disable caching temporarily:

```python
quota = quota_service.get_user_quota(user_uid, use_cache=False)
```

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Run unit tests to verify functionality
3. Check Firestore console for data integrity
4. Review security rules if permission errors occur

---

**Last Updated**: January 13, 2026  
**Version**: 1.0.0  
**Phase**: 1 - Core Foundation
