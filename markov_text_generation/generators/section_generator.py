"""
Section Generator
=================

Specialized generators for individual article sections.
Provides more fine-grained control over section generation.
"""

import random
from typing import Dict, List, Any, Optional
from ..core.engine import MarkovEngine


class SectionGenerator:
    """Base class for section-specific generators."""
    
    def __init__(self, model: MarkovEngine, temperature: float = 0.7):
        self.model = model
        self.temperature = temperature
    
    def generate(self, **kwargs) -> str:
        """Generate section text. Override in subclasses."""
        raise NotImplementedError


class IntroductionGenerator(SectionGenerator):
    """Generate varied introduction sections."""
    
    TEMPLATES = [
        "{COMPANY} ({TICKER}) is currently trading at {PRICE}, showing {CHANGE} {DIRECTION} with {SENTIMENT} market signals.",
        "Shares of {TICKER} are priced at {PRICE}, reflecting {CHANGE} {DIRECTION} amid {SENTIMENT} investor sentiment.",
        "{TICKER} stock stands at {PRICE}, marking {CHANGE} {DIRECTION} while maintaining {SENTIMENT} outlook.",
        "Trading at {PRICE}, {COMPANY} ({TICKER}) has moved {CHANGE} {DIRECTION}, indicating {SENTIMENT} momentum.",
        "{COMPANY} shares ({TICKER}) are valued at {PRICE}, demonstrating {CHANGE} {DIRECTION} with {SENTIMENT} indicators."
    ]
    
    def generate(self,
                ticker: str,
                company: str,
                price: float,
                change_pct: float,
                sentiment: str = "neutral") -> str:
        """
        Generate introduction with template variation.
        
        Args:
            ticker: Stock ticker
            company: Company name
            price: Current price
            change_pct: Price change percentage
            sentiment: Market sentiment
        
        Returns:
            Generated introduction
        """
        # Determine direction
        direction = "higher" if change_pct > 0 else "lower" if change_pct < 0 else "flat"
        
        # Select template
        template = random.choice(self.TEMPLATES)
        
        # Generate additional context if model available
        if self.model and self.model.chain:
            context = self.model.generate_variation(
                min_length=30,
                max_length=100,
                temperature=self.temperature,
                preserve_patterns=['{TICKER}', '{PRICE}', '{CHANGE}']
            )
        else:
            context = template
        
        # Fill placeholders
        text = template.format(
            COMPANY=company,
            TICKER=ticker,
            PRICE=f"${price:.2f}",
            CHANGE=f"{abs(change_pct):.2f}%",
            DIRECTION=direction,
            SENTIMENT=sentiment
        )
        
        return text


class TechnicalAnalysisGenerator(SectionGenerator):
    """Generate technical analysis sections."""
    
    RSI_INTERPRETATIONS = {
        'overbought': ['overbought territory', 'elevated levels', 'extended readings'],
        'neutral': ['neutral zone', 'balanced levels', 'midrange values'],
        'oversold': ['oversold conditions', 'depressed levels', 'compressed readings']
    }
    
    MACD_SIGNALS = {
        'bullish': ['bullish crossover', 'positive divergence', 'upward momentum'],
        'bearish': ['bearish signal', 'negative divergence', 'downward pressure'],
        'neutral': ['sideways action', 'range-bound behavior', 'mixed signals']
    }
    
    def generate(self,
                ticker: str,
                indicators: Dict[str, Any]) -> str:
        """
        Generate technical analysis section.
        
        Args:
            ticker: Stock ticker
            indicators: Technical indicators dict
        
        Returns:
            Generated technical analysis
        """
        parts = []
        
        # RSI analysis
        if 'RSI' in indicators:
            rsi = indicators['RSI']
            rsi_state = 'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'
            rsi_desc = random.choice(self.RSI_INTERPRETATIONS[rsi_state])
            
            parts.append(f"The RSI indicator for {ticker} reads {rsi:.1f}, suggesting {rsi_desc}.")
        
        # MACD analysis
        if 'MACD' in indicators:
            macd_data = indicators['MACD']
            signal = macd_data.get('signal', 'neutral')
            macd_desc = random.choice(self.MACD_SIGNALS.get(signal, ['mixed signals']))
            
            parts.append(f"MACD analysis indicates {macd_desc} for {ticker}.")
        
        # Moving averages
        if 'SMA_50' in indicators and 'SMA_200' in indicators:
            sma50 = indicators['SMA_50']
            sma200 = indicators['SMA_200']
            
            if sma50 > sma200:
                ma_signal = "bullish golden cross formation"
            elif sma50 < sma200:
                ma_signal = "bearish death cross pattern"
            else:
                ma_signal = "convergence of key moving averages"
            
            parts.append(f"The 50-day moving average at ${sma50:.2f} versus the 200-day at ${sma200:.2f} suggests {ma_signal}.")
        
        # Support and resistance
        if 'support' in indicators and 'resistance' in indicators:
            support = indicators['support']
            resistance = indicators['resistance']
            
            parts.append(f"Key support is identified at ${support:.2f}, with resistance around ${resistance:.2f}.")
        
        # Generate with model variation if available
        if self.model and self.model.chain and len(parts) > 0:
            # Get model-generated connecting phrases
            base_text = " ".join(parts)
            varied = self.model.generate_variation(
                min_length=len(base_text.split()) - 20,
                max_length=len(base_text.split()) + 30,
                temperature=self.temperature
            )
            return varied if varied else base_text
        
        return " ".join(parts)


