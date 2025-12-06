# Stock Page Feature - Integration Guide

## Quick Integration Steps

### 1. Install Dependencies

```powershell
cd C:\Tickzen\stock_page_feature
pip install -r requirements.txt
```

### 2. Test Standalone Demo

```powershell
# Run the demo application
python demo_app.py

# Open browser to:
# http://127.0.0.1:5000/stock/AAPL
```

### 3. Integration Checklist

#### A. Copy Files to Main Project

```powershell
# From the stock_page_feature directory:

# Copy CSS
Copy-Item "static/css/stock_page.css" "../Tickzen/app/static/css/" -Force

# Copy JavaScript  
Copy-Item "static/js/stock_page.js" "../Tickzen/app/static/js/" -Force

# Copy HTML template
Copy-Item "templates/stock_page.html" "../Tickzen/app/templates/" -Force

# Copy utilities
Copy-Item "utils/section_parser.py" "../Tickzen/app/utils/" -Force
```

#### B. Update Template Paths

Edit `Tickzen/app/templates/stock_page.html`:

**Change line 10:**
```html
<!-- FROM: -->
<link rel="stylesheet" href="../static/css/stock_page.css">

<!-- TO: -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/stock_page.css') }}">
```

**Change line 391:**
```html
<!-- FROM: -->
<script src="../static/js/stock_page.js"></script>

<!-- TO: -->
<script src="{{ url_for('static', filename='js/stock_page.js') }}"></script>
```

#### C. Add Route to Main App

Edit `Tickzen/app/main_portal_app.py`:

**Add imports at top:**
```python
import sys
import os

# Add utils to path if not already there
UTILS_PATH = os.path.join(PROJECT_ROOT, 'app', 'utils')
if UTILS_PATH not in sys.path:
    sys.path.insert(0, UTILS_PATH)
```

**Add helper function (around line 3150):**
```python
def get_latest_report_for_ticker(user_uid, ticker):
    """Get the most recent report for a specific ticker"""
    db = get_firestore_client()
    if not db:
        app.logger.error("Firestore client not available")
        return None
    
    try:
        query = db.collection('userGeneratedReports')\
            .where('user_uid', '==', user_uid)\
            .where('ticker', '==', ticker.upper())\
            .order_by('generated_at', direction=firestore.Query.DESCENDING)\
            .limit(1)
        
        docs = list(query.stream())
        if docs:
            report_data = docs[0].to_dict()
            report_data['id'] = docs[0].id
            
            # Get HTML content based on storage type
            if report_data.get('storage_type') == 'firestore_content':
                # Content is already in report_data['html_content']
                pass
            elif report_data.get('storage_type') == 'firestore_compressed':
                # Decompress content
                import gzip
                import base64
                compressed = base64.b64decode(report_data.get('compressed_content', ''))
                report_data['html_content'] = gzip.decompress(compressed).decode('utf-8')
            elif report_data.get('storage_type') == 'firebase_storage':
                # Load from Firebase Storage
                content = get_report_content_from_firestore(report_data)
                report_data['html_content'] = content
            
            return report_data
        
        return None
    except Exception as e:
        app.logger.error(f"Error getting latest report for {ticker}: {e}", exc_info=True)
        return None
```

**Add main route (after other routes, around line 2200):**
```python
@app.route('/stock/<ticker>')
@app.route('/stock/<ticker>/<section>')
@login_required
def stock_page(ticker, section='overview'):
    """Dynamic stock page with sectioned navigation"""
    user_uid = session.get('firebase_user_uid')
    ticker = ticker.upper()
    
    app.logger.info(f"Stock page requested for {ticker}, section: {section}")
    
    # Get latest report for this ticker
    report_data = get_latest_report_for_ticker(user_uid, ticker)
    
    if not report_data:
        flash(f"No report found for {ticker}. Please generate a report first.", "warning")
        return redirect(url_for('analyzer_input_page'))
    
    # Parse HTML content into sections using the parser
    try:
        from section_parser import ReportSectionParser
        
        html_content = report_data.get('html_content', '')
        if not html_content:
            flash(f"Report content not available for {ticker}.", "danger")
            return redirect(url_for('dashboard_page'))
        
        parser = ReportSectionParser(html_content)
        template_data = parser.generate_template_data()
        
        # Add active section
        template_data['active_section'] = section
        
        app.logger.info(f"Successfully parsed report for {ticker}")
        
        return render_template('stock_page.html', **template_data)
        
    except Exception as e:
        app.logger.error(f"Error rendering stock page for {ticker}: {e}", exc_info=True)
        flash(f"Error displaying report for {ticker}. Please try again.", "danger")
        return redirect(url_for('dashboard_page'))
```

#### D. Update Dashboard Links (Optional)

Edit `Tickzen/app/templates/dashboard.html`:

Find where reports are displayed and update links:

```html
<!-- Change report view links from: -->
<a href="{{ url_for('view_report', filename=report.filename) }}">View Report</a>

<!-- To: -->
<a href="{{ url_for('stock_page', ticker=report.ticker) }}">View Report</a>
```

#### E. Create Utils Directory (if not exists)

