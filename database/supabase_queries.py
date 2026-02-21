"""
Supabase Queries - Tab-Specific Data Retrieval
===============================================

Optimized queries for each stock page tab:
1. Overview Tab - Market snapshot
2. Forecast Tab - Price & earnings forecasts  
3. Technicals Tab - Price behavior & signals
4. Fundamentals Tab - Financial strength
5. Risk & Sentiment Tab - Downside exposure & psychology
6. Company Tab - Identity & ownership

Uses materialized views and indexes for fast concurrent queries.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class SupabaseQueries:
    """Tab-specific optimized queries for stock data retrieval"""
    
    def __init__(self, db: SupabaseClient):
        """
        Initialize queries handler.
        
        Args:
            db: SupabaseClient instance
        """
        self.db = db
    
    # ========================================================================
    # 1. OVERVIEW TAB - Instant market snapshot
    # ========================================================================
    
    def get_overview_data(self, stock_id: int) -> Dict[str, Any]:
        """
        Get all data for Overview tab.
        
        Purpose: Instant market snapshot
        
        Returns:
            Dict with:
            - Market Price: current_price, changes, volume
            - Market Size: market_cap, enterprise_value
            - Performance: returns, 52-week range
            - Market Context: exchange, interest_rate
        """
        
        # Get latest market price snapshot
        price_snapshot = self.db.select_latest(
            "market_price_snapshot",
            stock_id,
            columns="*"
        )
        
        # Get latest daily price
        daily = self.db.select_latest(
            "daily_price_data",
            stock_id,
            columns="*"
        )
        
        # Get latest fundamentals for enterprise value
        fundamentals = self.db.select_latest(
            "fundamental_data",
            stock_id,
            columns="ev_to_revenue, ev_to_ebitda, total_cash, total_debt"
        )
        
        # Build overview response
        overview = {
            "market_price": {
                "current_price": price_snapshot.get("current_price") if price_snapshot else None,
                "regular_market_price": daily.get("close_price") if daily else None,
                "open_price": daily.get("open_price") if daily else None,
                "high_price": daily.get("high_price") if daily else None,
                "low_price": daily.get("low_price") if daily else None,
                "close_price": daily.get("close_price") if daily else None,
                "volume": daily.get("volume") if daily else None
            },
            "market_size": {
                "market_cap": price_snapshot.get("market_cap") if price_snapshot else None,
                # Enterprise Value = Market Cap + Total Debt - Total Cash
                # (previously was total_cash + total_debt which is both wrong and crashes on None)
                "enterprise_value": (
                    (price_snapshot.get("market_cap") or 0)
                    + (fundamentals.get("total_debt") or 0)
                    - (fundamentals.get("total_cash") or 0)
                ) if (price_snapshot and fundamentals and
                      price_snapshot.get("market_cap") is not None) else None,
                "shares_outstanding": price_snapshot.get("shares_outstanding") if price_snapshot else None,
                "float_shares": price_snapshot.get("float_shares") if price_snapshot else None
            },
            "performance": {
                "daily_return_pct": daily.get("daily_return_pct") if daily else None,
                "change_15d_pct": price_snapshot.get("change_15d_pct") if price_snapshot else None,
                "change_52w_pct": price_snapshot.get("change_52w_pct") if price_snapshot else None,
                "performance_1y_pct": price_snapshot.get("performance_1y_pct") if price_snapshot else None,
                "overall_pct_change": price_snapshot.get("overall_pct_change") if price_snapshot else None,
                "high_52w": price_snapshot.get("high_52w") if price_snapshot else None,
                "low_52w": price_snapshot.get("low_52w") if price_snapshot else None
            },
            "market_context": {
                "exchange": None,  # From stocks table
                "country": None,   # From stocks table
                "sp500_index": price_snapshot.get("sp500_index") if price_snapshot else None,
                "interest_rate": price_snapshot.get("interest_rate") if price_snapshot else None
            }
        }
        
        return self._clean_response(overview)
    
    # ========================================================================
    # 2. FORECAST TAB - Forward-looking price and earnings visibility
    # ========================================================================
    
    def get_forecast_data(self, stock_id: int) -> Dict[str, Any]:
        """
        Get all data for Forecast tab.
        
        Purpose: Forward-looking price and earnings visibility
        
        Returns:
            Dict with:
            - Price Forecast: forecast_price_1y, forecast_range
            - Analyst Targets: target prices, analyst_rating
            - Earnings Timing: next_earnings_date, call time
        """
        
        # Get latest forecast
        forecast = self.db.select_latest(
            "forecast_data",
            stock_id,
            columns="*"
        )
        
        # Analyst targets and earnings dates are stored in the analyst_data table,
        # NOT in forecast_data (they were split into a separate table in the mapper).
        analyst = self.db.select_latest(
            "analyst_data",
            stock_id,
            columns="*"
        )

        forecast_response = {
            "price_forecast": {
                # forecast_price_1y stores the Prophet upper-band (High) price for the
                # nearest forecast month; rename to forecast_price_high for clarity.
                "forecast_price_high": forecast.get("forecast_price_1y") if forecast else None,
                "forecast_avg_price": forecast.get("forecast_avg_price") if forecast else None,
                "forecast_range_width": forecast.get("forecast_range_width") if forecast else None,
                "forecast_period": forecast.get("forecast_period") if forecast else None
            },
            "analyst_targets": {
                "target_price_mean": analyst.get("target_price_mean") if analyst else None,
                "target_price_median": analyst.get("target_price_median") if analyst else None,
                "target_price_high": analyst.get("target_price_high") if analyst else None,
                "target_price_low": analyst.get("target_price_low") if analyst else None,
                "analyst_rating": analyst.get("analyst_rating") if analyst else None,
                "analyst_count": analyst.get("analyst_count") if analyst else None
            },
            "earnings_timing": {
                "next_earnings_date": analyst.get("next_earnings_date") if analyst else None,
                "earnings_call_time_utc": analyst.get("earnings_call_time_utc") if analyst else None
            }
        }
        
        return self._clean_response(forecast_response)
    
    # ========================================================================
    # 3. TECHNICALS TAB - Price behavior and trading signals
    # ========================================================================
    
    def get_technicals_data(self, stock_id: int, days: int = 100) -> Dict[str, Any]:
        """
        Get technical analysis data for Technicals tab.
        
        Purpose: Price behavior and trading signals
        
        Args:
            stock_id: Stock database ID
            days: Number of historical days for trend analysis
            
        Returns:
            Dict with current indicators + historical trend
        """
        
        # Get latest technical indicators
        latest_tech = self.db.select_latest(
            "technical_indicators",
            stock_id,
            columns="*"
        )
        
        # Get recent data for trend – filter by stock_id at the database level.
        # Previously the columns list omitted stock_id, so the Python-side
        # filter `t.get("stock_id") == stock_id` always evaluated to False,
        # causing historical_trend to always be an empty list.
        recent_tech = self.db.select_ordered(
            "technical_indicators",
            columns="date, rsi_14, macd_line, bb_upper, bb_lower",
            order_by="date",
            ascending=False,
            limit=days,
            stock_id=stock_id
        )
        
        technicals = {
            "trend": {
                "sma_7": latest_tech.get("sma_7") if latest_tech else None,
                "sma_20": latest_tech.get("sma_20") if latest_tech else None,
                "sma_50": latest_tech.get("sma_50") if latest_tech else None,
                "sma_100": latest_tech.get("sma_100") if latest_tech else None,
                "sma_200": latest_tech.get("sma_200") if latest_tech else None,
                "ema_12": latest_tech.get("ema_12") if latest_tech else None,
                "ema_26": latest_tech.get("ema_26") if latest_tech else None,
                "adx": latest_tech.get("adx") if latest_tech else None,
                "parabolic_sar": latest_tech.get("parabolic_sar") if latest_tech else None
            },
            "momentum": {
                "rsi_14": latest_tech.get("rsi_14") if latest_tech else None,
                "macd_line": latest_tech.get("macd_line") if latest_tech else None,
                "macd_signal": latest_tech.get("macd_signal") if latest_tech else None,
                "macd_histogram": latest_tech.get("macd_histogram") if latest_tech else None,
                "stochastic_osc": latest_tech.get("stochastic_osc") if latest_tech else None,
                "williams_r": latest_tech.get("williams_r") if latest_tech else None
            },
            "volatility": {
                "bb_upper": latest_tech.get("bb_upper") if latest_tech else None,
                "bb_middle": latest_tech.get("bb_middle") if latest_tech else None,
                "bb_lower": latest_tech.get("bb_lower") if latest_tech else None,
                "atr_14": latest_tech.get("atr_14") if latest_tech else None,
                "volatility_7d": latest_tech.get("volatility_7d") if latest_tech else None,
                "volatility_30d_annual": latest_tech.get("volatility_30d_annual") if latest_tech else None,
                "keltner_upper": latest_tech.get("keltner_upper") if latest_tech else None,
                "keltner_lower": latest_tech.get("keltner_lower") if latest_tech else None
            },
            "volume": {
                "volume_sma_20": latest_tech.get("volume_sma_20") if latest_tech else None,
                "volume_sma_ratio": latest_tech.get("volume_sma_ratio") if latest_tech else None,
                "volume_trend_5d": latest_tech.get("volume_trend_5d") if latest_tech else None,
                "obv": latest_tech.get("obv") if latest_tech else None,
                "vpt": latest_tech.get("vpt") if latest_tech else None,
                "chaikin_money_flow": latest_tech.get("chaikin_money_flow") if latest_tech else None,
                "avg_volume_3m": latest_tech.get("avg_volume_3m") if latest_tech else None,
                "green_days_count": latest_tech.get("green_days_count") if latest_tech else None
            },
            "support_resistance": {
                "support_30d": latest_tech.get("support_30d") if latest_tech else None,
                "resistance_30d": latest_tech.get("resistance_30d") if latest_tech else None
            },
            "historical_trend": recent_tech
        }
        
        return self._clean_response(technicals)
    
    # ========================================================================
    # 4. FUNDAMENTALS TAB - Financial strength and valuation
    # ========================================================================
    
    def get_fundamentals_data(self, stock_id: int) -> Dict[str, Any]:
        """
        Get fundamental analysis data for Fundamentals tab.
        
        Purpose: Financial strength and valuation
        
        Returns:
            Dict with:
            - Valuation: P/E, P/B, PEG, EV ratios
            - Profitability: Margins, ROE, ROA
            - Financial Health: Debt, cash, ratios
            - Growth: Revenue, earnings growth
            - Efficiency: Turnover ratios
            - Dividends: Dividend metrics
        """
        
        # Get latest fundamental data
        fundamentals = self.db.select_latest(
            "fundamental_data",
            stock_id,
            columns="*"
        )
        
        # Get latest dividend data
        dividends = self.db.select_latest(
            "dividend_data",
            stock_id,
            columns="*"
        )
        
        fundamentals_response = {
            "valuation": {
                "pe_trailing": fundamentals.get("pe_ratio") if fundamentals else None,
                "pe_forward": fundamentals.get("pe_forward") if fundamentals else None,
                "price_to_sales": fundamentals.get("price_to_sales") if fundamentals else None,
                "price_to_book": fundamentals.get("price_to_book") if fundamentals else None,
                "peg_ratio": fundamentals.get("peg_ratio") if fundamentals else None,
                "ev_to_revenue": fundamentals.get("ev_to_revenue") if fundamentals else None,
                "ev_to_ebitda": fundamentals.get("ev_to_ebitda") if fundamentals else None,
                "price_to_fcf": fundamentals.get("price_to_fcf") if fundamentals else None
            },
            "profitability": {
                "net_margin": fundamentals.get("net_margin") if fundamentals else None,
                "operating_margin": fundamentals.get("operating_margin") if fundamentals else None,
                "gross_margin": fundamentals.get("gross_margin") if fundamentals else None,
                "ebitda_margin": fundamentals.get("ebitda_margin") if fundamentals else None,
                "roe": fundamentals.get("roe") if fundamentals else None,
                "roa": fundamentals.get("roa") if fundamentals else None,
                "roic": fundamentals.get("roic") if fundamentals else None
            },
            "financial_health": {
                "debt_to_equity": fundamentals.get("debt_to_equity") if fundamentals else None,
                "total_cash": fundamentals.get("total_cash") if fundamentals else None,
                "total_debt": fundamentals.get("total_debt") if fundamentals else None,
                "free_cash_flow": fundamentals.get("free_cash_flow") if fundamentals else None,
                "operating_cash_flow": fundamentals.get("operating_cash_flow") if fundamentals else None,
                "current_ratio": fundamentals.get("current_ratio") if fundamentals else None,
                "quick_ratio": fundamentals.get("quick_ratio") if fundamentals else None
            },
            "growth": {
                "revenue_ttm": fundamentals.get("revenue_ttm") if fundamentals else None,
                "revenue_growth_yoy": fundamentals.get("revenue_growth_yoy") if fundamentals else None,
                "net_income_ttm": fundamentals.get("net_income_ttm") if fundamentals else None,
                "earnings_growth_yoy": fundamentals.get("earnings_growth_yoy") if fundamentals else None,
                "ebitda_ttm": fundamentals.get("ebitda_ttm") if fundamentals else None,
                "gross_profit_ttm": fundamentals.get("gross_profit_ttm") if fundamentals else None
            },
            "efficiency": {
                "asset_turnover": fundamentals.get("asset_turnover") if fundamentals else None,
                "inventory_turnover": fundamentals.get("inventory_turnover") if fundamentals else None,
                "receivables_turnover": fundamentals.get("receivables_turnover") if fundamentals else None,
                "working_capital_turnover": fundamentals.get("working_capital_turnover") if fundamentals else None,
                "dso": fundamentals.get("dso") if fundamentals else None,
                "dio": fundamentals.get("dio") if fundamentals else None,
                "ccc": fundamentals.get("ccc") if fundamentals else None
            },
            "dividends": {
                "dividend_rate": dividends.get("dividend_rate") if dividends else None,
                "dividend_yield_pct": dividends.get("dividend_yield_pct") if dividends else None,
                "payout_ratio": dividends.get("payout_ratio") if dividends else None,
                "avg_dividend_yield_5y": dividends.get("avg_dividend_yield_5y") if dividends else None,
                "dividend_forward_rate": dividends.get("dividend_forward_rate") if dividends else None,
                "dividend_forward_yield": dividends.get("dividend_forward_yield") if dividends else None,
                "ex_dividend_date": dividends.get("ex_dividend_date") if dividends else None,
                "last_split_date": dividends.get("last_split_date") if dividends else None,
                "last_split_factor": dividends.get("last_split_factor") if dividends else None
            }
        }
        
        return self._clean_response(fundamentals_response)
    
    # ========================================================================
    # 5. RISK & SENTIMENT TAB - Downside exposure and market psychology
    # ========================================================================
    
    def get_risk_sentiment_data(self, stock_id: int) -> Dict[str, Any]:
        """
        Get risk analysis and sentiment data.
        
        Purpose: Downside exposure and market psychology
        
        Returns:
            Dict with risk metrics, sentiment, and insider activity
        """
        
        # Get latest risk data
        risk = self.db.select_latest(
            "risk_data",
            stock_id,
            columns="*"
        )
        
        # Get latest sentiment data
        sentiment = self.db.select_latest(
            "sentiment_data",
            stock_id,
            columns="*"
        )
        
        # Get latest ownership data
        ownership = self.db.select_latest(
            "ownership_data",
            stock_id,
            columns="shares_short, short_ratio_days, short_pct_float"
        )
        
        # Get recent insider transactions – filter server-side so the limit
        # applies only to THIS stock's rows, not the whole table.
        insider_transactions = self.db.select_ordered(
            "insider_transactions",
            columns="*",
            order_by="transaction_date",
            ascending=False,
            limit=10,
            stock_id=stock_id
        )
        
        risk_sentiment = {
            "risk": {
                "var_95": risk.get("var_95") if risk else None,
                "var_99": risk.get("var_99") if risk else None,
                "sharpe_ratio": risk.get("sharpe_ratio") if risk else None,
                "sortino_ratio": risk.get("sortino_ratio") if risk else None,
                "calmar_ratio": risk.get("calmar_ratio") if risk else None,
                "max_drawdown": risk.get("max_drawdown") if risk else None,
                "beta": risk.get("beta") if risk else None,
                "market_correlation": risk.get("market_correlation") if risk else None,
                "skewness": risk.get("skewness") if risk else None,
                "kurtosis": risk.get("kurtosis") if risk else None
            },
            "sentiment": {
                "sentiment_score": sentiment.get("sentiment_score") if sentiment else None,
                "sentiment_label": sentiment.get("sentiment_label") if sentiment else None,
                "sentiment_confidence": sentiment.get("sentiment_confidence") if sentiment else None,
                "news_sentiment": sentiment.get("news_sentiment") if sentiment else None,
                "analyst_sentiment": sentiment.get("analyst_sentiment") if sentiment else None,
                "options_sentiment": sentiment.get("options_sentiment") if sentiment else None,
                "put_call_ratio": sentiment.get("put_call_ratio") if sentiment else None
            },
            "insider_activity": {
                "shares_short": ownership.get("shares_short") if ownership else None,
                "short_ratio_days": ownership.get("short_ratio_days") if ownership else None,
                "short_pct_float": ownership.get("short_pct_float") if ownership else None,
                "recent_transactions": insider_transactions
            }
        }
        
        return self._clean_response(risk_sentiment)
    
    # ========================================================================
    # 6. COMPANY TAB - Identity, ownership, and insider transparency
    # ========================================================================
    
    def get_company_data(self, stock_id: int) -> Dict[str, Any]:
        """
        Get company profile and ownership data.
        
        Purpose: Identity, ownership, and insider transparency
        
        Returns:
            Dict with company info and insider details
        """
        
        # Get stock info
        stock = self.db.select("stocks", filters={"id": stock_id})
        stock = stock[0] if stock else {}
        
        # Get ownership data
        ownership = self.db.select_latest(
            "ownership_data",
            stock_id,
            columns="*"
        )
        
        # Get insider transactions (detailed table) – filter server-side so the
        # limit applies only to THIS stock's rows, not the whole table.
        insider_transactions = self.db.select_ordered(
            "insider_transactions",
            columns="*",
            order_by="transaction_date",
            ascending=False,
            limit=50,
            stock_id=stock_id
        )
        
        company = {
            "profile": {
                "company_name": stock.get("company_name"),
                "short_name": stock.get("short_name"),
                "long_name": stock.get("company_name"),
                "ticker": stock.get("ticker"),
                "symbol": stock.get("symbol"),
                "sector": stock.get("sector"),
                "industry": stock.get("industry"),
                "website_url": stock.get("website_url"),
                "employee_count": stock.get("employee_count"),
                "business_summary": stock.get("business_summary"),
                "long_business_summary": stock.get("long_business_summary"),
                "first_trade_date_epoch": stock.get("first_trade_date")
            },
            "ownership": {
                "shares_outstanding": ownership.get("shares_outstanding") if ownership else None,
                "shares_outstanding_diluted": ownership.get("shares_outstanding_diluted") if ownership else None,
                "insider_ownership_pct": ownership.get("insider_ownership_pct") if ownership else None,
                "institutional_ownership_pct": ownership.get("institutional_ownership_pct") if ownership else None,
                "shares_short": ownership.get("shares_short") if ownership else None,
                "short_ratio_days": ownership.get("short_ratio_days") if ownership else None,
                "short_pct_float": ownership.get("short_pct_float") if ownership else None,
                "shares_short_prev": ownership.get("shares_short_prev") if ownership else None,
                "shares_change_yoy": ownership.get("shares_change_yoy") if ownership else None
            },
            "insider_transactions": insider_transactions
        }
        
        return self._clean_response(company)
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def _clean_response(self, data: Dict) -> Dict:
        """Remove None values from response recursively"""
        if isinstance(data, dict):
            return {k: self._clean_response(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self._clean_response(item) for item in data]
        else:
            return data
    
    def get_stock_id(self, symbol: str) -> Optional[int]:
        """Get stock ID by symbol"""
        stock = self.db.get_stock_by_symbol(symbol)
        return stock["id"] if stock else None
    
    def get_complete_stock_page_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get all data needed for complete stock page.
        
        Combines all 6 tabs worth of data.
        """
        stock_id = self.get_stock_id(symbol)
        if not stock_id:
            return {"error": f"Stock {symbol} not found"}
        
        return {
            "overview": self.get_overview_data(stock_id),
            "forecast": self.get_forecast_data(stock_id),
            "technicals": self.get_technicals_data(stock_id),
            "fundamentals": self.get_fundamentals_data(stock_id),
            "risk_sentiment": self.get_risk_sentiment_data(stock_id),
            "company": self.get_company_data(stock_id)
        }


if __name__ == "__main__":
    # Example usage
    from .supabase_client import SupabaseClient
    
    db = SupabaseClient()
    queries = SupabaseQueries(db)
    
    # Get overview for AAPL
    stock_id = queries.get_stock_id("AAPL")
    if stock_id:
        overview = queries.get_overview_data(stock_id)
        print("Overview Data:")
        print(overview)