class FundamentalAnalysisGenerator(SectionGenerator):
    """Generate fundamental analysis sections."""
    
    PE_ASSESSMENT = {
        'undervalued': ['attractive valuation', 'compelling entry point', 'discounted levels'],
        'fair': ['reasonable valuation', 'fair market value', 'appropriate pricing'],
        'overvalued': ['premium valuation', 'elevated multiples', 'stretched pricing']
    }
    
    def generate(self,
                ticker: str,
                fundamentals: Dict[str, Any]) -> str:
        """Generate fundamental analysis."""
        parts = []
        
        # P/E analysis
        if 'PE_ratio' in fundamentals:
            pe = fundamentals['PE_ratio']
            pe_state = 'undervalued' if pe < 15 else 'overvalued' if pe > 25 else 'fair'
            pe_desc = random.choice(self.PE_ASSESSMENT[pe_state])
            
            parts.append(f"{ticker} trades at a P/E ratio of {pe:.2f}, indicating {pe_desc}.")
        
        # Profitability metrics
        if 'profit_margin' in fundamentals:
            margin = fundamentals['profit_margin']
            margin_quality = "strong" if margin > 15 else "modest" if margin > 5 else "thin"
            
            parts.append(f"The company maintains {margin_quality} profit margins at {margin:.1f}%.")
        
        # Growth metrics
        if 'revenue_growth' in fundamentals:
            growth = fundamentals['revenue_growth']
            growth_desc = "robust" if growth > 10 else "moderate" if growth > 0 else "negative"
            
            parts.append(f"Revenue growth of {growth:.1f}% demonstrates {growth_desc} expansion.")
        
        # Return metrics
        if 'ROE' in fundamentals:
            roe = fundamentals['ROE']
            roe_quality = "excellent" if roe > 15 else "adequate" if roe > 10 else "below-par"
            
            parts.append(f"Return on equity stands at {roe:.1f}%, reflecting {roe_quality} capital efficiency.")
        
        # Leverage
        if 'debt_to_equity' in fundamentals:
            de = fundamentals['debt_to_equity']
            de_level = "conservative" if de < 0.5 else "moderate" if de < 1.0 else "elevated"
            
            parts.append(f"With a debt-to-equity ratio of {de:.2f}, the balance sheet shows {de_level} leverage.")
        
        return " ".join(parts)


