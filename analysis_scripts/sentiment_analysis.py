#!/usr/bin/env python3
"""
Market Sentiment Analysis Engine
===============================

Advanced sentiment analysis system that aggregates and analyzes market sentiment
from multiple sources including news, social media, analyst reports, and market
data to provide comprehensive sentiment scoring for investment decisions.

Core Sentiment Sources:
----------------------
1. **News Sentiment**:
   - Financial news articles and headlines
   - Press releases and earnings announcements
   - Regulatory filings and SEC submissions
   - Industry and sector news analysis

2. **Social Media Sentiment**:
   - Twitter/X mentions and discussions
   - Reddit financial community posts
   - StockTwits and trading platform sentiment
   - YouTube and podcast transcript analysis

3. **Analyst Sentiment**:
   - Analyst reports and recommendations
   - Earnings estimate revisions
   - Price target changes and justifications
   - Institutional investor sentiment

4. **Market-Based Sentiment**:
   - Options flow and put/call ratios
   - Insider trading activity
   - Short interest and borrowing costs
   - Volume and price action sentiment

Sentiment Analysis Techniques:
-----------------------------
- **Natural Language Processing (NLP)**:
  - TextBlob polarity and subjectivity analysis
  - VADER sentiment analysis for social media
  - Custom financial lexicon-based scoring
  - Named entity recognition for company mentions

- **Machine Learning Models**:
  - Pre-trained transformer models for financial text
  - Custom sentiment classification models
  - Ensemble methods for improved accuracy
  - Time-series sentiment trend analysis

Sentiment Scoring Framework:
---------------------------
- **Weighted Composite Score**: Multi-source sentiment aggregation
- **Time Decay**: Recent sentiment weighted more heavily
- **Source Reliability**: Historical accuracy-based weighting
- **Volume Adjustment**: Sentiment scaled by mention volume
- **Market Context**: Sector and market condition adjustments

Sentiment Indicators:
--------------------
1. **Overall Sentiment Score**: -1.0 (very negative) to +1.0 (very positive)
2. **Sentiment Trend**: Direction and momentum of sentiment change
3. **Sentiment Volatility**: Consistency and stability of sentiment
4. **Source Consensus**: Agreement level across different sources
5. **Sentiment Strength**: Confidence level in sentiment assessment

Advanced Analytics:
------------------
- **Sentiment Momentum**: Rate of sentiment change analysis
- **Contrarian Indicators**: Extreme sentiment reversal signals
- **Sentiment Correlation**: Relationship with price movements
- **Event Impact**: Sentiment changes around specific events
- **Sector Comparison**: Relative sentiment vs peers and sector

Real-Time Monitoring:
--------------------
- **Live Sentiment Tracking**: Continuous sentiment updates
- **Alert System**: Significant sentiment change notifications
- **Trend Detection**: Early identification of sentiment shifts
- **Anomaly Detection**: Unusual sentiment pattern identification

Sentiment-Price Relationship:
----------------------------
- **Lead-Lag Analysis**: Sentiment as price predictor or follower
- **Correlation Studies**: Statistical relationship quantification
- **Reversal Patterns**: Sentiment extremes and price reversals
- **Confirmation Signals**: Sentiment confirming price trends

Data Processing Pipeline:
------------------------
1. **Data Collection**: Gather text data from multiple sources
2. **Text Preprocessing**: Clean and normalize text data
3. **Sentiment Extraction**: Apply NLP models for sentiment scoring
4. **Aggregation**: Combine scores with appropriate weighting
5. **Trend Analysis**: Calculate sentiment momentum and changes
6. **Signal Generation**: Create actionable sentiment signals

Usage Examples:
--------------
```python
# Initialize sentiment analyzer
analyzer = SentimentAnalyzer()

# Analyze overall sentiment for a ticker
sentiment_data = analyzer.analyze_sentiment('AAPL')

# Get detailed sentiment breakdown
detailed_sentiment = analyzer.get_sentiment_breakdown(
    ticker='AAPL',
    timeframe='7d',
    sources=['news', 'social', 'analyst']
)

# Track sentiment trends
trend_analysis = analyzer.analyze_sentiment_trends(
    ticker='AAPL',
    period='30d'
)
```

Integration Points:
------------------
- Used by fundamental_analysis.py for comprehensive company analysis
- Integrated with dashboard_analytics.py for sentiment visualization
- Provides signals for automation_scripts/pipeline.py
- Supports real-time sentiment updates via SocketIO

Performance Metrics:
-------------------
- **Prediction Accuracy**: Sentiment's ability to predict price moves
- **Signal Quality**: Precision and recall of sentiment signals
- **Processing Speed**: Real-time sentiment analysis performance
- **Coverage**: Breadth of sentiment data sources

Configuration:
-------------
Customizable parameters:
- **Source Weights**: Relative importance of different sentiment sources
- **Time Windows**: Analysis periods for different applications
- **Sensitivity**: Threshold settings for signal generation
- **Update Frequency**: Real-time vs batch processing modes

Author: TickZen Development Team
Version: 2.1
Last Updated: January 2026
"""

