"""
Section Parser Utility
Parses existing HTML stock reports into individual sections
for the new stock page feature
"""

from bs4 import BeautifulSoup
import re
import json
from typing import Dict, List, Optional
from datetime import datetime


class ReportSectionParser:
    """
    Parse HTML stock reports into structured sections
    """
    
    # Define section identifiers based on existing report structure
    SECTION_IDENTIFIERS = {
        'introduction': ['introduction', 'executive summary', 'summary', 'overview'],
        'metrics_summary': ['metrics summary', 'key metrics', 'metrics', 'quick stats'],
        'forecast': ['forecast', 'price forecast', 'prediction', 'detailed forecast'],
        'technical': ['technical analysis', 'technical', 'indicators', 'chart analysis'],
        'fundamentals': ['fundamental', 'valuation', 'financial health', 'profitability'],
        'company': ['company profile', 'company', 'business overview', 'about'],
        'trading': ['trading strategies', 'trading', 'strategies', 'recommendations'],
        'conclusion': ['conclusion', 'outlook', 'final', 'recommendation', 'risk factors', 'faq']
    }
    
    def __init__(self, html_content: str):
        """
        Initialize parser with HTML content
        
        Args:
            html_content: Full HTML report content
        """
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.sections = {}
        
    def parse_all_sections(self) -> Dict[str, str]:
        """
        Parse all sections from the HTML report
        
        Returns:
            Dictionary with section names as keys and HTML content as values
        """
        # Try to identify sections by headers
        sections = self._parse_by_headers()
        
        # If header-based parsing fails, try class-based parsing
        if not sections:
            sections = self._parse_by_classes()
        
        # If both fail, try content-based parsing
        if not sections:
            sections = self._parse_by_content()
        
        # Map parsed sections to standardized section names
        self.sections = self._map_to_standard_sections(sections)
        
        return self.sections
    
    def _parse_by_headers(self) -> Dict[str, str]:
        """Parse sections by identifying header tags (h1, h2, h3)"""
        sections = {}
        current_section = None
        current_content = []
        
        # Find all header tags
        headers = self.soup.find_all(['h1', 'h2', 'h3'])
        
        for header in headers:
            header_text = header.get_text().strip().lower()
            
            # Check if this header matches a section identifier
            section_name = self._identify_section(header_text)
            
            if section_name:
                # Save previous section if exists
                if current_section and current_content:
                    sections[current_section] = ''.join(str(elem) for elem in current_content)
                
                # Start new section
                current_section = section_name
                current_content = [str(header)]
            elif current_section:
                # Add content to current section
                # Get all siblings until next header
                next_elem = header.find_next_sibling()
                while next_elem and next_elem.name not in ['h1', 'h2', 'h3']:
                    current_content.append(str(next_elem))
                    next_elem = next_elem.find_next_sibling()
        
        # Save last section
        if current_section and current_content:
            sections[current_section] = ''.join(str(elem) for elem in current_content)
        
        return sections
    
    def _parse_by_classes(self) -> Dict[str, str]:
        """Parse sections by identifying elements with section-related class names"""
        sections = {}
        
        # Common class patterns in reports
        section_patterns = [
            r'section[-_]',
            r'report[-_]section',
            r'analysis[-_]section',
            r'content[-_]block'
        ]
        
        for pattern in section_patterns:
            elements = self.soup.find_all(class_=re.compile(pattern, re.I))
            
            for elem in elements:
                # Try to identify section from class name or content
                classes = elem.get('class', [])
                section_name = None
                
                for cls in classes:
                    section_name = self._identify_section(cls.lower())
                    if section_name:
                        break
                
                # If not found by class, try by content
                if not section_name:
                    text_content = elem.get_text()[:200].lower()
                    section_name = self._identify_section(text_content)
                
                if section_name:
                    sections[section_name] = str(elem)
        
        return sections
    
    def _parse_by_content(self) -> Dict[str, str]:
        """Parse sections by analyzing content and structure"""
        sections = {}
        
        # Find main content container
        main_content = self.soup.find('main') or self.soup.find('body')
        
        if not main_content:
            return sections
        
        # Split content into logical blocks
        blocks = main_content.find_all(['div', 'section', 'article'], recursive=False)
        
        for block in blocks:
            text_preview = block.get_text()[:300].lower()
            section_name = self._identify_section(text_preview)
            
            if section_name:
                # Check if we already have this section
                if section_name not in sections:
                    sections[section_name] = str(block)
                else:
                    # Append to existing section
                    sections[section_name] += str(block)
        
        return sections
    
    def _identify_section(self, text: str) -> Optional[str]:
        """
        Identify which section a piece of text belongs to
        
        Args:
            text: Text to analyze
            
        Returns:
            Section name or None if not identified
        """
        text_lower = text.lower()
        
        for section_name, identifiers in self.SECTION_IDENTIFIERS.items():
            for identifier in identifiers:
                if identifier in text_lower:
                    return section_name
        
        return None
    
    def _map_to_standard_sections(self, parsed_sections: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Map parsed sections to the standard section structure
        
        Returns:
            Dictionary with standard section names and their subsections
        """
        standard_sections = {
            'overview': {
                'introduction': '',
                'quick_stats': ''
            },
            'forecast': {
                'summary': '',
                'table': '',
                'chart': ''
            },
            'technical': {
                'summary': '',
                'indicators': '',
                'charts': ''
            },
            'fundamentals': {
                'valuation': '',
                'health': '',
                'growth': '',
                'analyst': ''
            },
            'company': {
                'profile': '',
                'business': '',
                'industry': ''
            },
            'trading': {
                'strategies': '',
                'points': '',
                'risk': ''
            },
            'conclusion': {
                'outlook': '',
                'risks': '',
                'recommendation': '',
                'faq': ''
            }
        }
        
        # Map parsed sections to standard structure
        for section_key, section_content in parsed_sections.items():
            if section_key == 'introduction' or section_key in ['overview']:
                standard_sections['overview']['introduction'] = section_content
            elif 'metrics' in section_key:
                standard_sections['overview']['quick_stats'] = section_content
            elif 'forecast' in section_key:
                standard_sections['forecast']['summary'] = section_content
            elif 'technical' in section_key:
                standard_sections['technical']['summary'] = section_content
            elif 'fundamental' in section_key or 'valuation' in section_key:
                standard_sections['fundamentals']['valuation'] = section_content
            elif 'company' in section_key:
                standard_sections['company']['profile'] = section_content
            elif 'trading' in section_key or 'strateg' in section_key:
                standard_sections['trading']['strategies'] = section_content
            elif 'conclusion' in section_key or 'outlook' in section_key:
                standard_sections['conclusion']['outlook'] = section_content
        
        return standard_sections
    
    def extract_metadata(self) -> Dict[str, str]:
        """
        Extract metadata from the report
        
        Returns:
            Dictionary with metadata (ticker, company name, price, etc.)
        """
        metadata = {
            'ticker': '',
            'company_name': '',
            'current_price': '',
            'price_change': '0',
            'market_cap': '',
            'volume': '',
            'pe_ratio': '',
            'dividend_yield': '',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Try to extract ticker from title or headers
        title = self.soup.find('title')
        if title:
            title_text = title.get_text()
            # Look for ticker pattern (e.g., "AAPL", "MSFT")
            ticker_match = re.search(r'\b([A-Z]{1,5})\b', title_text)
            if ticker_match:
                metadata['ticker'] = ticker_match.group(1)
        
        # Try to find company name
        h1 = self.soup.find('h1')
        if h1:
            metadata['company_name'] = h1.get_text().strip()
        
        # Try to extract price information
        price_patterns = [
            r'\$(\d+\.?\d*)',
            r'Price[:\s]+\$?(\d+\.?\d*)',
            r'Current[:\s]+\$?(\d+\.?\d*)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, self.html_content, re.I)
            if match:
                metadata['current_price'] = match.group(1)
                break
        
        return metadata
    
    def generate_template_data(self) -> Dict:
        """
        Generate complete data structure for the stock page template
        
        Returns:
            Dictionary with all data needed for the template
        """
        sections = self.parse_all_sections()
        metadata = self.extract_metadata()
        
        template_data = {
            **metadata,
            # Overview section
            'overview_introduction': sections.get('overview', {}).get('introduction', ''),
            'overview_quick_stats': sections.get('overview', {}).get('quick_stats', ''),
            
            # Forecast section
            'forecast_summary': sections.get('forecast', {}).get('summary', ''),
            'forecast_table': sections.get('forecast', {}).get('table', ''),
            'forecast_chart': sections.get('forecast', {}).get('chart', ''),
            
            # Technical section
            'technical_summary': sections.get('technical', {}).get('summary', ''),
            'technical_indicators': sections.get('technical', {}).get('indicators', ''),
            'technical_charts': sections.get('technical', {}).get('charts', ''),
            
            # Fundamentals section
            'fundamentals_valuation': sections.get('fundamentals', {}).get('valuation', ''),
            'fundamentals_health': sections.get('fundamentals', {}).get('health', ''),
            'fundamentals_growth': sections.get('fundamentals', {}).get('growth', ''),
            'fundamentals_analyst': sections.get('fundamentals', {}).get('analyst', ''),
            
            # Company section
            'company_profile': sections.get('company', {}).get('profile', ''),
            'company_business': sections.get('company', {}).get('business', ''),
            'company_industry': sections.get('company', {}).get('industry', ''),
            
            # Trading section
            'trading_strategies': sections.get('trading', {}).get('strategies', ''),
            'trading_points': sections.get('trading', {}).get('points', ''),
            'trading_risk': sections.get('trading', {}).get('risk', ''),
            
            # Conclusion section
            'conclusion_outlook': sections.get('conclusion', {}).get('outlook', ''),
            'conclusion_risks': sections.get('conclusion', {}).get('risks', ''),
            'conclusion_recommendation': sections.get('conclusion', {}).get('recommendation', ''),
            'conclusion_faq': sections.get('conclusion', {}).get('faq', '')
        }
        
        return template_data
    
    def save_to_json(self, output_path: str):
        """
        Save parsed sections to JSON file
        
        Args:
            output_path: Path to output JSON file
        """
        template_data = self.generate_template_data()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        print(f"Sections saved to {output_path}")


def parse_report_file(html_file_path: str, output_json_path: str = None):
    """
    Convenience function to parse a report file
    
    Args:
        html_file_path: Path to HTML report file
        output_json_path: Optional path to save JSON output
    
    Returns:
        Dictionary with parsed sections
    """
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    parser = ReportSectionParser(html_content)
    template_data = parser.generate_template_data()
    
    if output_json_path:
        parser.save_to_json(output_json_path)
    
    return template_data


# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'parsed_sections.json'
        
        print(f"Parsing report: {html_file}")
        data = parse_report_file(html_file, output_file)
        print(f"Successfully parsed {len(data)} data fields")
    else:
        print("Usage: python section_parser.py <html_report_file> [output_json_file]")
        print("\nExample:")
        print("  python section_parser.py ../generated_data/stock_reports/AAPL_report.html sections.json")
