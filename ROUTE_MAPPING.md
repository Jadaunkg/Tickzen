# Route Mapping - Old to New Structure

## Complete Route Transformation Guide

This document maps all existing routes to their new locations in the redesigned navigation structure.

---

## 📊 Route Mapping Table

| Old Route | New Route | Status | Notes |
|-----------|-----------|--------|-------|
| **HOMEPAGE & DASHBOARDS** |
| `/` | `/` | Keep | New homepage with clear feature separation |
| `/dashboard` | `/stock-analysis/dashboard` | Migrate | Stock analysis focused dashboard |
| `/dashboard-analytics` | `/stock-analysis/analytics` | Migrate | Portfolio analytics |
| **STOCK ANALYSIS** |
| `/analyzer` | `/stock-analysis/analyzer` | Migrate | Stock analysis input form |
| `/ai-assistant` | `/stock-analysis/ai-assistant` | Migrate | AI chatbot |
| `/api/dashboard/reports` | `/api/stock-analysis/reports` | Migrate | API for reports |
| N/A | `/stock-analysis/market-news` | New | Dedicated market news page |
| N/A | `/stock-analysis/reports` | New | Report history page |
| **AUTOMATION HUB** |
| N/A | `/automation/overview` | New | Main automation hub |
| **STOCK ANALYSIS AUTOMATION** |
| `/wordpress-automation-portal` | `/automation/stock-analysis/dashboard` | Migrate | Stock automation dashboard |
| `/automation-runner` | `/automation/stock-analysis/run` | Migrate | Run stock automation |
| `/run-automation-now` | `/automation/stock-analysis/execute` | Migrate | POST endpoint for execution |
| `/stop_automation_run/<profile_id>` | `/automation/stock-analysis/stop/<profile_id>` | Migrate | Stop automation |
| `/manage-profiles` | `/automation/stock-analysis/profiles` | Migrate | Manage WordPress profiles |
| N/A | `/automation/stock-analysis/history` | New | Publishing history for stock |
| **EARNINGS AUTOMATION** |
| `/automation-earnings-runner` | `/automation/earnings/run` | Migrate | Run earnings automation |
| `/run-earnings-automation` | `/automation/earnings/execute` | Migrate | POST endpoint |
| `/refresh-earnings-calendar` | `/automation/earnings/refresh-calendar` | Migrate | Refresh calendar |
| N/A | `/automation/earnings/dashboard` | New | Earnings automation dashboard |
| N/A | `/automation/earnings/calendar` | New | Earnings calendar view |
| N/A | `/automation/earnings/history` | New | Publishing history for earnings |
| **SPORTS AUTOMATION** |
| `/automation-sports-runner` | `/automation/sports/run` | Migrate | Run sports automation |
| `/run-sports-automation` | `/automation/sports/execute` | Migrate | POST endpoint |
| `/trends-dashboard` | `/automation/sports/trends` | Migrate | Google Trends dashboard |
| `/refresh-sports-articles` | `/automation/sports/refresh` | Migrate | Refresh articles |
| `/collect-sports-articles` | `/automation/sports/collect` | Migrate | Collect articles |
| `/run-sports-pipeline` | `/automation/sports/pipeline` | Migrate | Run pipeline |
| `/api/sports-articles` | `/automation/sports/api/articles` | Migrate | API endpoint |
| N/A | `/automation/sports/dashboard` | New | Sports automation dashboard |
| N/A | `/automation/sports/library` | New | Content library |
| N/A | `/automation/sports/history` | New | Publishing history for sports |
| **SHARED AUTOMATION** |
| `/publishing-history` | `/automation/history` | Migrate | Combined publishing history |
| `/wp-generator` | `/automation/tools/wp-generator` | Migrate | WordPress asset generator |
| **SETTINGS** |
| `/user-profile` | `/settings/profile` | Migrate | User profile |
| `/edit-profile` | `/settings/profile/edit` | Migrate | Edit profile |
| `/change-password` | `/settings/security/password` | Migrate | Change password |
| N/A | `/settings/wordpress-profiles` | New | WordPress profiles (same as manage-profiles) |
| N/A | `/settings/api` | New | API settings |
| N/A | `/settings/notifications` | New | Notification preferences |
| **AUTHENTICATION** |
| `/login` | `/auth/login` | Migrate | Login page |
| `/register` | `/auth/register` | Migrate | Registration |
| `/logout` | `/auth/logout` | Keep | Logout endpoint |
| **INFO & RESOURCES** |
| `/features/how-it-works` | `/resources/how-it-works` | Migrate | How it works |
| `/features/documentation` | `/resources/documentation` | Migrate | Documentation |
| N/A | `/resources/support` | New | Support page |
| **HEALTH & ADMIN** |
| `/health` | `/api/health` | Keep | Health check |
| `/api/admin/analytics` | `/api/admin/analytics` | Keep | Admin analytics |