class ValuationGenerator(SectionGenerator):
    """Generate valuation sections."""
    
    UPSIDE_PHRASES = {
        'high': ['significant upside potential', 'substantial appreciation opportunity', 'compelling reward scenario'],
        'moderate': ['reasonable upside', 'modest appreciation potential', 'balanced risk-reward'],
        'low': ['limited upside', 'minimal appreciation potential', 'range-bound outlook']
    }
    
    def generate(self,
                ticker: str,
                valuation_data: Dict[str, Any]) -> str:
        """Generate valuation analysis."""
        fair_value = valuation_data.get('fair_value', 0)
        current_price = valuation_data.get('current_price', 0)
        upside = valuation_data.get('upside', 0)
        target = valuation_data.get('target_price', 0)
        rating = valuation_data.get('analyst_rating', 'Hold')
        
        # Determine upside category
        upside_level = 'high' if upside > 15 else 'moderate' if upside > 5 else 'low'
        upside_phrase = random.choice(self.UPSIDE_PHRASES[upside_level])
        
        parts = [
            f"Based on comprehensive analysis, {ticker} appears to have a fair value estimate around ${fair_value:.2f}.",
            f"Compared to the current price of ${current_price:.2f}, this suggests {upside_phrase} of approximately {upside:.1f}%.",
            f"Analysts have set a consensus price target of ${target:.2f}, supporting a {rating} rating."
        ]
        
        return " ".join(parts)


class ConclusionGenerator(SectionGenerator):
    """Generate conclusion sections."""
    
    RATING_FRAMES = {
        'Buy': ['favorable investment opportunity', 'attractive entry point', 'compelling buy case'],
        'Hold': ['current positioning', 'wait-and-see approach', 'maintained exposure'],
        'Sell': ['risk management', 'profit-taking opportunity', 'defensive posture']
    }
    
    def generate(self,
                ticker: str,
                rating: str,
                key_points: List[str]) -> str:
        """Generate conclusion."""
        rating_frame = random.choice(self.RATING_FRAMES.get(rating, ['balanced approach']))
        
        points_text = ""
        if key_points:
            if len(key_points) == 1:
                points_text = f"Key consideration includes {key_points[0]}."
            elif len(key_points) == 2:
                points_text = f"Key considerations include {key_points[0]} and {key_points[1]}."
            else:
                points_text = f"Key considerations include {key_points[0]}, {key_points[1]}, and {key_points[2]}."
        
        parts = [
            f"In summary, {ticker} presents {rating_frame} for investors.",
            points_text if points_text else "",
            f"The overall assessment maintains a {rating} rating based on current market conditions and fundamental analysis."
        ]
        
        return " ".join([p for p in parts if p])


class SectorAnalysisGenerator(SectionGenerator):
    """Generate sector and industry analysis sections."""
    
    def generate(self,
                ticker: str,
                sector: str,
                industry: str,
                market_cap: float = None) -> str:
        """Generate sector analysis."""
        # Determine market position based on market cap
        position = "leading"
        if market_cap:
            if market_cap > 200e9:  # >$200B
                position = "leading"
            elif market_cap > 50e9:  # $50-200B
                position = "strong"
            elif market_cap > 10e9:  # $10-50B
                position = "established"
            else:
                position = "emerging"
        
        # Simple sector trend classification (can be enhanced with actual data)
        sector_trend = "growth-oriented"
        
        parts = []
        parts.append(f"{ticker} operates in the {sector} sector, specifically within the {industry} industry, "
                    f"where {position} positioning defines its competitive landscape.")
        
        # Add sector context
        if sector.lower() in ['technology', 'healthcare', 'communication services']:
            parts.append(f"The {sector} sector currently exhibits growth-oriented trends with strong innovation dynamics.")
        elif sector.lower() in ['utilities', 'consumer staples']:
            parts.append(f"The {sector} sector represents a mature, stable market with consistent demand patterns.")
        elif sector.lower() in ['energy', 'materials']:
            parts.append(f"The {sector} sector experiences cyclical dynamics influenced by commodity prices and global demand.")
        else:
            parts.append(f"The {sector} sector maintains varied characteristics depending on economic conditions.")
        
        return " ".join(parts)


class CompetitivePositioningGenerator(SectionGenerator):
    """Generate competitive positioning analysis."""
    
    def generate(self,
                ticker: str,
                peers: List[str] = None,
                competitive_advantage: str = None) -> str:
        """Generate competitive positioning."""
        if not peers:
            peers = ["industry peers"]
        
        peer_list = ", ".join(peers[:3]) if len(peers) > 1 else peers[0] if peers else "competitors"
        
        advantage = competitive_advantage or "operational efficiency and brand strength"
        
        parts = []
        parts.append(f"{ticker} competes with key rivals including {peer_list}, "
                    f"where it differentiates through {advantage}.")
        
        parts.append(f"The competitive landscape remains dynamic, with {ticker} focusing on "
                    f"innovation and market execution to maintain its position.")
        
        return " ".join(parts)