```powershell
# Create utils directory
New-Item -ItemType Directory -Path "C:\Tickzen\Tickzen\app\utils" -Force

# Copy section parser
Copy-Item "utils/section_parser.py" "../Tickzen/app/utils/" -Force

# Create __init__.py
New-Item -ItemType File -Path "C:\Tickzen\Tickzen\app\utils\__init__.py" -Force
```

### 4. Testing Integration

#### A. Start Your Flask App

```powershell
cd C:\Tickzen\Tickzen
python wsgi.py
```

#### B. Generate a Test Report

1. Login to your app
2. Go to Stock Analyzer
3. Generate a report for AAPL (or any ticker)

#### C. View with New Stock Page

Navigate to: `http://localhost:5000/stock/AAPL`

Or test specific sections: `http://localhost:5000/stock/AAPL/technical`

### 5. Troubleshooting

#### Issue: "No report found"

**Solution:**
- Ensure you've generated at least one report for the ticker
- Check Firestore to verify report exists
- Verify user_uid matches session user

#### Issue: "Report content not available"

**Solution:**
- Check storage_type in Firestore document
- Verify html_content or storage_path exists
- Check Firebase Storage permissions

#### Issue: Template not found

**Solution:**
```powershell
# Verify template was copied
Test-Path "C:\Tickzen\Tickzen\app\templates\stock_page.html"

# If false, copy again
Copy-Item "templates/stock_page.html" "../Tickzen/app/templates/" -Force
```

#### Issue: CSS not loading

**Solution:**
```powershell
# Verify CSS was copied
Test-Path "C:\Tickzen\Tickzen\app\static\css\stock_page.css"

# Clear browser cache
# Hard refresh: Ctrl+Shift+R
```

#### Issue: Sections not switching

**Solution:**
- Open browser console (F12)
- Check for JavaScript errors
- Verify stock_page.js was copied correctly
- Ensure no jQuery conflicts

### 6. Production Deployment

#### A. Minify Assets

```powershell
# Install minification tools
npm install -g csso-cli uglify-js

# Minify CSS
csso static/css/stock_page.css -o static/css/stock_page.min.css

# Minify JS
uglifyjs static/js/stock_page.js -o static/js/stock_page.min.js -c -m
```

#### B. Update Template for Production

```html
<!-- Use minified versions in production -->
{% if config.ENV == 'production' %}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/stock_page.min.css') }}">
    <script src="{{ url_for('static', filename='js/stock_page.min.js') }}"></script>
{% else %}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/stock_page.css') }}">
    <script src="{{ url_for('static', filename='js/stock_page.js') }}"></script>
{% endif %}
```

#### C. Add Caching Headers

In `main_portal_app.py`:

```python
@app.after_request
def add_cache_headers(response):
    """Add cache headers for static assets"""
    if request.path.startswith('/static/'):
        # Cache for 1 year for static files
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
    return response
```

### 7. SEO Optimization

#### A. Add Meta Tags

Edit `stock_page.html` head section:

```html
<meta name="description" content="Comprehensive AI-powered stock analysis for {{ ticker }} - {{ company_name }}. Get price forecasts, technical analysis, fundamentals, and trading strategies.">
<meta name="keywords" content="{{ ticker }}, stock analysis, {{ company_name }}, price prediction, technical analysis">

<!-- Open Graph -->
<meta property="og:title" content="{{ ticker }} Stock Analysis | Tickzen">
<meta property="og:description" content="AI-powered analysis and price prediction for {{ ticker }}">
<meta property="og:type" content="website">
<meta property="og:url" content="{{ request.url }}">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ ticker }} Stock Analysis | Tickzen">
<meta name="twitter:description" content="AI-powered analysis and price prediction for {{ ticker }}">
```

#### B. Add Structured Data

Add before closing `</head>`:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FinancialProduct",
  "name": "{{ ticker }} Stock Analysis",
  "description": "Comprehensive stock analysis for {{ company_name }}",
  "provider": {
    "@type": "Organization",
    "name": "Tickzen"
  }
}
</script>
```

### 8. Next Steps

- [ ] Test with multiple tickers
- [ ] Verify all sections display correctly
- [ ] Test on mobile devices
- [ ] Check browser compatibility
- [ ] Monitor performance
- [ ] Gather user feedback
- [ ] Optimize load times
- [ ] Add analytics tracking

### 9. Rollback Plan

If integration causes issues:

```powershell
# Remove copied files
Remove-Item "C:\Tickzen\Tickzen\app\templates\stock_page.html"
Remove-Item "C:\Tickzen\Tickzen\app\static\css\stock_page.css"
Remove-Item "C:\Tickzen\Tickzen\app\static\js\stock_page.js"

# Comment out the route in main_portal_app.py
# Restart your Flask application
```

### 10. Support

For issues during integration:
- Check standalone demo still works
- Compare integrated version with standalone
- Review browser console for errors
- Check Flask logs for server errors
- Verify all file paths are correct

---

**Integration Complexity:** Medium  
**Estimated Time:** 1-2 hours  
**Risk Level:** Low (standalone feature, minimal conflicts)