---

## 🔄 Backward Compatibility Redirects

All old routes will automatically redirect to new routes. Here's the implementation:

```python
# In main_portal_app.py

# Stock Analysis Redirects
@app.route('/dashboard')
@login_required
def old_dashboard():
    """Redirect old dashboard to new stock analysis dashboard"""
    return redirect(url_for('stock_analysis.dashboard'), code=301)

@app.route('/analyzer')
@login_required
def old_analyzer():
    """Redirect old analyzer to new location"""
    return redirect(url_for('stock_analysis.analyzer'), code=301)

@app.route('/dashboard-analytics')
@login_required
def old_dashboard_analytics():
    """Redirect old analytics to new location"""
    return redirect(url_for('stock_analysis.analytics'), code=301)

@app.route('/ai-assistant')
@login_required
def old_ai_assistant():
    """Redirect old AI assistant to new location"""
    return redirect(url_for('stock_analysis.ai_assistant'), code=301)

# Stock Automation Redirects
@app.route('/wordpress-automation-portal')
@login_required
def old_wordpress_automation_portal():
    """Redirect old WP automation portal to new dashboard"""
    return redirect(url_for('automation.stock_automation.dashboard'), code=301)

@app.route('/automation-runner')
@login_required
def old_automation_runner():
    """Redirect old automation runner to new location"""
    return redirect(url_for('automation.stock_automation.run'), code=301)

@app.route('/manage-profiles')
@login_required
def old_manage_profiles():
    """Redirect old manage profiles to new location"""
    return redirect(url_for('automation.stock_automation.profiles'), code=301)

# Earnings Automation Redirects
@app.route('/automation-earnings-runner')
@login_required
def old_automation_earnings_runner():
    """Redirect old earnings runner to new location"""
    return redirect(url_for('automation.earnings_automation.run'), code=301)

# Sports Automation Redirects
@app.route('/automation-sports-runner')
@login_required
def old_automation_sports_runner():
    """Redirect old sports runner to new location"""
    return redirect(url_for('automation.sports_automation.run'), code=301)

@app.route('/trends-dashboard')
@login_required
def old_trends_dashboard():
    """Redirect old trends dashboard to new location"""
    return redirect(url_for('automation.sports_automation.trends'), code=301)

# Settings Redirects
@app.route('/user-profile')
@login_required
def old_user_profile():
    """Redirect old user profile to new location"""
    return redirect(url_for('settings.profile'), code=301)

@app.route('/edit-profile')
@login_required
def old_edit_profile():
    """Redirect old edit profile to new location"""
    return redirect(url_for('settings.profile_edit'), code=301)

# Publishing History
@app.route('/publishing-history')
@login_required
def old_publishing_history():
    """Redirect to combined automation history"""
    return redirect(url_for('automation.history'), code=301)
```

---

## 📁 Template File Mapping

