"""
Data Processor
==============

Processes raw training data for model training.
Cleans, normalizes, and prepares financial articles.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Process raw financial articles for model training.
    
    Features:
    - Remove HTML/markdown formatting
    - Normalize data placeholders
    - Extract sections by type
    - Remove duplicates
    - Quality filtering
    """
    
    # Common data patterns to normalize
    DATA_PATTERNS = [
        (r'\$[\d,]+\.?\d*', '{PRICE}'),  # Prices: $123.45
        (r'[\d,]+\.?\d*%', '{PERCENT}'),  # Percentages: 12.5%
        (r'\b[A-Z]{1,5}\b', '{TICKER}'),  # Tickers: TSLA, AAPL
        (r'\d+\.\d+x', '{RATIO}'),  # Ratios: 2.5x
        (r'\$[\d,]+\.?\d*[BM]', '{MARKET_CAP}'),  # Market cap: $500B
    ]
    
    # Section headers to identify
    SECTION_HEADERS = {
        'introduction': [
            'introduction', 'overview', 'summary', 'snapshot',
            'executive summary', 'at a glance'
        ],
        'technical_analysis': [
            'technical analysis', 'technical indicators', 'chart analysis',
            'technical outlook', 'price action', 'technicals'
        ],
        'fundamental_analysis': [
            'fundamental analysis', 'fundamentals', 'financial analysis',
            'financial metrics', 'company analysis', 'valuation metrics'
        ],
        'valuation': [
            'valuation', 'price target', 'fair value', 'dcf analysis',
            'valuation analysis', 'intrinsic value'
        ],
        'conclusion': [
            'conclusion', 'summary', 'final thoughts', 'outlook',
            'recommendation', 'verdict', 'bottom line'
        ],
        # NEW: 18 additional section types
        'sector_analysis': [
            'sector analysis', 'industry analysis', 'sector overview',
            'industry overview', 'market position', 'competitive landscape'
        ],
        'competitive_positioning': [
            'competitive positioning', 'competitive analysis', 'competition',
            'peer comparison', 'market share', 'competitive advantages',
            'competitive landscape', 'versus competitors'
        ],
        'growth_prospects': [
            'growth prospects', 'growth outlook', 'growth strategy',
            'growth opportunities', 'expansion plans', 'future growth',
            'growth drivers', 'growth trajectory'
        ],
        'dividend_analysis': [
            'dividend analysis', 'dividend policy', 'dividends',
            'dividend yield', 'payout ratio', 'dividend history',
            'shareholder returns', 'dividend growth'
        ],
        'earnings_analysis': [
            'earnings analysis', 'earnings results', 'quarterly earnings',
            'earnings performance', 'eps analysis', 'earnings report',
            'earnings review', 'earnings surprise'
        ],
        'revenue_breakdown': [
            'revenue breakdown', 'revenue mix', 'revenue segmentation',
            'business segments', 'revenue composition', 'segment analysis',
            'revenue streams', 'revenue sources'
        ],
        'profit_margins': [
            'profit margins', 'margin analysis', 'profitability margins',
            'gross margin', 'operating margin', 'net margin',
            'margin profile', 'margin expansion'
        ],
        'cash_flow_analysis': [
            'cash flow analysis', 'cash flow', 'free cash flow',
            'operating cash flow', 'cash generation', 'cash flow metrics',
            'cash conversion', 'fcf analysis'
        ],
        'balance_sheet_strength': [
            'balance sheet', 'balance sheet strength', 'financial position',
            'capital structure', 'debt and liquidity', 'financial strength',
            'liquidity analysis', 'debt analysis'
        ],
        'management_quality': [
            'management', 'management team', 'leadership',
            'management quality', 'executive team', 'management assessment',
            'leadership quality', 'management analysis'
        ],
        'market_sentiment': [
            'market sentiment', 'investor sentiment', 'sentiment analysis',
            'market mood', 'trading sentiment', 'sentiment indicators',
            'market psychology', 'investor positioning'
        ],
        'analyst_consensus': [
            'analyst consensus', 'analyst ratings', 'wall street consensus',
            'analyst recommendations', 'street consensus', 'analyst views',
            'analyst opinion', 'consensus rating'
        ],
        'historical_performance': [
            'historical performance', 'price history', 'past performance',
            'historical returns', 'performance history', 'track record',
            'historical data', 'past results'
        ],
        'future_catalysts': [
            'future catalysts', 'catalysts', 'upcoming catalysts',
            'potential catalysts', 'drivers', 'value drivers',
            'catalyst pipeline', 'near-term catalysts'
        ],
        'regulatory_environment': [
            'regulatory environment', 'regulation', 'regulatory landscape',
            'compliance', 'regulatory risk', 'regulatory framework',
            'legal environment', 'regulatory considerations'
        ],
        'esg_sustainability': [
            'esg', 'sustainability', 'environmental social governance',
            'esg analysis', 'sustainability analysis', 'corporate responsibility',
            'esg factors', 'esg profile'
        ],
        'investment_thesis': [
            'investment thesis', 'investment case', 'bull case',
            'investment rationale', 'why buy', 'investment summary',
            'investment highlights', 'key takeaways'
        ],
        'risk_analysis': [
            'risk analysis', 'risks', 'risk factors', 'downside risks',
            'key risks', 'risk assessment', 'potential risks'
        ],
        'sentiment_analysis': [
            'sentiment analysis', 'market sentiment', 'investor sentiment',
            'news sentiment', 'analyst sentiment'
        ],
        'quarterly_earnings': [
            'quarterly earnings', 'quarterly results', 'q1 earnings',
            'q2 earnings', 'q3 earnings', 'q4 earnings', 'quarterly performance'
        ]
    }
    
    def __init__(self, 
                 raw_data_dir: str,
                 processed_data_dir: str,
                 min_words: int = 50,
                 max_words: int = 500):
        """
        Initialize Data Processor.
        
        Args:
            raw_data_dir: Directory with raw articles
            processed_data_dir: Directory for processed data
            min_words: Minimum words per section
            max_words: Maximum words per section
        """
        self.raw_dir = Path(raw_data_dir)
        self.processed_dir = Path(processed_data_dir)
        self.min_words = min_words
        self.max_words = max_words
        
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DataProcessor initialized: {raw_data_dir} -> {processed_data_dir}")
    
    def process_all(self) -> Dict[str, int]:
        """
        Process all raw articles.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            'files_processed': 0,
            'sections_extracted': 0,
            'duplicates_removed': 0,
            'quality_filtered': 0
        }
        
        # Find all text/json files in raw directory
        raw_files = list(self.raw_dir.glob('**/*.txt')) + list(self.raw_dir.glob('**/*.json'))
        
        logger.info(f"Found {len(raw_files)} raw files to process")
        
        # Track seen content to remove duplicates
        seen_hashes: Set[str] = set()
        
        # Process each file
        for raw_file in raw_files:
            try:
                content = self._read_file(raw_file)
                sections = self._extract_sections(content)
                
                for section_type, section_text in sections.items():
                    # Clean text
                    cleaned = self._clean_text(section_text)
                    
                    # Quality check
                    if not self._quality_check(cleaned):
                        stats['quality_filtered'] += 1
                        continue
                    
                    # Check for duplicates
                    content_hash = self._hash_content(cleaned)
                    if content_hash in seen_hashes:
                        stats['duplicates_removed'] += 1
                        continue
                    
                    seen_hashes.add(content_hash)
                    
                    # Normalize data placeholders
                    normalized = self._normalize_data(cleaned)
                    
                    # Save processed section
                    self._save_processed(section_type, normalized, raw_file.stem)
                    stats['sections_extracted'] += 1
                
                stats['files_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {raw_file}: {e}")
        
        logger.info(f"Processing complete: {stats}")
        return stats
    
    def _read_file(self, file_path: Path) -> str:
        """Read content from file."""
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Assume content is in 'text', 'content', or 'body' field
                return data.get('text', data.get('content', data.get('body', '')))
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        Extract sections from article content.
        
        Args:
            content: Full article text
        
        Returns:
            Dict mapping section type to text
        """
        sections = {}
        
        # Split by paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_section = None
        current_text = []
        
        for para in paragraphs:
            # Check if paragraph is a section header
            header_found = False
            for section_type, keywords in self.SECTION_HEADERS.items():
                if any(keyword in para.lower() for keyword in keywords):
                    # Save previous section
                    if current_section and current_text:
                        sections[current_section] = '\n'.join(current_text)
                    
                    # Start new section
                    current_section = section_type
                    current_text = []
                    header_found = True
                    break
            
            # Add paragraph to current section
            if not header_found and para:
                current_text.append(para)
        
        # Save last section
        if current_section and current_text:
            sections[current_section] = '\n'.join(current_text)
        
        # If no sections found, treat as general text
        if not sections and content:
            sections['general'] = content
        
        return sections
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw text
        
        Returns:
            Cleaned text
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters (keep basic punctuation)
        text = re.sub(r'[^\w\s\.,!?;:()\-$%]', '', text)
        
        return text.strip()
    
    def _normalize_data(self, text: str) -> str:
        """
        Replace data values with placeholders.
        
        Args:
            text: Cleaned text
        
        Returns:
            Text with normalized placeholders
        """
        normalized = text
        
        for pattern, placeholder in self.DATA_PATTERNS:
            normalized = re.sub(pattern, placeholder, normalized)
        
        return normalized
    
    def _quality_check(self, text: str) -> bool:
        """
        Check if text meets quality standards.
        
        Args:
            text: Text to check
        
        Returns:
            True if text passes quality checks
        """
        # Word count check
        word_count = len(text.split())
        if word_count < self.min_words or word_count > self.max_words:
            return False
        
        # Sentence check (at least 2 sentences)
        sentences = [s for s in re.split(r'[.!?]', text) if s.strip()]
        if len(sentences) < 2:
            return False
        
        # Avoid overly repetitive text
        words = text.lower().split()
        if len(set(words)) / len(words) < 0.3:  # Less than 30% unique words
            return False
        
        return True
    
    def _hash_content(self, text: str) -> str:
        """Create hash of content for duplicate detection."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def _save_processed(self, section_type: str, text: str, source_name: str):
        """
        Save processed text to file.
        
        Args:
            section_type: Type of section
            text: Processed text
            source_name: Original file name
        """
        # Create section directory
        section_dir = self.processed_dir / section_type
        section_dir.mkdir(exist_ok=True)
        
        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{timestamp}.txt"
        
        output_path = section_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
    
    def get_processed_texts(self, section_type: str) -> List[str]:
        """
        Get all processed texts for a section type.
        
        Args:
            section_type: Type of section
        
        Returns:
            List of processed text strings
        """
        section_dir = self.processed_dir / section_type
        
        if not section_dir.exists():
            return []
        
        texts = []
        for file_path in section_dir.glob('*.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                texts.append(f.read())
        
        return texts
    
    def create_training_corpus(self, section_type: str, output_file: str):
        """
        Create a single training corpus file from all processed texts.
        
        Args:
            section_type: Type of section
            output_file: Path to output corpus file
        """
        texts = self.get_processed_texts(section_type)
        
        if not texts:
            logger.warning(f"No processed texts found for {section_type}")
            return
        
        corpus = '\n\n'.join(texts)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(corpus)
        
        logger.info(f"Created training corpus: {output_file} ({len(texts)} texts)")


if __name__ == "__main__":
    # Test processor
    processor = DataProcessor(
        raw_data_dir="training_data/raw",
        processed_data_dir="training_data/processed"
    )
    
    # Create sample raw data
    sample_article = """
    Introduction
    
    Tesla Inc (TSLA) is trading at $242.84, up 3.5% on strong momentum.
    The stock has shown resilience with RSI at 68.4 indicating bullish sentiment.
    
    Technical Analysis
    
    From a technical perspective, TSLA demonstrates strength above key moving averages.
    The 50-day SMA at $245.30 provides support while the 200-day at $220.15 confirms the uptrend.
    RSI readings of 68.4 suggest near-overbought but sustainable momentum.
    
    Conclusion
    
    Overall, TSLA maintains a Buy rating based on strong technicals and fundamental strength.
    """
    
    Path("training_data/raw").mkdir(parents=True, exist_ok=True)
    with open("training_data/raw/sample.txt", 'w') as f:
        f.write(sample_article)
    
    stats = processor.process_all()
    print(f"Processing stats: {stats}")
