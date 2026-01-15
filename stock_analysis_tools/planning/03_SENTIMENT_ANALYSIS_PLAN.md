# Sentiment Analysis Tool - Implementation Plan

## 🎯 Tool Overview

**Purpose:** Analyze market sentiment, news coverage, social media trends, and overall market mood for any stock to gauge investor psychology and potential price movements.

**Target Users:**
- Sentiment traders
- News-based traders
- Social media analysts
- Market psychologists

## 📊 Features & Functionality

### **Core Features**

#### 1. **News Sentiment Analysis**
- Recent news articles (last 7-30 days)
- Sentiment score per article (Positive/Neutral/Negative)
- Overall sentiment trend
- Sentiment momentum
- Key topics and themes
- Source credibility weighting

#### 2. **Social Media Sentiment**
- Twitter/X mentions and sentiment
- Reddit discussions (r/wallstreetbets, r/stocks, etc.)
- StockTwits sentiment
- Social media volume trends
- Influencer mentions

#### 3. **Analyst Sentiment**
- Analyst ratings (Buy/Hold/Sell)
- Rating changes and upgrades/downgrades
- Price target changes
- Consensus sentiment
- Historical accuracy tracking

#### 4. **Market Sentiment Indicators**
- Put/Call ratio
- Short interest
- Insider trading activity
- Institutional ownership changes
- Fear & Greed index (for stock)

#### 5. **Sentiment Timeline**
- Historical sentiment tracking
- Sentiment vs. price correlation
- Event-driven sentiment spikes
- Sentiment momentum indicators

## 🎨 User Interface Design

### **Page Layout:**

```
┌─────────────────────────────────────────────┐
│  Sentiment Analysis: TSLA                   │
│  ─────────────────────────────────────────  │
│                                             │
│  📊 Overall Sentiment Score                 │
│  ┌────────────────────────────────────────┐ │
│  │        ★ 78/100 - BULLISH              │ │
│  │    [==============•========]            │ │
│  │  Bearish        Neutral      Bullish   │ │
│  └────────────────────────────────────────┘ │
│                                             │
├─────────────────────────────────────────────┤
│  📰 News Sentiment (Last 7 Days)            │
│  ├─ Positive: 62% (31 articles) 🟢         │
│  ├─ Neutral: 25% (13 articles) 🟡          │
│  └─ Negative: 13% (7 articles) 🔴          │
│                                             │
│  Trending Topics:                           │
│  #ElectricVehicles #Q4Earnings #Production │
│                                             │
├─────────────────────────────────────────────┤
│  💬 Social Media Buzz                       │
│  ├─ Twitter Mentions: 45.2K (↑ 23%)        │
│  ├─ Reddit Posts: 892 (↑ 15%)              │
│  ├─ StockTwits: Bullish 68%                │
│  └─ Social Sentiment: Very Positive         │
│                                             │
├─────────────────────────────────────────────┤
│  👔 Analyst Sentiment                       │
│  ├─ Buy: 18 analysts                        │
│  ├─ Hold: 10 analysts                       │
│  ├─ Sell: 2 analysts                        │
│  └─ Consensus: STRONG BUY                   │
│     Avg Price Target: $320 (↑ 47%)         │
│                                             │
├─────────────────────────────────────────────┤
│  📈 Sentiment Timeline (30 Days)            │
│  [Line chart: Sentiment score over time]   │
│  [Overlay: Stock price for correlation]    │
│                                             │
├─────────────────────────────────────────────┤
│  📰 Recent News Headlines                   │
│  ┌────────────────────────────────────────┐ │
│  │ 🟢 Tesla delivers record vehicles...   │ │
│  │    Sentiment: Positive | 4 hours ago   │ │
│  ├────────────────────────────────────────│ │
│  │ 🟡 Tesla faces competition in China... │ │
│  │    Sentiment: Neutral | 1 day ago      │ │
│  ├────────────────────────────────────────│ │
│  │ 🔴 Recall announced for Model Y...      │ │
│  │    Sentiment: Negative | 2 days ago    │ │
│  └────────────────────────────────────────┘ │
│                                             │
├─────────────────────────────────────────────┤
│  🎯 Trading Implications                    │
│  Signal: BULLISH SENTIMENT                  │
│  Confidence: 78%                            │
│  Risk: Sentiment may be overheated          │
│  Recommendation: Monitor for sentiment shift│
│                                             │
└─────────────────────────────────────────────┘
```