| Old Template | New Template | Notes |
|-------------|--------------|-------|
| `dashboard.html` | `stock_analysis/dashboard.html` | Stock analysis dashboard |
| `dashboard_analytics.html` | `stock_analysis/analytics.html` | Portfolio analytics |
| `analyzer_input.html` | `stock_analysis/analyzer.html` | Analysis input form |
| `ai_chatbot.html` | `stock_analysis/ai_assistant.html` | AI assistant |
| `market_news_modern_v2.html` | `stock_analysis/market_news.html` | Market news |
| `report_display.html` | `stock_analysis/report_display.html` | Report viewer |
| `automate_homepage.html` | `automation/overview.html` | Automation hub |
| `run_automation_page.html` | `automation/stock_analysis/run.html` | Run stock automation |
| `manage_profiles.html` | `automation/stock_analysis/profiles.html` | Manage profiles |
| `run_automation_earnings.html` | `automation/earnings/run.html` | Run earnings automation |
| `run_automation_sports_improved.html` | `automation/sports/run.html` | Run sports automation |
| `google_trends_dashboard.html` | `automation/sports/trends.html` | Trends dashboard |
| `publishing_history.html` | `automation/history.html` | Publishing history |
| `wp-asset.html` | `automation/tools/wp_generator.html` | WP asset generator |
| `user_profile.html` | `settings/profile.html` | User profile |
| `edit_profile.html` | `settings/profile_edit.html` | Edit profile |
| `change_password.html` | `settings/security_password.html` | Change password |
| N/A | `automation/stock_analysis/dashboard.html` | New stock automation dashboard |
| N/A | `automation/stock_analysis/history.html` | New stock publishing history |
| N/A | `automation/earnings/dashboard.html` | New earnings dashboard |
| N/A | `automation/earnings/calendar.html` | New earnings calendar |
| N/A | `automation/earnings/history.html` | New earnings history |
| N/A | `automation/sports/dashboard.html` | New sports dashboard |
| N/A | `automation/sports/library.html` | New sports library |
| N/A | `automation/sports/history.html` | New sports history |

---

## 🎯 API Endpoint Mapping

### Stock Analysis APIs
```python
# Old → New
/api/dashboard/reports → /api/stock-analysis/reports
/api/analyze → /api/stock-analysis/analyze
/api/ticker-status → /api/stock-analysis/ticker-status
/api/report/<ticker> → /api/stock-analysis/report/<ticker>
```

### Automation APIs
```python
# Stock Automation
/run-automation-now → /api/automation/stock-analysis/execute
/stop_automation_run/<profile_id> → /api/automation/stock-analysis/stop/<profile_id>

# Earnings Automation
/run-earnings-automation → /api/automation/earnings/execute
/refresh-earnings-calendar → /api/automation/earnings/refresh-calendar

# Sports Automation
/run-sports-automation → /api/automation/sports/execute
/refresh-sports-articles → /api/automation/sports/refresh
/collect-sports-articles → /api/automation/sports/collect
/api/sports-articles → /api/automation/sports/articles
```

### Shared APIs
```python
/api/profiles → /api/automation/profiles
/api/publishing-history → /api/automation/history
```

---

## 🔧 URL Generation Updates

### In Templates
Old:
```html
<a href="{{ url_for('analyzer_input_page') }}">Analyze Stock</a>
<a href="{{ url_for('automation_runner_page') }}">Run Automation</a>
```

New:
```html
<a href="{{ url_for('stock_analysis.analyzer') }}">Analyze Stock</a>
<a href="{{ url_for('automation.stock_automation.run') }}">Run Automation</a>
```

### In Python Code
Old:
```python
return redirect(url_for('automation_runner_page'))
flash_link = url_for('dashboard')
```

New:
```python
return redirect(url_for('automation.stock_automation.run'))
flash_link = url_for('stock_analysis.dashboard')
```

---

## 📋 Implementation Steps

### Step 1: Create Blueprint Files (Week 1)
```
app/blueprints/
├── __init__.py
├── stock_analysis.py          # Stock analysis blueprint
├── automation.py               # Automation hub blueprint
├── automation_stock.py         # Stock automation sub-blueprint
├── automation_earnings.py      # Earnings automation sub-blueprint
├── automation_sports.py        # Sports automation sub-blueprint
└── settings.py                 # Settings blueprint
```

