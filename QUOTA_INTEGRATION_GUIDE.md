# Quota System - Template Integration Guide

## 📍 Where to Add UI Components

This guide shows exactly where to add the quota widget and modal to your existing templates.

---

## 1️⃣ Stock Analyzer Page

**File to modify**: `app/templates/analyzer.html` (or your main stock analysis page)

### Add Quota Widget to Sidebar

```html
<!-- In your sidebar section -->
<div class="sidebar">
    
    <!-- Your existing sidebar content -->
    <div class="user-info">
        <!-- User profile info -->
    </div>
    
    <!-- ADD QUOTA WIDGET HERE -->
    {% include 'components/quota_widget.html' %}
    
    <!-- Rest of sidebar -->
    <div class="recent-searches">
        <!-- Recent searches -->
    </div>
    
</div>
```

### Alternative: Add to Main Content Area

```html
<div class="main-content">
    
    <h1>Stock Analysis</h1>
    
    <!-- ADD QUOTA WIDGET HERE (above analyzer form) -->
    <div class="row mb-4">
        <div class="col-12">
            {% include 'components/quota_widget.html' %}
        </div>
    </div>
    
    <!-- Your stock analyzer form -->
    <form id="analyzer-form">
        <input type="text" name="ticker" placeholder="Enter ticker symbol">
        <button type="submit">Analyze</button>
    </form>
    
</div>
```

---

## 2️⃣ Dashboard Page

**File to modify**: `app/templates/dashboard.html`

### Add as Dashboard Card

```html
<div class="dashboard-grid">
    
    <!-- Your existing dashboard cards -->
    <div class="card">
        <h3>Recent Reports</h3>
        <!-- Recent reports content -->
    </div>
    
    <!-- ADD QUOTA WIDGET AS A CARD -->
    <div class="card">
        {% include 'components/quota_widget.html' %}
    </div>
    
    <div class="card">
        <h3>Market Overview</h3>
        <!-- Market content -->
    </div>
    
</div>
```

---

## 3️⃣ Base Template (Global)

**File to modify**: `app/templates/base.html` or your main layout template

### Add Modal at Bottom (Before closing </body>)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}TickZen{% endblock %}</title>
    
    <!-- Your existing head content -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    
    <!-- Your header -->
    <header>
        <nav><!-- Navigation --></nav>
    </header>
    
    <!-- Main content -->
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <!-- Your footer -->
    <footer>
        <!-- Footer content -->
    </footer>
    
    <!-- ========================================== -->
    <!-- ADD QUOTA EXCEEDED MODAL HERE (GLOBAL)     -->
    <!-- This makes it available on all pages       -->
    <!-- ========================================== -->
    {% include 'components/quota_exceeded_modal.html' %}
    
    <!-- Your existing scripts -->
    <script src="{{ url_for('static', filename='js/jquery.min.js') }}"></script>
    <script src="{{ url_for('static', filename='js/bootstrap.bundle.min.js') }}"></script>
    {% block extra_js %}{% endblock %}
    
</body>
</html>
```

---

## 4️⃣ Handling Quota Exceeded in Your JavaScript

**File to modify**: `app/static/js/main.js` or your stock analyzer JavaScript

### Update Stock Analysis Form Handler

```javascript
// Find your existing stock analysis form handler
// It probably looks something like this:

// BEFORE (original code):
$('#analyzer-form').on('submit', function(e) {
    e.preventDefault();
    
    const ticker = $('#ticker').val();
    
    $.ajax({
        url: '/start-analysis',
        method: 'POST',
        data: { ticker: ticker },
        success: function(response) {
            console.log('Analysis started');
        },
        error: function(xhr) {
            console.error('Error:', xhr.responseText);
        }
    });
});

// AFTER (with quota handling):
$('#analyzer-form').on('submit', function(e) {
    e.preventDefault();
    
    const ticker = $('#ticker').val();
    
    $.ajax({
        url: '/start-analysis',
        method: 'POST',
        data: { ticker: ticker },
        success: function(response) {
            console.log('Analysis started');
            
            // Refresh quota widget after successful start
            if (window.quotaWidget) {
                setTimeout(() => window.quotaWidget.refresh(), 2000);
            }
        },
        error: function(xhr) {
            // ==========================================
            // ADD THIS: Handle quota exceeded (403)
            // ==========================================
            if (xhr.status === 403) {
                const response = JSON.parse(xhr.responseText);
                if (response.error === 'quota_exceeded') {
                    // Show the quota exceeded modal
                    showQuotaExceededModal(response.quota_info);
                    return;
                }
            }
            
            // Handle other errors
            console.error('Error:', xhr.responseText);
        }
    });
});
```

---

## 5️⃣ Optional: Add to Navigation Bar

If you want a compact quota indicator in the navigation:

```html
<nav class="navbar">
    <div class="navbar-brand">
        <a href="/">TickZen</a>
    </div>
    
    <div class="navbar-menu">
        <a href="/analyzer">Analyzer</a>
        <a href="/dashboard">Dashboard</a>
        
        <!-- ADD COMPACT QUOTA INDICATOR -->
        <div class="navbar-quota">
            <i class="fas fa-chart-line"></i>
            <span id="navbar-quota-text">-/-</span>
        </div>
    </div>
    
    <div class="navbar-end">
        <a href="/profile">Profile</a>
    </div>
</nav>

