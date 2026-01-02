#!/bin/bash
# Google Trends Integration Setup & Verification Script
# Run this script to verify the implementation is correctly integrated

echo "🔍 Google Trends Implementation Verification"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: Not in tickzen2-main directory${NC}"
    echo "Please run this script from the project root"
    exit 1
fi

echo -e "${GREEN}✅ Running from correct directory${NC}\n"

# Check 1: Requirements.txt
echo "Checking requirements.txt..."
if grep -q "pytrends==4.7.0" requirements.txt; then
    echo -e "${GREEN}✅ pytrends==4.7.0 found in requirements.txt${NC}"
else
    echo -e "${RED}❌ pytrends not found in requirements.txt${NC}"
fi
echo ""

# Check 2: Google Trends Collector Module
echo "Checking Google Trends collector module..."
if [ -f "app/google_trends_collector.py" ]; then
    echo -e "${GREEN}✅ app/google_trends_collector.py exists${NC}"
    LINES=$(wc -l < "app/google_trends_collector.py")
    echo "   Lines of code: $LINES"
else
    echo -e "${RED}❌ app/google_trends_collector.py not found${NC}"
fi
echo ""

# Check 3: Database File
echo "Checking database file..."
if [ -f "google_trends_database.json" ]; then
    echo -e "${GREEN}✅ google_trends_database.json exists${NC}"
    SIZE=$(wc -c < "google_trends_database.json")
    echo "   File size: $SIZE bytes"
else
    echo -e "${RED}❌ google_trends_database.json not found${NC}"
fi
echo ""

# Check 4: Frontend Template
echo "Checking frontend template..."
if [ -f "app/templates/google_trends_dashboard.html" ]; then
    echo -e "${GREEN}✅ google_trends_dashboard.html exists${NC}"
    LINES=$(wc -l < "app/templates/google_trends_dashboard.html")
    echo "   Lines of code: $LINES"
else
    echo -e "${RED}❌ google_trends_dashboard.html not found${NC}"
fi
echo ""

# Check 5: Automation Pipeline
echo "Checking automation pipeline..."
if [ -f "automation_scripts/google_trends_pipeline.py" ]; then
    echo -e "${GREEN}✅ google_trends_pipeline.py exists${NC}"
    LINES=$(wc -l < "automation_scripts/google_trends_pipeline.py")
    echo "   Lines of code: $LINES"
else
    echo -e "${RED}❌ google_trends_pipeline.py not found${NC}"
fi
echo ""

# Check 6: API Endpoints in main app
echo "Checking API endpoints in main_portal_app.py..."
if grep -q "@app.route('/api/trends/collect'" app/main_portal_app.py; then
    echo -e "${GREEN}✅ POST /api/trends/collect endpoint found${NC}"
else
    echo -e "${RED}❌ POST /api/trends/collect endpoint not found${NC}"
fi

if grep -q "@app.route('/api/trends/get'" app/main_portal_app.py; then
    echo -e "${GREEN}✅ GET /api/trends/get endpoint found${NC}"
else
    echo -e "${RED}❌ GET /api/trends/get endpoint not found${NC}"
fi

if grep -q "@app.route('/api/trends/related'" app/main_portal_app.py; then
    echo -e "${GREEN}✅ GET /api/trends/related endpoint found${NC}"
else
    echo -e "${RED}❌ GET /api/trends/related endpoint not found${NC}"
fi

if grep -q "@app.route('/api/trends/history'" app/main_portal_app.py; then
    echo -e "${GREEN}✅ GET /api/trends/history endpoint found${NC}"
else
    echo -e "${RED}❌ GET /api/trends/history endpoint not found${NC}"
fi
echo ""

# Check 7: Dashboard Route
echo "Checking dashboard route..."
if grep -q "@app.route('/trends-dashboard'" app/main_portal_app.py; then
    echo -e "${GREEN}✅ GET /trends-dashboard route found${NC}"
else
    echo -e "${RED}❌ GET /trends-dashboard route not found${NC}"
fi
echo ""

# Check 8: Documentation
echo "Checking documentation..."
if [ -f "GOOGLE_TRENDS_README.md" ]; then
    echo -e "${GREEN}✅ GOOGLE_TRENDS_README.md exists${NC}"
else
    echo -e "${RED}❌ GOOGLE_TRENDS_README.md not found${NC}"
fi

if [ -f "IMPLEMENTATION_SUMMARY.md" ]; then
    echo -e "${GREEN}✅ IMPLEMENTATION_SUMMARY.md exists${NC}"
else
    echo -e "${RED}❌ IMPLEMENTATION_SUMMARY.md not found${NC}"
fi
echo ""

# Summary
echo "=============================================="
echo "✅ Verification Complete!"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Start the application"
echo "3. Navigate to: http://localhost:5000/trends-dashboard"
echo "4. Click 'Collect Trends' to start"
echo ""
echo "For detailed documentation, see:"
echo "- GOOGLE_TRENDS_README.md (comprehensive guide)"
echo "- IMPLEMENTATION_SUMMARY.md (what was implemented)"
