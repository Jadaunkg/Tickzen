# Quota System Implementation Plan
## User Usage Tracking & Limits System

**Project**: Tickzen Quota & Usage Tracking System  
**Start Date**: January 13, 2026  
**Estimated Duration**: 5 weeks  
**Priority**: High  
**Status**: Planning Phase

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Phase-by-Phase Implementation](#phase-by-phase-implementation)
4. [Testing Strategy](#testing-strategy)
5. [Security Considerations](#security-considerations)
6. [Rollout Plan](#rollout-plan)

---

## Overview

### Objectives
- Implement per-user quota limits for stock analysis reports and automated articles
- Track usage metrics across different content categories
- Provide real-time quota checking with minimal performance impact
- Support multiple subscription tiers (Free, Premium, Enterprise)
- Enable admin oversight and quota management

### Success Metrics
- ✅ 100% quota enforcement accuracy
- ✅ < 50ms quota check latency
- ✅ Zero quota bypass incidents
- ✅ 99.9% uptime for quota service
- ✅ Complete audit trail of all usage

### Resources Tracked
1. **Stock Analysis Reports** (per month)
2. **Earnings Articles** (per month)
3. **Sports Articles** (per month)
4. **General Articles** (per month)
5. **Total Articles** (aggregate per month)

---

## System Architecture

### Database Schema

#### Collection: `userQuotas/{userId}`
```javascript
{
  user_uid: "string",
  plan_type: "free" | "premium" | "enterprise",
  plan_updated_at: timestamp,
  
  // Quota Limits
  quota_limits: {
    stock_reports_monthly: 10,
    articles_monthly: 50,
    earnings_articles_monthly: 20,
    sports_articles_monthly: 30,
    general_articles_monthly: 20
  },
  
  // Current Usage (resets monthly)
  current_usage: {
    stock_reports: 0,
    articles_total: 0,
    earnings_articles: 0,
    sports_articles: 0,
    general_articles: 0
  },
  
  // Period Tracking
  current_period_start: timestamp,  // First day of month
  current_period_end: timestamp,    // Last day of month
  last_reset: timestamp,
  
  // Metadata
  created_at: timestamp,
  updated_at: timestamp,
  
  // Flags
  is_suspended: false,
  suspension_reason: null,
  
  // Statistics
  lifetime_stats: {
    total_stock_reports: 0,
    total_articles: 0,
    member_since: timestamp
  }
}
```

#### SubCollection: `userQuotas/{userId}/usage_history/{year_month}`
```javascript
{
  period: "2026-01",
  user_uid: "string",
  
  // Detailed Usage Lists
  stock_reports: [
    {
      ticker: "AAPL",
      timestamp: timestamp,
      report_id: "string",
      status: "success" | "failed",
      generation_time_ms: 1234
    }
  ],
  
  articles: [
    {
      category: "earnings" | "sports" | "general",
      ticker: "TSLA",  // null for sports
      timestamp: timestamp,
      article_id: "string",
      profile_id: "string",
      profile_name: "string",
      status: "published" | "failed"
    }
  ],
  
  // Daily Aggregates
  daily_stats: {
    "2026-01-13": {
      stock_reports: 2,
      articles: 5,
      earnings_articles: 2,
      sports_articles: 2,
      general_articles: 1
    }
  },
  
  // Monthly Summary
  summary: {
    total_stock_reports: 5,
    total_articles: 15,
    total_earnings: 8,
    total_sports: 5,
    total_general: 2,
    peak_usage_day: "2026-01-13",
    avg_daily_usage: 2.5
  },
  
  created_at: timestamp,
  updated_at: timestamp
}
```

#### Collection: `quotaPlans` (Configuration)
```javascript
{
  plan_id: "free",
  display_name: "Free Plan",
  
  limits: {
    stock_reports_monthly: 10,
    articles_monthly: 50,
    earnings_articles_monthly: 20,
    sports_articles_monthly: 30,
    general_articles_monthly: 20
  },
  
  features: [
    "Basic stock analysis",
    "Limited automation",
    "Standard support"
  ],
  
  price_monthly: 0,
  is_active: true,
  created_at: timestamp,
  updated_at: timestamp
}
```

### Firestore Indexes Required
```javascript
// Composite Indexes
userQuotas:
  - user_uid (ASC) + current_period_start (DESC)
  - plan_type (ASC) + created_at (DESC)
  - is_suspended (ASC) + user_uid (ASC)

usage_history:
  - user_uid (ASC) + period (DESC)
  - category (ASC) + timestamp (DESC)
```

### Firestore Security Rules
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // User Quotas - Users can only read their own
    match /userQuotas/{userId} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if false;  // Only server (Admin SDK) can write
    }
    
    // Usage History - Users can only read their own
    match /userQuotas/{userId}/usage_history/{document=**} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if false;  // Only server (Admin SDK) can write
    }
    
    // Quota Plans - All authenticated users can read
    match /quotaPlans/{planId} {
      allow read: if request.auth != null;
      allow write: if false;  // Only admin
    }
  }
}
```

---

## Phase-by-Phase Implementation

### PHASE 1: Foundation & Core Service (Week 1)
**Duration**: 5 days  
**Status**: ✅ COMPLETE (January 13, 2026)

#### Tasks

##### Day 1-2: Setup & Configuration
- [x] Create directory structure (`app/services/`, `config/`)
- [x] Define quota plans in `config/quota_plans.py`
- [x] Create data models in `app/models/quota_models.py`
- [x] Setup Firestore indexes
- [x] Configure security rules

**Files to Create:**
```
tickzen2/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   └── quota_service.py
│   └── models/
│       └── quota_models.py
├── config/
│   └── quota_plans.py
└── scripts/
    └── init_quota_indexes.py
