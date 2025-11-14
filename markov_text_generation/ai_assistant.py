"""
Financial AI Assistant
======================

An intelligent financial assistant that combines Markov text generation
with rule-based reasoning to answer questions and generate content.

Features:
- Answer financial questions (like ChatGPT)
- Generate human-tone WordPress articles
- Perform financial calculations
- Provide stock analysis
- Multi-turn conversations
- Context awareness

This is a HYBRID approach:
- Markov chains for natural language style
- Rule-based logic for financial reasoning
- Template system for structured responses
- Knowledge base for facts

100% FREE - No API costs!
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
import logging

try:
    # Try relative imports first
    from .core.engine import MarkovEngine
    from .core.model_manager import ModelManager
    from .generators.summary_generator import FinancialSummaryGenerator
except ImportError:
    # Fall back to absolute imports
    from core.engine import MarkovEngine
    from core.model_manager import ModelManager
    from generators.summary_generator import FinancialSummaryGenerator

logger = logging.getLogger(__name__)


class FinancialKnowledgeBase:
    """
    Financial knowledge base for fact-based responses.
    Stores financial concepts, definitions, and relationships.
    """
    
    def __init__(self):
        self.knowledge = {
            # Financial ratios
            'PE_ratio': {
                'name': 'Price-to-Earnings Ratio',
                'formula': 'Stock Price / Earnings Per Share',
                'interpretation': {
                    'low': 'May indicate undervaluation or poor growth prospects',
                    'average': 'Typically between 15-25 for most stocks',
                    'high': 'May indicate overvaluation or high growth expectations'
                },
                'good_value': lambda x: x < 15,
                'fair_value': lambda x: 15 <= x <= 25,
                'expensive': lambda x: x > 25
            },
            
            'PEG_ratio': {
                'name': 'Price/Earnings to Growth Ratio',
                'formula': 'P/E Ratio / Annual EPS Growth Rate',
                'interpretation': {
                    'undervalued': 'PEG < 1.0',
                    'fairly_valued': 'PEG around 1.0',
                    'overvalued': 'PEG > 1.0'
                }
            },
            
            'RSI': {
                'name': 'Relative Strength Index',
                'range': '0-100',
                'interpretation': {
                    'oversold': 'RSI < 30 - potential buying opportunity',
                    'neutral': 'RSI 30-70 - balanced momentum',
                    'overbought': 'RSI > 70 - potential selling pressure'
                }
            },
            
            'MACD': {
                'name': 'Moving Average Convergence Divergence',
                'signals': {
                    'bullish': 'MACD line crosses above signal line',
                    'bearish': 'MACD line crosses below signal line'
                }
            },
            
            'debt_to_equity': {
                'name': 'Debt-to-Equity Ratio',
                'formula': 'Total Debt / Total Equity',
                'interpretation': {
                    'conservative': '< 0.5',
                    'moderate': '0.5 - 1.0',
                    'aggressive': '> 1.0'
                }
            }
        }
        
        # Stock market concepts
        self.concepts = {
            'bull_market': 'A market condition where prices are rising or expected to rise',
            'bear_market': 'A market condition where prices fall 20% or more from recent highs',
            'dividend': 'A portion of company profits distributed to shareholders',
            'market_cap': 'Total market value of outstanding shares (Price × Shares)',
            'blue_chip': 'Stock of large, established, financially sound companies',
            'volatility': 'Measure of price fluctuation over time',
            'liquidity': 'Ease of buying/selling without affecting price',
            'diversification': 'Spreading investments across different assets to reduce risk'
        }
    
    def get_metric_info(self, metric: str) -> Optional[Dict]:
        """Get information about a financial metric."""
        return self.knowledge.get(metric.lower())
    
    def get_concept(self, concept: str) -> Optional[str]:
        """Get definition of a financial concept."""
        return self.concepts.get(concept.lower())
    
    def interpret_value(self, metric: str, value: float) -> str:
        """Interpret a metric value."""
        info = self.get_metric_info(metric)
        if not info:
            return f"Unknown metric: {metric}"
        
        interpretation = info.get('interpretation', {})
        
        # Check if there are lambda functions for evaluation
        if 'good_value' in info:
            if info['good_value'](value):
                return f"{metric} of {value:.2f} is attractive/undervalued"
        if 'fair_value' in info:
            if info['fair_value'](value):
                return f"{metric} of {value:.2f} is fairly valued"
        if 'expensive' in info:
            if info['expensive'](value):
                return f"{metric} of {value:.2f} is expensive/overvalued"
        
        # RSI interpretation
        if metric == 'RSI':
            if value < 30:
                return interpretation['oversold']
            elif value > 70:
                return interpretation['overbought']
            else:
                return interpretation['neutral']
        
        return f"{metric}: {value:.2f}"


class QueryUnderstanding:
    """
    Understands user queries and extracts intent, entities, and context.
    """
    
    # Query patterns for different intents
    INTENT_PATTERNS = {
        'stock_analysis': [
            r'analyz[e]? (.+)',
            r'what (?:do you think|is your opinion) (?:about|on) (.+)',
            r'should i (?:buy|invest in) (.+)',
            r'(?:how|what) (?:is|are) (.+) (?:doing|performing)',
            r'tell me about (.+)',
            r'(.+) stock analysis'
        ],
        
        'price_question': [
            r'what(?:\'s| is) the price of (.+)',
            r'(?:how much|price) (?:is|of) (.+)',
            r'(.+) (?:price|trading at|current price)'
        ],
        
        'metric_question': [
            r'what(?:\'s| is) the (.+) (?:of|for) (.+)',
            r'(.+) (.+) ratio',
            r'(.+) pe ratio',
            r'(.+) rsi'
        ],
        
        'explanation': [
            r'what (?:is|are) (.+)',
            r'explain (.+)',
            r'define (.+)',
            r'(?:what does|meaning of) (.+)'
        ],
        
        'recommendation': [
            r'should i (?:buy|sell|hold) (.+)',
            r'is (.+) a (?:good|bad) (?:buy|investment)',
            r'(?:recommendation|rating) for (.+)'
        ],
        
        'comparison': [
            r'compare (.+) (?:and|vs|versus) (.+)',
            r'(.+) or (.+) (?:which is better|better)',
            r'difference between (.+) and (.+)'
        ],
        
        'article_generation': [
            r'(?:write|generate|create) (?:an? )?(?:article|report|analysis) (?:about|on|for) (.+)',
            r'wordpress article (?:for|about) (.+)',
            r'summarize (.+)',
            r'full analysis (?:of|for) (.+)'
        ],
        
        'general_question': [
            r'how (?:do|does|can) (.+)',
            r'why (?:is|does|do) (.+)',
            r'when (?:should|to) (.+)',
            r'can (?:i|you) (.+)'
        ]
    }
    
    @staticmethod
    def extract_intent(query: str) -> Tuple[str, List[str]]:
        """
        Extract intent and entities from query.
        
        Returns:
            (intent_type, [extracted_entities])
        """
        query_lower = query.lower().strip()
        
        for intent, patterns in QueryUnderstanding.INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    entities = [g.strip() for g in match.groups() if g]
                    return intent, entities
        
        return 'general_question', [query]
    
    @staticmethod
    def extract_ticker(text: str) -> Optional[str]:
        """Extract stock ticker from text."""
        # Look for uppercase ticker symbols
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', text)
        if ticker_match:
            return ticker_match.group(1)
        
        # Common company name to ticker mapping
        company_tickers = {
            'tesla': 'TSLA',
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'amazon': 'AMZN',
            'google': 'GOOGL',
            'meta': 'META',
            'facebook': 'META',
            'nvidia': 'NVDA',
            'netflix': 'NFLX'
        }
        
        text_lower = text.lower()
        for company, ticker in company_tickers.items():
            if company in text_lower:
                return ticker
        
        return None


class FinancialReasoning:
    """
    Financial calculations and reasoning logic.
    """
    
    @staticmethod
    def calculate_pe_ratio(price: float, eps: float) -> float:
        """Calculate P/E ratio."""
        if eps <= 0:
            return 0
        return price / eps
    
    @staticmethod
    def calculate_peg_ratio(pe_ratio: float, growth_rate: float) -> float:
        """Calculate PEG ratio."""
        if growth_rate <= 0:
            return 0
        return pe_ratio / growth_rate
    
    @staticmethod
    def calculate_target_price(current_price: float, upside_pct: float) -> float:
        """Calculate target price from upside percentage."""
        return current_price * (1 + upside_pct / 100)
    
    @staticmethod
    def determine_rating(
        pe_ratio: float,
        peg_ratio: float,
        rsi: float,
        debt_to_equity: float,
        upside_pct: float
    ) -> str:
        """Determine overall rating based on metrics."""
        bullish_signals = 0
        bearish_signals = 0
        
        # Valuation signals
        if pe_ratio < 20:
            bullish_signals += 1
        elif pe_ratio > 30:
            bearish_signals += 1
        
        if peg_ratio < 1.0:
            bullish_signals += 1
        elif peg_ratio > 2.0:
            bearish_signals += 1
        
        # Technical signals
        if rsi < 40:
            bullish_signals += 1
        elif rsi > 70:
            bearish_signals += 1
        
        # Financial health
        if debt_to_equity < 0.5:
            bullish_signals += 1
        elif debt_to_equity > 1.5:
            bearish_signals += 1
        
        # Upside potential
        if upside_pct > 15:
            bullish_signals += 2
        elif upside_pct < 0:
            bearish_signals += 2
        
        # Determine rating
        score = bullish_signals - bearish_signals
        
        if score >= 2:
            return "Buy"
        elif score <= -2:
            return "Sell"
        else:
            return "Hold"
    
    @staticmethod
    def analyze_momentum(rsi: float, macd_signal: str) -> str:
        """Analyze momentum signals."""
        if rsi > 70 and macd_signal == 'bullish':
            return "strong_bullish"
        elif rsi > 60 and macd_signal == 'bullish':
            return "bullish"
        elif rsi < 30 and macd_signal == 'bearish':
            return "strong_bearish"
        elif rsi < 40 and macd_signal == 'bearish':
            return "bearish"
        else:
            return "neutral"


class FinancialAIAssistant:
    """
    Main AI Assistant that combines all components.
    
    This is your ChatGPT-like financial assistant!
    """
    
    def __init__(self, models_dir: str = "markov_text_generation/models"):
        """Initialize the AI assistant."""
        self.knowledge_base = FinancialKnowledgeBase()
        self.query_parser = QueryUnderstanding()
        self.reasoning = FinancialReasoning()
        
        # Markov generator for human-like text
        try:
            self.text_generator = FinancialSummaryGenerator(models_dir, temperature=0.8)
        except:
            logger.warning("Could not load Markov models. Using template-based responses.")
            self.text_generator = None
        
        # Conversation history
        self.conversation_history: List[Dict] = []
        
        logger.info("FinancialAIAssistant initialized")
    
    def ask(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Main method to ask the assistant anything.
        
        Args:
            query: User's question
            context: Optional context (stock data, etc.)
        
        Returns:
            Natural language response
        """
        # Store in conversation history
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'context': context
        })
        
        # Extract intent and entities
        intent, entities = self.query_parser.extract_intent(query)
        
        logger.info(f"Intent: {intent}, Entities: {entities}")
        
        # Route to appropriate handler
        if intent == 'explanation':
            return self._handle_explanation(entities[0] if entities else query)
        
        elif intent == 'stock_analysis':
            return self._handle_stock_analysis(entities[0] if entities else None, context)
        
        elif intent == 'price_question':
            return self._handle_price_question(entities[0] if entities else None, context)
        
        elif intent == 'metric_question':
            return self._handle_metric_question(entities, context)
        
        elif intent == 'recommendation':
            return self._handle_recommendation(entities[0] if entities else None, context)
        
        elif intent == 'comparison':
            return self._handle_comparison(entities, context)
        
        elif intent == 'article_generation':
            return self._handle_article_generation(entities[0] if entities else None, context)
        
        else:
            return self._handle_general_question(query, context)
    
    def _handle_explanation(self, term: str) -> str:
        """Explain a financial term or concept."""
        term_clean = term.lower().strip()
        
        # Check concepts
        concept = self.knowledge_base.get_concept(term_clean)
        if concept:
            return f"**{term.title()}**: {concept}"
        
        # Check metrics
        metric_info = self.knowledge_base.get_metric_info(term_clean)
        if metric_info:
            response = f"**{metric_info['name']}**\n\n"
            
            if 'formula' in metric_info:
                response += f"**Formula**: {metric_info['formula']}\n\n"
            
            if 'interpretation' in metric_info:
                response += "**Interpretation**:\n"
                for key, value in metric_info['interpretation'].items():
                    response += f"- {key.replace('_', ' ').title()}: {value}\n"
            
            return response
        
        # Fallback response
        return f"I don't have specific information about '{term}', but I can help you analyze stocks, calculate metrics, or generate articles. What would you like to know?"
    
    def _handle_stock_analysis(self, ticker_input: Optional[str], context: Optional[Dict]) -> str:
        """Provide comprehensive stock analysis."""
        # Extract ticker
        ticker = self.query_parser.extract_ticker(ticker_input or "") if ticker_input else None
        
        if not ticker and context and 'ticker' in context:
            ticker = context['ticker']
        
        if not ticker:
            return "I need a stock ticker to analyze. Please specify a ticker (e.g., TSLA, AAPL, MSFT)."
        
        # Check if we have data in context
        if not context or not context.get('price'):
            return f"I don't have current data for {ticker}. Please provide stock data or connect to a data source."
        
        # Perform analysis
        price = context.get('price', 0)
        change_pct = context.get('change_pct', 0)
        indicators = context.get('indicators', {})
        fundamentals = context.get('fundamentals', {})
        
        # Generate human-tone response
        response = f"## Analysis of {ticker}\n\n"
        
        # Price overview
        direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
        response += f"**Current Price**: ${price:.2f} ({change_pct:+.2f}%)\n\n"
        response += f"The stock is currently trending {direction}. "
        
        # Technical analysis
        if indicators:
            rsi = indicators.get('RSI', 50)
            response += self.knowledge_base.interpret_value('RSI', rsi) + ". "
            
            macd_signal = indicators.get('MACD', {}).get('signal', 'neutral')
            response += f"MACD shows {macd_signal} momentum. "
        
        # Fundamental analysis
        if fundamentals:
            pe = fundamentals.get('PE_ratio')
            if pe:
                response += f"\n\n**Valuation**: "
                response += self.knowledge_base.interpret_value('PE_ratio', pe) + ". "
        
        # Recommendation
        if indicators and fundamentals:
            rating = self.reasoning.determine_rating(
                pe_ratio=fundamentals.get('PE_ratio', 20),
                peg_ratio=fundamentals.get('PEG_ratio', 1.5),
                rsi=indicators.get('RSI', 50),
                debt_to_equity=fundamentals.get('debt_to_equity', 0.5),
                upside_pct=context.get('upside', 0)
            )
            response += f"\n\n**Recommendation**: {rating}"
        
        return response
    
    def _handle_price_question(self, ticker_input: Optional[str], context: Optional[Dict]) -> str:
        """Answer price-related questions."""
        ticker = self.query_parser.extract_ticker(ticker_input or "") if ticker_input else None
        
        if not ticker:
            return "Please specify a stock ticker (e.g., 'What's the price of TSLA?')"
        
        if context and context.get('price'):
            price = context['price']
            change = context.get('change_pct', 0)
            return f"{ticker} is currently trading at ${price:.2f}, {change:+.2f}% for the day."
        
        return f"I don't have current price data for {ticker}. Please provide the data or connect to a data source."
    
    def _handle_metric_question(self, entities: List[str], context: Optional[Dict]) -> str:
        """Answer questions about specific metrics."""
        if len(entities) < 2:
            return "I need both a metric and a ticker (e.g., 'What's the PE ratio of TSLA?')"
        
        metric = entities[0].replace(' ', '_')
        ticker_input = entities[1]
        ticker = self.query_parser.extract_ticker(ticker_input)
        
        if not context or 'fundamentals' not in context:
            return f"I don't have fundamental data for {ticker}. Please provide the data."
        
        fundamentals = context['fundamentals']
        value = fundamentals.get(metric) or fundamentals.get(metric.upper())
        
        if value:
            interpretation = self.knowledge_base.interpret_value(metric, value)
            return f"The {metric.replace('_', ' ')} for {ticker} is {value:.2f}. {interpretation}"
        
        return f"I don't have {metric} data for {ticker}."
    
    def _handle_recommendation(self, ticker_input: Optional[str], context: Optional[Dict]) -> str:
        """Provide investment recommendation."""
        ticker = self.query_parser.extract_ticker(ticker_input or "") if ticker_input else None
        
        if not ticker or not context:
            return "I need ticker and stock data to provide a recommendation."
        
        # Gather metrics
        indicators = context.get('indicators', {})
        fundamentals = context.get('fundamentals', {})
        
        rating = self.reasoning.determine_rating(
            pe_ratio=fundamentals.get('PE_ratio', 20),
            peg_ratio=fundamentals.get('PEG_ratio', 1.5),
            rsi=indicators.get('RSI', 50),
            debt_to_equity=fundamentals.get('debt_to_equity', 0.5),
            upside_pct=context.get('upside', 0)
        )
        
        # Generate human-like explanation
        response = f"## Recommendation for {ticker}: **{rating}**\n\n"
        
        if rating == "Buy":
            response += "Based on the analysis, this appears to be an attractive entry point. "
            response += "The combination of valuation metrics, technical indicators, and growth prospects suggests favorable risk-reward."
        elif rating == "Sell":
            response += "Current analysis suggests taking a defensive posture. "
            response += "Valuation concerns and technical weakness indicate limited upside potential."
        else:
            response += "A wait-and-see approach seems prudent. "
            response += "The stock shows mixed signals warranting patience before making a move."
        
        return response
    
    def _handle_comparison(self, entities: List[str], context: Optional[Dict]) -> str:
        """Compare two stocks."""
        if len(entities) < 2:
            return "I need two tickers to compare (e.g., 'Compare TSLA and AAPL')"
        
        ticker1 = self.query_parser.extract_ticker(entities[0])
        ticker2 = self.query_parser.extract_ticker(entities[1])
        
        return f"To compare {ticker1} and {ticker2}, I'll need data for both stocks. Please provide price, fundamentals, and technical indicators for each."
    
    def _handle_article_generation(self, ticker_input: Optional[str], context: Optional[Dict]) -> str:
        """Generate a complete WordPress article."""
        ticker = self.query_parser.extract_ticker(ticker_input or "") if ticker_input else None
        
        if not ticker or not context:
            return "I need a ticker and complete stock data to generate an article."
        
        if not self.text_generator:
            return "Article generation requires trained Markov models. Please train the models first."
        
        # Generate article using Markov generator
        article = self.text_generator.generate_full_summary(ticker, context)
        
        # Format for WordPress
        wordpress_article = f"# {context.get('company_name', ticker)} Stock Analysis\n\n"
        wordpress_article += f"## Overview\n{article.get('introduction', '')}\n\n"
        wordpress_article += f"## Technical Analysis\n{article.get('technical_analysis', '')}\n\n"
        wordpress_article += f"## Fundamental Analysis\n{article.get('fundamental_analysis', '')}\n\n"
        wordpress_article += f"## Valuation\n{article.get('valuation', '')}\n\n"
        wordpress_article += f"## Conclusion\n{article.get('conclusion', '')}\n\n"
        
        return wordpress_article
    
    def _handle_general_question(self, query: str, context: Optional[Dict]) -> str:
        """Handle general questions."""
        query_lower = query.lower()
        
        # Pattern matching for common questions
        if 'how' in query_lower and 'invest' in query_lower:
            return ("Investing wisely involves several key principles:\n"
                    "1. Diversify across different assets\n"
                    "2. Invest for the long term\n"
                    "3. Understand your risk tolerance\n"
                    "4. Research before investing\n"
                    "5. Consider dollar-cost averaging\n"
                    "6. Monitor but don't obsess\n\n"
                    "I can help you analyze specific stocks if you'd like!")
        
        if 'what' in query_lower and ('stock market' in query_lower or 'market' in query_lower):
            return ("The stock market is where shares of publicly traded companies are bought and sold. "
                    "It provides a platform for companies to raise capital and investors to own stakes in businesses. "
                    "Major markets include NYSE, NASDAQ, and exchanges worldwide. "
                    "Would you like me to analyze a specific stock?")
        
        # Default response
        return ("I'm a financial AI assistant specializing in stock analysis. I can:\n"
                "- Analyze stocks (e.g., 'Analyze TSLA')\n"
                "- Explain financial terms (e.g., 'What is P/E ratio?')\n"
                "- Provide recommendations (e.g., 'Should I buy AAPL?')\n"
                "- Generate WordPress articles (e.g., 'Write an article about MSFT')\n"
                "- Answer financial questions\n\n"
                "What would you like to know?")
    
    def chat(self, query: str, stock_data: Optional[Dict] = None) -> str:
        """
        Simple chat interface.
        
        Args:
            query: User's question
            stock_data: Optional stock data context
        
        Returns:
            Assistant's response
        """
        return self.ask(query, stock_data)
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()


# Convenience function for quick access
_assistant_instance = None

def get_assistant(models_dir: str = "markov_text_generation/models") -> FinancialAIAssistant:
    """Get singleton assistant instance."""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = FinancialAIAssistant(models_dir)
    return _assistant_instance


if __name__ == "__main__":
    # Demo
    assistant = FinancialAIAssistant()
    
    # Test queries
    queries = [
        "What is P/E ratio?",
        "Analyze TSLA",
        "Should I buy Apple?",
        "What's the price of MSFT?",
        "Explain bull market"
    ]
    
    for query in queries:
        print(f"\nQ: {query}")
        print(f"A: {assistant.chat(query)}")
        print("-" * 80)
