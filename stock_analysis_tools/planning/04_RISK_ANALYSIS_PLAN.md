# Risk Analysis Tool - Implementation Plan

## 🎯 Tool Overview

**Purpose:** Comprehensive risk assessment tool that analyzes volatility, drawdowns, beta, Value at Risk (VaR), and other risk metrics to help investors understand the potential downside and risk profile of any stock.

**Target Users:**
- Risk-averse investors
- Portfolio managers
- Financial advisors
- Conservative traders

## 📊 Features & Functionality

### **Core Features**

#### 1. **Volatility Analysis**
- Historical volatility (HV)
- Implied volatility (IV) from options
- Volatility percentile ranking
- Volatility trends (increasing/decreasing)
- Comparison to market volatility
- Annualized volatility

#### 2. **Value at Risk (VaR)**
- 95% VaR (1-day, 1-week, 1-month)
- 99% VaR (conservative estimate)
- Historical simulation method
- Monte Carlo simulation
- Expected shortfall (CVaR)
- Maximum probable loss

#### 3. **Drawdown Analysis**
- Current drawdown from peak
- Maximum historical drawdown
- Drawdown duration
- Recovery time analysis
- Drawdown frequency
- Underwater periods chart

#### 4. **Beta & Correlation**
- Beta vs. S&P 500
- Beta vs. sector index
- Rolling beta analysis
- Correlation to market
- Correlation to sector
- Systematic vs. unsystematic risk

#### 5. **Risk-Adjusted Returns**
- Sharpe Ratio
- Sortino Ratio
- Treynor Ratio
- Information Ratio
- Calmar Ratio
- Risk-return scatter plot

#### 6. **Downside Risk Metrics**
- Downside deviation
- Downside capture ratio
- Worst single-day loss
- Worst week/month/year
- Tail risk analysis
- Probability of loss

#### 7. **Risk Scoring**
- Overall risk score (0-100)
- Risk rating (Low/Medium/High/Very High)
- Risk vs. return profile
- Risk comparison to peers

## 🎨 User Interface Design

### **Page Layout:**

```
┌─────────────────────────────────────────────┐
│  Risk Analysis: TSLA                        │
│  ─────────────────────────────────────────  │
│                                             │
│  ⚠️ Risk Score: 78/100 - HIGH RISK         │
│  ┌────────────────────────────────────────┐ │
│  │        [============•=====]             │ │
│  │   Low    Medium    High    Very High   │ │
│  └────────────────────────────────────────┘ │
│  Risk Level: Suitable for aggressive       │
│  investors only. High volatility expected. │
│                                             │
├─────────────────────────────────────────────┤
│  📉 Volatility Metrics                      │
│  ├─ Current Volatility: 45.2% (Annual)     │
│  ├─ 30-Day Average: 42.8%                  │
│  ├─ Percentile Rank: 82nd                  │
│  ├─ vs. Market (SPY): 2.1x higher          │
│  └─ Trend: Increasing ⬆️                   │
│                                             │
│  [Volatility Chart - 1Y]                   │
│                                             │
├─────────────────────────────────────────────┤
│  💸 Value at Risk (VaR)                     │
│  ┌─────────────────────────────────────┐   │
│  │ Confidence │ 1-Day  │ 1-Week │ 1-Mo │   │
│  ├─────────────────────────────────────┤   │
│  │ 95%        │ -3.2%  │ -7.1%  │-12.8%│   │
│  │ 99%        │ -5.8%  │-12.9%  │-23.4%│   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Expected Shortfall (95%): -4.8%            │
│  Max Probable Loss (99%): -5.8%             │
│                                             │
├─────────────────────────────────────────────┤
│  📊 Drawdown Analysis                       │
│  ├─ Current Drawdown: -8.3% from peak      │
│  ├─ Max Historical DD: -73.4% (2022)       │
│  ├─ Average Drawdown: -18.6%               │
│  ├─ Recovery Time (Avg): 45 days           │
│  └─ Currently Underwater: 12 days          │
│                                             │
│  [Underwater Equity Chart]                  │
│                                             │
├─────────────────────────────────────────────┤
│  📈 Beta & Correlation                      │
│  ├─ Beta (vs SPY): 1.82                    │
│  ├─ Correlation: 0.68                      │
│  ├─ Systematic Risk: 46%                   │
│  ├─ Unsystematic Risk: 54%                 │
│  └─ R²: 0.62                               │
│                                             │
│  Interpretation: Stock is 82% more volatile │
│  than market, with moderate correlation.   │
│                                             │
├─────────────────────────────────────────────┤
│  🎯 Risk-Adjusted Returns                   │
│  ┌────────────────────────────────────────┐ │
│  │ Sharpe Ratio:     0.82 (Good)          │ │
│  │ Sortino Ratio:    1.15 (Excellent)     │ │
│  │ Treynor Ratio:    0.18                 │ │
│  │ Calmar Ratio:     0.45                 │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  [Risk-Return Scatter vs. Peers]            │
│                                             │
├─────────────────────────────────────────────┤
│  ⚡ Downside Risk                           │
│  ├─ Downside Deviation: 28.4%              │
│  ├─ Worst Day: -21.3% (Dec 2021)           │
│  ├─ Worst Week: -32.8%                     │
│  ├─ Worst Month: -42.6%                    │
│  ├─ Probability of Loss: 45%               │
│  └─ Downside Capture: 135% (⚠️ High)      │
│                                             │
├─────────────────────────────────────────────┤
│  📋 Risk Summary                            │
│  ┌────────────────────────────────────────┐ │
│  │ ✓ High growth potential                │ │
│  │ ⚠️ Very high volatility                │ │
│  │ ⚠️ Large historical drawdowns          │ │
│  │ ⚠️ High beta (market amplification)    │ │
│  │ ✓ Good risk-adjusted returns           │ │
│  │ ⚠️ Suitable for risk-tolerant only     │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  [Export Risk Report] [Set Risk Alerts]    │
│                                             │
└─────────────────────────────────────────────┘
```