```

##### Day 3-4: Core Quota Service
- [x] Implement `QuotaService` class
  - [x] `check_quota(user_uid, resource_type, category=None)`
  - [x] `consume_quota(user_uid, resource_type, metadata, category=None)`
  - [x] `get_usage_stats(user_uid, period=None)`
  - [x] `get_remaining_quota(user_uid, resource_type)`
  - [x] `reset_monthly_quota(user_uid)`
- [x] Add in-memory caching layer
- [x] Implement atomic transactions
- [x] Add error handling and logging

##### Day 5: User Initialization
- [x] Create `initialize_user_quota()` function
- [x] Hook into user registration flow
- [x] Build migration script for existing users
- [x] Run migration on development database

#### Deliverables
- ✅ Working `QuotaService` class
- ✅ Database schema implemented
- ✅ All existing users have quota documents (migration script ready)
- ✅ Unit tests passing (18/18 tests)

#### Testing Strategy - Phase 1

**Unit Tests** (`tests/test_quota_service.py`)
```python
def test_check_quota_within_limit()
def test_check_quota_at_limit()
def test_check_quota_exceeded()
def test_consume_quota_success()
def test_consume_quota_atomic_transaction()
def test_consume_quota_concurrent_requests()
def test_get_usage_stats()
def test_reset_monthly_quota()
def test_cache_performance()
def test_invalid_resource_type()
def test_unlimited_quota()
```

**Integration Tests**
```python
def test_firestore_quota_creation()
def test_firestore_quota_update()
def test_firestore_transaction_rollback()
def test_usage_history_creation()
```

**Performance Tests**
```python
def test_quota_check_latency()  # Target: < 50ms
def test_concurrent_consumption()  # 100 simultaneous requests
def test_cache_hit_rate()  # Target: > 80%
```

**Test Coverage Target**: 90%+

---

### PHASE 2: Stock Analysis Integration (Week 2)
**Duration**: 5 days  
**Status**: Not Started

#### Tasks

##### Day 1-2: Integration Points
- [ ] Add quota decorator `@quota_required()`
- [ ] Integrate with `/start-analysis` route
- [ ] Add quota check before analysis starts
- [ ] Consume quota after successful report generation
- [ ] Handle quota exceeded errors gracefully

##### Day 3: Error Handling & UX
- [ ] Create quota error response format
- [ ] Add notification messages for quota limits
- [ ] Show remaining quota in analyzer page
- [ ] Add "upgrade" prompts when quota exceeded
- [ ] Implement retry logic for transient failures

##### Day 4: Usage Tracking
- [ ] Track report generation in usage_history
- [ ] Store metadata (ticker, timestamp, status)
- [ ] Calculate generation time
- [ ] Update daily stats

##### Day 5: Testing & Refinement
- [ ] Run integration tests
- [ ] Performance testing
- [ ] User acceptance testing
- [ ] Bug fixes and optimization

#### Deliverables
- ✅ Stock analysis fully integrated with quota system
- ✅ Users see quota status in UI
- ✅ Quota exceeded handled gracefully
- ✅ All tests passing

#### Testing Strategy - Phase 2

**Integration Tests**
```python
def test_stock_analysis_with_quota_available()
def test_stock_analysis_quota_exceeded()
def test_stock_analysis_consumes_quota_on_success()
def test_stock_analysis_no_consumption_on_failure()
def test_concurrent_stock_analyses()
def test_quota_reset_during_analysis()
```

**End-to-End Tests**
```python
def test_user_workflow_within_quota()
def test_user_workflow_exceeds_quota()
def test_quota_message_displayed()
def test_upgrade_prompt_shown()
```

**Performance Tests**
```python
def test_analysis_latency_with_quota_check()  # Max 10% overhead
def test_throughput_with_quota()  # 100 requests/minute
```

---

### PHASE 3: Automation Integration (Week 3)
**Duration**: 5 days  
**Status**: Not Started

#### Tasks

##### Day 1: Earnings Automation
- [ ] Integrate quota check in `/run-earnings-automation`
- [ ] Add category-specific tracking (earnings)
- [ ] Handle per-article quota consumption
- [ ] Update quota after bulk operations
- [ ] Test with multiple profiles

##### Day 2: Sports Automation
- [ ] Integrate quota check in `/run-sports-automation`
- [ ] Add category-specific tracking (sports)
- [ ] Handle article selection based on quota
- [ ] Show available quota in sports dashboard
- [ ] Implement partial publishing (if quota runs out mid-batch)

##### Day 3: General Automation
- [ ] Integrate quota check in `/run-automation-now`
- [ ] Add category detection logic
- [ ] Support mixed automation runs
- [ ] Track per-profile usage
- [ ] Handle quota across multiple profiles

##### Day 4: Batch Operations
- [ ] Implement batch quota checking
- [ ] Add pre-flight quota validation
- [ ] Show quota impact before running automation
- [ ] Implement smart batching (respect limits)
- [ ] Add quota reservation system

##### Day 5: Testing & Optimization
- [ ] Integration testing
- [ ] Load testing with automation
- [ ] Edge case handling
- [ ] Performance optimization

#### Deliverables
- ✅ All automation types integrated
- ✅ Category-specific tracking working
- ✅ Batch operations respect quotas
- ✅ UI shows quota impact

#### Testing Strategy - Phase 3

**Integration Tests**
```python
def test_earnings_automation_with_quota()
def test_sports_automation_with_quota()
def test_general_automation_with_quota()
def test_batch_quota_checking()
def test_partial_publishing()
def test_quota_exceeded_during_batch()
def test_multiple_profiles_quota_tracking()
```

**Stress Tests**
```python
def test_bulk_article_publishing()  # 100 articles
def test_concurrent_automation_runs()
def test_quota_under_heavy_load()
```

---

### PHASE 4: UI/UX & User Dashboard (Week 4)
**Duration**: 5 days  
**Status**: Not Started

#### Tasks

##### Day 1-2: User Dashboard Widget
- [ ] Create quota status component
- [ ] Show current usage vs limits
- [ ] Display progress bars for each resource
- [ ] Show quota reset date
- [ ] Add "days until reset" countdown

##### Day 2-3: Integration Points
- [ ] Add quota widget to user profile page
- [ ] Show quota in analyzer page header
- [ ] Display quota in automation dashboards
- [ ] Add quota warnings at 80% usage
- [ ] Implement upgrade prompts

##### Day 3-4: Quota History Page
- [ ] Create `/quota/history` route
- [ ] Show monthly usage trends
- [ ] Display usage breakdown by category
- [ ] Add charts and visualizations
- [ ] Export usage reports (CSV/PDF)

##### Day 5: Polish & Testing
- [ ] UI/UX refinements
- [ ] Mobile responsiveness
- [ ] Accessibility improvements
- [ ] User testing
- [ ] Bug fixes

#### Deliverables
- ✅ Quota dashboard widget
- ✅ Usage history page
- ✅ Real-time quota display
- ✅ Visual progress indicators

#### Testing Strategy - Phase 4

**UI Tests**
```python
def test_quota_widget_displays_correctly()
def test_progress_bars_accurate()
def test_quota_warning_at_80_percent()
def test_upgrade_prompt_on_exceeded()
def test_quota_history_page_loads()
def test_chart_rendering()
```

**Browser Tests** (Selenium/Playwright)
```python
def test_quota_widget_responsive()
def test_real_time_updates()
def test_mobile_display()
def test_accessibility_standards()
```

---

### PHASE 5: Admin Dashboard & Monitoring (Week 5)
**Duration**: 5 days  
**Status**: Not Started

#### Tasks

##### Day 1-2: Admin Dashboard
- [ ] Create `/admin/quota-management` route
- [ ] List all users with quota status
- [ ] Filter by plan type, usage level
- [ ] Search users by email/UID
- [ ] Show high-usage users
- [ ] Display quota abuse detection

##### Day 2-3: Admin Actions
- [ ] Manually adjust user quotas
- [ ] Change user plan types
- [ ] Reset user quotas
- [ ] Suspend/unsuspend users
- [ ] Add quota credits
- [ ] View detailed usage history

##### Day 3-4: Monitoring & Analytics
- [ ] Create quota monitoring dashboard
- [ ] Track quota exceeded events
- [ ] Monitor consumption patterns
- [ ] Alert on unusual usage
- [ ] Generate monthly reports
- [ ] Export analytics data

##### Day 5: Documentation & Training
- [ ] Write admin documentation
- [ ] Create user guide for quota system
- [ ] Prepare training materials
- [ ] Final testing
- [ ] Deployment preparation

#### Deliverables
- ✅ Admin quota management interface
- ✅ Monitoring dashboard
- ✅ Analytics and reporting
- ✅ Complete documentation

#### Testing Strategy - Phase 5

**Admin Tests**
```python
def test_admin_view_all_users()
def test_admin_adjust_quota()
def test_admin_change_plan()
def test_admin_suspend_user()
def test_admin_export_reports()
def test_admin_access_control()
```

**Security Tests**
```python
def test_non_admin_cannot_access()
def test_quota_modification_logged()
def test_admin_action_audit_trail()
```

---

## Testing Strategy

### Testing Pyramid

```
                    /\
                   /  \
                  / E2E \
                 /______\
                /        \
               /Integration\
              /____________\
             /              \
            /   Unit Tests   \
           /__________________\
