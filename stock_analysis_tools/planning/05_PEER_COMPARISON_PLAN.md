# Peer Comparison Tool - Implementation Plan

## 🎯 Tool Overview

**Purpose:** Compare a stock against its industry peers and competitors across multiple dimensions including financial metrics, valuation, performance, growth rates, and market positioning to identify relative strengths and weaknesses.

**Target Users:**
- Value investors
- Stock pickers
- Portfolio managers
- Research analysts

## 📊 Features & Functionality

### **Core Features**

#### 1. **Automatic Peer Identification**
- Industry classification
- Market cap peers
- Business model similarity
- Geographic overlap
- Competitive set identification

#### 2. **Financial Comparison**
- Revenue comparison
- Profitability metrics
- Cash flow generation
- Debt levels
- Working capital efficiency

#### 3. **Valuation Comparison**
- P/E ratio ranking
- P/B, P/S, EV/EBITDA
- PEG ratio
- Dividend yield
- Premium/discount to peers

#### 4. **Performance Comparison**
- Price performance (1M, 3M, 6M, 1Y, 3Y)
- Volatility comparison
- Risk-adjusted returns
- Drawdown comparison
- Alpha generation

#### 5. **Growth Comparison**
- Revenue growth rates
- Earnings growth
- Book value growth
- Historical growth trends
- Growth consistency

#### 6. **Operational Metrics**
- Margins (gross, operating, net)
- ROE, ROA, ROIC
- Asset turnover
- Efficiency ratios
- Quality scores

#### 7. **Market Position**
- Market share
- Market cap ranking
- Trading volume
- Institutional ownership
- Analyst coverage

## 🎨 User Interface Design

### **Page Layout:**