class GrowthProspectsGenerator(SectionGenerator):
    """Generate growth prospects analysis."""
    
    def generate(self,
                ticker: str,
                revenue_growth: float = None,
                earnings_growth: float = None,
                growth_drivers: List[str] = None) -> str:
        """Generate growth prospects."""
        # Classify growth rate
        if revenue_growth:
            if revenue_growth > 15:
                growth_rate = "double-digit"
            elif revenue_growth > 5:
                growth_rate = "moderate"
            elif revenue_growth > 0:
                growth_rate = "modest"
            else:
                growth_rate = "challenged"
        else:
            growth_rate = "moderate"
        
        drivers = growth_drivers or ["organic expansion", "market share gains", "operational improvements"]
        driver_text = ", ".join(drivers[:2])
        
        parts = []
        parts.append(f"{ticker} targets {growth_rate} growth driven by {driver_text}, "
                    f"and strategic market expansion initiatives.")
        
        if revenue_growth and revenue_growth > 10:
            parts.append(f"The company's growth trajectory appears robust, supported by strong market demand "
                        f"and effective execution of strategic priorities.")
        elif revenue_growth and revenue_growth < 0:
            parts.append(f"Growth faces near-term headwinds, though management initiatives aim to "
                        f"restore positive momentum over time.")
        
        return " ".join(parts)


class DividendAnalysisGenerator(SectionGenerator):
    """Generate dividend analysis sections."""
    
    def generate(self,
                ticker: str,
                dividend_yield: float = None,
                payout_ratio: float = None,
                dividend_growth_rate: float = None) -> str:
        """Generate dividend analysis."""
        if not dividend_yield or dividend_yield == 0:
            return f"{ticker} currently does not pay a dividend, focusing capital allocation on growth investments and business reinvestment."
        
        # Classify yield
        if dividend_yield > 4:
            yield_desc = "attractive"
        elif dividend_yield > 2:
            yield_desc = "moderate"
        else:
            yield_desc = "modest"
        
        # Classify payout ratio
        if payout_ratio:
            if payout_ratio > 80:
                payout_desc = "elevated payout ratio"
                sustainability = "which may limit flexibility"
            elif payout_ratio > 50:
                payout_desc = "balanced payout ratio"
                sustainability = "indicating reasonable sustainability"
            else:
                payout_desc = "conservative payout ratio"
                sustainability = "providing ample coverage and growth potential"
        else:
            payout_desc = "payout ratio"
            sustainability = ""
        
        parts = []
        parts.append(f"{ticker} currently offers a {yield_desc} dividend yield of {dividend_yield:.2f}% "
                    f"with a {payout_desc}")
        if sustainability:
            parts[-1] += f", {sustainability}."
        else:
            parts[-1] += "."
        
        if dividend_growth_rate and dividend_growth_rate > 0:
            parts.append(f"The company has demonstrated consistent dividend growth, "
                        f"reflecting management's commitment to returning value to shareholders.")
        
        return " ".join(parts)


class EarningsAnalysisGenerator(SectionGenerator):
    """Generate earnings analysis sections."""
    
    def generate(self,
                ticker: str,
                eps_actual: float = None,
                eps_estimate: float = None,
                quarter: str = None,
                earnings_growth: float = None) -> str:
        """Generate earnings analysis."""
        if not eps_actual or not eps_estimate:
            return f"{ticker}'s recent earnings results reflect the company's ongoing operational performance and market positioning."
        
        # Calculate surprise
        surprise_pct = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100 if eps_estimate != 0 else 0
        
        if surprise_pct > 5:
            surprise_desc = "beating"
            quality = "strong"
        elif surprise_pct < -5:
            surprise_desc = "missing"
            quality = "soft"
        else:
            surprise_desc = "meeting"
            quality = "in-line"
        
        quarter_text = quarter or "the latest quarter"
        
        parts = []
        parts.append(f"{ticker} reported {quarter_text} earnings of ${eps_actual:.2f} versus "
                    f"expectations of ${eps_estimate:.2f}, {surprise_desc} consensus estimates.")
        
        parts.append(f"The {quality} results reflect the company's current operational trajectory "
                    f"and market execution capabilities.")
        
        if earnings_growth and earnings_growth > 15:
            parts.append(f"Year-over-year earnings growth of {earnings_growth:.1f}% demonstrates "
                        f"strong momentum and operational leverage.")
        
        return " ".join(parts)