### **Interactive Elements:**
- Adjust analysis timeframe (1M, 3M, 6M, 1Y, 3Y, 5Y)
- Toggle VaR calculation method
- Compare risk to peers/sector
- Export risk report (PDF)
- Set risk alerts (e.g., volatility > 50%)

## 🔌 API Endpoints

### **1. Run Risk Analysis**
```
POST /stock-analysis/tools/api/risk-analysis
```

**Request:**
```json
{
  "ticker": "TSLA",
  "timeframe": "1Y",
  "var_confidence": [95, 99],
  "include_options_iv": false
}
```

**Response:**
```json
{
  "status": "success",
  "ticker": "TSLA",
  "analysis_date": "2026-01-14T10:30:00Z",
  "timeframe": "1Y",
  
  "risk_score": {
    "overall": 78,
    "rating": "HIGH",
    "interpretation": "Suitable for aggressive investors only"
  },
  
  "volatility": {
    "current_annual": 45.2,
    "30day_average": 42.8,
    "percentile_rank": 82,
    "vs_market_multiplier": 2.1,
    "trend": "INCREASING",
    "historical_volatility": {
      "dates": ["2025-01-14", ...],
      "values": [38.5, 40.2, ...]
    }
  },
  
  "value_at_risk": {
    "95_confidence": {
      "1_day": -3.2,
      "1_week": -7.1,
      "1_month": -12.8
    },
    "99_confidence": {
      "1_day": -5.8,
      "1_week": -12.9,
      "1_month": -23.4
    },
    "expected_shortfall_95": -4.8,
    "max_probable_loss_99": -5.8,
    "methodology": "historical_simulation"
  },
  
  "drawdown": {
    "current_drawdown": -8.3,
    "current_peak": 412.50,
    "current_price": 378.25,
    "days_underwater": 12,
    "max_drawdown": -73.4,
    "max_drawdown_date": "2022-12-28",
    "average_drawdown": -18.6,
    "average_recovery_days": 45,
    "drawdown_frequency": 12,
    "drawdown_history": [
      {
        "peak": 414.50,
        "trough": 110.26,
        "recovery": 380.00,
        "drawdown_pct": -73.4,
        "start_date": "2021-11-04",
        "trough_date": "2022-12-28",
        "recovery_date": "2023-08-15",
        "duration_days": 284
      }
    ]
  },
  
  "beta_correlation": {
    "beta": 1.82,
    "correlation": 0.68,
    "r_squared": 0.62,
    "alpha": 0.15,
    "systematic_risk": 46,
    "unsystematic_risk": 54,
    "rolling_beta": {
      "dates": ["2025-01-14", ...],
      "values": [1.75, 1.82, ...]
    }
  },
  
  "risk_adjusted_returns": {
    "sharpe_ratio": 0.82,
    "sharpe_rating": "Good",
    "sortino_ratio": 1.15,
    "sortino_rating": "Excellent",
    "treynor_ratio": 0.18,
    "calmar_ratio": 0.45,
    "information_ratio": 0.32
  },
  
  "downside_risk": {
    "downside_deviation": 28.4,
    "worst_day": {
      "date": "2021-12-03",
      "return": -21.3
    },
    "worst_week": -32.8,
    "worst_month": -42.6,
    "worst_year": -65.0,
    "probability_of_loss": 45,
    "downside_capture_ratio": 135,
    "tail_risk_measure": "HIGH"
  },
  
  "risk_summary": {
    "strengths": [
      "High growth potential",
      "Good risk-adjusted returns (Sortino)"
    ],
    "weaknesses": [
      "Very high volatility",
      "Large historical drawdowns",
      "High beta (amplifies market moves)",
      "High downside capture ratio"
    ],
    "recommendation": "Suitable for risk-tolerant investors only. Consider position sizing.",
    "risk_category": "AGGRESSIVE"
  }
}
```