```
┌─────────────────────────────────────────────┐
│  Peer Comparison: TSLA                      │
│  ─────────────────────────────────────────  │
│                                             │
│  🏢 Industry: Electric Vehicles & Auto     │
│  Comparing against 5 peers                  │
│  [RIVN] [LCID] [F] [GM] [NIO]              │
│                                             │
├─────────────────────────────────────────────┤
│  📊 Quick Comparison                        │
│  ┌────────────────────────────────────────┐ │
│  │        TSLA  RIVN  LCID   F    GM  NIO │ │
│  │ Mkt Cap 1.2T  45B   12B  48B  52B  18B │ │
│  │ P/E     45.2  N/A   N/A  6.2  5.8  12.3│ │
│  │ Rev Grw  24%  -5%   12%   2%   8%  15% │ │
│  │ Rank      #1   #5    #4   #3   #2  N/A │ │
│  └────────────────────────────────────────┘ │
│                                             │
├─────────────────────────────────────────────┤
│  💰 Valuation Metrics                       │
│  [Bar chart comparing P/E, P/B, P/S, EV/E] │
│                                             │
│  TSLA Valuation: PREMIUM                    │
│  - P/E: 45.2 (Peers Avg: 8.1) 🔴 +458%    │
│  - P/B: 12.5 (Peers Avg: 1.8) 🔴 +594%    │
│  - P/S: 8.2 (Peers Avg: 0.4) 🔴 +1950%    │
│  - EV/EBITDA: 32.4 (Peers: 6.5) 🔴 +398%  │
│                                             │
│  Interpretation: TSLA trades at significant │
│  premium to peers, justified by growth.    │
│                                             │
├─────────────────────────────────────────────┤
│  📈 Performance Comparison (1Y)             │
│  [Line chart: All tickers performance]     │
│                                             │
│  Returns (1 Year):                          │
│  1. TSLA: +47.2% 🥇                        │
│  2. GM: +28.5%                              │
│  3. F: +12.3%                               │
│  4. NIO: -8.4%                              │
│  5. RIVN: -15.2%                            │
│  6. LCID: -32.1%                            │
│                                             │
├─────────────────────────────────────────────┤
│  💵 Financial Health                        │
│  ┌────────────────────────────────────────┐ │
│  │ Metric     TSLA   Avg   Best   Worst  │ │
│  ├────────────────────────────────────────│ │
│  │ ROE        28.5%  8.2%  28.5%  -45.2% │ │
│  │ ROA        12.3%  3.1%  12.3%  -18.5% │ │
│  │ Debt/Eq     0.08  1.85   0.08   3.45  │ │
│  │ Curr Rat    1.73  1.12   1.73   0.85  │ │
│  │ Op Marg    15.2%  2.8%  15.2%  -28.5% │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  TSLA leads in profitability and efficiency│
│                                             │
├─────────────────────────────────────────────┤
│  🚀 Growth Comparison                       │
│  [Bar chart: Revenue & Earnings growth]    │
│                                             │
│  Revenue Growth (3Y CAGR):                  │
│  1. LCID: 248% (Low base) 🥇               │
│  2. RIVN: 185% (Low base)                   │
│  3. TSLA: 24% ⭐                            │
│  4. NIO: 15%                                │
│  5. GM: 8%                                  │
│  6. F: 2%                                   │
│                                             │
│  Earnings Growth (3Y CAGR):                 │
│  1. TSLA: 68% 🥇                           │
│  2. GM: 12%                                 │
│  3. F: 8%                                   │
│  (RIVN, LCID, NIO: Not profitable)         │
│                                             │
├─────────────────────────────────────────────┤
│  🎯 Operating Efficiency                    │
│  [Spider/Radar chart: Multiple metrics]    │
│                                             │
│  Margins:                                   │
│  - Gross Margin: TSLA 25.6% vs Avg 12.3%  │
│  - Operating Margin: TSLA 15.2% vs Avg 2.8%│
│  - Net Margin: TSLA 11.8% vs Avg 1.5%     │
│                                             │
│  Return Metrics:                            │
│  - ROE: TSLA 28.5% (BEST)                  │
│  - ROA: TSLA 12.3% (BEST)                  │
│  - ROIC: TSLA 18.7% (BEST)                 │
│                                             │
├─────────────────────────────────────────────┤
│  📋 Ranking Summary                         │
│  ┌────────────────────────────────────────┐ │
│  │ Category          TSLA Rank  Score     │ │
│  ├────────────────────────────────────────│ │
│  │ Valuation           6/6      2.0/10    │ │
│  │ Performance         1/6     10.0/10    │ │
│  │ Profitability       1/6     10.0/10    │ │
│  │ Growth              3/6      7.5/10    │ │
│  │ Financial Health    1/6     10.0/10    │ │
│  │ Efficiency          1/6     10.0/10    │ │
│  ├────────────────────────────────────────│ │
│  │ Overall Score                8.3/10    │ │
│  │ Overall Rank                 #1/6      │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  ✓ Leader in profitability and efficiency  │
│  ✓ Best performance vs. peers               │
│  ⚠️ Most expensive valuation                │
│  ✓ Strong growth, but slowing               │
│                                             │
│  [Export Comparison] [Add/Remove Peers]    │
│                                             │
└─────────────────────────────────────────────┘
```

### **Interactive Elements:**
- Add/remove custom peers
- Adjust time periods for comparisons
- Sort tables by any column
- Toggle between chart types
- Export comparison report
- Save custom peer groups

## 🔌 API Endpoints

### **1. Run Peer Comparison**
```
POST /stock-analysis/tools/api/peer-comparison
```

**Request:**
```json
{
  "ticker": "TSLA",
  "custom_peers": ["RIVN", "LCID", "F", "GM", "NIO"],
  "auto_identify": false,
  "timeframe": "1Y"
}
```