class RevenueBreakdownGenerator(SectionGenerator):
    """Generate revenue breakdown sections."""
    
    def generate(self,
                ticker: str,
                revenue_segments: Dict[str, float] = None) -> str:
        """Generate revenue breakdown."""
        if not revenue_segments or len(revenue_segments) == 0:
            return f"{ticker} generates revenue through its diversified business operations across multiple segments and geographies."
        
        # Convert to list and sort by contribution
        segments = sorted(revenue_segments.items(), key=lambda x: x[1], reverse=True)
        
        parts = []
        if len(segments) >= 3:
            parts.append(f"{ticker} generates revenue through {segments[0][0]} ({segments[0][1]:.1f}%), "
                        f"{segments[1][0]} ({segments[1][1]:.1f}%), and {segments[2][0]} ({segments[2][1]:.1f}%).")
        elif len(segments) == 2:
            parts.append(f"{ticker} generates revenue through {segments[0][0]} ({segments[0][1]:.1f}%) "
                        f"and {segments[1][0]} ({segments[1][1]:.1f}%).")
        else:
            parts.append(f"{ticker} primarily generates revenue through {segments[0][0]} ({segments[0][1]:.1f}%).")
        
        # Add commentary about diversification
        if len(segments) >= 3 and segments[0][1] < 60:
            parts.append(f"This diversified revenue base provides balanced exposure across different business lines.")
        elif segments[0][1] > 70:
            parts.append(f"Revenue concentration in the primary segment creates both focus and dependency.")
        
        return " ".join(parts)


class ProfitMarginsGenerator(SectionGenerator):
    """Generate profit margins analysis."""
    
    def generate(self,
                ticker: str,
                gross_margin: float = None,
                operating_margin: float = None,
                net_margin: float = None) -> str:
        """Generate profit margins analysis."""
        parts = []
        
        if gross_margin:
            if gross_margin > 60:
                gm_quality = "industry-leading"
            elif gross_margin > 40:
                gm_quality = "strong"
            elif gross_margin > 25:
                gm_quality = "moderate"
            else:
                gm_quality = "compressed"
            
            parts.append(f"{ticker} maintains {gross_margin:.1f}% gross margin, reflecting {gm_quality} profitability at the product level.")
        
        if operating_margin:
            if operating_margin > 25:
                om_quality = "exceptional"
            elif operating_margin > 15:
                om_quality = "healthy"
            elif operating_margin > 5:
                om_quality = "adequate"
            else:
                om_quality = "challenged"
            
            parts.append(f"Operating margin of {operating_margin:.1f}% demonstrates {om_quality} operational efficiency.")
        
        if gross_margin and operating_margin:
            sg_and_a = gross_margin - operating_margin
            if sg_and_a > 30:
                parts.append(f"The gap between gross and operating margins suggests opportunity for expense optimization.")
            elif sg_and_a < 15:
                parts.append(f"Tight control of operating expenses enhances overall profitability.")
        
        if not parts:
            parts.append(f"{ticker} maintains profitability metrics aligned with its business model and market positioning.")
        
        return " ".join(parts)


class CashFlowAnalysisGenerator(SectionGenerator):
    """Generate cash flow analysis sections."""
    
    def generate(self,
                ticker: str,
                operating_cashflow: float = None,
                free_cashflow: float = None,
                capex: float = None) -> str:
        """Generate cash flow analysis."""
        if not operating_cashflow:
            return f"{ticker} generates operating cash flow from its business operations, supporting ongoing investments and capital allocation priorities."
        
        parts = []
        parts.append(f"{ticker} generated ${abs(operating_cashflow)/1e9:.2f}B in operating cash flow")
        
        if free_cashflow:
            fcf_margin = (free_cashflow / operating_cashflow * 100) if operating_cashflow != 0 else 0
            parts[-1] += f", with ${abs(free_cashflow)/1e9:.2f}B in free cash flow after capex."
            
            if fcf_margin > 70:
                parts.append(f"Strong free cash flow conversion demonstrates capital efficiency and limited reinvestment needs.")
            elif fcf_margin > 40:
                parts.append(f"Healthy free cash flow generation supports balanced capital allocation between growth and returns.")
            elif fcf_margin < 20:
                parts.append(f"Significant capital reinvestment reflects growth priorities and infrastructure development.")
        else:
            parts[-1] += "."
        
        return " ".join(parts)