### **2. Get Risk History**
```
GET /stock-analysis/tools/api/risk-history/{ticker}?metric=volatility&period=1Y
```

### **3. Compare Risk Profiles**
```
POST /stock-analysis/tools/api/risk-compare
Body: { "tickers": ["TSLA", "AAPL", "SPY"] }
```

### **4. Calculate Portfolio Risk**
```
POST /stock-analysis/tools/api/portfolio-risk
Body: {
  "positions": [
    {"ticker": "TSLA", "weight": 0.3},
    {"ticker": "AAPL", "weight": 0.4},
    {"ticker": "MSFT", "weight": 0.3}
  ]
}
```

## 🛠️ Implementation Details

### **Backend Components:**

#### **Blueprint:** `risk_analysis_bp.py`
```python
from flask import Blueprint, render_template, jsonify, request
from analysis_scripts.risk_analysis import RiskAnalyzer

risk_bp = Blueprint('risk_analysis', __name__, 
                   url_prefix='/stock-analysis/tools')

@risk_bp.route('/risk')
def risk_analysis_page():
    """Render risk analysis page"""
    return render_template('stock_analysis/tools/risk_analysis.html')

@risk_bp.route('/api/risk-analysis', methods=['POST'])
def run_risk_analysis():
    """Run comprehensive risk analysis"""
    data = request.get_json()
    ticker = data.get('ticker')
    timeframe = data.get('timeframe', '1Y')
    var_confidence = data.get('var_confidence', [95, 99])
    
    analyzer = RiskAnalyzer(ticker, timeframe)
    results = analyzer.analyze_all(var_confidence)
    
    return jsonify(results), 200

@risk_bp.route('/api/risk-compare', methods=['POST'])
def compare_risk_profiles():
    """Compare risk metrics across multiple tickers"""
    data = request.get_json()
    tickers = data.get('tickers', [])
    
    comparison = {}
    for ticker in tickers:
        analyzer = RiskAnalyzer(ticker, '1Y')
        comparison[ticker] = analyzer.get_summary()
    
    return jsonify(comparison), 200
```

#### **Analysis Module Enhancement:**
Extend `analysis_scripts/risk_analysis.py` with:
- VaR calculation (historical simulation, Monte Carlo)
- Drawdown tracking and analysis
- Beta calculation (rolling window)
- Risk-adjusted return ratios
- Volatility forecasting