**Response:**
```json
{
  "status": "success",
  "ticker": "TSLA",
  "analysis_date": "2026-01-14T10:30:00Z",
  "industry": "Electric Vehicles & Automotive",
  
  "peers": [
    {
      "ticker": "RIVN",
      "name": "Rivian Automotive",
      "market_cap": 45000000000,
      "similarity_score": 0.85
    },
    {
      "ticker": "LCID",
      "name": "Lucid Group",
      "market_cap": 12000000000,
      "similarity_score": 0.82
    },
    {
      "ticker": "F",
      "name": "Ford Motor",
      "market_cap": 48000000000,
      "similarity_score": 0.68
    },
    {
      "ticker": "GM",
      "name": "General Motors",
      "market_cap": 52000000000,
      "similarity_score": 0.65
    },
    {
      "ticker": "NIO",
      "name": "NIO Inc",
      "market_cap": 18000000000,
      "similarity_score": 0.75
    }
  ],
  
  "valuation_comparison": {
    "TSLA": {
      "pe_ratio": 45.2,
      "pb_ratio": 12.5,
      "ps_ratio": 8.2,
      "ev_ebitda": 32.4,
      "peg_ratio": 1.88,
      "dividend_yield": 0.0
    },
    "peer_average": {
      "pe_ratio": 8.1,
      "pb_ratio": 1.8,
      "ps_ratio": 0.4,
      "ev_ebitda": 6.5,
      "peg_ratio": 0.95
    },
    "ranking": {
      "pe_ratio": 6,
      "pb_ratio": 6,
      "ps_ratio": 6,
      "overall_valuation": "PREMIUM"
    }
  },
  
  "performance_comparison": {
    "1Y": {
      "TSLA": 47.2,
      "RIVN": -15.2,
      "LCID": -32.1,
      "F": 12.3,
      "GM": 28.5,
      "NIO": -8.4
    },
    "ranking": {
      "TSLA": 1,
      "GM": 2,
      "F": 3,
      "NIO": 4,
      "RIVN": 5,
      "LCID": 6
    },
    "volatility_comparison": {
      "TSLA": 45.2,
      "peer_average": 52.8,
      "ranking": 2
    }
  },
  
  "financial_health": {
    "TSLA": {
      "roe": 28.5,
      "roa": 12.3,
      "debt_to_equity": 0.08,
      "current_ratio": 1.73,
      "quick_ratio": 1.21,
      "operating_margin": 15.2,
      "net_margin": 11.8
    },
    "peer_average": {
      "roe": 8.2,
      "roa": 3.1,
      "debt_to_equity": 1.85,
      "current_ratio": 1.12,
      "operating_margin": 2.8,
      "net_margin": 1.5
    },
    "ranking": {
      "roe": 1,
      "roa": 1,
      "debt_to_equity": 1,
      "profitability": "LEADER"
    }
  },
  
  "growth_comparison": {
    "revenue_growth_3y_cagr": {
      "TSLA": 24.0,
      "LCID": 248.0,
      "RIVN": 185.0,
      "NIO": 15.0,
      "GM": 8.0,
      "F": 2.0
    },
    "earnings_growth_3y_cagr": {
      "TSLA": 68.0,
      "GM": 12.0,
      "F": 8.0,
      "RIVN": null,
      "LCID": null,
      "NIO": null
    },
    "ranking": {
      "revenue_growth": 3,
      "earnings_growth": 1,
      "interpretation": "Leading profitable growth"
    }
  },
  
  "efficiency_metrics": {
    "TSLA": {
      "gross_margin": 25.6,
      "operating_margin": 15.2,
      "net_margin": 11.8,
      "roic": 18.7,
      "asset_turnover": 0.85
    },
    "peer_average": {
      "gross_margin": 12.3,
      "operating_margin": 2.8,
      "net_margin": 1.5,
      "roic": 5.2,
      "asset_turnover": 0.72
    },
    "ranking": "LEADER"
  },
  
  "overall_ranking": {
    "categories": {
      "valuation": { "rank": 6, "score": 2.0 },
      "performance": { "rank": 1, "score": 10.0 },
      "profitability": { "rank": 1, "score": 10.0 },
      "growth": { "rank": 3, "score": 7.5 },
      "financial_health": { "rank": 1, "score": 10.0 },
      "efficiency": { "rank": 1, "score": 10.0 }
    },
    "overall_score": 8.3,
    "overall_rank": 1,
    "total_peers": 6
  },
  
  "summary": {
    "strengths": [
      "Leader in profitability and efficiency",
      "Best performance vs. peers",
      "Strong financial health",
      "Sustainable growth with profitability"
    ],
    "weaknesses": [
      "Most expensive valuation",
      "Growth slowing from peak levels"
    ],
    "recommendation": "TSLA is the clear leader among EV peers but trades at a significant premium. Valuation may be justified by superior fundamentals."
  }
}
```

