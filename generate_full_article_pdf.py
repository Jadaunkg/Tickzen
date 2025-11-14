"""
Full Pipeline Script: Data Collection to PDF Generation
========================================================
This script executes the complete WordPress pipeline from data collection
to generating a clean text-only PDF report.

Features:
- Real data collection from yfinance
- Complete analysis pipeline (technical, fundamental, sentiment, risk)
- Content library variations for unique content
- Clean PDF output with text only (no HTML tags)
- Progress tracking and error handling

Usage:
    python generate_full_article_pdf.py TICKER [--output-dir PATH]
    
Example:
    python generate_full_article_pdf.py AAPL
    python generate_full_article_pdf.py MSFT --output-dir c:/reports
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
import re
from html.parser import HTMLParser

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("WARNING: reportlab not installed. Install with: pip install reportlab")

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from automation_scripts.pipeline import run_wp_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'pipeline_pdf_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML, preserving structure."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_tag = None
        self.in_script = False
        self.in_style = False
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ['script', 'style']:
            if tag == 'script':
                self.in_script = True
            else:
                self.in_style = True
        elif tag == 'br':
            self.text_parts.append('\n')
        elif tag == 'p':
            if self.text_parts and self.text_parts[-1] != '\n\n':
                self.text_parts.append('\n\n')
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.text_parts and self.text_parts[-1] != '\n\n':
                self.text_parts.append('\n\n')
        elif tag == 'li':
            self.text_parts.append('\n  • ')
        elif tag == 'tr':
            if self.text_parts and self.text_parts[-1] != '\n':
                self.text_parts.append('\n')
        elif tag == 'td' or tag == 'th':
            self.text_parts.append(' | ')
    
    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        elif tag == 'style':
            self.in_style = False
        elif tag in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.text_parts and self.text_parts[-1] != '\n\n':
                self.text_parts.append('\n\n')
        elif tag == 'tr':
            self.text_parts.append('\n')
    
    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            # Clean up whitespace but preserve intentional line breaks
            text = data.strip()
            if text:
                self.text_parts.append(text + ' ')
    
    def get_text(self):
        """Get extracted text with cleaned whitespace."""
        text = ''.join(self.text_parts)
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
        # Clean up multiple newlines (max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def extract_text_from_html(html_content):
    """
    Extract clean text from HTML content.
    
    Args:
        html_content (str): HTML string
        
    Returns:
        str: Clean text without HTML tags
    """
    try:
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        return parser.get_text()
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        # Fallback: simple regex-based cleaning
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def create_pdf_from_text(html_content, ticker, output_path):
    """
    Create a PDF from HTML content using ReportLab with proper table and formatting support.
    
    Args:
        html_content (str): HTML content with tables and formatting
        ticker (str): Stock ticker symbol
        output_path (str): Path to save PDF
        
    Returns:
        bool: Success status
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab is not installed. Cannot generate PDF.")
        return False
    
    try:
        from bs4 import BeautifulSoup
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Justify',
            parent=styles['BodyText'],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=14,
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='SubHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Parse HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Add title
        title = f"Stock Analysis Report: {ticker}"
        elements.append(Paragraph(title, styles['CustomTitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add generation date
        date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        elements.append(Paragraph(date_text, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Process HTML elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table', 'div']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Handle headers
                level = int(element.name[1])
                if level == 1:
                    style = styles['CustomTitle']
                elif level == 2:
                    style = styles['SectionHeader']
                elif level == 3:
                    style = styles['SubHeader']
                else:
                    style = styles['Heading4']
                
                text = element.get_text().strip()
                if text:
                    elements.append(Paragraph(text, style))
                    
            elif element.name == 'p':
                # Handle paragraphs
                text = element.get_text().strip()
                if text:
                    # Escape special characters for ReportLab
                    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    elements.append(Paragraph(text, styles['Justify']))
                    
            elif element.name == 'table':
                # Handle tables
                table_data = []
                headers = []
                
                # Extract table headers
                thead = element.find('thead')
                if thead:
                    header_row = thead.find('tr')
                    if header_row:
                        headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                        table_data.append(headers)
                
                # Extract table body
                tbody = element.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr'):
                        row_data = []
                        for cell in row.find_all(['td', 'th']):
                            cell_text = cell.get_text().strip()
                            # Clean up any HTML entities or extra whitespace
                            cell_text = cell_text.replace('\n', ' ').replace('\r', '').strip()
                            row_data.append(cell_text)
                        if row_data:
                            table_data.append(row_data)
                
                # Create ReportLab table if we have data
                if table_data:
                    # Calculate column widths (distribute evenly)
                    col_count = len(table_data[0]) if table_data else 1
                    available_width = doc.width
                    col_width = available_width / col_count
                    
                    # Create table
                    table = Table(table_data, colWidths=[col_width] * col_count)
                    
                    # Style the table
                    table_style = TableStyle([
                        # Header styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#495057')),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                        
                        # Body styling
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                        
                        # Grid lines
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef')),
                        
                        # Alternating row colors for body
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                        
                        # Padding
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ])
                    
                    table.setStyle(table_style)
                    elements.append(Spacer(1, 0.2*inch))
                    elements.append(table)
                    elements.append(Spacer(1, 0.2*inch))
                    
            elif element.name == 'div' and 'narrative' in element.get('class', []):
                # Handle narrative divs (paragraphs)
                for p in element.find_all('p'):
                    text = p.get_text().strip()
                    if text:
                        # Escape special characters for ReportLab
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        elements.append(Paragraph(text, styles['Justify']))
        
        # Add footer disclaimer
        elements.append(PageBreak())
        disclaimer = """
        <b>DISCLAIMER:</b> This report is for informational purposes only and should not be 
        considered as financial advice. Always conduct your own research and consult with a 
        qualified financial advisor before making investment decisions. Past performance does 
        not guarantee future results.
        """
        elements.append(Paragraph(disclaimer, styles['BodyText']))
        
        # Build PDF
        doc.build(elements)
        logger.info(f"PDF successfully created: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating PDF: {e}", exc_info=True)
        return False


def create_simple_text_pdf(text_content, ticker, output_path):
    """
    Fallback: Create a simple text file if ReportLab is not available.
    
    Args:
        text_content (str): Plain text content
        ticker (str): Stock ticker symbol
        output_path (str): Path to save text file
        
    Returns:
        bool: Success status
    """
    try:
        # Change extension to .txt
        output_path = output_path.replace('.pdf', '.txt')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Stock Analysis Report: {ticker}\n")
            f.write(f"{'='*80}\n")
            f.write(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n")
            f.write(f"{'='*80}\n\n")
            f.write(text_content)
            f.write(f"\n\n{'='*80}\n")
            f.write("DISCLAIMER: This report is for informational purposes only.\n")
            f.write(f"{'='*80}\n")
        
        logger.info(f"Text file successfully created: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating text file: {e}", exc_info=True)
        return False


def run_full_pipeline_to_pdf(ticker, output_dir=None):
    """
    Execute complete pipeline from data collection to PDF generation.
    
    Args:
        ticker (str): Stock ticker symbol
        output_dir (str, optional): Directory to save PDF. Defaults to generated_data/pdf_reports
        
    Returns:
        str: Path to generated PDF file, or None if failed
    """
    logger.info(f"{'='*80}")
    logger.info(f"Starting Full Pipeline for {ticker}")
    logger.info(f"{'='*80}")
    
    # Set up output directory
    if output_dir is None:
        app_root = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(app_root, 'generated_data', 'pdf_reports')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        # Step 1: Run WordPress Pipeline
        logger.info(f"\n{'='*80}")
        logger.info("STEP 1: Running Data Collection & Analysis Pipeline")
        logger.info(f"{'='*80}")
        
        app_root = os.path.dirname(os.path.abspath(__file__))
        
        model, forecast, html_report, image_urls = run_wp_pipeline(
            ticker=ticker,
            ts=timestamp,
            app_root=app_root,
            socketio_instance=None,
            task_room=None
        )
        
        if html_report is None or "Error Generating Report" in html_report:
            logger.error(f"Pipeline failed to generate report for {ticker}")
            return None
        
        logger.info(f"✓ Pipeline completed successfully for {ticker}")
        logger.info(f"  - Model trained: {'Yes' if model else 'No'}")
        logger.info(f"  - Forecast generated: {'Yes' if forecast is not None else 'No'}")
        logger.info(f"  - HTML report length: {len(html_report)} characters")
        logger.info(f"  - Images generated: {len(image_urls)} items")
        
        # Step 2: Extract Text from HTML (for fallback)
        logger.info(f"\n{'='*80}")
        logger.info("STEP 2: Processing HTML Report for PDF")
        logger.info(f"{'='*80}")
        
        # Keep HTML content for PDF generation
        html_content = html_report
        text_content = extract_text_from_html(html_report)
        logger.info(f"✓ HTML content ready: {len(html_content)} characters")
        logger.info(f"✓ Text extracted: {len(text_content)} characters")
        
        # Step 3: Generate PDF
        logger.info(f"\n{'='*80}")
        logger.info("STEP 3: Generating PDF Report")
        logger.info(f"{'='*80}")
        
        pdf_filename = f"{ticker}_analysis_report_{timestamp}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        if REPORTLAB_AVAILABLE:
            success = create_pdf_from_text(html_content, ticker, pdf_path)  # Pass HTML instead of text
        else:
            logger.warning("ReportLab not available, creating text file instead")
            success = create_simple_text_pdf(text_content, ticker, pdf_path)
        
        if success:
            logger.info(f"\n{'='*80}")
            logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info(f"{'='*80}")
            logger.info(f"Report saved to: {pdf_path}")
            logger.info(f"File size: {os.path.getsize(pdf_path) / 1024:.2f} KB")
            return pdf_path
        else:
            logger.error("Failed to create PDF/text file")
            return None
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Generate full stock analysis PDF report from real data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_full_article_pdf.py AAPL
  python generate_full_article_pdf.py MSFT --output-dir c:/reports
  python generate_full_article_pdf.py TSLA --output-dir ./my_reports

Supported Tickers:
  - Any valid stock ticker from US markets (AAPL, MSFT, GOOGL, TSLA, etc.)
  - Requires sufficient historical data for analysis
        """
    )
    
    parser.add_argument(
        'ticker',
        type=str,
        help='Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory to save PDF report (default: generated_data/pdf_reports)'
    )
    
    args = parser.parse_args()
    
    # Validate ticker
    ticker = args.ticker.upper().strip()
    if not ticker or len(ticker) > 5:
        print(f"ERROR: Invalid ticker symbol: {args.ticker}")
        print("Please provide a valid stock ticker (1-5 characters)")
        sys.exit(1)
    
    # Check dependencies
    if not REPORTLAB_AVAILABLE:
        print("\n⚠ WARNING: ReportLab not installed!")
        print("PDF generation will fall back to text file (.txt) format.")
        print("To install ReportLab: pip install reportlab\n")
    
    print(f"\n{'='*80}")
    print(f"Full Pipeline PDF Generator")
    print(f"{'='*80}")
    print(f"Ticker: {ticker}")
    print(f"Output Directory: {args.output_dir or 'generated_data/pdf_reports (default)'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Run pipeline
    result_path = run_full_pipeline_to_pdf(ticker, args.output_dir)
    
    if result_path:
        print(f"\n{'='*80}")
        print("✓ SUCCESS!")
        print(f"{'='*80}")
        print(f"Report generated: {result_path}")
        print(f"\nYou can now:")
        print(f"  1. Open the report: {result_path}")
        print(f"  2. Review the analysis")
        print(f"  3. Share with stakeholders")
        sys.exit(0)
    else:
        print(f"\n{'='*80}")
        print("✗ FAILED")
        print(f"{'='*80}")
        print("Pipeline execution failed. Check the log file for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