class BalanceSheetStrengthGenerator(SectionGenerator):
    """Generate balance sheet strength analysis."""
    
    def generate(self,
                ticker: str,
                total_cash: float = None,
                total_debt: float = None,
                debt_to_equity: float = None) -> str:
        """Generate balance sheet strength."""
        if not total_cash and not total_debt:
            return f"{ticker} maintains a balance sheet structure aligned with its capital allocation strategy and business model."
        
        parts = []
        
        # Net debt position
        if total_cash and total_debt:
            net_debt = total_debt - total_cash
            if net_debt < 0:  # Net cash
                parts.append(f"{ticker} maintains a net cash position of ${abs(net_debt)/1e9:.2f}B, "
                            f"providing financial flexibility and strategic optionality.")
            elif net_debt / total_debt < 0.5:  # Low net leverage
                parts.append(f"{ticker} holds ${total_cash/1e9:.2f}B in cash against ${total_debt/1e9:.2f}B in debt, "
                            f"yielding a strong liquidity position.")
            else:
                parts.append(f"With ${total_cash/1e9:.2f}B cash and ${total_debt/1e9:.2f}B debt, "
                            f"{ticker} maintains a leveraged capital structure.")
        
        # Debt-to-equity assessment
        if debt_to_equity:
            if debt_to_equity < 0.5:
                leverage_desc = "conservative"
            elif debt_to_equity < 1.0:
                leverage_desc = "moderate"
            elif debt_to_equity < 2.0:
                leverage_desc = "elevated"
            else:
                leverage_desc = "aggressive"
            
            parts.append(f"The debt-to-equity ratio of {debt_to_equity:.2f}x indicates {leverage_desc} leverage, "
                        f"impacting financial flexibility and risk profile.")
        
        if not parts:
            parts.append(f"{ticker}'s balance sheet supports its operational requirements and strategic objectives.")
        
        return " ".join(parts)


class ManagementQualityGenerator(SectionGenerator):
    """Generate management quality assessment."""
    
    def generate(self,
                ticker: str,
                ceo_name: str = None,
                management_tenure: float = None,
                insider_ownership: float = None) -> str:
        """Generate management quality assessment."""
        ceo = ceo_name or "the executive team"
        
        parts = []
        parts.append(f"{ticker}'s management team, led by {ceo}, demonstrates operational experience and strategic vision.")
        
        if insider_ownership and insider_ownership > 10:
            parts.append(f"Significant insider ownership of {insider_ownership:.1f}% aligns management interests with shareholder value creation.")
        elif insider_ownership and insider_ownership > 1:
            parts.append(f"Management maintains {insider_ownership:.1f}% insider ownership, demonstrating confidence in the business.")
        
        parts.append(f"The leadership team focuses on executing strategic priorities while navigating market dynamics.")
        
        return " ".join(parts)


class MarketSentimentGenerator(SectionGenerator):
    """Generate market sentiment analysis."""
    
    def generate(self,
                ticker: str,
                price_momentum: str = None,
                volume_trend: str = None,
                short_interest: float = None) -> str:
        """Generate market sentiment."""
        # Determine overall sentiment
        if price_momentum:
            sentiment = price_momentum
        else:
            sentiment = "mixed"
        
        parts = []
        parts.append(f"Market sentiment toward {ticker} is {sentiment}, reflected in recent trading activity.")
        
        if short_interest and short_interest > 10:
            parts.append(f"Elevated short interest of {short_interest:.1f}% of float indicates notable bearish positioning "
                        f"that could fuel volatility.")
        elif short_interest and short_interest > 5:
            parts.append(f"Moderate short interest of {short_interest:.1f}% suggests balanced market views.")
        elif short_interest and short_interest < 2:
            parts.append(f"Low short interest of {short_interest:.1f}% reflects limited bearish conviction.")
        
        return " ".join(parts)


