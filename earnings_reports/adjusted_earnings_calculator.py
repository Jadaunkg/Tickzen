"""
Adjusted Earnings Calculator Module

Calculates normalized and adjusted earnings metrics by removing one-time items
and non-recurring charges to provide a clearer view of operational performance.

This module is essential for accurate earnings analysis and professional-grade
financial reporting.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class AdjustedEarningsCalculator:
    """
    Calculates adjusted and normalized earnings metrics.
    
    This class removes one-time items, non-recurring charges, and other
    distortions to reveal underlying business performance.
    """
    
    def __init__(self):
        """Initialize the adjusted earnings calculator."""
        self.calculation_metadata = {}
    
    def calculate_all_adjusted_metrics(self, 
                                     raw_financial_data: Dict[str, Any],
                                     one_time_items: Dict[str, Any],
                                     ticker: str) -> Dict[str, Any]:
        """
        Calculate all adjusted earnings metrics for a ticker.
        
        Args:
            raw_financial_data: Raw financial data from yfinance
            one_time_items: One-time items identified by extractor
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing all adjusted earnings metrics
        """
        logger.info(f"Calculating adjusted earnings metrics for {ticker}")
        
        adjusted_metrics = {
            'ticker': ticker,
            'calculation_timestamp': datetime.now().isoformat(),
            'adjustments_made': [],
            'metrics': {},
            'confidence_level': 'high',
            'methodology': 'one_time_items_adjustment'
        }
        
        try:
            # Get base financial data
            income_data = raw_financial_data.get('data', {}).get('income_stmt', {})
            quarterly_income = raw_financial_data.get('data', {}).get('quarterly_income_stmt', {})
            info = raw_financial_data.get('data', {}).get('info', {})
            
            # Calculate adjusted net income
            adjusted_metrics['metrics']['adjusted_net_income'] = self._calculate_adjusted_net_income(
                income_data, one_time_items, adjusted_metrics['adjustments_made']
            )
            
            # Calculate adjusted EPS
            adjusted_metrics['metrics']['adjusted_eps'] = self._calculate_adjusted_eps(
                adjusted_metrics['metrics']['adjusted_net_income'], 
                income_data, 
                info
            )
            
            # Calculate normalized operating metrics
            adjusted_metrics['metrics']['normalized_operating_margin'] = self._calculate_normalized_operating_margin(
                income_data, one_time_items
            )
            
            # Calculate cash-adjusted metrics
            cashflow_data = raw_financial_data.get('data', {}).get('cashflow', {})
            adjusted_metrics['metrics']['cash_adjusted_loss'] = self._calculate_cash_adjusted_loss(
                adjusted_metrics['metrics']['adjusted_net_income'], 
                cashflow_data
            )
            
            # Calculate non-cash loss percentage
            adjusted_metrics['metrics']['non_cash_loss_percentage'] = self._calculate_non_cash_loss_percentage(
                adjusted_metrics['metrics']['adjusted_net_income'],
                cashflow_data
            )
            
            # Calculate quarterly trends
            adjusted_metrics['metrics']['quarterly_adjusted_trends'] = self._calculate_quarterly_trends(
                quarterly_income, one_time_items
            )
            
            # Calculate adjusted margins
            adjusted_metrics['metrics']['adjusted_margins'] = self._calculate_adjusted_margins(
                income_data, one_time_items
            )
            
            logger.info(f"Successfully calculated adjusted metrics for {ticker}")
            
        except Exception as e:
            logger.error(f"Error calculating adjusted metrics for {ticker}: {e}")
            adjusted_metrics['error'] = str(e)
            adjusted_metrics['confidence_level'] = 'low'
        
        return adjusted_metrics
    
    def _calculate_adjusted_net_income(self, 
                                     income_data: Dict[str, Any], 
                                     one_time_items: Dict[str, Any],
                                     adjustments_made: List[str]) -> Dict[str, Any]:
        """Calculate adjusted net income by removing one-time items."""
        adjusted_income = {}
        
        try:
            # Get the most recent periods
            periods = list(income_data.keys()) if income_data else []
            
            for period in periods[:3]:  # Last 3 years
                if period in income_data:
                    period_data = income_data[period]
                    
                    # Start with reported net income
                    reported_net_income = period_data.get('Net Income', 0) or 0
                    
                    # Remove one-time items for this period
                    one_time_adjustment = 0
                    period_str = str(period)
                    
                    for item_key, item_data in one_time_items.get('items_found', {}).items():
                        if period_str in item_key:
                            item_amount = item_data.get('amount', 0) or 0
                            # Add back expenses (they reduce income), subtract gains
                            if item_data.get('type') == 'expense':
                                one_time_adjustment += abs(float(item_amount))
                                adjustments_made.append(f"Added back {item_key}: ${abs(float(item_amount)):,.0f}")
                            else:
                                one_time_adjustment -= abs(float(item_amount))
                                adjustments_made.append(f"Removed gain {item_key}: ${abs(float(item_amount)):,.0f}")
                    
                    # Calculate adjusted net income
                    adjusted_net_income = float(reported_net_income) + one_time_adjustment
                    
                    adjusted_income[str(period)] = {
                        'reported_net_income': float(reported_net_income),
                        'one_time_adjustments': one_time_adjustment,
                        'adjusted_net_income': adjusted_net_income,
                        'improvement': adjusted_net_income - float(reported_net_income),
                        'improvement_percentage': ((adjusted_net_income - float(reported_net_income)) / abs(float(reported_net_income)) * 100) if reported_net_income != 0 else 0
                    }
        
        except Exception as e:
            logger.warning(f"Error calculating adjusted net income: {e}")
        
        return adjusted_income
    
    def _calculate_adjusted_eps(self, 
                              adjusted_income_data: Dict[str, Any], 
                              income_data: Dict[str, Any],
                              info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate adjusted earnings per share."""
        adjusted_eps = {}
        
        try:
            for period, period_data in adjusted_income_data.items():
                adjusted_net_income = period_data.get('adjusted_net_income', 0)
                
                # Get shares outstanding for this period
                shares_outstanding = None
                
                # Try to get from income statement first
                if period in income_data:
                    period_income = income_data[period]
                    shares_outstanding = (
                        period_income.get('Diluted Average Shares', None) or
                        period_income.get('Basic Average Shares', None) or
                        period_income.get('Weighted Average Shares Outstanding', None)
                    )
                
                # Fallback to info data
                if shares_outstanding is None:
                    shares_outstanding = (
                        info.get('sharesOutstanding', None) or
                        info.get('impliedSharesOutstanding', None) or
                        info.get('floatShares', None)
                    )
                
                if shares_outstanding and shares_outstanding > 0:
                    adjusted_eps[period] = {
                        'adjusted_eps': adjusted_net_income / float(shares_outstanding),
                        'reported_eps': period_data.get('reported_net_income', 0) / float(shares_outstanding),
                        'shares_outstanding': float(shares_outstanding),
                        'adjustment_impact': (adjusted_net_income - period_data.get('reported_net_income', 0)) / float(shares_outstanding)
                    }
        
        except Exception as e:
            logger.warning(f"Error calculating adjusted EPS: {e}")
        
        return adjusted_eps
    
    def _calculate_normalized_operating_margin(self, 
                                             income_data: Dict[str, Any], 
                                             one_time_items: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate normalized operating margin removing one-time operating items."""
        normalized_margins = {}
        
        try:
            for period, period_data in income_data.items():
                if isinstance(period_data, dict):
                    revenue = period_data.get('Total Revenue', 0) or 0
                    operating_income = period_data.get('Operating Income', 0) or 0
                    
                    if revenue != 0:
                        # Adjust operating income for one-time items
                        period_str = str(period)
                        operating_adjustments = 0
                        
                        for item_key, item_data in one_time_items.get('items_found', {}).items():
                            if period_str in item_key and item_data.get('category') in ['restructuring', 'impairment', 'litigation']:
                                item_amount = item_data.get('amount', 0) or 0
                                operating_adjustments += abs(float(item_amount))
                        
                        adjusted_operating_income = float(operating_income) + operating_adjustments
                        
                        normalized_margins[str(period)] = {
                            'reported_operating_margin': (float(operating_income) / float(revenue)) * 100,
                            'normalized_operating_margin': (adjusted_operating_income / float(revenue)) * 100,
                            'adjustment_amount': operating_adjustments,
                            'revenue': float(revenue),
                            'reported_operating_income': float(operating_income),
                            'adjusted_operating_income': adjusted_operating_income
                        }
        
        except Exception as e:
            logger.warning(f"Error calculating normalized operating margin: {e}")
        
        return normalized_margins
    
    def _calculate_cash_adjusted_loss(self, 
                                    adjusted_income_data: Dict[str, Any], 
                                    cashflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate loss adjusted for non-cash items."""
        cash_adjusted = {}
        
        try:
            for period, income_period_data in adjusted_income_data.items():
                if period in cashflow_data:
                    cf_period_data = cashflow_data[period]
                    
                    adjusted_net_income = income_period_data.get('adjusted_net_income', 0)
                    operating_cash_flow = cf_period_data.get('Operating Cash Flow', 0) or 0
                    
                    # Calculate non-cash portion
                    non_cash_items = float(operating_cash_flow) - adjusted_net_income
                    
                    cash_adjusted[period] = {
                        'adjusted_net_income': adjusted_net_income,
                        'operating_cash_flow': float(operating_cash_flow),
                        'non_cash_items': non_cash_items,
                        'cash_based_earnings': float(operating_cash_flow)
                    }
        
        except Exception as e:
            logger.warning(f"Error calculating cash adjusted loss: {e}")
        
        return cash_adjusted
    
    def _calculate_non_cash_loss_percentage(self, 
                                          adjusted_income_data: Dict[str, Any], 
                                          cashflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate what percentage of loss is from non-cash items."""
        non_cash_percentages = {}
        
        try:
            for period, income_period_data in adjusted_income_data.items():
                adjusted_net_income = income_period_data.get('adjusted_net_income', 0)
                
                if adjusted_net_income < 0:  # Only for losses
                    if period in cashflow_data:
                        cf_period_data = cashflow_data[period]
                        operating_cash_flow = cf_period_data.get('Operating Cash Flow', 0) or 0
                        
                        # Calculate non-cash portion of loss
                        non_cash_portion = float(operating_cash_flow) - adjusted_net_income
                        non_cash_percentage = (non_cash_portion / abs(adjusted_net_income)) * 100
                        
                        non_cash_percentages[period] = {
                            'loss_amount': adjusted_net_income,
                            'operating_cash_flow': float(operating_cash_flow),
                            'non_cash_portion': non_cash_portion,
                            'non_cash_percentage': non_cash_percentage,
                            'interpretation': self._interpret_non_cash_percentage(non_cash_percentage)
                        }
        
        except Exception as e:
            logger.warning(f"Error calculating non-cash loss percentage: {e}")
        
        return non_cash_percentages
    
    def _interpret_non_cash_percentage(self, percentage: float) -> str:
        """Provide interpretation of non-cash loss percentage."""
        if percentage >= 80:
            return "Loss is primarily non-cash (depreciation, amortization, impairments)"
        elif percentage >= 50:
            return "Loss has significant non-cash components"
        elif percentage >= 20:
            return "Loss has moderate non-cash elements"
        else:
            return "Loss is primarily cash-based"
    
    def _calculate_quarterly_trends(self, 
                                  quarterly_data: Dict[str, Any], 
                                  one_time_items: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quarterly adjusted earnings trends."""
        quarterly_trends = {}
        
        try:
            if quarterly_data:
                quarters = list(quarterly_data.keys())[:4]  # Last 4 quarters
                
                for quarter in quarters:
                    if quarter in quarterly_data:
                        quarter_data = quarterly_data[quarter]
                        
                        net_income = quarter_data.get('Net Income', 0) or 0
                        revenue = quarter_data.get('Total Revenue', 0) or 0
                        
                        # Adjust for one-time items in this quarter
                        quarter_str = str(quarter)
                        quarterly_adjustments = 0
                        
                        for item_key, item_data in one_time_items.get('items_found', {}).items():
                            if quarter_str in item_key and '_Q' in item_key:
                                item_amount = item_data.get('amount', 0) or 0
                                if item_data.get('type') == 'expense':
                                    quarterly_adjustments += abs(float(item_amount))
                        
                        adjusted_quarterly_income = float(net_income) + quarterly_adjustments
                        
                        quarterly_trends[str(quarter)] = {
                            'reported_net_income': float(net_income),
                            'adjusted_net_income': adjusted_quarterly_income,
                            'revenue': float(revenue),
                            'adjusted_margin': (adjusted_quarterly_income / float(revenue) * 100) if revenue != 0 else 0,
                            'one_time_adjustments': quarterly_adjustments
                        }
        
        except Exception as e:
            logger.warning(f"Error calculating quarterly trends: {e}")
        
        return quarterly_trends
    
    def _calculate_adjusted_margins(self, 
                                  income_data: Dict[str, Any], 
                                  one_time_items: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate various adjusted profit margins."""
        adjusted_margins = {}
        
        try:
            for period, period_data in income_data.items():
                if isinstance(period_data, dict):
                    revenue = period_data.get('Total Revenue', 0) or 0
                    
                    if revenue != 0:
                        # Get various profit levels
                        gross_profit = period_data.get('Gross Profit', 0) or 0
                        operating_income = period_data.get('Operating Income', 0) or 0
                        net_income = period_data.get('Net Income', 0) or 0
                        
                        # Apply adjustments
                        period_str = str(period)
                        one_time_total = 0
                        
                        for item_key, item_data in one_time_items.get('items_found', {}).items():
                            if period_str in item_key:
                                item_amount = item_data.get('amount', 0) or 0
                                if item_data.get('type') == 'expense':
                                    one_time_total += abs(float(item_amount))
                        
                        adjusted_margins[str(period)] = {
                            'gross_margin': (float(gross_profit) / float(revenue)) * 100,
                            'reported_operating_margin': (float(operating_income) / float(revenue)) * 100,
                            'adjusted_operating_margin': ((float(operating_income) + one_time_total) / float(revenue)) * 100,
                            'reported_net_margin': (float(net_income) / float(revenue)) * 100,
                            'adjusted_net_margin': ((float(net_income) + one_time_total) / float(revenue)) * 100,
                            'one_time_impact_on_margin': (one_time_total / float(revenue)) * 100
                        }
        
        except Exception as e:
            logger.warning(f"Error calculating adjusted margins: {e}")
        
        return adjusted_margins
    
    def generate_adjustment_summary(self, adjusted_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all adjustments made for reporting purposes."""
        summary = {
            'total_adjustments_made': len(adjusted_metrics.get('adjustments_made', [])),
            'key_insights': [],
            'improvement_in_performance': False,
            'adjusted_vs_reported': {},
            'recommendation': ""
        }
        
        try:
            # Analyze the impact of adjustments
            adjusted_income = adjusted_metrics.get('metrics', {}).get('adjusted_net_income', {})
            
            if adjusted_income:
                latest_period = max(adjusted_income.keys()) if adjusted_income.keys() else None
                
                if latest_period:
                    latest_data = adjusted_income[latest_period]
                    improvement = latest_data.get('improvement', 0)
                    
                    if improvement > 0:
                        summary['improvement_in_performance'] = True
                        summary['key_insights'].append(
                            f"Adjusted earnings show ${improvement:,.0f} improvement over reported results"
                        )
                    
                    summary['adjusted_vs_reported'] = {
                        'reported_net_income': latest_data.get('reported_net_income', 0),
                        'adjusted_net_income': latest_data.get('adjusted_net_income', 0),
                        'improvement_amount': improvement,
                        'improvement_percentage': latest_data.get('improvement_percentage', 0)
                    }
            
            # Generate recommendation
            if summary['improvement_in_performance']:
                summary['recommendation'] = (
                    "Focus on adjusted earnings as they better represent underlying "
                    "business performance after removing one-time distortions."
                )
            else:
                summary['recommendation'] = (
                    "One-time items do not significantly distort reported earnings. "
                    "Reported results appear to reflect normal business operations."
                )
        
        except Exception as e:
            logger.warning(f"Error generating adjustment summary: {e}")
        
        return summary


def calculate_adjusted_earnings_for_ticker(ticker: str, 
                                         raw_financial_data: Dict[str, Any], 
                                         one_time_items: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to calculate adjusted earnings for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        raw_financial_data: Raw financial data from yfinance
        one_time_items: One-time items identified by extractor
        
    Returns:
        Adjusted earnings analysis
    """
    calculator = AdjustedEarningsCalculator()
    return calculator.calculate_all_adjusted_metrics(raw_financial_data, one_time_items, ticker)