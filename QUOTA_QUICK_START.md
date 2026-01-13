# Quota System - Quick Start Guide

## Phase 1: Stock Analysis Quotas

This guide will help you get the quota system up and running in 5 minutes.

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Deploy Firestore Configuration (2 min)

```bash
cd tickzen2

# Deploy indexes and security rules
firebase deploy --only firestore:indexes
firebase deploy --only firestore:rules
```

### Step 2: Migrate Existing Users (2 min)

```bash
# Preview what will happen (dry run)
python scripts/migrate_user_quotas.py

# Execute the migration
python scripts/migrate_user_quotas.py --execute

# Verify all users have quotas
python scripts/migrate_user_quotas.py --verify
```

### Step 3: Test It (1 min)

```bash
# Run unit tests
python -m pytest testing/test_quota/test_quota_service.py -v

# Should see: 18 passed
```

---

## 💡 Basic Usage

### Check if User Has Quota

```python
from app.services.quota_service import get_quota_service
from app.models.quota_models import ResourceType

quota_service = get_quota_service()

has_quota, info = quota_service.check_quota(
    user_uid="user_123",
    resource_type=ResourceType.STOCK_REPORT.value
)

if has_quota:
    print(f"✅ User has {info['remaining']} reports remaining")
else:
    print(f"❌ Quota exceeded: {info['used']}/{info['limit']}")
```

### Consume Quota After Generating Report

```python
from app.services.quota_service import get_quota_service, QuotaExceededException

quota_service = get_quota_service()

try:
    # After successfully generating the report
    quota_service.consume_quota(
        user_uid="user_123",
        resource_type=ResourceType.STOCK_REPORT.value,
        metadata={
            'ticker': 'AAPL',
            'status': 'success',
            'report_id': 'report_xyz'
        }
    )
    print("✅ Quota consumed")
except QuotaExceededException as e:
    print(f"❌ Quota exceeded: {e}")
```

---

## 📊 Subscription Plans

| Plan | Reports/Month | Price |
|------|---------------|-------|
| Free | 10 | $0 |
| Pro | 45 | $29 |
| Pro+ | 100 | $79 |
| Enterprise | Unlimited | $299 |

---

## 🔧 Common Tasks

### Get User's Usage Stats

```python
stats = quota_service.get_usage_stats("user_123")
print(f"Used: {stats['current_usage']['stock_reports']}")
print(f"Limit: {stats['quota_limits']['stock_reports_monthly']}")
print(f"Plan: {stats['plan_type']}")
```

### Upgrade User's Plan

```python
quota_service.update_user_plan("user_123", "pro")
print("✅ User upgraded to Pro plan (45 reports/month)")
```

### Initialize Quota for New User

```python
quota_service.initialize_user_quota("new_user_456", "free")
print("✅ Quota initialized for new user")
```

---

## 🎯 Integration Example

### Flask Route Integration

```python
@app.route('/start-analysis', methods=['POST'])
def start_analysis():
    user_uid = g.current_user.uid
    ticker = request.json.get('ticker')
    
    # 1. Check quota BEFORE generating report
    has_quota, info = quota_service.check_quota(
        user_uid, 
        ResourceType.STOCK_REPORT.value
    )
    
    if not has_quota:
        return jsonify({
            'error': 'Quota exceeded',
            'message': f"You've used all {info['limit']} reports this month.",
            'upgrade_url': '/upgrade'
        }), 403
    
    # 2. Generate the report
    report = generate_stock_report(ticker)
    
    # 3. Consume quota AFTER success
    quota_service.consume_quota(
        user_uid,
        ResourceType.STOCK_REPORT.value,
        {'ticker': ticker, 'status': 'success', 'report_id': report.id}
    )
    
    return jsonify({
        'success': True,
        'report': report.to_dict(),
        'quota_remaining': info['remaining'] - 1
    })
```

---

## 📅 Monthly Reset

Quotas automatically reset at the start of each month.

### Manual Reset (if needed)

```bash
# Dry run (preview)
python scripts/reset_monthly_quotas.py

# Execute reset
python scripts/reset_monthly_quotas.py --execute
```

### Automate with Cron

```bash
# Run on 1st of every month at midnight
0 0 1 * * cd /path/to/tickzen2 && python scripts/reset_monthly_quotas.py --execute
```

---

## ❓ Troubleshooting

### User doesn't have quota document?

No problem! It will be created automatically on first use:

```python
quota = quota_service.get_user_quota("user_123")
if not quota:
    quota = quota_service.initialize_user_quota("user_123", "free")
```

### Need to check quota without consuming?

```python
remaining = quota_service.get_remaining_quota(
    "user_123", 
    ResourceType.STOCK_REPORT.value
)
print(f"User has {remaining} reports left")
```

### Cache issues?

Invalidate the cache:

```python
quota_service._invalidate_cache("user_123")
```

---

## 📚 Full Documentation

For complete documentation, see:
- **QUOTA_SYSTEM_README.md** - Complete usage guide
- **QUOTA_SYSTEM_PHASE1_SUMMARY.md** - Implementation summary
- **QUOTA_SYSTEM_IMPLEMENTATION_PLAN.md** - Full project plan

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Firestore indexes deployed
- [ ] Security rules deployed
- [ ] All existing users migrated
- [ ] Unit tests passing (18/18)
- [ ] Can check quota successfully
- [ ] Can consume quota successfully
- [ ] Quota limits enforced correctly

---

**That's it! You're ready to use the quota system.**

For questions or issues, check the full documentation or the test files for examples.

---

**Quick Links**:
- [Full Documentation](QUOTA_SYSTEM_README.md)
- [API Reference](QUOTA_SYSTEM_README.md#api-reference)
- [Database Schema](QUOTA_SYSTEM_README.md#database-schema)
- [Error Handling](QUOTA_SYSTEM_README.md#error-handling)