class AnalystConsensusGenerator(SectionGenerator):
    """Generate analyst consensus summary."""
    
    def generate(self,
                ticker: str,
                consensus_rating: str = None,
                num_analysts: int = None,
                target_price: float = None,
                current_price: float = None) -> str:
        """Generate analyst consensus."""
        if not num_analysts:
            num_analysts = "multiple"
        
        rating = consensus_rating or "Hold"
        
        parts = []
        parts.append(f"Analyst consensus rates {ticker} as {rating} with {num_analysts} analysts covering the stock")
        
        if target_price and current_price:
            upside = ((target_price - current_price) / current_price) * 100
            parts[-1] += f", setting ${target_price:.2f} average price target implying {upside:+.1f}% {'upside' if upside > 0 else 'downside'}."
        else:
            parts[-1] += "."
        
        return " ".join(parts)


class HistoricalPerformanceGenerator(SectionGenerator):
    """Generate historical performance analysis."""
    
    def generate(self,
                ticker: str,
                return_1y: float = None,
                return_3y: float = None,
                return_5y: float = None,
                benchmark_1y: float = None) -> str:
        """Generate historical performance."""
        parts = []
        
        if return_1y:
            parts.append(f"{ticker} has delivered {return_1y:+.1f}% return over the past year")
        
        if return_3y:
            annualized_3y = return_3y / 3 if return_3y else 0
            if parts:
                parts[-1] += f", {return_3y:+.1f}% over three years (annualized: {annualized_3y:+.1f}%)"
            else:
                parts.append(f"{ticker} has delivered {return_3y:+.1f}% over three years")
        
        if return_5y:
            annualized_5y = return_5y / 5 if return_5y else 0
            if parts:
                parts[-1] += f", and {return_5y:+.1f}% over five years (annualized: {annualized_5y:+.1f}%)."
            else:
                parts.append(f"{ticker} has delivered {return_5y:+.1f}% over five years.")
        elif parts:
            parts[-1] += "."
        
        # Compare to benchmark if available
        if return_1y and benchmark_1y:
            if return_1y > benchmark_1y + 5:
                parts.append(f"This performance significantly outpaced broader market benchmarks.")
            elif return_1y < benchmark_1y - 5:
                parts.append(f"This performance lagged behind broader market benchmarks.")
            else:
                parts.append(f"This performance tracked broadly in-line with market benchmarks.")
        
        if not parts:
            parts.append(f"{ticker}'s historical performance reflects its market positioning and operational execution over time.")
        
        return " ".join(parts)


class FutureCatalystsGenerator(SectionGenerator):
    """Generate future catalysts analysis."""
    
    def generate(self,
                ticker: str,
                catalysts: List[str] = None,
                catalyst_timing: str = None) -> str:
        """Generate future catalysts."""
        timing = catalyst_timing or "the near to medium term"
        
        if catalysts and len(catalysts) > 0:
            catalyst_list = ", ".join(catalysts[:3])
            parts = []
            parts.append(f"Key catalysts for {ticker} include {catalyst_list}, with potential to materialize over {timing}.")
            parts.append(f"These developments could serve as inflection points for the stock's trajectory.")
        else:
            parts = [f"{ticker} faces several potential catalysts over {timing} that could influence its valuation and performance."]
        
        return " ".join(parts)


class RegulatoryEnvironmentGenerator(SectionGenerator):
    """Generate regulatory environment assessment."""
    
    def generate(self,
                ticker: str,
                sector: str = None,
                regulatory_risk: str = None) -> str:
        """Generate regulatory environment."""
        # Determine regulatory intensity by sector
        high_reg_sectors = ['financials', 'healthcare', 'utilities', 'energy']
        mod_reg_sectors = ['industrials', 'materials', 'consumer staples']
        
        if sector and sector.lower() in high_reg_sectors:
            intensity = "heightened"
            framework = "stringent"
        elif sector and sector.lower() in mod_reg_sectors:
            intensity = "moderate"
            framework = "standard"
        else:
            intensity = "normal"
            framework = "balanced"
        
        risk_level = regulatory_risk or "manageable"
        
        parts = []
        parts.append(f"{ticker} operates under {framework} regulatory framework, facing {intensity} oversight "
                    f"with {risk_level} compliance risk level.")
        
        if intensity == "heightened":
            parts.append(f"Regulatory compliance remains a key consideration impacting operational flexibility and strategic decisions.")
        
        return " ".join(parts)


