# Stock Page Feature - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     STOCK PAGE FEATURE                          │
│                    Standalone Implementation                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Header (Stock Price Badge)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Navigation Tabs (Desktop) / Dropdown (Mobile)           │  │
│  │  [Overview] [Forecast] [Technical] [Fundamentals] ...    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │    Section Content (dynamically switched)                │  │
│  │                                                           │  │
│  │    ┌────────────┐  ┌────────────┐  ┌────────────┐       │  │
│  │    │  Metric 1  │  │  Metric 2  │  │  Metric 3  │       │  │
│  │    └────────────┘  └────────────┘  └────────────┘       │  │
│  │                                                           │  │
│  │    ┌──────────────────────────────────────────────┐     │  │
│  │    │         Section Block (Content)               │     │  │
│  │    └──────────────────────────────────────────────┘     │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Footer (Disclaimer & Info)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ User Interaction
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    JAVASCRIPT CONTROLLER                        │
├─────────────────────────────────────────────────────────────────┤
│  Tab Switching Logic      │  Mobile Dropdown Logic              │
│  Keyboard Navigation      │  URL Hash Management                │
│  Smooth Scrolling         │  Analytics Tracking                 │
│  State Management         │  Event Handling                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Data Flow
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK APPLICATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐         ┌──────────────────────────┐       │
│  │  demo_app.py   │────────▶│  Template Renderer       │       │
│  │  (Standalone)  │         │  (Jinja2)                │       │
│  └────────────────┘         └──────────────────────────┘       │
│         │                              │                        │
│         │                              │                        │
│         ▼                              ▼                        │
│  ┌────────────────┐         ┌──────────────────────────┐       │
│  │  Load Demo     │         │  stock_page.html         │       │
│  │  Data (JSON)   │         │  (Template)              │       │
│  └────────────────┘         └──────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Data Source
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA PROCESSING                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           section_parser.py (HTML Parser)              │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │  • Parse by Headers (h1, h2, h3)                       │    │
│  │  • Parse by Classes (section-, report-section)         │    │
│  │  • Parse by Content Analysis                           │    │
│  │  • Extract Metadata (ticker, price, etc.)              │    │
│  │  • Map to Standard Structure                           │    │
│  │  • Generate Template Data                              │    │
│  └────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Output (JSON / Dict)                      │    │
│  │  {                                                     │    │
│  │    "ticker": "AAPL",                                   │    │
│  │    "overview_introduction": "<p>...</p>",             │    │
│  │    "forecast_summary": "<div>...</div>",              │    │
│  │    ...                                                 │    │
│  │  }                                                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Section Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         7 MAIN SECTIONS                         │
└─────────────────────────────────────────────────────────────────┘

1. OVERVIEW                    2. FORECAST                3. TECHNICAL
   ├─ Introduction                ├─ Summary                ├─ Summary
   └─ Quick Stats                 ├─ Table                  ├─ Indicators
                                  └─ Chart                  └─ Charts

4. FUNDAMENTALS                5. COMPANY                 6. TRADING
   ├─ Valuation                   ├─ Profile                ├─ Strategies
   ├─ Health                      ├─ Business               ├─ Entry/Exit
   ├─ Growth                      └─ Industry               └─ Risk
   └─ Analyst

7. CONCLUSION
   ├─ Outlook
   ├─ Risks
   ├─ Recommendation
   └─ FAQ

Total: 7 main sections, 21 subsections, 28 content areas
```

## Data Flow Diagram

```
┌──────────────┐
│  HTML Report │  (Existing generated reports)
└──────┬───────┘
       │
       │ Input to Parser
       ▼
┌──────────────────────────────┐
│    section_parser.py         │
│  (BeautifulSoup + Regex)     │
└──────┬───────────────────────┘
       │
       │ Parsed Data
       ▼
┌──────────────────────────────┐
│    Template Data (Dict)      │
│  • ticker: "AAPL"            │
│  • overview_*: "<html>"      │
│  • forecast_*: "<html>"      │
│  • technical_*: "<html>"     │
│  • fundamentals_*: "<html>"  │
│  • company_*: "<html>"       │
│  • trading_*: "<html>"       │
│  • conclusion_*: "<html>"    │
└──────┬───────────────────────┘
       │
       │ Passed to Template
       ▼
