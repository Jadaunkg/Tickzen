"""
Gemini Article System
SEO-optimized article generation for stock analysis reports
"""

from .article_rewriter import (
    GeminiArticleRewriter, 
    rewrite_stock_report,
    generate_article_from_pipeline
)

__version__ = "1.0.0"
__all__ = [
    'GeminiArticleRewriter', 
    'rewrite_stock_report',
    'generate_article_from_pipeline'
]