### **2. Auto-Identify Peers**
```
GET /stock-analysis/tools/api/identify-peers/{ticker}?count=5
```

### **3. Get Industry Benchmarks**
```
GET /stock-analysis/tools/api/industry-benchmarks/{ticker}
```

### **4. Export Comparison**
```
POST /stock-analysis/tools/api/export-comparison
Body: { "ticker": "TSLA", "peers": [...], "format": "pdf" }
```

## 🛠️ Implementation Details

### **Backend Components:**

#### **Blueprint:** `peer_comparison_bp.py`
```python
from flask import Blueprint, render_template, jsonify, request
from analysis_scripts.peer_comparison import PeerComparisonAnalyzer

peer_bp = Blueprint('peer_comparison', __name__, 
                   url_prefix='/stock-analysis/tools')

@peer_bp.route('/peer-comparison')
def peer_comparison_page():
    """Render peer comparison page"""
    return render_template('stock_analysis/tools/peer_comparison.html')

@peer_bp.route('/api/peer-comparison', methods=['POST'])
def run_peer_comparison():
    """Run comprehensive peer comparison"""
    data = request.get_json()
    ticker = data.get('ticker')
    custom_peers = data.get('custom_peers', [])
    auto_identify = data.get('auto_identify', True)
    timeframe = data.get('timeframe', '1Y')
    
    analyzer = PeerComparisonAnalyzer(ticker)
    
    # Identify peers if needed
    if auto_identify or not custom_peers:
        peers = analyzer.identify_peers(count=5)
    else:
        peers = custom_peers
    
    # Run comparison
    results = analyzer.compare_all(peers, timeframe)
    
    return jsonify(results), 200

@peer_bp.route('/api/identify-peers/<ticker>')
def identify_peers(ticker):
    """Auto-identify peer companies"""
    count = request.args.get('count', 5, type=int)
    
    analyzer = PeerComparisonAnalyzer(ticker)
    peers = analyzer.identify_peers(count)
    
    return jsonify(peers), 200
```

#### **Analysis Module Enhancement:**
Extend `analysis_scripts/peer_comparison.py` with:
- Industry classification logic
- Peer identification algorithm
- Multi-dimensional comparison framework
- Ranking algorithms
- Scoring methodology

### **Frontend Components:**

#### **Template:** `peer_comparison.html`
- Quick comparison table
- Valuation bar charts
- Performance line chart
- Financial health table
- Spider/radar chart for efficiency
- Ranking summary cards

#### **JavaScript:**
```javascript
async function runPeerComparison(ticker, customPeers = []) {
    const response = await fetch('/stock-analysis/tools/api/peer-comparison', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            ticker,
            custom_peers: customPeers,
            auto_identify: customPeers.length === 0,
            timeframe: '1Y'
        })
    });
    
    const data = await response.json();
    displayPeerList(data.peers);
    displayValuationComparison(data.valuation_comparison);
    displayPerformanceChart(data.performance_comparison);
    displayFinancialHealth(data.financial_health);
    displayGrowthComparison(data.growth_comparison);
    displayEfficiencyMetrics(data.efficiency_metrics);
    displayRankingSummary(data.overall_ranking);
}
```

## 📈 Data Sources

**Company Data:**
- yfinance (all financial data)
- Yahoo Finance (company info, industry)
- Finnhub (peer identification)

**Industry Classification:**
- GICS sectors and industries
- SIC codes
- Custom business model classification

**Benchmarks:**
- Industry averages
- Sector ETF data

## 🎯 Success Metrics

