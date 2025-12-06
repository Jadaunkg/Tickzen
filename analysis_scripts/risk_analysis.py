# risk_analysis.py - Enhanced Risk Analysis Module
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

class RiskAnalyzer:
    """Advanced risk analysis for stock evaluation"""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% risk-free rate
    
    def calculate_var(self, returns, confidence_level=0.05, method='historical'):
        """Calculate Value at Risk"""
        if method == 'historical':
            return np.percentile(returns, confidence_level * 100)
        elif method == 'parametric':
            mu = returns.mean()
            sigma = returns.std()
            return stats.norm.ppf(confidence_level, mu, sigma)
    
    def calculate_sharpe_ratio(self, returns):
        """Calculate Sharpe ratio"""
        excess_returns = returns - self.risk_free_rate/252
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    
    def calculate_sortino_ratio(self, returns):
        """Calculate Sortino ratio (downside deviation)"""
        excess_returns = returns - self.risk_free_rate/252
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = downside_returns.std()
        return excess_returns.mean() / downside_deviation * np.sqrt(252)
    
    def calculate_max_drawdown(self, prices):
        """Calculate maximum drawdown"""
        cumulative = (1 + prices.pct_change()).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def calculate_beta(self, stock_returns, market_returns):
        """Calculate beta coefficient"""
        covariance = np.cov(stock_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        return covariance / market_variance
    
    def comprehensive_risk_profile(self, price_data, market_data=None):
        """Generate comprehensive risk analysis"""
        returns = price_data.pct_change().dropna()
        
        risk_metrics = {
            'volatility_annualized': returns.std() * np.sqrt(252),
            'var_5': self.calculate_var(returns, 0.05),
            'var_1': self.calculate_var(returns, 0.01),
            'sharpe_ratio': self.calculate_sharpe_ratio(returns),
            'sortino_ratio': self.calculate_sortino_ratio(returns),
            'max_drawdown': self.calculate_max_drawdown(price_data),
            'skewness': stats.skew(returns),
            'kurtosis': stats.kurtosis(returns)
        }
        
        if market_data is not None:
            market_returns = market_data.pct_change().dropna()
            risk_metrics['beta'] = self.calculate_beta(returns, market_returns)
            risk_metrics['correlation_market'] = np.corrcoef(returns, market_returns)[0][1]
        
        return risk_metrics