"""
Markov Text Generation System for Financial Analysis
====================================================

A production-ready Markov Chain text generation system designed specifically
for financial analysts to generate unique, high-quality summaries and narratives.

Key Components:
--------------
- Core Engine: Advanced Markov chain implementation
- Model Manager: Load, save, version control for trained models
- Training Pipeline: Process large datasets and articles
- Summary Generator: Generate financial summaries with data preservation
- WordPress Integration: Seamless integration with WordPress reporter

Usage:
------
    from markov_text_generation import FinancialSummaryGenerator
    
    generator = FinancialSummaryGenerator()
    summary = generator.generate_summary(
        ticker="AAPL",
        data=financial_data,
        section_type="introduction"
    )

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Tickzen Development Team"

from .core.engine import MarkovEngine
from .core.model_manager import ModelManager
from .generators.summary_generator import FinancialSummaryGenerator
from .generators.section_generator import SectionGenerator

__all__ = [
    'MarkovEngine',
    'ModelManager',
    'FinancialSummaryGenerator',
    'SectionGenerator',
]
