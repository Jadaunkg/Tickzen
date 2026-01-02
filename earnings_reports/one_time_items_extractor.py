"""
One-Time Items Extractor Module

Extracts non-recurring, unusual, and one-time items from financial statements
to enable accurate adjusted earnings calculations and proper loss explanation.

This module is critical for explaining extreme losses and providing context
for unusual financial results.
"""

import logging
import re
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class OneTimeItemsExtractor:
    """
    Extracts one-time and non-recurring items from financial statements.
    
    This class focuses on identifying unusual items that distort normal
    operating performance, particularly important for loss-making companies.
    """
    
    # Known one-time item keywords and patterns
    ONE_TIME_KEYWORDS = {
        'impairment': ['impairment', 'impaired', 'write-down', 'writedown'],
        'restructuring': ['restructuring', 'reorganization', 'severance', 'facility closure'],
        'litigation': ['litigation', 'settlement', 'legal', 'lawsuit', 'fine', 'penalty'],
        'acquisition': ['acquisition', 'merger', 'transaction costs', 'deal costs'],
        'asset_disposal': ['disposal', 'sale of assets', 'discontinued operations'],
        'goodwill_impairment': ['goodwill impairment', 'goodwill write-off'],
        'fair_value': ['fair value adjustment', 'mark-to-market', 'unrealized'],
        'contingencies': ['contingent', 'provision for', 'accrual'],
        'tax_items': ['tax benefit', 'tax charge', 'deferred tax', 'tax adjustment']
    }
    
    def __init__(self):
        """Initialize the one-time items extractor."""
        self.extracted_items = {}
    
    def extract_from_yfinance_data(self, yf_data: Dict[str, Any], ticker: str) -> Dict[str, Any]:
        """
        Extract one-time items from yfinance financial statements.
        
        Args:
            yf_data: yfinance data dictionary
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing identified one-time items
        """
        logger.info(f"Extracting one-time items for {ticker} from yfinance data")
        
        one_time_items = {
            'ticker': ticker,
            'extraction_timestamp': datetime.now().isoformat(),
            'items_found': {},
            'total_one_time_impact': 0,
            'confidence_level': 'medium',  # Based on yfinance data limitation
            'data_source': 'yfinance_inference'
        }
        
        try:
            # Extract from income statement
            income_stmt = yf_data.get('data', {}).get('income_stmt', {})
            quarterly_income = yf_data.get('data', {}).get('quarterly_income_stmt', {})
            
            # Look for unusual expense items in income statement
            one_time_items['items_found'].update(
                self._analyze_income_statement_items(income_stmt, quarterly_income)
            )
            
            # Extract from cash flow statement
            cashflow = yf_data.get('data', {}).get('cashflow', {})
            quarterly_cashflow = yf_data.get('data', {}).get('quarterly_cashflow', {})
            
            one_time_items['items_found'].update(
                self._analyze_cashflow_items(cashflow, quarterly_cashflow)
            )
            
            # Calculate total impact
            one_time_items['total_one_time_impact'] = self._calculate_total_impact(
                one_time_items['items_found']
            )
            
            logger.info(f"Found {len(one_time_items['items_found'])} one-time items for {ticker}")
            
        except Exception as e:
            logger.error(f"Error extracting one-time items for {ticker}: {e}")
            one_time_items['error'] = str(e)
        
        return one_time_items
    
    def _analyze_income_statement_items(self, annual_data: Dict, quarterly_data: Dict) -> Dict[str, Any]:
        """Analyze income statement for one-time items."""
        items_found = {}
        
        try:
            # CORRECTED: Using actual yfinance field names
            actual_yfinance_one_time_fields = [
                'Total Unusual Items',
                'Total Unusual Items Excluding Goodwill', 
                'Special Income Charges',
                'Restructuring And Mergern Acquisition',  # Note: yfinance has typo "Mergern"
                'Tax Effect Of Unusual Items',
                'Other Income Expense',  # Can contain one-time items
                'Other Non Operating Income Expenses'  # Can contain one-time items
            ]
            
            # Check annual data first
            for period, data in annual_data.items():
                if isinstance(data, dict):
                    for item_name in actual_yfinance_one_time_fields:
                        if item_name in data and data[item_name] is not None and data[item_name] != 0:
                            amount = data[item_name]
                            # Only include significant amounts (over $1M or 1% of revenue)
                            if abs(float(amount)) > 1000000:  # $1M threshold
                                items_found[f"{item_name}_{period}"] = {
                                    'amount': amount,
                                    'period': str(period),
                                    'type': 'expense' if amount > 0 else 'income',
                                    'category': self._categorize_yfinance_item(item_name),
                                    'frequency': 'annual',
                                    'field_name': item_name
                                }
            
            # Check quarterly data for recent unusual items
            if quarterly_data:
                latest_quarters = list(quarterly_data.keys())[:2]  # Last 2 quarters
                for period in latest_quarters:
                    if period in quarterly_data:
                        quarter_data = quarterly_data[period]
                        if isinstance(quarter_data, dict):
                            for item_name in actual_yfinance_one_time_fields:
                                if item_name in quarter_data and quarter_data[item_name] is not None and quarter_data[item_name] != 0:
                                    amount = quarter_data[item_name]
                                    # Lower threshold for quarterly data
                                    if abs(float(amount)) > 500000:  # $500K threshold for quarterly
                                        items_found[f"{item_name}_{period}_Q"] = {
                                            'amount': amount,
                                            'period': str(period),
                                            'type': 'expense' if amount > 0 else 'income',
                                            'category': self._categorize_yfinance_item(item_name),
                                            'frequency': 'quarterly',
                                            'field_name': item_name
                                        }
            
        except Exception as e:
            logger.warning(f"Error analyzing income statement items: {e}")
        
        return items_found
    
    def _analyze_cashflow_items(self, annual_data: Dict, quarterly_data: Dict) -> Dict[str, Any]:
        """Analyze cash flow statement for one-time items."""
        items_found = {}
        
        try:
            # CORRECTED: Using actual yfinance cash flow field names
            actual_yfinance_cashflow_fields = [
                'Asset Impairment Charge',
                'Gain Loss On Sale Of PPE',
                'Sale Of Investment',
                'Net Business Purchase And Sale',
                'Sale Of Business',
                'Net Intangibles Purchase And Sale', 
                'Sale Of Intangibles',
                'Net Investment Purchase And Sale'
            ]
            
            # Check annual cash flow
            for period, data in annual_data.items():
                if isinstance(data, dict):
                    for item_name in actual_yfinance_cashflow_fields:
                        if item_name in data and data[item_name] is not None and data[item_name] != 0:
                            amount = data[item_name]
                            # Only include significant amounts (over $1M)
                            if abs(float(amount)) > 1000000:  # $1M threshold
                                items_found[f"CF_{item_name}_{period}"] = {
                                    'amount': amount,
                                    'period': str(period),
                                    'type': 'cash_flow',
                                    'category': self._categorize_cashflow_item(item_name),
                                    'frequency': 'annual',
                                    'field_name': item_name
                                }
            
            # Check quarterly data
            if quarterly_data:
                latest_quarters = list(quarterly_data.keys())[:2]  # Last 2 quarters
                for period in latest_quarters:
                    if period in quarterly_data:
                        quarter_data = quarterly_data[period]
                        if isinstance(quarter_data, dict):
                            for item_name in actual_yfinance_cashflow_fields:
                                if item_name in quarter_data and quarter_data[item_name] is not None and quarter_data[item_name] != 0:
                                    amount = quarter_data[item_name]
                                    if abs(float(amount)) > 500000:  # $500K threshold for quarterly
                                        items_found[f"CF_{item_name}_{period}_Q"] = {
                                            'amount': amount,
                                            'period': str(period),
                                            'type': 'cash_flow',
                                            'category': self._categorize_cashflow_item(item_name),
                                            'frequency': 'quarterly',
                                            'field_name': item_name
                                        }
            
        except Exception as e:
            logger.warning(f"Error analyzing cash flow items: {e}")
        
        return items_found
    
    def _categorize_cashflow_item(self, field_name: str) -> str:
        """Categorize cash flow one-time items."""
        field_lower = field_name.lower()
        
        if 'impairment' in field_lower:
            return 'impairment'
        elif 'sale of business' in field_lower or 'business purchase' in field_lower:
            return 'acquisition_disposal'
        elif 'sale of investment' in field_lower or 'investment purchase' in field_lower:
            return 'investment_activity'
        elif 'gain loss on sale' in field_lower:
            return 'asset_disposal'
        elif 'intangibles' in field_lower:
            return 'intangible_transactions'
        else:
            return 'other_investing'
    
    def _categorize_item(self, item_name: str) -> str:
        """Categorize one-time item by type."""
        item_lower = item_name.lower()
        
        if any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['impairment']):
            return 'impairment'
        elif any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['restructuring']):
            return 'restructuring'
        elif any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['litigation']):
            return 'litigation'
        elif any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['acquisition']):
            return 'acquisition'
        elif any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['asset_disposal']):
            return 'asset_disposal'
        elif any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['goodwill_impairment']):
            return 'goodwill_impairment'
        elif any(keyword in item_lower for keyword in self.ONE_TIME_KEYWORDS['fair_value']):
            return 'fair_value'
        else:
            return 'other'
    
    def _categorize_yfinance_item(self, field_name: str) -> str:
        """Categorize yfinance-specific one-time item fields."""
        field_lower = field_name.lower()
        
        if 'unusual items' in field_lower:
            return 'unusual_items'
        elif 'restructuring' in field_lower or 'merger' in field_lower:
            return 'restructuring'
        elif 'special income charges' in field_lower:
            return 'special_charges'
        elif 'tax effect' in field_lower:
            return 'tax_adjustments'
        elif 'other income expense' in field_lower or 'other non operating' in field_lower:
            return 'other_non_operating'
        else:
            return 'other'
    
    def _calculate_total_impact(self, items_found: Dict[str, Any]) -> float:
        """Calculate total financial impact of one-time items, avoiding double counting."""
        total_impact = 0
        seen_amounts = set()  # Track amounts to avoid double counting
        
        try:
            for item_key, item_data in items_found.items():
                if 'amount' in item_data and item_data['amount'] is not None:
                    # Convert to float if it's not already
                    amount = float(item_data['amount'])
                    period = item_data.get('period', '')
                    field_name = item_data.get('field_name', '')
                    
                    # Create a unique key to avoid double counting similar items from same period
                    unique_key = f"{field_name}_{period}_{abs(amount)}"
                    
                    # Skip if we've already counted this exact amount from same field and period
                    if unique_key not in seen_amounts:
                        # For investment activities, only count if they're unusual (not normal business)
                        if 'investment_activity' in item_data.get('category', ''):
                            # Only count investment sales/purchases over $1B as truly unusual
                            if abs(amount) > 1000000000:  # $1B threshold for investments
                                total_impact += abs(amount)
                                seen_amounts.add(unique_key)
                        else:
                            # Count all other one-time items
                            total_impact += abs(amount)
                            seen_amounts.add(unique_key)
        except Exception as e:
            logger.warning(f"Error calculating total one-time impact: {e}")
        
        return total_impact
    
    def get_one_time_summary(self, one_time_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of one-time items for reporting.
        
        Args:
            one_time_data: One-time items data
            
        Returns:
            Summary dictionary for report generation
        """
        summary = {
            'has_one_time_items': len(one_time_data.get('items_found', {})) > 0,
            'total_impact': one_time_data.get('total_one_time_impact', 0),
            'categories_affected': [],
            'major_items': [],
            'explanation_text': ""
        }
        
        items_found = one_time_data.get('items_found', {})
        
        # Categorize items
        categories = set()
        major_items = []
        
        for item_key, item_data in items_found.items():
            category = item_data.get('category', 'other')
            categories.add(category)
            
            # Consider items over $1M as major (adjust threshold as needed)
            amount = abs(float(item_data.get('amount', 0)))
            if amount > 1000000:  # $1M threshold
                major_items.append({
                    'name': item_key,
                    'amount': amount,
                    'category': category,
                    'period': item_data.get('period', 'unknown')
                })
        
        summary['categories_affected'] = list(categories)
        summary['major_items'] = sorted(major_items, key=lambda x: x['amount'], reverse=True)
        
        # Generate explanation text
        if summary['has_one_time_items']:
            impact_millions = summary['total_impact'] / 1000000
            summary['explanation_text'] = (
                f"The company reported approximately ${impact_millions:.1f}M in one-time items "
                f"across {len(categories)} categories, including {', '.join(categories)}. "
                f"These items significantly impact reported earnings and should be considered "
                f"when evaluating underlying business performance."
            )
        else:
            summary['explanation_text'] = (
                "No significant one-time items identified in recent financial statements. "
                "Reported earnings appear to reflect normal business operations."
            )
        
        return summary


def extract_one_time_items_for_ticker(ticker: str, yf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to extract one-time items for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        yf_data: yfinance data dictionary
        
    Returns:
        One-time items analysis
    """
    extractor = OneTimeItemsExtractor()
    return extractor.extract_from_yfinance_data(yf_data, ticker)