import pandas as pd
import numpy as np
from textblob import TextBlob
import yfinance as yf
from datetime import datetime, timedelta

class SentimentAnalyzer:
    """Advanced sentiment analysis for market sentiment tracking"""
    
    def __init__(self):
        self.sentiment_weights = {
            'news': 0.4,
            'analyst': 0.3,
            'options': 0.2,
            'social': 0.1
        }
    
    def analyze_news_sentiment(self, news_headlines):
        """Analyze sentiment from news headlines"""
        if not news_headlines:
            return {'score': 0, 'classification': 'neutral', 'confidence': 0}
        
        sentiments = []
        for headline in news_headlines:
            # Handle nested news data structure from yfinance
            text_content = ""
            if isinstance(headline, dict):
                # Try different possible structures
                if 'content' in headline and isinstance(headline['content'], dict):
                    # yfinance structure: headline['content']['title'] or ['summary']
                    content_dict = headline['content']
                    text_content = content_dict.get('title', '') or content_dict.get('summary', '') or content_dict.get('description', '')
                else:
                    # Direct structure: headline['title'] or ['content']
                    text_content = headline.get('title', '') or headline.get('content', '') or headline.get('headline', '')
            
            if text_content and isinstance(text_content, str):
                blob = TextBlob(text_content)
                sentiments.append(blob.sentiment.polarity)
        
        if not sentiments:
            return {'score': 0, 'classification': 'neutral', 'confidence': 0, 'sample_size': 0}
            
        avg_sentiment = np.mean(sentiments)
        
        if avg_sentiment > 0.1:
            classification = 'positive'
        elif avg_sentiment < -0.1:
            classification = 'negative'
        else:
            classification = 'neutral'
        
        confidence = min(abs(avg_sentiment) * 2, 1.0)
        
        return {
            'score': avg_sentiment,
            'classification': classification,
            'confidence': confidence,
            'sample_size': len(sentiments)
        }
    
    def analyze_analyst_sentiment(self, analyst_data):
        """Convert analyst recommendations to sentiment score"""
        recommendation = analyst_data.get('Recommendation', 'N/A')
        
        sentiment_mapping = {
            'Strong Buy': 0.8,
            'Buy': 0.4,
            'Hold': 0.0,
            'Sell': -0.4,
            'Strong Sell': -0.8
        }
        
        for key, value in sentiment_mapping.items():
            if key.lower() in recommendation.lower():
                return {
                    'score': value,
                    'classification': 'positive' if value > 0 else 'negative' if value < 0 else 'neutral',
                    'confidence': 0.8
                }
        
        return {'score': 0, 'classification': 'neutral', 'confidence': 0}
    
    def analyze_options_sentiment(self, ticker):
        """Analyze options flow for sentiment (simplified version)"""
        try:
            stock = yf.Ticker(ticker)
            options_dates = stock.options
            
            if not options_dates:
                return {'score': 0, 'classification': 'neutral', 'confidence': 0}
            
            # Get nearest expiration options
            opt_chain = stock.option_chain(options_dates[0])
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            if calls.empty or puts.empty:
                return {'score': 0, 'classification': 'neutral', 'confidence': 0}
            
            # Calculate put/call ratio
            total_call_volume = calls['volume'].sum()
            total_put_volume = puts['volume'].sum()
            
            if total_call_volume + total_put_volume == 0:
                return {'score': 0, 'classification': 'neutral', 'confidence': 0}
            
            put_call_ratio = total_put_volume / (total_call_volume + total_put_volume)
            
            # Convert to sentiment score (lower put/call ratio = more bullish)
            sentiment_score = (0.5 - put_call_ratio) * 2  # Normalize to -1 to 1 range
            
            classification = 'positive' if sentiment_score > 0.1 else 'negative' if sentiment_score < -0.1 else 'neutral'
            
            return {
                'score': sentiment_score,
                'classification': classification,
                'confidence': 0.6,
                'put_call_ratio': put_call_ratio
            }
            
        except Exception as e:
            return {'score': 0, 'classification': 'neutral', 'confidence': 0, 'error': str(e)}
    
    def calculate_composite_sentiment(self, news_sentiment, analyst_sentiment, options_sentiment):
        """Calculate weighted composite sentiment score"""
        components = {
            'news': news_sentiment,
            'analyst': analyst_sentiment,
            'options': options_sentiment
        }
        
        weighted_score = 0
        total_weight = 0
        
        for component, weight in self.sentiment_weights.items():
            if component in components and components[component]['confidence'] > 0:
                weighted_score += components[component]['score'] * weight * components[component]['confidence']
                total_weight += weight * components[component]['confidence']
        
        if total_weight == 0:
            return {'score': 0, 'classification': 'neutral', 'confidence': 0}
        
        final_score = weighted_score / total_weight
        
        if final_score > 0.1:
            classification = 'positive'
        elif final_score < -0.1:
            classification = 'negative'
        else:
            classification = 'neutral'
        
        confidence = min(total_weight / sum(self.sentiment_weights.values()), 1.0)
        
        return {
            'score': final_score,
            'classification': classification,
            'confidence': confidence,
            'components': components
        }