```

### Test Coverage Requirements

| Component | Unit Tests | Integration Tests | E2E Tests | Coverage Target |
|-----------|-----------|------------------|-----------|-----------------|
| QuotaService | ✅ Required | ✅ Required | ❌ N/A | 95%+ |
| Stock Analysis | ✅ Required | ✅ Required | ✅ Required | 90%+ |
| Automation | ✅ Required | ✅ Required | ✅ Required | 85%+ |
| UI Components | ✅ Required | ❌ N/A | ✅ Required | 80%+ |
| Admin Dashboard | ✅ Required | ✅ Required | ✅ Required | 85%+ |

### Testing Environments

1. **Local Development**: SQLite/Firestore Emulator
2. **Staging**: Real Firestore (separate project)
3. **Production**: Canary deployment (1% → 10% → 100%)

### Test Data

**Test Users**
- `test_free_user@tickzen.com` - Free plan, 5/10 reports used
- `test_premium_user@tickzen.com` - Premium plan, 50/100 reports used
- `test_enterprise_user@tickzen.com` - Enterprise plan, unlimited
- `test_over_quota@tickzen.com` - Free plan, 10/10 reports used
- `test_suspended@tickzen.com` - Suspended account

### Automated Testing

**Continuous Integration** (GitHub Actions)
```yaml
on: [push, pull_request]
jobs:
  test:
    - Run unit tests
    - Run integration tests
    - Check coverage (min 85%)
    - Run security scans
    - Performance benchmarks
