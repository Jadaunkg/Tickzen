"""
Cash Sustainability Analyzer Module

Analyzes cash burn rates, runway, and sustainability metrics for companies,
particularly important for loss-making firms and growth companies.

This module provides critical insights for investors about a company's
financial runway and cash management.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class CashSustainabilityAnalyzer:
    """
    Analyzes cash sustainability metrics including burn rate and runway.
    
    This class focuses on cash management analysis, particularly critical
    for companies with negative cash flows or high growth spending.
    """
    
    def __init__(self):
        """Initialize the cash sustainability analyzer."""
        self.analysis_metadata = {}
    
    def analyze_cash_sustainability(self, 
                                  raw_financial_data: Dict[str, Any],
                                  ticker: str) -> Dict[str, Any]:
        """
        Perform comprehensive cash sustainability analysis.
        
        Args:
            raw_financial_data: Raw financial data from yfinance
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing cash sustainability metrics and analysis
        """
        logger.info(f"Analyzing cash sustainability for {ticker}")
        
        sustainability_analysis = {
            'ticker': ticker,
            'analysis_timestamp': datetime.now().isoformat(),
            'metrics': {},
            'risk_level': 'unknown',
            'recommendations': [],
            'key_insights': []
        }
        
        try:
            # Get financial data
            cashflow_data = raw_financial_data.get('data', {}).get('cashflow', {})
            quarterly_cashflow = raw_financial_data.get('data', {}).get('quarterly_cashflow', {})
            balance_sheet = raw_financial_data.get('data', {}).get('balance_sheet', {})
            info = raw_financial_data.get('data', {}).get('info', {})
            
            # Calculate burn rate metrics
            sustainability_analysis['metrics']['burn_rate'] = self._calculate_burn_rate(
                cashflow_data, quarterly_cashflow
            )
            
            # Calculate cash runway
            sustainability_analysis['metrics']['cash_runway'] = self._calculate_cash_runway(
                balance_sheet, sustainability_analysis['metrics']['burn_rate'], info
            )
            
            # Analyze burn rate trends
            sustainability_analysis['metrics']['burn_trends'] = self._analyze_burn_trends(
                quarterly_cashflow
            )
            
            # Calculate financing dependency
            sustainability_analysis['metrics']['financing_dependency'] = self._calculate_financing_dependency(
                cashflow_data, quarterly_cashflow
            )
            
            # Assess liquidity position
            sustainability_analysis['metrics']['liquidity_analysis'] = self._assess_liquidity_position(
                balance_sheet, info
            )
            
            # Generate risk assessment
            sustainability_analysis['risk_level'] = self._assess_cash_risk_level(
                sustainability_analysis['metrics']
            )
            
            # Generate insights and recommendations
            sustainability_analysis['key_insights'] = self._generate_key_insights(
                sustainability_analysis['metrics']
            )
            sustainability_analysis['recommendations'] = self._generate_recommendations(
                sustainability_analysis['metrics'], sustainability_analysis['risk_level']
            )
            
            logger.info(f"Successfully analyzed cash sustainability for {ticker}")
            
        except Exception as e:
            logger.error(f"Error analyzing cash sustainability for {ticker}: {e}")
            sustainability_analysis['error'] = str(e)
        
        return sustainability_analysis
    
    def _calculate_burn_rate(self, 
                           annual_cashflow: Dict[str, Any], 
                           quarterly_cashflow: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quarterly and annual cash burn rates."""
        burn_metrics = {
            'quarterly_burn_rate': 0,
            'annual_burn_rate': 0,
            'operating_burn_rate': 0,
            'free_cash_flow_burn': 0,
            'burn_rate_calculation_method': 'operating_cash_flow'
        }
        
        try:
            # Calculate from quarterly data (more recent)
            if quarterly_cashflow:
                quarters = list(quarterly_cashflow.keys())[:4]  # Last 4 quarters
                quarterly_operating_cf = []
                quarterly_fcf = []
                
                for quarter in quarters:
                    if quarter in quarterly_cashflow:
                        quarter_data = quarterly_cashflow[quarter]
                        
                        # Operating cash flow
                        operating_cf = quarter_data.get('Operating Cash Flow', 0) or 0
                        quarterly_operating_cf.append(float(operating_cf))
                        
                        # Free cash flow (Operating CF - CapEx)
                        capex = abs(quarter_data.get('Capital Expenditures', 0) or 0)
                        fcf = float(operating_cf) - capex
                        quarterly_fcf.append(fcf)
                
                if quarterly_operating_cf:
                    # Average quarterly burn (negative values indicate cash burn)
                    avg_quarterly_operating_cf = np.mean(quarterly_operating_cf)
                    avg_quarterly_fcf = np.mean(quarterly_fcf)
                    
                    burn_metrics['quarterly_burn_rate'] = abs(avg_quarterly_operating_cf) if avg_quarterly_operating_cf < 0 else 0
                    burn_metrics['annual_burn_rate'] = burn_metrics['quarterly_burn_rate'] * 4
                    burn_metrics['free_cash_flow_burn'] = abs(avg_quarterly_fcf) if avg_quarterly_fcf < 0 else 0
                    
                    # Use FCF burn if company is burning through FCF but has positive operating CF
                    if avg_quarterly_operating_cf > 0 and avg_quarterly_fcf < 0:
                        burn_metrics['quarterly_burn_rate'] = burn_metrics['free_cash_flow_burn'] / 4
                        burn_metrics['burn_rate_calculation_method'] = 'free_cash_flow'
            
            # Fallback to annual data if quarterly not available
            elif annual_cashflow:
                latest_year = max(annual_cashflow.keys()) if annual_cashflow.keys() else None
                if latest_year and latest_year in annual_cashflow:
                    year_data = annual_cashflow[latest_year]
                    operating_cf = year_data.get('Operating Cash Flow', 0) or 0
                    
                    if float(operating_cf) < 0:
                        burn_metrics['annual_burn_rate'] = abs(float(operating_cf))
                        burn_metrics['quarterly_burn_rate'] = burn_metrics['annual_burn_rate'] / 4
        
        except Exception as e:
            logger.warning(f"Error calculating burn rate: {e}")
        
        return burn_metrics
    
    def _calculate_cash_runway(self, 
                             balance_sheet: Dict[str, Any], 
                             burn_metrics: Dict[str, Any],
                             info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cash runway in months based on current burn rate."""
        runway_metrics = {
            'cash_runway_months': 'N/A',
            'cash_runway_years': 'N/A',
            'runway_end_date': 'N/A',
            'current_cash': 0,
            'runway_scenario': 'unknown'
        }
        
        try:
            # Get current cash position
            current_cash = 0
            
            # Try balance sheet first
            if balance_sheet:
                latest_period = max(balance_sheet.keys()) if balance_sheet.keys() else None
                if latest_period and latest_period in balance_sheet:
                    balance_data = balance_sheet[latest_period]
                    current_cash = (
                        balance_data.get('Cash And Cash Equivalents', 0) or
                        balance_data.get('Cash', 0) or 
                        0
                    )
            
            # Fallback to info data
            if current_cash == 0:
                current_cash = info.get('totalCash', 0) or 0
            
            runway_metrics['current_cash'] = float(current_cash)
            
            # Calculate runway if we have burn rate
            quarterly_burn = burn_metrics.get('quarterly_burn_rate', 0)
            
            if quarterly_burn > 0 and current_cash > 0:
                runway_months = (float(current_cash) / quarterly_burn) * 3  # Convert quarterly to monthly
                runway_metrics['cash_runway_months'] = runway_months
                runway_metrics['cash_runway_years'] = runway_months / 12
                
                # Calculate approximate runway end date
                runway_end = datetime.now() + timedelta(days=runway_months * 30)
                runway_metrics['runway_end_date'] = runway_end.strftime('%Y-%m-%d')
                
                # Categorize runway scenario
                if runway_months < 6:
                    runway_metrics['runway_scenario'] = 'critical'
                elif runway_months < 12:
                    runway_metrics['runway_scenario'] = 'concerning'
                elif runway_months < 24:
                    runway_metrics['runway_scenario'] = 'moderate'
                else:
                    runway_metrics['runway_scenario'] = 'comfortable'
            
            elif quarterly_burn == 0:
                runway_metrics['runway_scenario'] = 'cash_positive'
                runway_metrics['cash_runway_months'] = 'Indefinite (Cash Positive)'
        
        except Exception as e:
            logger.warning(f"Error calculating cash runway: {e}")
        
        return runway_metrics
    
    def _analyze_burn_trends(self, quarterly_cashflow: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in cash burn rate over recent quarters."""
        trend_analysis = {
            'trend_direction': 'unknown',
            'trend_strength': 'unknown',
            'quarterly_burn_progression': [],
            'burn_acceleration': False,
            'quarterly_variance': 0
        }
        
        try:
            if quarterly_cashflow:
                quarters = sorted(quarterly_cashflow.keys(), reverse=True)[:6]  # Last 6 quarters
                quarterly_burns = []
                
                for quarter in reversed(quarters):  # Chronological order
                    if quarter in quarterly_cashflow:
                        quarter_data = quarterly_cashflow[quarter]
                        operating_cf = quarter_data.get('Operating Cash Flow', 0) or 0
                        
                        # Convert to burn (positive number for cash burn)
                        burn_amount = abs(float(operating_cf)) if float(operating_cf) < 0 else 0
                        quarterly_burns.append({
                            'quarter': str(quarter),
                            'burn_amount': burn_amount,
                            'operating_cf': float(operating_cf)
                        })
                
                trend_analysis['quarterly_burn_progression'] = quarterly_burns
                
                if len(quarterly_burns) >= 3:
                    # Analyze trend
                    recent_burns = [q['burn_amount'] for q in quarterly_burns[-3:]]
                    
                    if len(recent_burns) >= 2:
                        # Simple trend analysis
                        if recent_burns[-1] > recent_burns[0] * 1.1:  # 10% increase
                            trend_analysis['trend_direction'] = 'increasing'
                            trend_analysis['burn_acceleration'] = True
                        elif recent_burns[-1] < recent_burns[0] * 0.9:  # 10% decrease
                            trend_analysis['trend_direction'] = 'decreasing'
                        else:
                            trend_analysis['trend_direction'] = 'stable'
                        
                        # Calculate variance
                        if len(recent_burns) > 1:
                            trend_analysis['quarterly_variance'] = np.std(recent_burns)
                            
                            if trend_analysis['quarterly_variance'] > np.mean(recent_burns) * 0.3:
                                trend_analysis['trend_strength'] = 'volatile'
                            elif trend_analysis['quarterly_variance'] > np.mean(recent_burns) * 0.1:
                                trend_analysis['trend_strength'] = 'moderate'
                            else:
                                trend_analysis['trend_strength'] = 'stable'
        
        except Exception as e:
            logger.warning(f"Error analyzing burn trends: {e}")
        
        return trend_analysis
    
    def _calculate_financing_dependency(self, 
                                      annual_cashflow: Dict[str, Any], 
                                      quarterly_cashflow: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate how dependent the company is on external financing."""
        financing_metrics = {
            'financing_dependency_ratio': 0,
            'recent_financing_activity': 0,
            'debt_issuance': 0,
            'equity_issuance': 0,
            'dependency_level': 'low'
        }
        
        try:
            # Look at recent financing activities
            total_financing = 0
            total_operating_needs = 0
            
            if quarterly_cashflow:
                quarters = list(quarterly_cashflow.keys())[:4]  # Last 4 quarters
                
                for quarter in quarters:
                    if quarter in quarterly_cashflow:
                        quarter_data = quarterly_cashflow[quarter]
                        
                        # Financing cash flows
                        financing_cf = quarter_data.get('Net Cash from Financing Activities', 0) or 0
                        if float(financing_cf) > 0:
                            total_financing += float(financing_cf)
                        
                        # Operating cash flow needs (if negative)
                        operating_cf = quarter_data.get('Operating Cash Flow', 0) or 0
                        if float(operating_cf) < 0:
                            total_operating_needs += abs(float(operating_cf))
            
            financing_metrics['recent_financing_activity'] = total_financing
            
            if total_operating_needs > 0:
                financing_metrics['financing_dependency_ratio'] = (total_financing / total_operating_needs) * 100
                
                # Categorize dependency level
                ratio = financing_metrics['financing_dependency_ratio']
                if ratio >= 80:
                    financing_metrics['dependency_level'] = 'high'
                elif ratio >= 40:
                    financing_metrics['dependency_level'] = 'moderate'
                else:
                    financing_metrics['dependency_level'] = 'low'
        
        except Exception as e:
            logger.warning(f"Error calculating financing dependency: {e}")
        
        return financing_metrics
    
    def _assess_liquidity_position(self, 
                                 balance_sheet: Dict[str, Any], 
                                 info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall liquidity position beyond just cash."""
        liquidity_metrics = {
            'current_ratio': 0,
            'quick_ratio': 0,
            'cash_ratio': 0,
            'working_capital': 0,
            'liquidity_score': 'unknown'
        }
        
        try:
            # Get latest balance sheet data
            if balance_sheet:
                latest_period = max(balance_sheet.keys()) if balance_sheet.keys() else None
                if latest_period and latest_period in balance_sheet:
                    balance_data = balance_sheet[latest_period]
                    
                    # Get balance sheet items
                    current_assets = balance_data.get('Current Assets', 0) or 0
                    current_liabilities = balance_data.get('Current Liabilities', 0) or 0
                    cash = balance_data.get('Cash And Cash Equivalents', 0) or 0
                    accounts_receivable = balance_data.get('Accounts Receivable', 0) or 0
                    inventory = balance_data.get('Inventory', 0) or 0
                    
                    if current_liabilities > 0:
                        # Current ratio
                        liquidity_metrics['current_ratio'] = float(current_assets) / float(current_liabilities)
                        
                        # Quick ratio (excluding inventory)
                        quick_assets = float(current_assets) - float(inventory)
                        liquidity_metrics['quick_ratio'] = quick_assets / float(current_liabilities)
                        
                        # Cash ratio
                        liquidity_metrics['cash_ratio'] = float(cash) / float(current_liabilities)
                    
                    # Working capital
                    liquidity_metrics['working_capital'] = float(current_assets) - float(current_liabilities)
            
            # Alternative from info
            current_ratio_info = info.get('currentRatio', None)
            if current_ratio_info and liquidity_metrics['current_ratio'] == 0:
                liquidity_metrics['current_ratio'] = float(current_ratio_info)
            
            # Score liquidity position
            current_ratio = liquidity_metrics['current_ratio']
            if current_ratio >= 2.0:
                liquidity_metrics['liquidity_score'] = 'strong'
            elif current_ratio >= 1.5:
                liquidity_metrics['liquidity_score'] = 'adequate'
            elif current_ratio >= 1.0:
                liquidity_metrics['liquidity_score'] = 'marginal'
            else:
                liquidity_metrics['liquidity_score'] = 'weak'
        
        except Exception as e:
            logger.warning(f"Error assessing liquidity position: {e}")
        
        return liquidity_metrics
    
    def _assess_cash_risk_level(self, metrics: Dict[str, Any]) -> str:
        """Assess overall cash risk level based on all metrics."""
        risk_factors = []
        
        try:
            # Check runway
            runway_data = metrics.get('cash_runway', {})
            runway_scenario = runway_data.get('runway_scenario', 'unknown')
            
            if runway_scenario == 'critical':
                risk_factors.append('critical_runway')
            elif runway_scenario == 'concerning':
                risk_factors.append('short_runway')
            
            # Check burn trends
            burn_trends = metrics.get('burn_trends', {})
            if burn_trends.get('burn_acceleration', False):
                risk_factors.append('accelerating_burn')
            
            # Check financing dependency
            financing = metrics.get('financing_dependency', {})
            if financing.get('dependency_level') == 'high':
                risk_factors.append('high_financing_dependency')
            
            # Check liquidity
            liquidity = metrics.get('liquidity_analysis', {})
            if liquidity.get('liquidity_score') in ['weak', 'marginal']:
                risk_factors.append('poor_liquidity')
            
            # Assess overall risk
            if 'critical_runway' in risk_factors:
                return 'critical'
            elif len(risk_factors) >= 3:
                return 'high'
            elif len(risk_factors) >= 2:
                return 'moderate'
            elif len(risk_factors) >= 1:
                return 'elevated'
            else:
                return 'low'
        
        except Exception as e:
            logger.warning(f"Error assessing cash risk level: {e}")
            return 'unknown'
    
    def _generate_key_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate key insights about cash sustainability."""
        insights = []
        
        try:
            # Runway insights
            runway_data = metrics.get('cash_runway', {})
            runway_months = runway_data.get('cash_runway_months')
            
            if isinstance(runway_months, (int, float)) and runway_months > 0:
                insights.append(f"Company has approximately {runway_months:.1f} months of cash runway at current burn rate")
            
            # Burn rate insights
            burn_data = metrics.get('burn_rate', {})
            quarterly_burn = burn_data.get('quarterly_burn_rate', 0)
            
            if quarterly_burn > 0:
                insights.append(f"Quarterly cash burn rate is approximately ${quarterly_burn:,.0f}")
            
            # Trend insights
            trends = metrics.get('burn_trends', {})
            trend_direction = trends.get('trend_direction')
            
            if trend_direction == 'increasing':
                insights.append("Cash burn rate is accelerating in recent quarters")
            elif trend_direction == 'decreasing':
                insights.append("Cash burn rate is improving (decreasing) in recent quarters")
            
            # Financing insights
            financing = metrics.get('financing_dependency', {})
            dependency_level = financing.get('dependency_level')
            
            if dependency_level == 'high':
                insights.append("Company is highly dependent on external financing to fund operations")
            
        except Exception as e:
            logger.warning(f"Error generating insights: {e}")
        
        return insights
    
    def _generate_recommendations(self, metrics: Dict[str, Any], risk_level: str) -> List[str]:
        """Generate recommendations based on cash sustainability analysis."""
        recommendations = []
        
        try:
            if risk_level == 'critical':
                recommendations.extend([
                    "Immediate action required to secure additional financing",
                    "Consider emergency cost reduction measures",
                    "Evaluate asset sales or strategic alternatives"
                ])
            elif risk_level == 'high':
                recommendations.extend([
                    "Actively pursue additional funding sources",
                    "Implement cost reduction initiatives",
                    "Accelerate revenue generation efforts"
                ])
            elif risk_level == 'moderate':
                recommendations.extend([
                    "Monitor cash burn closely and plan for future funding needs",
                    "Evaluate operational efficiency improvements",
                    "Maintain relationships with potential funding sources"
                ])
            else:
                recommendations.extend([
                    "Current cash position appears sustainable",
                    "Continue monitoring burn rate trends",
                    "Consider optimizing cash deployment for growth"
                ])
            
            # Specific recommendations based on metrics
            runway_data = metrics.get('cash_runway', {})
            if runway_data.get('runway_scenario') == 'critical':
                recommendations.append("Cash runway is critically short - immediate financing required")
            
            trends = metrics.get('burn_trends', {})
            if trends.get('burn_acceleration'):
                recommendations.append("Address factors driving increased cash burn")
        
        except Exception as e:
            logger.warning(f"Error generating recommendations: {e}")
        
        return recommendations


def analyze_cash_sustainability_for_ticker(ticker: str, raw_financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to analyze cash sustainability for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        raw_financial_data: Raw financial data from yfinance
        
    Returns:
        Cash sustainability analysis
    """
    analyzer = CashSustainabilityAnalyzer()
    return analyzer.analyze_cash_sustainability(raw_financial_data, ticker)