### **Interactive Elements:**
- Adjust sentiment timeframe (7D, 14D, 30D, 90D)
- Filter news by source
- Click headlines to read full articles
- Export sentiment report
- Set sentiment alerts

## 🔌 API Endpoints

### **1. Run Sentiment Analysis**
```
POST /stock-analysis/tools/api/sentiment-analysis
```

**Request:**
```json
{
  "ticker": "TSLA",
  "timeframe": "7D",
  "include_social": true,
  "include_news": true,
  "include_analysts": true
}
```

**Response:**
```json
{
  "status": "success",
  "ticker": "TSLA",
  "analysis_date": "2026-01-14T10:30:00Z",
  
  "overall_sentiment": {
    "score": 78,
    "rating": "BULLISH",
    "momentum": "INCREASING",
    "confidence": 82
  },
  
  "news_sentiment": {
    "total_articles": 51,
    "positive": 31,
    "neutral": 13,
    "negative": 7,
    "positive_percentage": 60.8,
    "average_sentiment": 0.42,
    "trending_topics": [
      "Electric Vehicles",
      "Q4 Earnings",
      "Production"
    ],
    "recent_headlines": [
      {
        "title": "Tesla delivers record vehicles in Q4",
        "sentiment": "positive",
        "score": 0.85,
        "source": "Reuters",
        "published": "2026-01-14T06:00:00Z",
        "url": "https://..."
      }
    ]
  },
  
  "social_sentiment": {
    "twitter": {
      "mentions": 45200,
      "change_24h": 23,
      "sentiment": "positive",
      "score": 0.68
    },
    "reddit": {
      "posts": 892,
      "change_24h": 15,
      "sentiment": "bullish",
      "score": 0.72
    },
    "stocktwits": {
      "bullish_percentage": 68,
      "bearish_percentage": 32,
      "message_volume": "very_high"
    }
  },
  
  "analyst_sentiment": {
    "total_analysts": 30,
    "buy": 18,
    "hold": 10,
    "sell": 2,
    "consensus": "STRONG BUY",
    "average_price_target": 320.00,
    "upside_potential": 46.8,
    "recent_changes": [
      {
        "analyst": "Morgan Stanley",
        "action": "upgrade",
        "from": "Hold",
        "to": "Buy",
        "date": "2026-01-12"
      }
    ]
  },
  
  "market_indicators": {
    "put_call_ratio": 0.65,
    "short_interest": 12.5,
    "institutional_ownership": 58.3,
    "insider_buying": true
  },
  
  "sentiment_timeline": {
    "dates": ["2025-12-15", "2025-12-22", ...],
    "scores": [65, 68, 72, 75, 78]
  },
  
  "trading_implications": {
    "signal": "BULLISH",
    "confidence": 78,
    "risk_warning": "Sentiment may be overheated",
    "recommendation": "Monitor for sentiment shift"
  }
}
```

### **2. Get Sentiment History**
```
GET /stock-analysis/tools/api/sentiment-history/{ticker}?days=30
```

### **3. Compare Sentiment**
```
POST /stock-analysis/tools/api/sentiment-compare
Body: { "tickers": ["TSLA", "RIVN", "LCID"] }
```

### **4. Get News Feed**
```
GET /stock-analysis/tools/api/news-feed/{ticker}?limit=20&sentiment=positive
```

## 🛠️ Implementation Details

### **Backend Components:**

#### **Blueprint:** `sentiment_analysis_bp.py`
```python
from flask import Blueprint, render_template, jsonify, request
from analysis_scripts.sentiment_analysis import SentimentAnalyzer

sentiment_bp = Blueprint('sentiment_analysis', __name__, 
                        url_prefix='/stock-analysis/tools')

@sentiment_bp.route('/sentiment')
def sentiment_analysis_page():
    """Render sentiment analysis page"""
    return render_template('stock_analysis/tools/sentiment_analysis.html')

@sentiment_bp.route('/api/sentiment-analysis', methods=['POST'])
def run_sentiment_analysis():
    """Run sentiment analysis for given ticker"""
    data = request.get_json()
    ticker = data.get('ticker')
    timeframe = data.get('timeframe', '7D')
    
    analyzer = SentimentAnalyzer(ticker)
    results = analyzer.analyze_all(timeframe)
    
    return jsonify(results), 200

@sentiment_bp.route('/api/news-feed/<ticker>')
def get_news_feed(ticker):
    """Get filtered news feed"""
    limit = request.args.get('limit', 20, type=int)
    sentiment_filter = request.args.get('sentiment')
    
    analyzer = SentimentAnalyzer(ticker)
    news = analyzer.get_news(limit, sentiment_filter)
    
    return jsonify(news), 200
```

