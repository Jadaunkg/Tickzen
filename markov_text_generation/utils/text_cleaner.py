"""
Text Cleaning Utilities
=======================

Utilities for preprocessing and cleaning financial text data.
"""

import re
from typing import List, Set


class TextCleaner:
    """Utilities for cleaning and normalizing text."""
    
    # Common financial stopwords to optionally remove
    FINANCIAL_STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'should', 'could', 'may', 'might', 'must', 'can'
    }
    
    @staticmethod
    def remove_html(text: str) -> str:
        """Remove HTML tags."""
        return re.sub(r'<[^>]+>', '', text)
    
    @staticmethod
    def remove_markdown(text: str) -> str:
        """Remove markdown formatting."""
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'__([^_]+)__', r'\1', text)  # Bold alt
        text = re.sub(r'_([^_]+)_', r'\1', text)  # Italic alt
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
        text = re.sub(r'#+\s*', '', text)  # Headers
        return text
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace to single spaces."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def remove_urls(text: str) -> str:
        """Remove URLs."""
        return re.sub(r'https?://\S+|www\.\S+', '', text)
    
    @staticmethod
    def remove_emails(text: str) -> str:
        """Remove email addresses."""
        return re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
    
    @staticmethod
    def normalize_numbers(text: str, placeholder: str = '{NUMBER}') -> str:
        """Replace numbers with placeholder."""
        return re.sub(r'\d+\.?\d*', placeholder, text)
    
    @staticmethod
    def normalize_prices(text: str, placeholder: str = '{PRICE}') -> str:
        """Replace prices with placeholder."""
        return re.sub(r'\$[\d,]+\.?\d*', placeholder, text)
    
    @staticmethod
    def normalize_percentages(text: str, placeholder: str = '{PERCENT}') -> str:
        """Replace percentages with placeholder."""
        return re.sub(r'[\d,]+\.?\d*%', placeholder, text)
    
    @staticmethod
    def normalize_tickers(text: str, placeholder: str = '{TICKER}') -> str:
        """Replace stock tickers with placeholder."""
        return re.sub(r'\b[A-Z]{1,5}\b', placeholder, text)
    
    @staticmethod
    def remove_special_chars(text: str, keep: str = '.,!?;:()-$%') -> str:
        """Remove special characters, keeping specified ones."""
        pattern = f'[^\\w\\s{re.escape(keep)}]'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def remove_stopwords(text: str, stopwords: Set[str] = None) -> str:
        """Remove stopwords from text."""
        if stopwords is None:
            stopwords = TextCleaner.FINANCIAL_STOPWORDS
        
        words = text.split()
        filtered = [w for w in words if w.lower() not in stopwords]
        return ' '.join(filtered)
    
    @staticmethod
    def clean_financial_text(text: str,
                           remove_html: bool = True,
                           remove_markdown: bool = True,
                           remove_urls: bool = True,
                           normalize_ws: bool = True) -> str:
        """
        Apply standard cleaning pipeline for financial text.
        
        Args:
            text: Input text
            remove_html: Remove HTML tags
            remove_markdown: Remove markdown formatting
            remove_urls: Remove URLs
            normalize_ws: Normalize whitespace
        
        Returns:
            Cleaned text
        """
        if remove_html:
            text = TextCleaner.remove_html(text)
        
        if remove_markdown:
            text = TextCleaner.remove_markdown(text)
        
        if remove_urls:
            text = TextCleaner.remove_urls(text)
        
        if normalize_ws:
            text = TextCleaner.normalize_whitespace(text)
        
        return text
    
    @staticmethod
    def extract_data_placeholders(text: str) -> List[str]:
        """
        Extract all placeholder patterns from text.
        
        Returns:
            List of placeholder strings found
        """
        pattern = r'\{[A-Z_]+\}'
        return re.findall(pattern, text)
    
    @staticmethod
    def preserve_placeholders(text: str, operation) -> str:
        """
        Apply operation while preserving placeholders.
        
        Args:
            text: Input text
            operation: Function to apply
        
        Returns:
            Processed text with placeholders preserved
        """
        # Extract placeholders with positions
        placeholders = []
        pattern = r'\{[A-Z_]+\}'
        
        for match in re.finditer(pattern, text):
            placeholders.append({
                'text': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        # Replace with temporary markers
        temp_text = text
        for i, ph in enumerate(placeholders):
            marker = f'__PH{i}__'
            temp_text = temp_text.replace(ph['text'], marker, 1)
        
        # Apply operation
        processed = operation(temp_text)
        
        # Restore placeholders
        for i, ph in enumerate(placeholders):
            marker = f'__PH{i}__'
            processed = processed.replace(marker, ph['text'], 1)
        
        return processed


def clean_text(text: str) -> str:
    """Quick clean function."""
    return TextCleaner.clean_financial_text(text)


def normalize_data_values(text: str) -> str:
    """Normalize all data values to placeholders."""
    text = TextCleaner.normalize_prices(text)
    text = TextCleaner.normalize_percentages(text)
    text = TextCleaner.normalize_tickers(text)
    return text


if __name__ == "__main__":
    # Test cleaner
    sample = """
    <p>**Tesla Inc (TSLA)** is trading at $242.84, up 3.5% today.</p>
    Visit https://example.com for more info.
    Contact: info@example.com
    
    The   stock    shows   strong momentum.
    """
    
    cleaned = TextCleaner.clean_financial_text(sample)
    print("Cleaned:", cleaned)
    
    normalized = normalize_data_values(cleaned)
    print("Normalized:", normalized)