<script>
// Update navbar quota indicator
function updateNavbarQuota() {
    fetch('/api/quota/status')
        .then(res => res.json())
        .then(data => {
            const used = data.stock_reports.used;
            const limit = data.stock_reports.unlimited ? '∞' : data.stock_reports.limit;
            document.getElementById('navbar-quota-text').textContent = `${used}/${limit}`;
        });
}

// Call on page load
document.addEventListener('DOMContentLoaded', updateNavbarQuota);
</script>

<style>
.navbar-quota {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: rgba(33, 150, 243, 0.1);
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    color: #2196F3;
}
</style>
```

---

## 6️⃣ Socket.IO Event Listener (Already Working)

The quota exceeded modal already listens for Socket.IO events. Your existing Socket.IO code emits `quota_exceeded` when quota is exceeded, and the modal automatically appears.

**No changes needed** - this is already handled in the modal component!

```javascript
// This is already in quota_exceeded_modal.html
socket.on('quota_exceeded', function(data) {
    showQuotaExceededModal(data.quota_info);
});
```

---

## 📋 Complete Integration Checklist

Use this checklist to ensure everything is integrated:

### Templates
- [ ] Add `{% include 'components/quota_widget.html' %}` to analyzer page
- [ ] Add `{% include 'components/quota_widget.html' %}` to dashboard
- [ ] Add `{% include 'components/quota_exceeded_modal.html' %}` to base template

### JavaScript
- [ ] Update stock analysis form handler to catch 403 errors
- [ ] Call `showQuotaExceededModal()` when quota exceeded
- [ ] Refresh quota widget after successful analysis
- [ ] (Optional) Add navbar quota indicator

### Testing
- [ ] Load analyzer page → Quota widget appears
- [ ] Check browser console → No errors
- [ ] Submit analysis → Widget refreshes after completion
- [ ] Use all quota → Modal appears on next attempt
- [ ] Click "Upgrade" → Redirects to pricing page

### Styling (Optional)
- [ ] Adjust widget width/position to fit your layout
- [ ] Match color scheme to your brand
- [ ] Ensure mobile responsive
- [ ] Test on all major browsers

---

## 🎨 Customization Examples

### Change Widget Colors to Match Your Brand

```css
/* Add to your custom CSS file */

/* Change primary color (Free plan) */
.quota-plan-badge {
    background: linear-gradient(135deg, #FF6B6B 0%, #EE5A5A 100%) !important;
}

/* Change progress bar color */
.quota-progress-fill {
    background: linear-gradient(90deg, #FF6B6B 0%, #EE5A5A 100%) !important;
}

/* Change widget background */
.quota-widget {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
}
```

### Make Widget Smaller/Compact

```css
.quota-widget {
    padding: 12px !important;
}

.quota-title {
    font-size: 14px !important;
}

.quota-usage-text {
    font-size: 20px !important;
}
```

### Add Widget to Sticky Sidebar

```css
.quota-widget {
    position: sticky;
    top: 20px;
    z-index: 100;
}
```

---

## 🔧 Troubleshooting Integration Issues

### Widget Not Showing
```
✓ Check: Is {% include 'components/quota_widget.html' %} added?
✓ Check: Is user logged in? (Widget hides for anonymous users)
✓ Check: Browser console for JavaScript errors
✓ Check: quota-widget.js is loaded (Network tab)
```

### Widget Shows "Loading..." Forever
```
✓ Check: /api/quota/status endpoint is accessible
✓ Check: User has firebase_user_uid in session
✓ Check: Firestore security rules allow read access
✓ Check: Browser console for 401/403 errors
```

### Modal Not Appearing
```
✓ Check: Is {% include 'components/quota_exceeded_modal.html' %} in base template?
✓ Check: Bootstrap 5 is loaded (modal requires it)
✓ Check: showQuotaExceededModal() function exists
✓ Check: 403 error is being caught in AJAX error handler
```

### Quota Not Updating After Analysis
```
✓ Check: consume_user_quota() is called after success
✓ Check: Firestore transaction completed successfully
✓ Check: Widget auto-refresh is working (60s interval)
✓ Try: Manual refresh - window.quotaWidget.refresh()
```

---

## 📞 Need Help?

If you encounter integration issues:

1. **Check the documentation**:
   - [QUOTA_SYSTEM_README.md](QUOTA_SYSTEM_README.md) - System overview
   - [QUOTA_QUICK_START.md](QUOTA_QUICK_START.md) - Quick start guide
   - [QUOTA_PHASE2_SUMMARY.md](QUOTA_PHASE2_SUMMARY.md) - Complete implementation details

2. **Check the logs**:
   ```bash
   # Server logs
   tail -f logs/app.log
   
   # Quota logs (after monthly reset)
   tail -f logs/quota_reset.log
   ```

3. **Test the API directly**:
   ```bash
   # Test quota status endpoint
   curl -X GET http://localhost:5000/api/quota/status \
        -H "Cookie: session=YOUR_SESSION_COOKIE"
   ```

4. **Browser Developer Tools**:
   - Console tab: Check for JavaScript errors
   - Network tab: Verify API calls are succeeding
   - Application tab: Check session storage/cookies

---

## ✅ Integration Complete!

Once you've added all components to your templates, the quota system will be fully operational with:

- Real-time quota tracking
- Automatic updates every 60 seconds
- Smooth upgrade prompts
- Mobile-responsive design
- Professional UI/UX

**Ready for production!** 🚀

---

**Last Updated**: January 13, 2026  
**For**: TickZen Quota System Phase 2