### **Frontend Components:**

#### **Template:** `risk_analysis.html`
- Risk score gauge
- Volatility chart (line chart)
- Underwater equity chart
- VaR table
- Risk-return scatter plot
- Drawdown history timeline

#### **JavaScript:**
```javascript
async function runRiskAnalysis(ticker) {
    const response = await fetch('/stock-analysis/tools/api/risk-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            ticker,
            timeframe: '1Y',
            var_confidence: [95, 99]
        })
    });
    
    const data = await response.json();
    updateRiskGauge(data.risk_score);
    displayVolatility(data.volatility);
    displayVaR(data.value_at_risk);
    displayDrawdown(data.drawdown);
    displayBeta(data.beta_correlation);
    displayRiskAdjustedReturns(data.risk_adjusted_returns);
    renderVolatilityChart(data.volatility.historical_volatility);
}
```

## 📈 Data Sources

**Price Data:**
- yfinance (historical prices)
- Alpha Vantage

**Risk-Free Rate:**
- U.S. Treasury yields (for Sharpe/Sortino)
- FRED API

**Market Data:**
- S&P 500 (SPY) for beta calculation
- Sector ETFs for sector beta

**Options Data (Optional):**
- Implied volatility from options chains

## 🎯 Success Metrics

- Accuracy of volatility forecasts
- VaR model back-testing results
- User engagement with risk reports
- Correlation between risk score and actual losses

## 🚀 Development Phases

### **Phase 1: Core Risk Metrics** (Week 1-2)
- Volatility calculation
- Basic VaR (historical method)
- Current drawdown
- Beta calculation
- Simple risk score

### **Phase 2: Advanced Risk Metrics** (Week 3-4)
- Monte Carlo VaR
- Full drawdown analysis
- Rolling beta
- Risk-adjusted returns (Sharpe, Sortino)
- Downside risk metrics

### **Phase 3: Visualization & Reports** (Week 5-6)
- Risk score gauge
- Volatility charts
- Underwater equity chart
- Risk-return scatter plot
- PDF export

### **Phase 4: Portfolio & Alerts** (Week 7-8)
- Portfolio risk aggregation
- Risk alerts and notifications
- Peer risk comparison
- Risk dashboard

## 🔐 Access Control

- **Free Users:** 3 risk analyses per day
- **Premium Users:** Unlimited + Portfolio risk analysis
- **Requires Login:** Yes

## 💾 Caching Strategy

- Price data: Cache for 15 minutes (during market hours)
- Risk calculations: Cache for 1 hour
- Historical risk: Cache for 24 hours
- Beta/correlation: Cache for 4 hours

## 📱 Risk Score Calculation

```python
def calculate_risk_score(volatility, max_drawdown, beta, sortino):
    """
    Calculate overall risk score (0-100)
    Higher score = Higher risk
    """
    # Normalize metrics to 0-100 scale
    vol_score = min(volatility / 100 * 100, 100)  # 100% vol = max score
    dd_score = min(abs(max_drawdown) / 80 * 100, 100)  # 80% DD = max
    beta_score = min(beta / 3 * 100, 100)  # Beta of 3 = max score
    sortino_score = max(100 - (sortino * 20), 0)  # Lower Sortino = higher risk
    
    # Weighted average
    weights = {'vol': 0.35, 'dd': 0.35, 'beta': 0.20, 'sortino': 0.10}
    
    risk_score = (
        vol_score * weights['vol'] +
        dd_score * weights['dd'] +
        beta_score * weights['beta'] +
        sortino_score * weights['sortino']
    )
    
    return risk_score

def get_risk_rating(risk_score):
    """Convert risk score to rating"""
    if risk_score < 25:
        return "LOW"
    elif risk_score < 50:
        return "MEDIUM"
    elif risk_score < 75:
        return "HIGH"
    else:
        return "VERY HIGH"
```

---

**Priority:** High  
**Estimated Effort:** 7-8 weeks  
**Dependencies:** risk_analysis.py, yfinance, numpy, scipy  
**Status:** 📋 Planning