```

**Scheduled Tests** (Daily)
- Full E2E test suite
- Load testing
- Database integrity checks
- Quota accuracy verification

---

## Security Considerations

### Access Control
- ✅ Users can only read their own quota data
- ✅ Only Admin SDK can write quota data
- ✅ Admin actions require authentication + authorization
- ✅ All quota modifications are logged

### Data Integrity
- ✅ Atomic transactions prevent race conditions
- ✅ Quota consumption is idempotent
- ✅ Regular integrity checks (cron job)
- ✅ Audit trail for all changes

### Attack Prevention
- ✅ Rate limiting on quota checks
- ✅ Detection of quota abuse patterns
- ✅ Automatic suspension on suspicious activity
- ✅ IP-based rate limiting

### Compliance
- ✅ GDPR compliant (data export, deletion)
- ✅ Usage data retention policy (12 months)
- ✅ Encrypted data at rest
- ✅ Audit logs for compliance

---

## Rollout Plan

### Pre-Launch Checklist
- [ ] All tests passing (coverage > 85%)
- [ ] Security audit completed
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Admin training completed
- [ ] Rollback plan prepared

### Deployment Strategy

**Week 1: Internal Testing**
- Deploy to staging environment
- Internal team testing
- Fix critical bugs

**Week 2: Beta Testing**
- Select 10 beta users
- Monitor usage and feedback
- Iterate on UX

**Week 3: Canary Deployment**
- Deploy to 1% of users
- Monitor metrics closely
- Increase to 10% if stable

**Week 4: Full Rollout**
- Deploy to 50% of users
- Monitor for 48 hours
- Deploy to 100%

### Success Metrics
- Zero quota bypass incidents
- < 0.1% error rate
- < 50ms quota check latency
- > 95% user satisfaction
- Zero data loss

### Rollback Triggers
- Error rate > 1%
- Quota check latency > 200ms
- Data corruption detected
- Security breach

---

## Post-Launch

### Week 1 After Launch
- [ ] Monitor all metrics 24/7
- [ ] Daily team check-ins
- [ ] Quick bug fixes
- [ ] User feedback collection

### Month 1 After Launch
- [ ] Weekly analytics review
- [ ] User behavior analysis
- [ ] Plan optimization based on data
- [ ] Feature improvements

### Ongoing
- [ ] Monthly quota accuracy audits
- [ ] Quarterly plan review
- [ ] Continuous performance optimization
- [ ] Feature enhancements based on feedback

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Quota bypass bug | Medium | High | Extensive testing, code review |
| Performance degradation | Low | Medium | Caching, optimization |
| Data inconsistency | Low | High | Atomic transactions, integrity checks |
| User confusion | Medium | Low | Clear UI, documentation |
| Firestore quota limits | Low | High | Monitoring, optimization |

---

## Resources Required

### Development Team
- 1 Backend Developer (full-time, 5 weeks)
- 1 Frontend Developer (part-time, 2 weeks)
- 1 QA Engineer (part-time, throughout)
- 1 DevOps Engineer (part-time, Week 5)

### Infrastructure
- Firestore database
- Cloud Functions (for scheduled tasks)
- Monitoring tools (Cloud Monitoring)
- Testing environment

### Budget Estimate
- Development: ~200 hours
- Testing: ~80 hours
- Infrastructure: $50/month (estimated)

---

## Success Criteria

### Technical
- ✅ 100% quota enforcement accuracy
- ✅ < 50ms average quota check latency
- ✅ 99.9% uptime
- ✅ Zero quota bypass incidents
- ✅ 90%+ test coverage

### Business
- ✅ Clear path to monetization (plan upgrades)
- ✅ Reduced server costs from abuse prevention
- ✅ Improved user experience
- ✅ Data-driven insights on usage patterns

### User Experience
- ✅ Users understand their quota limits
- ✅ Clear upgrade paths
- ✅ No surprise quota blocks
- ✅ Seamless experience within limits

---

## Appendix

### Key Files Reference
```
app/services/quota_service.py        # Core quota logic
app/decorators.py                    # @quota_required decorator
app/models/quota_models.py           # Data models
config/quota_plans.py                # Plan definitions
scripts/init_user_quotas.py          # Migration script
scripts/reset_monthly_quotas.py      # Cron job
tests/test_quota_service.py          # Unit tests
tests/test_quota_integration.py      # Integration tests
```

### Contact & Support
- **Project Lead**: [Name]
- **Technical Lead**: [Name]
- **QA Lead**: [Name]
- **Documentation**: See `/docs/quota-system/`

---

**Last Updated**: January 13, 2026  
**Version**: 1.0  
**Status**: Planning Complete - Ready for Implementation