class ESGSustainabilityGenerator(SectionGenerator):
    """Generate ESG and sustainability assessment."""
    
    def generate(self,
                ticker: str,
                esg_score: float = None,
                environmental_score: str = None,
                social_score: str = None,
                governance_score: str = None) -> str:
        """Generate ESG sustainability."""
        if esg_score:
            if esg_score > 70:
                rating = "strong ESG"
            elif esg_score > 50:
                rating = "moderate ESG"
            else:
                rating = "developing ESG"
        else:
            rating = "ESG"
        
        env = environmental_score or "moderate"
        soc = social_score or "moderate"
        gov = governance_score or "moderate"
        
        parts = []
        parts.append(f"{ticker} demonstrates {rating} profile with {env} environmental score, "
                    f"{soc} social score, and {gov} governance score.")
        
        parts.append(f"The company's sustainability initiatives align with evolving stakeholder expectations "
                    f"and regulatory requirements.")
        
        return " ".join(parts)


class InvestmentThesisGenerator(SectionGenerator):
    """Generate investment thesis summary."""
    
    def generate(self,
                ticker: str,
                thesis_pillars: List[str] = None,
                investment_outlook: str = None,
                risk_reward: str = None) -> str:
        """Generate investment thesis."""
        outlook = investment_outlook or "balanced"
        risk_reward_profile = risk_reward or "reasonable"
        
        if thesis_pillars and len(thesis_pillars) >= 3:
            pillar_text = f"{thesis_pillars[0]}, {thesis_pillars[1]}, and {thesis_pillars[2]}"
        else:
            pillar_text = "operational execution, market positioning, and financial management"
        
        parts = []
        parts.append(f"The investment case for {ticker} rests on {pillar_text}, "
                    f"supporting {outlook} outlook with {risk_reward_profile} risk/reward profile.")
        
        parts.append(f"Investors should weigh these factors against individual risk tolerance and portfolio objectives "
                    f"when considering position sizing.")
        
        return " ".join(parts)


class SectionGeneratorFactory:
    """Factory for creating section generators."""
    
    @staticmethod
    def create_generator(section_type: str,
                        model: Optional[MarkovEngine] = None,
                        temperature: float = 0.7) -> SectionGenerator:
        """
        Create appropriate generator for section type.
        
        Args:
            section_type: Type of section
            model: Trained MarkovEngine
            temperature: Generation temperature
        
        Returns:
            Specialized SectionGenerator
        """
        generators = {
            'introduction': IntroductionGenerator,
            'technical_analysis': TechnicalAnalysisGenerator,
            'fundamental_analysis': FundamentalAnalysisGenerator,
            'valuation': ValuationGenerator,
            'conclusion': ConclusionGenerator,
            # NEW: 18 additional section generators
            'sector_analysis': SectorAnalysisGenerator,
            'competitive_positioning': CompetitivePositioningGenerator,
            'growth_prospects': GrowthProspectsGenerator,
            'dividend_analysis': DividendAnalysisGenerator,
            'earnings_analysis': EarningsAnalysisGenerator,
            'revenue_breakdown': RevenueBreakdownGenerator,
            'profit_margins': ProfitMarginsGenerator,
            'cash_flow_analysis': CashFlowAnalysisGenerator,
            'balance_sheet_strength': BalanceSheetStrengthGenerator,
            'management_quality': ManagementQualityGenerator,
            'market_sentiment': MarketSentimentGenerator,
            'analyst_consensus': AnalystConsensusGenerator,
            'historical_performance': HistoricalPerformanceGenerator,
            'future_catalysts': FutureCatalystsGenerator,
            'regulatory_environment': RegulatoryEnvironmentGenerator,
            'esg_sustainability': ESGSustainabilityGenerator,
            'investment_thesis': InvestmentThesisGenerator
        }
        
        generator_class = generators.get(section_type, SectionGenerator)
        return generator_class(model, temperature)
