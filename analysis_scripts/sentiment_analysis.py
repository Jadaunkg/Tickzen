# sentiment_analysis.py - Advanced Sentiment Analysis Module
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