┌──────────────────────────────┐
│    stock_page.html           │
│  (Jinja2 Template)           │
└──────┬───────────────────────┘
       │
       │ Rendered HTML
       ▼
┌──────────────────────────────┐
│    Browser                   │
│  • stock_page.css loaded     │
│  • stock_page.js loaded      │
└──────┬───────────────────────┘
       │
       │ User Interaction
       ▼
┌──────────────────────────────┐
│  JavaScript Tab Switching    │
│  • Show/Hide Sections        │
│  • Update URL Hash           │
│  • Smooth Animations         │
└──────────────────────────────┘
```

## Integration Flow (Future)

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAIN TICKZEN APP                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ User generates report
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Firestore / Firebase Storage                   │
│  • userGeneratedReports collection                              │
│  • HTML content (compressed or in storage)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ User clicks "View Report"
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Route: /stock/<ticker>                             │
│  1. Get latest report from Firestore                            │
│  2. Load HTML content                                           │
│  3. Parse with section_parser.py                                │
│  4. Render stock_page.html                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Rendered Page
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Stock Page (Browser)                          │
│  • Sectioned navigation                                         │
│  • Interactive tabs                                             │
│  • Mobile responsive                                            │
│  • Shareable URLs                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                       TECHNOLOGY STACK                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend:                                                       │
│  ├─ HTML5 (Semantic, Accessible)                               │
│  ├─ CSS3 (Custom Properties, Grid, Flexbox)                    │
│  ├─ JavaScript (ES6+, Vanilla - No Dependencies)               │
│  └─ Font Awesome 6.4.0 (Icons)                                 │
│                                                                  │
│  Backend:                                                        │
│  ├─ Python 3.8+                                                │
│  ├─ Flask 2.3+ (Web Framework)                                 │
│  ├─ BeautifulSoup4 (HTML Parsing)                             │
│  └─ Jinja2 (Templating Engine)                                │
│                                                                  │
│  Design:                                                         │
│  ├─ Mobile-First Responsive                                    │
│  ├─ CSS Custom Properties (Theming)                            │
│  ├─ Flexbox & CSS Grid Layout                                  │
│  └─ GPU-Accelerated Animations                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Dependencies

```
stock_page_feature/
│
├─ demo_app.py
│   ├─ Requires: Flask
│   ├─ Uses: templates/stock_page.html
│   ├─ Uses: static/css/stock_page.css
│   └─ Uses: static/js/stock_page.js
│
├─ utils/section_parser.py
│   ├─ Requires: BeautifulSoup4
│   └─ Standalone utility (no other dependencies)
│
├─ templates/stock_page.html
│   ├─ Links: ../static/css/stock_page.css
│   ├─ Links: ../static/js/stock_page.js
│   └─ Uses: Font Awesome CDN
│
├─ static/css/stock_page.css
│   └─ Standalone (no dependencies)
│
└─ static/js/stock_page.js
    └─ Standalone (no dependencies, vanilla JS)
```

## Responsive Behavior

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSIVE BREAKPOINTS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Mobile (< 480px)                                               │
│  ├─ Single column layout                                       │
│  ├─ Stacked metrics (1 per row)                                │
│  ├─ Mobile dropdown navigation                                  │
│  ├─ Smaller fonts (14px base)                                  │
│  └─ Reduced padding/margins                                     │
│                                                                  │
│  Tablet (481px - 768px)                                         │
│  ├─ Two column metrics grid                                    │
│  ├─ Mobile dropdown navigation                                  │
│  ├─ Medium fonts (15px base)                                   │
│  └─ Moderate padding/margins                                    │
│                                                                  │
│  Desktop (769px - 1399px)                                       │
│  ├─ Horizontal tab navigation                                   │
│  ├─ Multi-column metrics grid                                  │
│  ├─ Full fonts (16px base)                                     │
│  └─ Standard padding/margins                                    │
│                                                                  │
│  Large Desktop (1400px+)                                        │
│  ├─ Wide content container (1400px max)                        │
│  ├─ 4-column metrics grid                                      │
│  ├─ Enhanced spacing                                            │
│  └─ Optimal reading width                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**Diagram Version**: 1.0  
**Last Updated**: December 3, 2025  
**Architecture Status**: ✅ Complete
