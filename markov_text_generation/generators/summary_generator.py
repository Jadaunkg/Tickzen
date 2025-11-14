"""
Financial Summary Generator
============================

Main interface for generating financial article summaries with Markov variation.
WordPress reporter integration point.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import random

from ..core.model_manager import ModelManager
from ..core.engine import MarkovEngine

logger = logging.getLogger(__name__)


class FinancialSummaryGenerator:
    """
    Main generator for financial article summaries.
    
    This is the primary integration point for WordPress reporter.
    Generates unique article sections while preserving data accuracy.
    """
    
    def __init__(self, models_dir: str, temperature: float = 0.7):
        """
        Initialize Summary Generator.
        
        Args:
            models_dir: Path to trained models directory
            temperature: Generation randomness (0.0-1.0, higher = more random)
        """
        self.manager = ModelManager(models_dir)
        self.temperature = temperature
        
        logger.info(f"FinancialSummaryGenerator initialized (temperature={temperature})")
    
    def generate_introduction(self, 
                            ticker: str,
                            company_name: str,
                            price: float,
                            change_pct: float,
                            sentiment: str = "neutral",
                            max_length: int = 150) -> str:
        """
        Generate introduction section.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Full company name
            price: Current stock price
            change_pct: Price change percentage
            sentiment: Overall sentiment ('bullish', 'bearish', 'neutral')
            max_length: Maximum word count
        
        Returns:
            Generated introduction text
        """
        model = self.manager.get_model('introduction')
        
        if not model:
            return self._fallback_introduction(ticker, company_name, price, change_pct, sentiment)
        
        # Create context-aware placeholders
        placeholders = {
            '{TICKER}': ticker,
            '{COMPANY}': company_name,
            '{PRICE}': f"${price:.2f}",
            '{CHANGE}': f"{change_pct:+.2f}%",
            '{SENTIMENT}': sentiment
        }
        
        text = model.generate_variation(
            min_length=50,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        # Replace placeholders
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_technical_analysis(self,
                                   ticker: str,
                                   indicators: Dict[str, Any],
                                   max_length: int = 200) -> str:
        """
        Generate technical analysis section.
        
        Args:
            ticker: Stock ticker symbol
            indicators: Dict of technical indicators
                Examples:
                {
                    'RSI': 68.4,
                    'MACD': {'value': 2.5, 'signal': 'bullish'},
                    'SMA_50': 245.30,
                    'SMA_200': 220.15,
                    'support': 235.00,
                    'resistance': 255.00
                }
            max_length: Maximum word count
        
        Returns:
            Generated technical analysis text
        """
        model = self.manager.get_model('technical_analysis')
        
        if not model:
            return self._fallback_technical_analysis(ticker, indicators)
        
        # Build placeholders from indicators
        placeholders = {'{TICKER}': ticker}
        
        if 'RSI' in indicators:
            placeholders['{RSI}'] = f"{indicators['RSI']:.1f}"
        if 'MACD' in indicators:
            placeholders['{MACD}'] = str(indicators['MACD'].get('value', 'N/A'))
        if 'SMA_50' in indicators:
            placeholders['{SMA50}'] = f"${indicators['SMA_50']:.2f}"
        if 'SMA_200' in indicators:
            placeholders['{SMA200}'] = f"${indicators['SMA_200']:.2f}"
        if 'support' in indicators:
            placeholders['{SUPPORT}'] = f"${indicators['support']:.2f}"
        if 'resistance' in indicators:
            placeholders['{RESISTANCE}'] = f"${indicators['resistance']:.2f}"
        
        text = model.generate_variation(
            min_length=80,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        # Replace placeholders
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_fundamental_analysis(self,
                                    ticker: str,
                                    fundamentals: Dict[str, Any],
                                    max_length: int = 200) -> str:
        """
        Generate fundamental analysis section.
        
        Args:
            ticker: Stock ticker symbol
            fundamentals: Dict of fundamental metrics
                Examples:
                {
                    'PE_ratio': 25.4,
                    'PEG_ratio': 1.8,
                    'debt_to_equity': 0.45,
                    'ROE': 15.2,
                    'profit_margin': 12.5,
                    'revenue_growth': 8.3
                }
            max_length: Maximum word count
        
        Returns:
            Generated fundamental analysis text
        """
        model = self.manager.get_model('fundamental_analysis')
        
        if not model:
            return self._fallback_fundamental_analysis(ticker, fundamentals)
        
        placeholders = {'{TICKER}': ticker}
        
        if 'PE_ratio' in fundamentals:
            placeholders['{PE}'] = f"{fundamentals['PE_ratio']:.2f}"
        if 'PEG_ratio' in fundamentals:
            placeholders['{PEG}'] = f"{fundamentals['PEG_ratio']:.2f}"
        if 'debt_to_equity' in fundamentals:
            placeholders['{DEBT_EQUITY}'] = f"{fundamentals['debt_to_equity']:.2f}"
        if 'ROE' in fundamentals:
            placeholders['{ROE}'] = f"{fundamentals['ROE']:.1f}%"
        if 'profit_margin' in fundamentals:
            placeholders['{PROFIT_MARGIN}'] = f"{fundamentals['profit_margin']:.1f}%"
        if 'revenue_growth' in fundamentals:
            placeholders['{REVENUE_GROWTH}'] = f"{fundamentals['revenue_growth']:.1f}%"
        
        text = model.generate_variation(
            min_length=80,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_valuation(self,
                         ticker: str,
                         valuation_data: Dict[str, Any],
                         max_length: int = 150) -> str:
        """
        Generate valuation section.
        
        Args:
            ticker: Stock ticker symbol
            valuation_data: Valuation metrics
                Examples:
                {
                    'fair_value': 265.00,
                    'current_price': 242.84,
                    'upside': 9.1,
                    'target_price': 270.00,
                    'analyst_rating': 'Buy'
                }
            max_length: Maximum word count
        
        Returns:
            Generated valuation text
        """
        model = self.manager.get_model('valuation')
        
        if not model:
            return self._fallback_valuation(ticker, valuation_data)
        
        placeholders = {
            '{TICKER}': ticker,
            '{FAIR_VALUE}': f"${valuation_data.get('fair_value', 0):.2f}",
            '{CURRENT_PRICE}': f"${valuation_data.get('current_price', 0):.2f}",
            '{UPSIDE}': f"{valuation_data.get('upside', 0):.1f}%",
            '{TARGET}': f"${valuation_data.get('target_price', 0):.2f}",
            '{RATING}': valuation_data.get('analyst_rating', 'N/A')
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_conclusion(self,
                          ticker: str,
                          overall_rating: str,
                          key_points: List[str],
                          max_length: int = 120) -> str:
        """
        Generate conclusion section.
        
        Args:
            ticker: Stock ticker symbol
            overall_rating: Overall rating ('Buy', 'Hold', 'Sell')
            key_points: List of key takeaways
            max_length: Maximum word count
        
        Returns:
            Generated conclusion text
        """
        model = self.manager.get_model('conclusion')
        
        if not model:
            return self._fallback_conclusion(ticker, overall_rating, key_points)
        
        placeholders = {
            '{TICKER}': ticker,
            '{RATING}': overall_rating,
            '{KEY_POINT_1}': key_points[0] if len(key_points) > 0 else '',
            '{KEY_POINT_2}': key_points[1] if len(key_points) > 1 else '',
            '{KEY_POINT_3}': key_points[2] if len(key_points) > 2 else ''
        }
        
        text = model.generate_variation(
            min_length=50,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_sector_analysis(self,
                                ticker: str,
                                sector: str,
                                industry: str,
                                market_cap: float,
                                max_length: int = 180) -> str:
        """
        Generate sector analysis section.
        
        Args:
            ticker: Stock ticker symbol
            sector: Sector name (e.g., 'Technology', 'Healthcare')
            industry: Industry name (e.g., 'Software', 'Biotechnology')
            market_cap: Market capitalization in billions
            max_length: Maximum word count
        
        Returns:
            Generated sector analysis text
        """
        model = self.manager.get_model('sector_analysis')
        
        if not model:
            return self._fallback_sector_analysis(ticker, sector, industry, market_cap)
        
        # Classify position
        if market_cap > 200:
            position = "dominant"
        elif market_cap > 50:
            position = "leading"
        elif market_cap > 10:
            position = "established"
        else:
            position = "emerging"
        
        placeholders = {
            '{TICKER}': ticker,
            '{SECTOR}': sector,
            '{INDUSTRY}': industry,
            '{MARKET_CAP}': f"${market_cap:.2f}B",
            '{POSITION}': position
        }
        
        text = model.generate_variation(
            min_length=70,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_competitive_positioning(self,
                                        ticker: str,
                                        peers: List[str],
                                        competitive_advantage: str,
                                        max_length: int = 170) -> str:
        """
        Generate competitive positioning section.
        
        Args:
            ticker: Stock ticker symbol
            peers: List of competitor tickers
            competitive_advantage: Key advantage description
            max_length: Maximum word count
        
        Returns:
            Generated competitive positioning text
        """
        model = self.manager.get_model('competitive_positioning')
        
        if not model:
            return self._fallback_competitive_positioning(ticker, peers, competitive_advantage)
        
        peers_str = ", ".join(peers[:3]) if peers else "industry peers"
        
        placeholders = {
            '{TICKER}': ticker,
            '{PEERS}': peers_str,
            '{ADVANTAGE}': competitive_advantage,
            '{NUM_PEERS}': str(len(peers))
        }
        
        text = model.generate_variation(
            min_length=70,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_growth_prospects(self,
                                 ticker: str,
                                 revenue_growth: float,
                                 earnings_growth: float,
                                 growth_drivers: List[str],
                                 max_length: int = 180) -> str:
        """
        Generate growth prospects section.
        
        Args:
            ticker: Stock ticker symbol
            revenue_growth: Revenue growth rate (%)
            earnings_growth: Earnings growth rate (%)
            growth_drivers: List of key growth drivers
            max_length: Maximum word count
        
        Returns:
            Generated growth prospects text
        """
        model = self.manager.get_model('growth_prospects')
        
        if not model:
            return self._fallback_growth_prospects(ticker, revenue_growth, earnings_growth, growth_drivers)
        
        # Classify growth
        avg_growth = (revenue_growth + earnings_growth) / 2
        if avg_growth > 20:
            outlook = "exceptional"
        elif avg_growth > 10:
            outlook = "strong"
        elif avg_growth > 5:
            outlook = "moderate"
        else:
            outlook = "limited"
        
        drivers_str = ", ".join(growth_drivers[:2]) if growth_drivers else "operational improvements"
        
        placeholders = {
            '{TICKER}': ticker,
            '{REVENUE_GROWTH}': f"{revenue_growth:.1f}%",
            '{EARNINGS_GROWTH}': f"{earnings_growth:.1f}%",
            '{OUTLOOK}': outlook,
            '{DRIVERS}': drivers_str
        }
        
        text = model.generate_variation(
            min_length=70,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_dividend_analysis(self,
                                  ticker: str,
                                  dividend_yield: float,
                                  payout_ratio: float,
                                  growth_rate: float,
                                  max_length: int = 160) -> str:
        """
        Generate dividend analysis section.
        
        Args:
            ticker: Stock ticker symbol
            dividend_yield: Current dividend yield (%)
            payout_ratio: Payout ratio (%)
            growth_rate: Dividend growth rate (%)
            max_length: Maximum word count
        
        Returns:
            Generated dividend analysis text
        """
        model = self.manager.get_model('dividend_analysis')
        
        if not model:
            return self._fallback_dividend_analysis(ticker, dividend_yield, payout_ratio, growth_rate)
        
        # Assess sustainability
        if payout_ratio > 80:
            sustainability = "stretched"
        elif payout_ratio > 60:
            sustainability = "moderate"
        else:
            sustainability = "sustainable"
        
        # Classify yield
        if dividend_yield > 4:
            yield_class = "high"
        elif dividend_yield > 2:
            yield_class = "moderate"
        else:
            yield_class = "low"
        
        placeholders = {
            '{TICKER}': ticker,
            '{YIELD}': f"{dividend_yield:.2f}%",
            '{PAYOUT}': f"{payout_ratio:.1f}%",
            '{GROWTH}': f"{growth_rate:.1f}%",
            '{SUSTAINABILITY}': sustainability,
            '{YIELD_CLASS}': yield_class
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_earnings_analysis(self,
                                  ticker: str,
                                  eps_actual: float,
                                  eps_estimate: float,
                                  quarter: str,
                                  max_length: int = 150) -> str:
        """
        Generate earnings analysis section.
        
        Args:
            ticker: Stock ticker symbol
            eps_actual: Actual EPS reported
            eps_estimate: Analyst EPS estimate
            quarter: Quarter identifier (e.g., 'Q4 2023')
            max_length: Maximum word count
        
        Returns:
            Generated earnings analysis text
        """
        model = self.manager.get_model('earnings_analysis')
        
        if not model:
            return self._fallback_earnings_analysis(ticker, eps_actual, eps_estimate, quarter)
        
        # Calculate surprise
        surprise = ((eps_actual - eps_estimate) / abs(eps_estimate) * 100) if eps_estimate != 0 else 0
        
        if surprise > 5:
            result = "beat"
        elif surprise < -5:
            result = "missed"
        else:
            result = "met"
        
        placeholders = {
            '{TICKER}': ticker,
            '{EPS_ACTUAL}': f"${eps_actual:.2f}",
            '{EPS_ESTIMATE}': f"${eps_estimate:.2f}",
            '{QUARTER}': quarter,
            '{SURPRISE}': f"{surprise:+.1f}%",
            '{RESULT}': result
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_revenue_breakdown(self,
                                  ticker: str,
                                  revenue_segments: Dict[str, float],
                                  max_length: int = 170) -> str:
        """
        Generate revenue breakdown section.
        
        Args:
            ticker: Stock ticker symbol
            revenue_segments: Dictionary of segment names to percentages
                Example: {'Products': 65.0, 'Services': 35.0}
            max_length: Maximum word count
        
        Returns:
            Generated revenue breakdown text
        """
        model = self.manager.get_model('revenue_breakdown')
        
        if not model:
            return self._fallback_revenue_breakdown(ticker, revenue_segments)
        
        # Find primary and secondary segments
        sorted_segments = sorted(revenue_segments.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_segments[0] if sorted_segments else ('N/A', 0)
        secondary = sorted_segments[1] if len(sorted_segments) > 1 else ('N/A', 0)
        
        # Assess diversification
        diversification = "highly diversified" if len(revenue_segments) >= 4 else "concentrated"
        
        placeholders = {
            '{TICKER}': ticker,
            '{PRIMARY_SEGMENT}': primary[0],
            '{PRIMARY_PCT}': f"{primary[1]:.1f}%",
            '{SECONDARY_SEGMENT}': secondary[0],
            '{SECONDARY_PCT}': f"{secondary[1]:.1f}%",
            '{DIVERSIFICATION}': diversification,
            '{NUM_SEGMENTS}': str(len(revenue_segments))
        }
        
        text = model.generate_variation(
            min_length=70,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_profit_margins(self,
                               ticker: str,
                               gross_margin: float,
                               operating_margin: float,
                               net_margin: float,
                               max_length: int = 160) -> str:
        """
        Generate profit margins section.
        
        Args:
            ticker: Stock ticker symbol
            gross_margin: Gross profit margin (%)
            operating_margin: Operating margin (%)
            net_margin: Net profit margin (%)
            max_length: Maximum word count
        
        Returns:
            Generated profit margins text
        """
        model = self.manager.get_model('profit_margins')
        
        if not model:
            return self._fallback_profit_margins(ticker, gross_margin, operating_margin, net_margin)
        
        # Assess margin quality
        if net_margin > 20:
            quality = "exceptional"
        elif net_margin > 10:
            quality = "strong"
        elif net_margin > 5:
            quality = "moderate"
        else:
            quality = "weak"
        
        placeholders = {
            '{TICKER}': ticker,
            '{GROSS_MARGIN}': f"{gross_margin:.1f}%",
            '{OPERATING_MARGIN}': f"{operating_margin:.1f}%",
            '{NET_MARGIN}': f"{net_margin:.1f}%",
            '{QUALITY}': quality
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_cash_flow_analysis(self,
                                   ticker: str,
                                   operating_cash_flow: float,
                                   free_cash_flow: float,
                                   capex: float,
                                   max_length: int = 170) -> str:
        """
        Generate cash flow analysis section.
        
        Args:
            ticker: Stock ticker symbol
            operating_cash_flow: Operating cash flow ($B)
            free_cash_flow: Free cash flow ($B)
            capex: Capital expenditures ($B)
            max_length: Maximum word count
        
        Returns:
            Generated cash flow analysis text
        """
        model = self.manager.get_model('cash_flow_analysis')
        
        if not model:
            return self._fallback_cash_flow_analysis(ticker, operating_cash_flow, free_cash_flow, capex)
        
        # Calculate FCF conversion
        fcf_conversion = (free_cash_flow / operating_cash_flow * 100) if operating_cash_flow != 0 else 0
        
        # Assess strength
        if free_cash_flow > 10:
            strength = "robust"
        elif free_cash_flow > 2:
            strength = "solid"
        elif free_cash_flow > 0:
            strength = "positive"
        else:
            strength = "negative"
        
        placeholders = {
            '{TICKER}': ticker,
            '{OCF}': f"${operating_cash_flow:.2f}B",
            '{FCF}': f"${free_cash_flow:.2f}B",
            '{CAPEX}': f"${capex:.2f}B",
            '{FCF_CONVERSION}': f"{fcf_conversion:.1f}%",
            '{STRENGTH}': strength
        }
        
        text = model.generate_variation(
            min_length=70,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_balance_sheet_strength(self,
                                       ticker: str,
                                       cash: float,
                                       debt: float,
                                       debt_to_equity: float,
                                       max_length: int = 160) -> str:
        """
        Generate balance sheet strength section.
        
        Args:
            ticker: Stock ticker symbol
            cash: Cash and equivalents ($B)
            debt: Total debt ($B)
            debt_to_equity: Debt-to-equity ratio
            max_length: Maximum word count
        
        Returns:
            Generated balance sheet strength text
        """
        model = self.manager.get_model('balance_sheet_strength')
        
        if not model:
            return self._fallback_balance_sheet_strength(ticker, cash, debt, debt_to_equity)
        
        # Calculate net debt
        net_debt = debt - cash
        
        # Assess position
        if debt_to_equity < 0.3:
            position = "fortress"
        elif debt_to_equity < 0.7:
            position = "healthy"
        elif debt_to_equity < 1.5:
            position = "moderate"
        else:
            position = "leveraged"
        
        placeholders = {
            '{TICKER}': ticker,
            '{CASH}': f"${cash:.2f}B",
            '{DEBT}': f"${debt:.2f}B",
            '{NET_DEBT}': f"${net_debt:.2f}B",
            '{DEBT_EQUITY}': f"{debt_to_equity:.2f}",
            '{POSITION}': position
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_management_quality(self,
                                   ticker: str,
                                   ceo_name: str,
                                   tenure: int,
                                   insider_ownership: float,
                                   max_length: int = 150) -> str:
        """
        Generate management quality section.
        
        Args:
            ticker: Stock ticker symbol
            ceo_name: CEO name
            tenure: CEO tenure in years
            insider_ownership: Insider ownership percentage
            max_length: Maximum word count
        
        Returns:
            Generated management quality text
        """
        model = self.manager.get_model('management_quality')
        
        if not model:
            return self._fallback_management_quality(ticker, ceo_name, tenure, insider_ownership)
        
        # Assess alignment
        if insider_ownership > 15:
            alignment = "highly aligned"
        elif insider_ownership > 5:
            alignment = "well aligned"
        else:
            alignment = "moderately aligned"
        
        # Assess experience
        if tenure > 10:
            experience = "seasoned"
        elif tenure > 5:
            experience = "experienced"
        else:
            experience = "new"
        
        placeholders = {
            '{TICKER}': ticker,
            '{CEO}': ceo_name,
            '{TENURE}': f"{tenure} years",
            '{OWNERSHIP}': f"{insider_ownership:.1f}%",
            '{ALIGNMENT}': alignment,
            '{EXPERIENCE}': experience
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_market_sentiment(self,
                                 ticker: str,
                                 momentum: str,
                                 volume_trend: str,
                                 short_interest: float,
                                 max_length: int = 150) -> str:
        """
        Generate market sentiment section.
        
        Args:
            ticker: Stock ticker symbol
            momentum: Momentum indicator ('bullish', 'bearish', 'neutral')
            volume_trend: Volume trend ('increasing', 'decreasing', 'stable')
            short_interest: Short interest as % of float
            max_length: Maximum word count
        
        Returns:
            Generated market sentiment text
        """
        model = self.manager.get_model('market_sentiment')
        
        if not model:
            return self._fallback_market_sentiment(ticker, momentum, volume_trend, short_interest)
        
        # Assess sentiment
        if short_interest > 10:
            sentiment = "heavily shorted"
        elif short_interest > 5:
            sentiment = "moderately shorted"
        else:
            sentiment = "lightly shorted"
        
        placeholders = {
            '{TICKER}': ticker,
            '{MOMENTUM}': momentum,
            '{VOLUME}': volume_trend,
            '{SHORT_INTEREST}': f"{short_interest:.1f}%",
            '{SENTIMENT}': sentiment
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_analyst_consensus(self,
                                  ticker: str,
                                  avg_rating: str,
                                  num_analysts: int,
                                  target_price: float,
                                  current_price: float,
                                  max_length: int = 150) -> str:
        """
        Generate analyst consensus section.
        
        Args:
            ticker: Stock ticker symbol
            avg_rating: Average rating ('Strong Buy', 'Buy', 'Hold', etc.)
            num_analysts: Number of analysts covering
            target_price: Average analyst target price
            current_price: Current stock price
            max_length: Maximum word count
        
        Returns:
            Generated analyst consensus text
        """
        model = self.manager.get_model('analyst_consensus')
        
        if not model:
            return self._fallback_analyst_consensus(ticker, avg_rating, num_analysts, target_price, current_price)
        
        # Calculate upside
        upside = ((target_price - current_price) / current_price * 100) if current_price != 0 else 0
        
        placeholders = {
            '{TICKER}': ticker,
            '{RATING}': avg_rating,
            '{NUM_ANALYSTS}': str(num_analysts),
            '{TARGET}': f"${target_price:.2f}",
            '{CURRENT}': f"${current_price:.2f}",
            '{UPSIDE}': f"{upside:+.1f}%"
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_historical_performance(self,
                                       ticker: str,
                                       return_1y: float,
                                       return_3y: float,
                                       return_5y: float,
                                       benchmark: str = "S&P 500",
                                       max_length: int = 160) -> str:
        """
        Generate historical performance section.
        
        Args:
            ticker: Stock ticker symbol
            return_1y: 1-year return (%)
            return_3y: 3-year annualized return (%)
            return_5y: 5-year annualized return (%)
            benchmark: Benchmark name
            max_length: Maximum word count
        
        Returns:
            Generated historical performance text
        """
        model = self.manager.get_model('historical_performance')
        
        if not model:
            return self._fallback_historical_performance(ticker, return_1y, return_3y, return_5y, benchmark)
        
        # Assess performance
        if return_5y > 15:
            track_record = "exceptional"
        elif return_5y > 10:
            track_record = "strong"
        elif return_5y > 5:
            track_record = "moderate"
        else:
            track_record = "weak"
        
        placeholders = {
            '{TICKER}': ticker,
            '{RETURN_1Y}': f"{return_1y:+.1f}%",
            '{RETURN_3Y}': f"{return_3y:+.1f}%",
            '{RETURN_5Y}': f"{return_5y:+.1f}%",
            '{BENCHMARK}': benchmark,
            '{TRACK_RECORD}': track_record
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_future_catalysts(self,
                                 ticker: str,
                                 catalysts: List[str],
                                 timing: str,
                                 max_length: int = 160) -> str:
        """
        Generate future catalysts section.
        
        Args:
            ticker: Stock ticker symbol
            catalysts: List of upcoming catalysts
            timing: Timing description ('near-term', 'medium-term', 'long-term')
            max_length: Maximum word count
        
        Returns:
            Generated future catalysts text
        """
        model = self.manager.get_model('future_catalysts')
        
        if not model:
            return self._fallback_future_catalysts(ticker, catalysts, timing)
        
        primary_catalyst = catalysts[0] if catalysts else "operational improvements"
        secondary_catalyst = catalysts[1] if len(catalysts) > 1 else "market expansion"
        
        placeholders = {
            '{TICKER}': ticker,
            '{PRIMARY_CATALYST}': primary_catalyst,
            '{SECONDARY_CATALYST}': secondary_catalyst,
            '{TIMING}': timing,
            '{NUM_CATALYSTS}': str(len(catalysts))
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_regulatory_environment(self,
                                       ticker: str,
                                       sector: str,
                                       regulatory_risk: str,
                                       max_length: int = 150) -> str:
        """
        Generate regulatory environment section.
        
        Args:
            ticker: Stock ticker symbol
            sector: Sector name
            regulatory_risk: Risk level ('low', 'moderate', 'high')
            max_length: Maximum word count
        
        Returns:
            Generated regulatory environment text
        """
        model = self.manager.get_model('regulatory_environment')
        
        if not model:
            return self._fallback_regulatory_environment(ticker, sector, regulatory_risk)
        
        # Assess intensity by sector
        high_reg_sectors = ['Financial Services', 'Healthcare', 'Utilities', 'Energy']
        intensity = "heavy" if sector in high_reg_sectors else "moderate"
        
        placeholders = {
            '{TICKER}': ticker,
            '{SECTOR}': sector,
            '{RISK}': regulatory_risk,
            '{INTENSITY}': intensity
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_esg_sustainability(self,
                                   ticker: str,
                                   esg_score: float,
                                   e_score: float,
                                   s_score: float,
                                   g_score: float,
                                   max_length: int = 160) -> str:
        """
        Generate ESG & sustainability section.
        
        Args:
            ticker: Stock ticker symbol
            esg_score: Overall ESG score (0-100)
            e_score: Environmental score
            s_score: Social score
            g_score: Governance score
            max_length: Maximum word count
        
        Returns:
            Generated ESG sustainability text
        """
        model = self.manager.get_model('esg_sustainability')
        
        if not model:
            return self._fallback_esg_sustainability(ticker, esg_score, e_score, s_score, g_score)
        
        # Assess rating
        if esg_score > 70:
            rating = "leader"
        elif esg_score > 50:
            rating = "above average"
        elif esg_score > 30:
            rating = "average"
        else:
            rating = "laggard"
        
        # Find strongest pillar
        scores = {'Environmental': e_score, 'Social': s_score, 'Governance': g_score}
        strongest = max(scores, key=scores.get)
        
        placeholders = {
            '{TICKER}': ticker,
            '{ESG_SCORE}': f"{esg_score:.1f}",
            '{E_SCORE}': f"{e_score:.1f}",
            '{S_SCORE}': f"{s_score:.1f}",
            '{G_SCORE}': f"{g_score:.1f}",
            '{RATING}': rating,
            '{STRONGEST}': strongest
        }
        
        text = model.generate_variation(
            min_length=60,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_investment_thesis(self,
                                  ticker: str,
                                  thesis_pillars: List[str],
                                  outlook: str,
                                  risk_reward: str,
                                  max_length: int = 180) -> str:
        """
        Generate investment thesis section.
        
        Args:
            ticker: Stock ticker symbol
            thesis_pillars: List of key thesis points
            outlook: Outlook description ('bullish', 'neutral', 'bearish')
            risk_reward: Risk-reward assessment ('favorable', 'balanced', 'unfavorable')
            max_length: Maximum word count
        
        Returns:
            Generated investment thesis text
        """
        model = self.manager.get_model('investment_thesis')
        
        if not model:
            return self._fallback_investment_thesis(ticker, thesis_pillars, outlook, risk_reward)
        
        pillar_1 = thesis_pillars[0] if len(thesis_pillars) > 0 else "financial strength"
        pillar_2 = thesis_pillars[1] if len(thesis_pillars) > 1 else "market position"
        pillar_3 = thesis_pillars[2] if len(thesis_pillars) > 2 else "growth prospects"
        
        placeholders = {
            '{TICKER}': ticker,
            '{PILLAR_1}': pillar_1,
            '{PILLAR_2}': pillar_2,
            '{PILLAR_3}': pillar_3,
            '{OUTLOOK}': outlook,
            '{RISK_REWARD}': risk_reward,
            '{NUM_PILLARS}': str(len(thesis_pillars))
        }
        
        text = model.generate_variation(
            min_length=70,
            max_length=max_length,
            temperature=self.temperature,
            preserve_patterns=list(placeholders.keys())
        )
        
        for placeholder, value in placeholders.items():
            text = text.replace(placeholder, value)
        
        return text
    
    def generate_full_summary(self,
                            ticker: str,
                            data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate complete article with all 23 sections.
        
        Args:
            ticker: Stock ticker symbol
            data: Complete data dictionary with all sections
                Expected structure:
                {
                    # Introduction
                    'company_name': str,
                    'price': float,
                    'change_pct': float,
                    'sentiment': str,
                    
                    # Technical Analysis
                    'indicators': {...},
                    
                    # Fundamental Analysis
                    'fundamentals': {...},
                    
                    # Valuation
                    'valuation': {...},
                    
                    # Sector Analysis
                    'sector': str,
                    'industry': str,
                    'market_cap': float,
                    
                    # Competitive Positioning
                    'peers': [...],
                    'competitive_advantage': str,
                    
                    # Growth Prospects
                    'revenue_growth': float,
                    'earnings_growth': float,
                    'growth_drivers': [...],
                    
                    # Dividend Analysis
                    'dividend_yield': float,
                    'payout_ratio': float,
                    'dividend_growth_rate': float,
                    
                    # Earnings Analysis
                    'eps_actual': float,
                    'eps_estimate': float,
                    'quarter': str,
                    
                    # Revenue Breakdown
                    'revenue_segments': {...},
                    
                    # Profit Margins
                    'gross_margin': float,
                    'operating_margin': float,
                    'net_margin': float,
                    
                    # Cash Flow Analysis
                    'operating_cash_flow': float,
                    'free_cash_flow': float,
                    'capex': float,
                    
                    # Balance Sheet Strength
                    'cash': float,
                    'debt': float,
                    'debt_to_equity': float,
                    
                    # Management Quality
                    'ceo_name': str,
                    'ceo_tenure': int,
                    'insider_ownership': float,
                    
                    # Market Sentiment
                    'momentum': str,
                    'volume_trend': str,
                    'short_interest': float,
                    
                    # Analyst Consensus
                    'analyst_rating': str,
                    'num_analysts': int,
                    'target_price': float,
                    
                    # Historical Performance
                    'return_1y': float,
                    'return_3y': float,
                    'return_5y': float,
                    'benchmark': str,
                    
                    # Future Catalysts
                    'catalysts': [...],
                    'catalyst_timing': str,
                    
                    # Regulatory Environment
                    'regulatory_risk': str,
                    
                    # ESG Sustainability
                    'esg_score': float,
                    'e_score': float,
                    's_score': float,
                    'g_score': float,
                    
                    # Investment Thesis
                    'thesis_pillars': [...],
                    'outlook': str,
                    'risk_reward': str,
                    
                    # Conclusion
                    'rating': str,
                    'key_points': [...]
                }
        
        Returns:
            Dictionary with generated sections (23 sections):
            {
                'introduction': str,
                'technical_analysis': str,
                'fundamental_analysis': str,
                'sector_analysis': str,
                'competitive_positioning': str,
                'growth_prospects': str,
                'revenue_breakdown': str,
                'profit_margins': str,
                'earnings_analysis': str,
                'dividend_analysis': str,
                'cash_flow_analysis': str,
                'balance_sheet_strength': str,
                'management_quality': str,
                'valuation': str,
                'analyst_consensus': str,
                'market_sentiment': str,
                'historical_performance': str,
                'future_catalysts': str,
                'regulatory_environment': str,
                'esg_sustainability': str,
                'investment_thesis': str,
                'conclusion': str
            }
        """
        summary = {}
        
        # 1. Introduction
        if 'company_name' in data:
            summary['introduction'] = self.generate_introduction(
                ticker=ticker,
                company_name=data['company_name'],
                price=data.get('price', 0),
                change_pct=data.get('change_pct', 0),
                sentiment=data.get('sentiment', 'neutral')
            )
        
        # 2. Technical Analysis
        if 'indicators' in data:
            summary['technical_analysis'] = self.generate_technical_analysis(
                ticker=ticker,
                indicators=data['indicators']
            )
        
        # 3. Fundamental Analysis
        if 'fundamentals' in data:
            summary['fundamental_analysis'] = self.generate_fundamental_analysis(
                ticker=ticker,
                fundamentals=data['fundamentals']
            )
        
        # 4. Sector Analysis
        if 'sector' in data and 'industry' in data:
            summary['sector_analysis'] = self.generate_sector_analysis(
                ticker=ticker,
                sector=data['sector'],
                industry=data['industry'],
                market_cap=data.get('market_cap', 0)
            )
        
        # 5. Competitive Positioning
        if 'peers' in data:
            summary['competitive_positioning'] = self.generate_competitive_positioning(
                ticker=ticker,
                peers=data['peers'],
                competitive_advantage=data.get('competitive_advantage', 'operational excellence')
            )
        
        # 6. Growth Prospects
        if 'revenue_growth' in data and 'earnings_growth' in data:
            summary['growth_prospects'] = self.generate_growth_prospects(
                ticker=ticker,
                revenue_growth=data['revenue_growth'],
                earnings_growth=data['earnings_growth'],
                growth_drivers=data.get('growth_drivers', [])
            )
        
        # 7. Revenue Breakdown
        if 'revenue_segments' in data:
            summary['revenue_breakdown'] = self.generate_revenue_breakdown(
                ticker=ticker,
                revenue_segments=data['revenue_segments']
            )
        
        # 8. Profit Margins
        if 'gross_margin' in data:
            summary['profit_margins'] = self.generate_profit_margins(
                ticker=ticker,
                gross_margin=data['gross_margin'],
                operating_margin=data.get('operating_margin', 0),
                net_margin=data.get('net_margin', 0)
            )
        
        # 9. Earnings Analysis
        if 'eps_actual' in data and 'eps_estimate' in data:
            summary['earnings_analysis'] = self.generate_earnings_analysis(
                ticker=ticker,
                eps_actual=data['eps_actual'],
                eps_estimate=data['eps_estimate'],
                quarter=data.get('quarter', 'Q4 2023')
            )
        
        # 10. Dividend Analysis
        if 'dividend_yield' in data:
            summary['dividend_analysis'] = self.generate_dividend_analysis(
                ticker=ticker,
                dividend_yield=data['dividend_yield'],
                payout_ratio=data.get('payout_ratio', 0),
                growth_rate=data.get('dividend_growth_rate', 0)
            )
        
        # 11. Cash Flow Analysis
        if 'operating_cash_flow' in data:
            summary['cash_flow_analysis'] = self.generate_cash_flow_analysis(
                ticker=ticker,
                operating_cash_flow=data['operating_cash_flow'],
                free_cash_flow=data.get('free_cash_flow', 0),
                capex=data.get('capex', 0)
            )
        
        # 12. Balance Sheet Strength
        if 'cash' in data and 'debt' in data:
            summary['balance_sheet_strength'] = self.generate_balance_sheet_strength(
                ticker=ticker,
                cash=data['cash'],
                debt=data['debt'],
                debt_to_equity=data.get('debt_to_equity', 0)
            )
        
        # 13. Management Quality
        if 'ceo_name' in data:
            summary['management_quality'] = self.generate_management_quality(
                ticker=ticker,
                ceo_name=data['ceo_name'],
                tenure=data.get('ceo_tenure', 0),
                insider_ownership=data.get('insider_ownership', 0)
            )
        
        # 14. Valuation
        if 'valuation' in data:
            summary['valuation'] = self.generate_valuation(
                ticker=ticker,
                valuation_data=data['valuation']
            )
        
        # 15. Analyst Consensus
        if 'analyst_rating' in data:
            summary['analyst_consensus'] = self.generate_analyst_consensus(
                ticker=ticker,
                avg_rating=data['analyst_rating'],
                num_analysts=data.get('num_analysts', 0),
                target_price=data.get('target_price', 0),
                current_price=data.get('price', 0)
            )
        
        # 16. Market Sentiment
        if 'momentum' in data:
            summary['market_sentiment'] = self.generate_market_sentiment(
                ticker=ticker,
                momentum=data['momentum'],
                volume_trend=data.get('volume_trend', 'stable'),
                short_interest=data.get('short_interest', 0)
            )
        
        # 17. Historical Performance
        if 'return_1y' in data:
            summary['historical_performance'] = self.generate_historical_performance(
                ticker=ticker,
                return_1y=data['return_1y'],
                return_3y=data.get('return_3y', 0),
                return_5y=data.get('return_5y', 0),
                benchmark=data.get('benchmark', 'S&P 500')
            )
        
        # 18. Future Catalysts
        if 'catalysts' in data:
            summary['future_catalysts'] = self.generate_future_catalysts(
                ticker=ticker,
                catalysts=data['catalysts'],
                timing=data.get('catalyst_timing', 'near-term')
            )
        
        # 19. Regulatory Environment
        if 'sector' in data:
            summary['regulatory_environment'] = self.generate_regulatory_environment(
                ticker=ticker,
                sector=data['sector'],
                regulatory_risk=data.get('regulatory_risk', 'moderate')
            )
        
        # 20. ESG Sustainability
        if 'esg_score' in data:
            summary['esg_sustainability'] = self.generate_esg_sustainability(
                ticker=ticker,
                esg_score=data['esg_score'],
                e_score=data.get('e_score', 0),
                s_score=data.get('s_score', 0),
                g_score=data.get('g_score', 0)
            )
        
        # 21. Investment Thesis
        if 'thesis_pillars' in data:
            summary['investment_thesis'] = self.generate_investment_thesis(
                ticker=ticker,
                thesis_pillars=data['thesis_pillars'],
                outlook=data.get('outlook', 'neutral'),
                risk_reward=data.get('risk_reward', 'balanced')
            )
        
        # 22. Conclusion
        if 'rating' in data and 'key_points' in data:
            summary['conclusion'] = self.generate_conclusion(
                ticker=ticker,
                overall_rating=data['rating'],
                key_points=data['key_points']
            )
        
        logger.info(f"Generated full summary for {ticker} with {len(summary)} sections")
        return summary
    
    # Fallback methods (when models not available)
    
    def _fallback_introduction(self, ticker, company, price, change, sentiment):
        templates = [
            f"{company} ({ticker}) is trading at ${price:.2f}, {change:+.2f}% with {sentiment} momentum.",
            f"Shares of {ticker} are priced at ${price:.2f}, showing {change:+.2f}% movement with {sentiment} signals.",
            f"{ticker} stock is currently valued at ${price:.2f}, reflecting {change:+.2f}% change and {sentiment} outlook."
        ]
        return random.choice(templates)
    
    def _fallback_technical_analysis(self, ticker, indicators):
        rsi = indicators.get('RSI', 50)
        return f"Technical indicators for {ticker} show RSI at {rsi:.1f} with mixed signals across momentum metrics."
    
    def _fallback_fundamental_analysis(self, ticker, fundamentals):
        pe = fundamentals.get('PE_ratio', 0)
        return f"Fundamental analysis reveals {ticker} trading at P/E ratio of {pe:.2f} with solid financial metrics."
    
    def _fallback_valuation(self, ticker, valuation):
        upside = valuation.get('upside', 0)
        return f"Valuation suggests {ticker} has {upside:.1f}% potential upside based on current metrics."
    
    def _fallback_conclusion(self, ticker, rating, points):
        return f"Overall assessment for {ticker} indicates {rating} rating based on comprehensive analysis."
    
    def _fallback_sector_analysis(self, ticker, sector, industry, market_cap):
        return f"{ticker} operates in the {industry} industry within the broader {sector} sector with ${market_cap:.2f}B market cap."
    
    def _fallback_competitive_positioning(self, ticker, peers, advantage):
        return f"{ticker} competes with {len(peers)} major players, leveraging {advantage} as key differentiator."
    
    def _fallback_growth_prospects(self, ticker, revenue_growth, earnings_growth, drivers):
        return f"{ticker} shows {revenue_growth:.1f}% revenue growth and {earnings_growth:.1f}% earnings expansion."
    
    def _fallback_dividend_analysis(self, ticker, dividend_yield, payout_ratio, growth_rate):
        return f"{ticker} offers {dividend_yield:.2f}% yield with {payout_ratio:.1f}% payout ratio and {growth_rate:.1f}% growth."
    
    def _fallback_earnings_analysis(self, ticker, eps_actual, eps_estimate, quarter):
        return f"{ticker} reported ${eps_actual:.2f} EPS vs. ${eps_estimate:.2f} estimate for {quarter}."
    
    def _fallback_revenue_breakdown(self, ticker, segments):
        return f"{ticker} generates revenue across {len(segments)} business segments with diversified operations."
    
    def _fallback_profit_margins(self, ticker, gross, operating, net):
        return f"{ticker} maintains {gross:.1f}% gross, {operating:.1f}% operating, and {net:.1f}% net margins."
    
    def _fallback_cash_flow_analysis(self, ticker, ocf, fcf, capex):
        return f"{ticker} generated ${ocf:.2f}B operating cash flow and ${fcf:.2f}B free cash flow."
    
    def _fallback_balance_sheet_strength(self, ticker, cash, debt, debt_equity):
        return f"{ticker} holds ${cash:.2f}B cash against ${debt:.2f}B debt with {debt_equity:.2f} debt-to-equity ratio."
    
    def _fallback_management_quality(self, ticker, ceo, tenure, ownership):
        return f"{ticker} is led by {ceo} with {tenure} years tenure and {ownership:.1f}% insider ownership."
    
    def _fallback_market_sentiment(self, ticker, momentum, volume, short_interest):
        return f"{ticker} shows {momentum} momentum with {volume} volume trends and {short_interest:.1f}% short interest."
    
    def _fallback_analyst_consensus(self, ticker, rating, num, target, current):
        return f"{num} analysts rate {ticker} as {rating} with ${target:.2f} average target vs. ${current:.2f} current."
    
    def _fallback_historical_performance(self, ticker, r1y, r3y, r5y, benchmark):
        return f"{ticker} delivered {r1y:+.1f}% (1Y), {r3y:+.1f}% (3Y), {r5y:+.1f}% (5Y) returns vs. {benchmark}."
    
    def _fallback_future_catalysts(self, ticker, catalysts, timing):
        return f"{ticker} has {len(catalysts)} identified catalysts expected in {timing} timeframe."
    
    def _fallback_regulatory_environment(self, ticker, sector, risk):
        return f"{ticker} operates in {sector} with {risk} regulatory risk profile."
    
    def _fallback_esg_sustainability(self, ticker, esg, e, s, g):
        return f"{ticker} scores {esg:.1f} overall ESG rating (E:{e:.1f}, S:{s:.1f}, G:{g:.1f})."
    
    def _fallback_investment_thesis(self, ticker, pillars, outlook, risk_reward):
        return f"{ticker} investment thesis rests on {len(pillars)} pillars with {outlook} outlook and {risk_reward} risk-reward."


# Singleton instance for easy access
_generator_instance = None

def get_generator(models_dir: Optional[str] = None, 
                 temperature: float = 0.7) -> FinancialSummaryGenerator:
    """
    Get singleton generator instance.
    
    Args:
        models_dir: Path to models (required on first call)
        temperature: Generation temperature
    
    Returns:
        FinancialSummaryGenerator instance
    """
    global _generator_instance
    
    if _generator_instance is None:
        if models_dir is None:
            raise ValueError("models_dir required for first initialization")
        _generator_instance = FinancialSummaryGenerator(models_dir, temperature)
    
    return _generator_instance