### Step 2: Register Blueprints (Week 1)
```python
# In main_portal_app.py
from app.blueprints.stock_analysis import stock_analysis_bp
from app.blueprints.automation import automation_bp
from app.blueprints.settings import settings_bp

app.register_blueprint(stock_analysis_bp)
app.register_blueprint(automation_bp)
app.register_blueprint(settings_bp)
```

### Step 3: Move Templates (Week 2)
```bash
# Create new template structure
mkdir -p app/templates/stock_analysis
mkdir -p app/templates/automation/stock_analysis
mkdir -p app/templates/automation/earnings
mkdir -p app/templates/automation/sports
mkdir -p app/templates/settings

# Move existing templates
mv app/templates/dashboard.html app/templates/stock_analysis/
mv app/templates/analyzer_input.html app/templates/stock_analysis/analyzer.html
mv app/templates/run_automation_page.html app/templates/automation/stock_analysis/run.html
# ... etc
```

### Step 4: Update All url_for References (Week 2)
Use find & replace:
```bash
# Find all url_for references
grep -r "url_for('analyzer_input_page')" app/templates/
grep -r "url_for('automation_runner_page')" app/templates/

# Update them
# Old: url_for('analyzer_input_page')
# New: url_for('stock_analysis.analyzer')
```

### Step 5: Add Redirects (Week 3)
Implement all backward compatibility redirects

### Step 6: Update Documentation (Week 3)
- Update README
- Update API documentation
- Update user guides

### Step 7: Testing (Week 4)
- Test all old routes redirect correctly
- Test all new routes work
- Test all links in templates
- Test API endpoints
- User acceptance testing

---

## ✅ Validation Checklist

Before going live, verify:

- [ ] All old routes redirect to correct new routes
- [ ] No broken links in templates
- [ ] All url_for() calls updated
- [ ] All API endpoints work
- [ ] Authentication works on new routes
- [ ] SocketIO events still work
- [ ] Firebase integration intact
- [ ] Mobile navigation works
- [ ] Breadcrumbs display correctly
- [ ] Sidebar navigation works
- [ ] Color coding applied
- [ ] SEO meta tags updated
- [ ] Analytics tracking updated
- [ ] Error handling works
- [ ] Form submissions work
- [ ] File uploads work
- [ ] WebSocket connections work
- [ ] Session management works
- [ ] CSRF protection works
- [ ] Rate limiting works
- [ ] All tests pass

---

## 🚨 Potential Issues & Solutions

### Issue 1: Hardcoded URLs in JavaScript
**Problem**: JavaScript files may have hardcoded URLs
**Solution**: Update all JS files to use new routes
```javascript
// Old
const url = '/automation-runner';

// New
const url = '/automation/stock-analysis/run';
```

### Issue 2: External Links
**Problem**: Bookmarks, emails, external sites linking to old URLs
**Solution**: 301 redirects handle this automatically

### Issue 3: API Clients
**Problem**: External API clients using old endpoints
**Solution**: Support both old and new endpoints for 6 months, then deprecate

### Issue 4: Session Data
**Problem**: Old session data may have wrong route references
**Solution**: Clear sessions on deployment or handle both formats

### Issue 5: Firestore Data
**Problem**: Database may store old route references
**Solution**: Data migration script to update stored routes

---

## 📊 Migration Timeline

| Week | Tasks | Deliverables |
|------|-------|--------------|
| Week 1 | Create blueprints, route structure | Working blueprint files, routes registered |
| Week 2 | Move templates, update url_for | New template structure, updated links |
| Week 3 | Add redirects, update docs | All redirects working, docs updated |
| Week 4 | Testing, bug fixes, polish | Production-ready code |

---

## 🎉 Success Criteria

The migration is successful when:
1. All old URLs redirect to new URLs
2. No broken links anywhere in the app
3. All features work as before
4. Navigation is clearer and more intuitive
5. Users can find automation types easily
6. All tests pass
7. No increase in error rates
8. Positive user feedback on new structure