#### **Analysis Module Enhancement:**
Extend `analysis_scripts/sentiment_analysis.py` with:
- News API integration (NewsAPI, Finnhub)
- Social media scraping (Twitter API, Reddit API)
- NLP sentiment scoring (VADER, TextBlob, or Transformers)
- Analyst rating aggregation

### **Frontend Components:**

#### **Template:** `sentiment_analysis.html`
- Sentiment gauge/meter
- News article cards with sentiment badges
- Social media activity charts
- Analyst ratings display
- Sentiment timeline chart

#### **JavaScript:**
```javascript
async function runSentimentAnalysis(ticker) {
    const response = await fetch('/stock-analysis/tools/api/sentiment-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            ticker, 
            timeframe: '7D',
            include_social: true,
            include_news: true,
            include_analysts: true
        })
    });
    
    const data = await response.json();
    updateSentimentGauge(data.overall_sentiment);
    displayNewsSentiment(data.news_sentiment);
    displaySocialSentiment(data.social_sentiment);
    displayAnalystRatings(data.analyst_sentiment);
    renderSentimentTimeline(data.sentiment_timeline);
}
```

## 📈 Data Sources

**News Sources:**
- NewsAPI (newsapi.org)
- Finnhub (finnhub.io)
- Alpha Vantage News
- Yahoo Finance News

**Social Media:**
- Twitter API (X API)
- Reddit API (PRAW)
- StockTwits API

**Analyst Data:**
- Yahoo Finance
- Finnhub
- Alpha Vantage

**NLP Models:**
- VADER (for finance-specific sentiment)
- TextBlob (general sentiment)
- FinBERT (optional, for advanced sentiment)

## 🎯 Success Metrics

- Sentiment prediction accuracy
- Correlation between sentiment and price movements
- User engagement with news articles
- Social media integration usage

## 🚀 Development Phases

### **Phase 1: News Sentiment MVP** (Week 1-2)
- Fetch news articles
- Basic sentiment scoring (VADER)
- Display sentiment score and articles
- Simple visualization

### **Phase 2: Social Media Integration** (Week 3-4)
- Twitter/Reddit integration
- Social sentiment scoring
- Volume tracking
- Trending topics

### **Phase 3: Analyst Ratings** (Week 5-6)
- Analyst rating aggregation
- Price target tracking
- Upgrade/downgrade notifications
- Consensus calculation

### **Phase 4: Advanced Features** (Week 7-8)
- Sentiment timeline chart
- Sentiment alerts
- Export sentiment reports
- Custom sentiment dashboard

## 🔐 Access Control

- **Free Users:** 5 sentiment analyses per day
- **Premium Users:** Unlimited + Real-time alerts
- **Requires Login:** Yes

## 💾 Caching Strategy

- News sentiment: Cache for 30 minutes
- Social media data: Cache for 15 minutes
- Analyst ratings: Cache for 24 hours
- Historical sentiment: Cache for 7 days

## 📱 Sentiment Score Calculation

```python
def calculate_overall_sentiment(news_score, social_score, analyst_score):
    """
    Weighted average of different sentiment sources
    """
    weights = {
        'news': 0.40,      # 40% weight
        'social': 0.30,    # 30% weight
        'analyst': 0.30    # 30% weight
    }
    
    overall = (
        news_score * weights['news'] +
        social_score * weights['social'] +
        analyst_score * weights['analyst']
    )
    
    return overall * 100  # Scale to 0-100
```

---

**Priority:** Medium-High  
**Estimated Effort:** 7-9 weeks  
**Dependencies:** sentiment_analysis.py, NewsAPI, Social APIs  
**Status:** 📋 Planning