- Accuracy of peer identification
- User engagement with comparisons
- Custom peer group usage
- Export report downloads

## 🚀 Development Phases

### **Phase 1: Core Comparison** (Week 1-2)
- Manual peer selection
- Basic financial comparison
- Valuation metrics
- Simple ranking

### **Phase 2: Auto-Identification** (Week 3-4)
- Industry classification
- Peer identification algorithm
- Similarity scoring
- Market cap matching

### **Phase 3: Advanced Metrics** (Week 5-6)
- Growth comparison
- Efficiency metrics
- Performance analysis
- Risk-adjusted returns
- Spider/radar charts

### **Phase 4: Polish & Export** (Week 7-8)
- Interactive charts
- Custom peer groups
- PDF export
- Saved comparisons
- Comparison history

## 🔐 Access Control

- **Free Users:** 3 peer comparisons per day, up to 3 peers
- **Premium Users:** Unlimited, up to 10 peers per comparison
- **Requires Login:** Yes

## 💾 Caching Strategy

- Company data: Cache for 4 hours
- Financial metrics: Cache for 24 hours
- Industry benchmarks: Cache for 7 days
- Peer lists: Cache for 24 hours

## 📱 Peer Identification Algorithm

```python
def identify_peers(ticker, count=5):
    """
    Identify peer companies using multiple criteria
    """
    # 1. Get company info
    company = get_company_info(ticker)
    industry = company['industry']
    market_cap = company['marketCap']
    
    # 2. Find companies in same industry
    industry_companies = get_companies_by_industry(industry)
    
    # 3. Filter by market cap (0.2x to 5x)
    filtered = [
        c for c in industry_companies
        if (market_cap * 0.2) <= c['marketCap'] <= (market_cap * 5)
    ]
    
    # 4. Calculate similarity scores
    for company in filtered:
        score = calculate_similarity(ticker, company['ticker'])
        company['similarity_score'] = score
    
    # 5. Sort by similarity and return top N
    sorted_peers = sorted(filtered, key=lambda x: x['similarity_score'], reverse=True)
    return sorted_peers[:count]

def calculate_similarity(ticker1, ticker2):
    """
    Calculate similarity score based on:
    - Industry match
    - Market cap proximity
    - Geographic overlap
    - Business model similarity
    """
    score = 0.0
    
    # Industry match (40%)
    if same_industry(ticker1, ticker2):
        score += 0.4
    
    # Market cap proximity (30%)
    cap_ratio = get_market_cap_ratio(ticker1, ticker2)
    if cap_ratio < 2:
        score += 0.3
    elif cap_ratio < 5:
        score += 0.15
    
    # Geographic overlap (15%)
    geo_score = calculate_geographic_overlap(ticker1, ticker2)
    score += geo_score * 0.15
    
    # Business model (15%)
    model_score = calculate_business_model_similarity(ticker1, ticker2)
    score += model_score * 0.15
    
    return score
```

## 📊 Overall Ranking Methodology

```python
def calculate_overall_rank(comparisons):
    """
    Calculate overall ranking across multiple categories
    """
    categories = {
        'valuation': 0.10,      # 10% weight (lower valuation is better)
        'performance': 0.25,     # 25% weight
        'profitability': 0.20,   # 20% weight
        'growth': 0.20,          # 20% weight
        'financial_health': 0.15,# 15% weight
        'efficiency': 0.10       # 10% weight
    }
    
    scores = {}
    for ticker in comparisons:
        total_score = 0
        for category, weight in categories.items():
            rank = comparisons[ticker][category]['rank']
            total_peers = len(comparisons)
            
            # Convert rank to score (1st = 10, last = 0)
            category_score = 10 * (1 - (rank - 1) / (total_peers - 1))
            
            total_score += category_score * weight
        
        scores[ticker] = round(total_score, 1)
    
    return scores
```

---

**Priority:** Medium  
**Estimated Effort:** 7-8 weeks  
**Dependencies:** peer_comparison.py, yfinance, industry data  
**Status:** 📋 Planning
