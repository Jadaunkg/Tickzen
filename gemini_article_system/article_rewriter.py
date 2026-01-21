"""
Gemini Article Rewriter
A production-ready system for rewriting stock analysis reports into SEO-optimized, 
human-like articles using Google Gemini 2.5 Flash model.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Load environment variables
load_dotenv()


class GeminiArticleRewriter:
    """
    Rewrite HTML stock reports into engaging, SEO-optimized articles.
    Focuses on human-like writing with proper structure and schema.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini Article Rewriter.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Model fallback hierarchy (in order of preference)
        self.model_hierarchy = [
            'gemini-2.5-flash',           # Primary model (fast, high quality)
            'gemini-3-flash-preview',     # Fallback 1 (latest preview, 20 RPD available)
            'gemini-2.5-flash-lite',      # Fallback 2 (lighter version, 20 RPD available)
            'gemini-2.0-flash-lite'       # Fallback 3 (stable lite version)
        ]
        self.current_model_index = 0
        self.current_model_name = self.model_hierarchy[0]
        self.model = genai.GenerativeModel(self.current_model_name)
        
        # Request counter for quota tracking
        self.api_requests_made = 0
        self.daily_limit_warning = 15  # Warn at 75% of 20 request limit
        self.quota_exceeded_count = {}  # Track quota exceeded per model
        
        # Generation configuration for quality output
        self.generation_config = {
            'temperature': 0.8,  # Higher temperature for more human-like variation
            'top_p': 0.95,
            'top_k': 50,
            'max_output_tokens': 32768,  # Increased to handle complete long reports
            'candidate_count': 1,
        }
    
    @property
    def available(self) -> bool:
        """Check if the generator is available (has valid API key and model)"""
        return self.model is not None
    
    def _switch_to_fallback_model(self) -> bool:
        """
        Switch to the next available fallback model
        
        Returns:
            bool: True if successfully switched to fallback, False if no fallbacks available
        """
        self.current_model_index += 1
        
        if self.current_model_index >= len(self.model_hierarchy):
            print("❌ All fallback models exhausted!")
            return False
        
        self.current_model_name = self.model_hierarchy[self.current_model_index]
        self.model = genai.GenerativeModel(self.current_model_name)
        
        print(f"🔄 Switching to fallback model: {self.current_model_name}")
        print(f"   📊 Remaining fallbacks: {len(self.model_hierarchy) - self.current_model_index - 1}")
        
        return True
    
    def rewrite_report(
        self,
        html_report: str,
        ticker: str,
        company_name: str,
        max_input_length: int = 80000,
        variation_number: int = 0
    ) -> Tuple[str, Dict]:
        """
        Rewrite HTML stock analysis report into SEO-optimized article.
        
        Args:
            html_report: HTML content of the stock report
            ticker: Stock ticker symbol (e.g., 'AAPL')
            company_name: Full company name (e.g., 'Apple Inc.')
            max_input_length: Maximum characters to send to Gemini
            variation_number: Article variation number (0=first, 1=second variation, etc.)
            
        Returns:
            Tuple of (article_html, metadata_dict)
        """
        print(f"\n{'='*60}")
        print(f"GEMINI ARTICLE REWRITER - {ticker}")
        print(f"{'='*60}\n")
        
        # Extract text content from HTML
        print("Step 1: Extracting content from HTML report...")
        report_text = self._extract_text_from_html(html_report)
        print(f"   ✓ Extracted {len(report_text):,} characters")
        
        # Optimize input length - only truncate if absolutely necessary
        if len(report_text) > max_input_length:
            print(f"   ⚠ Report is large ({len(report_text):,} chars), processing in full context mode")
            # Don't truncate - send the full report for complete rewriting
            # Gemini 2.5 Flash can handle up to ~1M tokens input
        
        # Generate the rewritten article
        print("\nStep 2: Generating SEO-optimized article with Gemini AI...")
        if variation_number > 0:
            print(f"   ⚙ VARIATION MODE: Generating different perspective (variation #{variation_number + 1})")
        prompt = self._build_rewrite_prompt(ticker, company_name, report_text, variation_number)
        
        try:
            # Adjust temperature for variations to get different perspectives
            config = self.generation_config.copy() if hasattr(self.generation_config, 'copy') else genai.GenerationConfig(
                temperature=self.generation_config.get('temperature', 0.8),
                top_p=self.generation_config.get('top_p', 0.95),
                top_k=self.generation_config.get('top_k', 50),
                max_output_tokens=self.generation_config.get('max_output_tokens', 32768)
            )
            
            # Increase temperature for variations to get more diverse content
            if variation_number > 0:
                # Base: 0.7, Variation 1: 0.85, Variation 2: 1.0, etc.
                new_temp = min(1.0, 0.7 + (variation_number * 0.15))
                if hasattr(config, 'temperature'):
                    config.temperature = new_temp
                else:
                    config['temperature'] = new_temp
                print(f"   ⚙ Temperature set to {new_temp} for variation")
            
            # Check quota warning before making request
            self.api_requests_made += 1
            if self.api_requests_made >= self.daily_limit_warning:
                print(f"⚠️  QUOTA WARNING: {self.api_requests_made} API requests made this session. Free tier limit is 20/day!")
            
            print(f"🔄 Sending to Gemini for article rewriting...")
            print(f"   🤖 Model: {self.current_model_name}, Request #{self.api_requests_made} this session)")
            
            # Try generation with automatic fallback on quota error
            max_retries = len(self.model_hierarchy)
            response = None
            for attempt in range(max_retries):
                try:
                    # Generate article using Gemini
                    response = self.model.generate_content(
                        prompt,
                        generation_config=config
                    )
                    
                    if not response or not response.text:
                        print("❌ Gemini returned empty response")
                        raise RuntimeError("Empty response from Gemini")
                    
                    # Success! Log which model was used
                    if attempt > 0:
                        print(f"✅ Successfully generated using fallback model: {self.current_model_name}")
                    
                    article_html = response.text
                    print(f"   ✓ Generated article: ~{len(article_html.split()):,} words")
                    break  # Exit retry loop on success
                    
                except Exception as e:
                    error_str = str(e)
                    
                    # Check if it's a quota error (429)
                    if '429' in error_str and 'quota' in error_str.lower():
                        # Track quota exceeded for this model
                        if self.current_model_name not in self.quota_exceeded_count:
                            self.quota_exceeded_count[self.current_model_name] = 0
                        self.quota_exceeded_count[self.current_model_name] += 1
                        
                        print(f"❌ Quota exceeded for {self.current_model_name} (attempt {attempt + 1}/{max_retries})")
                        
                        # Try to switch to fallback model
                        if attempt < max_retries - 1:
                            if self._switch_to_fallback_model():
                                print(f"♻️  Retrying with {self.current_model_name}...")
                                continue
                            else:
                                # No more fallbacks available
                                print(f"❌ All fallback models exhausted for {ticker}")
                                raise
                        else:
                            # Last attempt failed
                            print(f"❌ Final attempt failed for {ticker}")
                            raise
                    else:
                        # Non-quota error, don't retry
                        print(f"   ✗ Error generating article: {e}")
                        raise
            
            # Should never reach here, but just in case
            if not article_html:
                raise RuntimeError("Failed to generate article after all retries")
            
        except Exception as e:
            print(f"   ✗ Error generating article: {e}")
            raise
        
        # Post-process the article
        print("\nStep 3: Post-processing article...")
        article_html = self._post_process_article(article_html, ticker, company_name)
        
        # Extract metadata
        print("Step 4: Extracting metadata...")
        metadata = self._extract_metadata(article_html, ticker, company_name)
        
        print(f"\n{'='*60}")
        print(f"✓ Article generation complete!")
        print(f"   - Word count: {metadata.get('word_count', 0):,}")
        print(f"   - Sections: {metadata.get('section_count', 0)}")
        print(f"{'='*60}\n")
        
        return article_html, metadata
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML report while preserving links."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'meta', 'link']):
            element.decompose()
            
        # Transform links to text representation [Text](URL) so Gemini sees them
        for a in soup.find_all('a', href=True):
            if a.get_text().strip():
                a.replace_with(f"[{a.get_text().strip()}]({a['href']})")
        
        # Get text with some structure preserved
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _build_rewrite_prompt(self, ticker: str, company_name: str, report_text: str, variation_number: int = 0) -> str:
        """
        Build comprehensive prompt for article rewriting.
        Focuses on preserving exact report structure while improving readability.
        
        Args:
            variation_number: If > 0, add instructions to generate a different perspective
        """
        # Add variation instructions at the start if this is a variation
        variation_instructions = ""
        if variation_number > 0:
            variation_instructions = f"""
⚠️ VARIATION MODE (CRITICAL - READ FIRST):
   - This is VARIATION #{variation_number + 1} of this article
   - You MUST generate a DIFFERENT VERSION than previous attempts
   - Use DIFFERENT wording, DIFFERENT explanations, DIFFERENT perspectives
   - However, the 23-section structure MUST remain exactly the same
   - Focus on different aspects of the data (e.g., if variation 1 focused on risks, focus on opportunities)
   - Use synonyms and rephrase sentences completely
   - Change sentence structures and paragraph flow
   - Present the same data from a fresh angle
   - This ensures unique content when same ticker publishes to same site multiple times
   - CRITICAL: Structure stays identical, but presentation and language must differ significantly

"""
        
        prompt = f"""You are an expert financial journalist. Your task is to REWRITE the following stock analysis report into an SEO-optimized article while PRESERVING THE EXACT STRUCTURE AND SECTIONS from the original report.

{variation_instructions}CRITICAL INSTRUCTIONS:

⚠️ DATA FRESHNESS REQUIREMENT (CRITICAL - MUST FOLLOW):
   - You MUST use ONLY the latest information from the last 2-3 days
   - ALL external data, news, events, and market information MUST be current and recent
   - This is financial content - NO OUTDATED DATA ALLOWED
   - Only cite trusted sources: SEC filings, official company announcements, major financial news (Bloomberg, Reuters, WSJ, CNBC, Yahoo Finance, MarketWatch)
   - If you reference any external information beyond the provided report, it MUST be from the last 2-3 days only
   - NEVER use old data, historical news from weeks/months ago, or outdated analysis
   - For stock analysis and earnings reports, focus on CURRENT market conditions and RECENT company developments

⚠️ COMPLETENESS REQUIREMENT: This is a LONG REPORT. You MUST process and rewrite the ENTIRE report from start to finish. DO NOT stop mid-way. DO NOT truncate. The output must include EVERY section from the original report.

1. STRUCTURE PRESERVATION:
   - Keep the EXACT SAME sections as in the original report
   - Maintain the SAME ORDER of sections
   - Use the SAME section headings (but enhance them for SEO)
   - DO NOT reorganize or create new sections
   - DO NOT skip any sections that have data
   - Process the COMPLETE report - all sections from beginning to end

2. HTML FORMATTING (CRITICAL):
   - Use ONLY proper HTML tags for formatting
   - For bold text: Use <strong>text</strong> NOT **text**
   - For emphasis: Use <em>text</em> NOT *text*
   - STRICT HEADING HIERARCHY (CRITICAL):
     * <h2> for ALL main sections (e.g., "Stock Analysis", "Technical Indicators", "Investment Outlook")
     * <h3> for subsections under h2 (e.g., "Price Trends" under "Technical Indicators")
     * <h4> for sub-subsections under h3 (e.g., "Monthly Patterns" under "Price Trends")
     * NEVER skip levels: h2 → h3 → h4 (never h2 → h4)
     * NEVER use h3 as main section headings - always start with h2
   - For lists: Use <ul><li> or <ol><li> ONLY for non-tabular data
   - For tables: Use proper <table><thead><tbody><tr><th><td> tags with proper structure
   - PREFER TABLES over bullet points when presenting:
     * Financial metrics (Price, P/E, EPS, Revenue, etc.)
     * Comparison data (vs competitors, vs benchmarks)
     * Time-series data (historical prices, forecast values)
     * Multiple related data points (ratios, percentages, values)
   - NEVER use Markdown syntax (**, *, _, etc.)
   - Add CSS classes for tables: <table class="financial-data-table">
   - Use proper table headers: <th> for column/row headers

   EXTERNAL LINKS REQUIREMENT:
   ✅ Include 3-4 high-quality external links throughout the article
   ✅ IMPORTANT: PRESERVE RECENT NEWS LINKS
      - If the original report contains specific news items with links (formatted like [News Title](URL)), YOU MUST INCLUDE THEM.
      - Link to the original news source when discussing specific recent events.
      - This increases credibility significantly.
   ✅ Link to reputable financial sources:
      - SEC Edgar filings: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}
      - Yahoo Finance: https://finance.yahoo.com/quote/{ticker}
      - MarketWatch: https://www.marketwatch.com/investing/stock/{ticker.lower()}
      - Company Investor Relations page (if available)
   ✅ Place links naturally in context where relevant (spread throughout article)
   ✅ Use descriptive anchor text, not "click here" or bare URLs
   ✅ Format: <a href="URL" target="_blank" rel="noopener">descriptive text</a>
   ❌ Don't cluster all links in one section
   ❌ Don't use affiliate or promotional links

3. WRITING STYLE & VOICE (CRITICAL FOR UNIQUENESS):
   - Write as a human financial analyst sharing insights, NOT as AI or a robot
   - Use NATURAL, conversational language like you're explaining to a friend
   - ESPECIALLY in the introduction - make it engaging but professional
   
   ⚠️ FORBIDDEN OPENING PHRASES (STRICT):
   - DO NOT start with "Let's talk about...", "Let's dive into...", "Today we are looking at...", "In this article...", "Welcome to...".
   - Start DIRECTLY with the company name or the main news.
   - Example CORRECT: "{{Company Name}} ({{Ticker}}) recently reported earnings..." or "{{Company Name}} shares are trading at..."
   - Example WRONG: "Let's talk about {{Company Name}}..."
   
   ⚠️ AVOID PATTERNS & REPETITION (STRICT):
   - STOP using repetitive phrases like "This suggests", "This indicates", "This highlights", "It is important to note", "Investors should monitor".
   - DO NOT repeat the same sentence structure across sections.
   - VARY your transitions. Use "Meanwhile," "Conversely," "On the flip side," "Looking closer at," etc.
   
   PARAGRAPH RULES (VERY IMPORTANT):
   - Maximum 4-5 sentences per paragraph
   - If a paragraph exceeds 5 sentences, BREAK IT INTO MULTIPLE PARAGRAPHS
   - Each paragraph = ONE key idea or concept
   - Add blank line between paragraphs for readability
   - Long explanations = multiple short paragraphs, not one long paragraph
   
   SENTENCE VARIETY:
   - Vary sentence structure - mix short punchy sentences with flowing longer ones
   - Use different words and phrases to express similar concepts - avoid repetition
   - Add natural transitions: "However", "Meanwhile", "What's interesting is", "Here's the thing", etc.
   
   AVOID:
   - Robotic phrases like "based on the data", "according to reports", "it is important to note"
   - Corporate jargon and stiff language
   - Long walls of text
   
   ENGAGE THE READER:
   - Use rhetorical questions, insights, observations
   - Start introduction with a hook - something compelling
   - Use contractions occasionally (it's, here's, that's)
   - Address the reader directly ("you might wonder", "if you're looking at")

4. DATA HANDLING (CRITICAL - READ CAREFULLY):
   
   ⚠️ NO DATA RESTATEMENT RULE (CRITICAL):
   - If you present data in a table, DO NOT repeat the exact same numbers in the paragraph immediately following it.
   - TEXT IS FOR INSIGHTS, TABLES ARE FOR DATA.
   - Instead of writing "Revenue was $10B", write "Revenue exceeded expectations..." or "Revenue growth slowed compared to..."
   - Provide ANALYSIS and CONTEXT for the numbers in the table, not just a verbal list of them.
   
   ⚠️ EXACT DATA PRESERVATION:
   - Preserve ALL numerical values EXACTLY as shown in the original report
   - DO NOT change, round, or modify any numbers, percentages, or values
   - Copy dates, prices, percentages, ratios EXACTLY character-by-character
   - If original shows "$123.45", write "$123.45" (not "$123" or "approximately $123")
   - If original shows "5.67%", write "5.67%" (not "5.7%" or "around 6%")
   
   ⚠️ HANDLING MISSING/INVALID DATA:
   - If a metric shows "N/A", "nan", "null", "0.0", or "None" - COMPLETELY SKIP that metric
   - DO NOT write about metrics with missing or zero values
   - DO NOT mention that data is "unavailable", "not available", or "missing"
   - DO NOT explain why data is absent
   - DO NOT create placeholder text for missing metrics
   - Simply exclude that entire metric/row from tables and skip it in narrative
   
   ⚠️ ZERO VALUES:
   - If a value is genuinely 0 (like "0% change") - include it if it's meaningful
   - If a value is 0 because data is missing - SKIP it entirely
   - When in doubt about whether 0 is real or missing data - SKIP it
   
   EXAMPLES:
   ✅ CORRECT: If P/E ratio is "N/A", don't include P/E ratio in the table or text at all
   ❌ WRONG: "The P/E ratio is currently unavailable" or "P/E: N/A"
   
   ✅ CORRECT: If Revenue is "$0" or "0.0", skip revenue entirely
   ❌ WRONG: "Revenue data is not currently available"
   
   ✅ CORRECT: Only write about metrics that have real, valid numbers
   ❌ WRONG: Including rows with N/A, 0, null, or explaining missing data

5. SEO OPTIMIZATION:
   - Enhance headings to be descriptive and keyword-rich
   - Include the stock ticker ({ticker}) and company name ({company_name}) naturally
   - Use relevant keywords: stock analysis, investment, financial performance, earnings report
   - MUST include 3-4 external links to reputable sources (CRITICAL):
     * https://finance.yahoo.com/quote/{ticker}
     * https://www.marketwatch.com/investing/stock/{ticker.lower()}
     * https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}
     * Company official investor relations page
   - Distribute links naturally throughout the article
   - Use descriptive anchor text for all links

6. CONTENT ELEMENTS & TABLE USAGE:
   
   WHEN TO USE TABLES (PREFERRED):
   - Financial metrics: Revenue, EPS, P/E ratio, Market Cap, etc.
   - Price data: Historical prices, forecasts, targets
   - Comparison data: This stock vs competitors or benchmarks
   - Technical indicators: RSI, MACD, Moving Averages with values
   - Ratios and percentages: Multiple related metrics
   - Time-series: Quarterly data, yearly performance
   
   TABLE STRUCTURE:
   ```html
   <table class="financial-data-table">
       <thead>
           <tr>
               <th>Metric</th>
               <th>Value</th>
               <th>Change</th>
           </tr>
       </thead>
       <tbody>
           <tr>
               <td>Current Price</td>
               <td>$XXX.XX</td>
               <td>+X.X%</td>
           </tr>
       </tbody>
   </table>
   ```
   
   WHEN TO USE BULLET POINTS:
   - Qualitative observations (not numbers)
   - Key takeaways or insights
   - Action items or recommendations
   - Brief explanatory points
   
   OTHER ELEMENTS:
   - Use <strong> tags (NOT **) for important metrics and values
   - Use <a href="url" target="_blank"> for external links
   - Break long paragraphs into shorter ones (4-5 sentences max)
   - IMPORTANT: DO NOT START EVERY BULLET POINT WITH "This suggests..." or "This indicates..."

7. COMPLETENESS (CRITICAL - READ THIS):
   - ⚠️ YOU MUST PROCESS THE ENTIRE REPORT - DO NOT STOP EARLY
   - REWRITE EVERY SINGLE SECTION from the original report
   - ENSURE THE ARTICLE IS COMPLETE - don't cut off mid-sentence or mid-table
   - All tables must be properly closed with </table>
   - All sections must have proper conclusions
   - NO WORD LIMIT - Write as much as needed to cover the full report (typically 3000-5000+ words)
   - Count the sections in the original report and ensure your output has the SAME number
   - End with a strong concluding paragraph
   - The article should be as comprehensive as the original report
   - ⚠️ ABSOLUTELY NO FAQ SECTIONS: Do NOT include a "Frequently Asked Questions" section. It repeats info and duplicates content. This is forbidden.

8. SECTION MAPPING & SPECIAL INSTRUCTIONS:
   Look at the original report sections and map them directly:
   
   A. COMPANY OVERVIEW (High Risk for Duplication):
   - DO NOT write a generic "About Us" profile like Yahoo Finance or Reuters.
   - Focus on: What is the company's *current* strategic focus? What are the *recent* major developments?
   - Avoid listing every single product/subsidiary unless critical to current news.
   - Make it unique to THIS specific moment in the company's history.
   
   B. METHODOLOGY DISCLOSURE (REQUIRED ADDITION):
   - Add a brief section at the end titled "Analysis Methodology".
   - State that this analysis utilizes:
     * Real-time market data
     * Standard technical indicators (RSI, MACD, etc.)
     * Recent SEC filings and earnings reports
     * AI-driven sentiment analysis of recent news
   - This improves trust and E-E-A-T.

   C. FORECAST SECTIONS:
   - VARY your language. Do not use the exact same disclaimer in every article.
   - Contextualize the confidence of the forecast based on volatility.

   Standard Mapping:
   - If report has "Introduction" → Keep as <h2>Introduction</h2>
   - If report has "15-Year Price History" → Keep as <h2>15-Year Price History & Charts</h2>
   - If report has "Technical Indicators" → Keep as <h2>Technical Indicators (RSI, MACD, Histogram)</h2>
   - If report has "Fundamental Analysis" → Keep as <h2>Fundamental Analysis & Ratios</h2>
   - If report has "Forecast" → Keep as <h2>Forecast Table & Price Targets</h2>
   - Continue this pattern for ALL sections in the original report

ORIGINAL REPORT TO REWRITE:
{report_text}

9. LANGUAGE & VOCABULARY:
   - Use SIMPLE, clear vocabulary that everyday investors can understand
   - Avoid overly technical jargon unless necessary
   - When technical terms are needed, briefly explain them
   - Write at a 10th-grade reading level
   - Use short, clear sentences

OUTPUT FORMAT REQUIREMENTS:
- Start directly with the first content paragraph or section (NO article header div with title/metadata)
- Begin with the main content - the article title will be added separately by WordPress
- Use proper HTML tags ONLY (no Markdown)
- DO NOT include <h1> tags - WordPress will generate the title
- STRICT HEADING HIERARCHY:
  * Start with <h2> for the first main section heading
  * Use <h3> for subsections under <h2>
  * Use <h4> for sub-subsections under <h3>
  * NEVER skip levels (e.g., h2 → h4)
- Preserve exact report structure and section order
- Use <strong> for bold, NEVER use **
- Use proper <table> tags for all tabular data
- Include 3-4 external links with <a href> tags (CRITICAL)
- DO NOT include an FAQ (Frequently Asked Questions) section
- DO NOT include any disclaimer section about investment advice

⚠️ FINAL CRITICAL REMINDERS:
1. Use ONLY current information from the last 2-3 days for any external data
2. Only cite trusted financial sources (Bloomberg, Reuters, WSJ, SEC, Yahoo Finance, MarketWatch)
3. Include 3-4 external links to reputable sources naturally throughout the article
4. Follow strict heading hierarchy: h2 (main sections) → h3 (subsections) → h4 (sub-subsections)
5. Copy ALL numbers EXACTLY - do not round, estimate, or modify
6. SKIP any metrics with N/A, 0, null, or nan - don't mention them at all
7. NEVER write about missing or unavailable data
8. Include ONLY metrics that have real, valid numerical values
9. Process the ENTIRE report - don't stop early
10. Use <strong> for bold, NEVER **


Now rewrite the COMPLETE report with proper HTML formatting:
"""
        return prompt
    
    def _break_long_paragraphs(self, html: str) -> str:
        """Break long paragraphs into shorter, more readable ones (max 4-5 sentences)."""
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all paragraph tags
        paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            text = p.get_text().strip()
            
            # Skip empty or short paragraphs
            if not text or len(text) < 200:
                continue
            
            # Split by sentences (look for period followed by space and capital letter)
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
            
            # If more than 5 sentences, break into multiple paragraphs
            if len(sentences) > 5:
                # Create new paragraphs (4 sentences each)
                new_paragraphs = []
                chunk_size = 4
                
                for i in range(0, len(sentences), chunk_size):
                    chunk = sentences[i:i+chunk_size]
                    new_p = soup.new_tag('p')
                    new_p.string = ' '.join(chunk)
                    new_paragraphs.append(new_p)
                
                # Replace original paragraph with new ones
                if new_paragraphs:
                    for new_p in reversed(new_paragraphs):
                        p.insert_after(new_p)
                    p.decompose()
        
        return str(soup)
    
    def _post_process_article(self, article_html: str, ticker: str, company_name: str) -> str:
        """Clean up and enhance the generated article."""
        
        # Remove any Markdown syntax that might have slipped through
        # Replace **text** with <strong>text</strong>
        import re
        from bs4 import BeautifulSoup
        
        # Replace **text** with <strong>text</strong>
        article_html = re.sub(r'\*\*([^\*]+?)\*\*', r'<strong>\1</strong>', article_html)
        
        # Replace *text* with <em>text</em>
        article_html = re.sub(r'(?<!\*)\*([^\*]+?)\*(?!\*)', r'<em>\1</em>', article_html)
        
        # Remove any remaining markdown code blocks
        article_html = article_html.replace('```html', '').replace('```', '')
        
        # Parse HTML to remove problematic content
        soup = BeautifulSoup(article_html, 'html.parser')
        
        # Remove table rows that contain N/A, nan, null, or 0 values
        for table in soup.find_all('table'):
            rows_to_remove = []
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                row_text = ' '.join([cell.get_text().strip() for cell in cells]).lower()
                
                # Check if row contains invalid/missing data indicators
                if any(indicator in row_text for indicator in ['n/a', 'nan', 'null', 'none', ': 0', ': 0.0', ': $0', '$0.00']):
                    # Don't remove header rows
                    if not row.find('th'):
                        rows_to_remove.append(row)
            
            # Remove problematic rows
            for row in rows_to_remove:
                row.decompose()
        
        # Remove paragraphs that explicitly mention unavailable/missing data
        for p in soup.find_all('p'):
            p_text = p.get_text().lower()
            if any(phrase in p_text for phrase in [
                'not available', 'unavailable', 'no data', 'data is missing',
                'information is not', 'currently unavailable', 'data not available',
                'n/a', 'is n/a', 'shows n/a', 'not applicable'
            ]):
                p.decompose()
        
        # Remove list items mentioning missing data
        for li in soup.find_all('li'):
            li_text = li.get_text().lower()
            if any(phrase in li_text for phrase in [
                'not available', 'unavailable', 'no data', 'n/a', 'is n/a'
            ]):
                li.decompose()
        
        # Remove any FAQ sections (we don't want them in the blog)
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().lower()
            if 'faq' in heading_text or 'frequently asked' in heading_text:
                # Remove the heading and all content until the next h2
                current = heading
                while current:
                    next_sibling = current.find_next_sibling()
                    current.decompose()
                    if next_sibling and next_sibling.name == 'h2':
                        break
                    current = next_sibling
        
        # Convert back to string
        article_html = str(soup)
        
        # Remove the disclaimer section if present (multiple patterns for thorough removal)
        disclaimer_patterns = [
            r'<h[23][^>]*>\s*IMPORTANT\s+DISCLAIMER:?\s*</h[23]>.*?(?=<h[23]|</body>|</div>\s*</body>|$)',
            r'<h[23][^>]*>\s*Disclaimer:?\s*</h[23]>.*?(?=<h[23]|</body>|</div>\s*</body>|$)',
            r'<h[23][^>]*>\s*Important\s+Disclaimer:?\s*</h[23]>.*?(?=<h[23]|</body>|</div>\s*</body>|$)',
            r'<div[^>]*disclaimer[^>]*>.*?</div>',
            r'IMPORTANT DISCLAIMER:.*?(?=<h[23]|</body>|$)',
            r'This\s+report\s+has\s+been\s+automatically\s+generated.*?at\s+your\s+own\s+risk\.?',
        ]
        
        for pattern in disclaimer_patterns:
            article_html = re.sub(pattern, '', article_html, flags=re.IGNORECASE | re.DOTALL)
        
        # Additional cleanup for any remaining disclaimer-like content
        lines = article_html.split('\n')
        filtered_lines = []
        skip_mode = False
        
        for line in lines:
            # Check if line starts disclaimer section
            if re.search(r'<h[23][^>]*>\s*(important\s+)?disclaimer', line, re.IGNORECASE):
                skip_mode = True
                continue
            # Check if we're back to a normal section
            if skip_mode and re.search(r'<h[23]', line):
                skip_mode = False
            # Only add line if not in skip mode
            if not skip_mode:
                filtered_lines.append(line)
        
        article_html = '\n'.join(filtered_lines)
        
        # Remove any AI-like and robotic phrases
        ai_phrases = [
            "based on the data provided",
            "according to the report",
            "as an AI",
            "I cannot",
            "I don't have access",
            "the data shows",
            "it appears that",
            "the report indicates",
            "it is important to note",
            "it should be noted",
            "it is worth mentioning",
            "it is worth noting",
            "one should consider",
            "investors should be aware",
            "it can be observed",
            "analysis reveals",
            "examination of the data",
            "upon closer inspection",
        ]
        
        for phrase in ai_phrases:
            # Case-insensitive replacement
            article_html = re.sub(re.escape(phrase), '', article_html, flags=re.IGNORECASE)
        
        # Remove any FAQ sections (we don't want them in stock analysis blogs)
        soup = BeautifulSoup(article_html, 'html.parser')
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text().lower()
            if 'faq' in heading_text or 'frequently asked' in heading_text:
                # Remove the heading and all content until the next h2
                current = heading
                elements_to_remove = [current]
                while current:
                    next_sibling = current.find_next_sibling()
                    if next_sibling and next_sibling.name == 'h2':
                        break
                    if next_sibling:
                        elements_to_remove.append(next_sibling)
                    current = next_sibling
                
                # Remove all collected elements
                for element in elements_to_remove:
                    element.decompose()
        
        article_html = str(soup)
        
        # Break long paragraphs into shorter ones
        article_html = self._break_long_paragraphs(article_html)
        
        # Clean up excessive whitespace
        article_html = re.sub(r'\n\s*\n\s*\n', '\n\n', article_html)
        
        # Ensure proper HTML structure
        if not article_html.startswith('<'):
            article_html = f'<div class="article-content">\n{article_html}\n</div>'
        
        # Add article metadata at the top
        current_date = datetime.now().strftime("%Y-%m-%d")
        metadata_html = f"""
<div class="article-header">
    <h1>{company_name} ({ticker}) Stock Analysis</h1>
    <div class="article-meta">
        <span class="publish-date">Published: {current_date}</span>
        <span class="ticker-tag">#{ticker}</span>
    </div>
</div>
"""
        
        article_html = metadata_html + article_html
        
        return article_html
    
    def _generate_faq_schema(self, article_html: str, ticker: str, company_name: str) -> str:
        """
        Generate FAQ schema markup by extracting questions from the article.
        """
        import json
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(article_html, 'html.parser')
        
        # Try to find FAQ section
        faq_section = None
        for h2 in soup.find_all(['h2', 'h3']):
            if 'faq' in h2.get_text().lower() or 'frequently asked' in h2.get_text().lower():
                faq_section = h2
                break
        
        if not faq_section:
            return ""
        
        # Extract questions and answers
        questions = []
        current_element = faq_section.find_next_sibling()
        
        while current_element and current_element.name not in ['h2']:
            if current_element.name in ['h3', 'h4', 'p', 'strong', 'b']:
                text = current_element.get_text().strip()
                # Check if it's a question
                if '?' in text or text.lower().startswith(('what', 'how', 'when', 'why', 'is', 'does', 'can', 'should')):
                    question_text = text
                    # Get answer (next elements until next question or section)
                    answer_parts = []
                    answer_elem = current_element.find_next_sibling()
                    while answer_elem and answer_elem.name not in ['h2', 'h3', 'h4']:
                        if answer_elem.name in ['p', 'ul', 'ol', 'div']:
                            answer_parts.append(answer_elem.get_text().strip())
                        answer_elem = answer_elem.find_next_sibling()
                        if len(answer_parts) >= 3:  # Limit answer length
                            break
                    
                    if answer_parts:
                        questions.append({
                            "question": question_text,
                            "answer": ' '.join(answer_parts[:2])  # Use first 2 paragraphs
                        })
                    
                    if len(questions) >= 7:  # Max 7 questions
                        break
            
            current_element = current_element.find_next_sibling()
        
        # Generate schema if we found questions
        if not questions:
            # Fallback: Generate generic questions
            questions = [
                {
                    "question": f"Is {ticker} a good buy right now?",
                    "answer": f"The analysis of {company_name} ({ticker}) considers multiple factors including technical indicators, fundamental metrics, and market conditions. Review the complete analysis above for detailed insights."
                },
                {
                    "question": f"What is {company_name}'s price target?",
                    "answer": f"Price targets for {ticker} are based on technical analysis, historical trends, and forecast models. Check the forecast section for specific price projections."
                },
                {
                    "question": f"What are the main risks for {ticker}?",
                    "answer": f"Key risks include market volatility, industry competition, economic conditions, and company-specific factors. Review the risk analysis section for comprehensive details."
                },
            ]
        
        # Build schema
        schema_entities = []
        for q in questions[:7]:  # Max 7 questions
            schema_entities.append({
                "@type": "Question",
                "name": q["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": q["answer"]
                }
            })
        
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": schema_entities
        }
        
        schema_html = f"""
<script type="application/ld+json">
{json.dumps(schema, indent=2, ensure_ascii=False)}
</script>
"""
        
        return schema_html
    
    def _extract_metadata(self, article_html: str, ticker: str, company_name: str) -> Dict:
        """Extract metadata from the generated article."""
        soup = BeautifulSoup(article_html, 'html.parser')
        
        # Count words
        text = soup.get_text()
        word_count = len(text.split())
        
        # Count sections
        h2_tags = soup.find_all('h2')
        section_count = len(h2_tags)
        
        # Check for schema (general, not FAQ-specific)
        has_schema = bool(soup.find('script', type='application/ld+json'))
        
        # Extract section titles
        sections = [h2.get_text(strip=True) for h2 in h2_tags]
        
        metadata = {
            'ticker': ticker,
            'company_name': company_name,
            'word_count': word_count,
            'section_count': section_count,
            'sections': sections,
            'has_schema': has_schema,
            'generated_date': datetime.now().isoformat(),
            'model': 'gemini-2.5-flash',
        }
        
        return metadata
    
    def save_article(
        self,
        article_html: str,
        metadata: Dict,
        output_dir: str = "generated_articles"
    ) -> str:
        """
        Save the generated article and its metadata.
        
        Args:
            article_html: The generated article HTML
            metadata: Article metadata dictionary
            output_dir: Directory to save articles
            
        Returns:
            Path to the saved article file
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        ticker = metadata['ticker']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_article_{timestamp}.html"
        filepath = output_path / filename
        
        # Create complete HTML document
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Comprehensive stock analysis for {metadata['company_name']} ({ticker}) including financial performance, technical analysis, and investment outlook.">
    <meta name="keywords" content="{ticker}, {metadata['company_name']}, stock analysis, investment, financial analysis">
    <title>{metadata['company_name']} ({ticker}) Stock Analysis - Complete Guide</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .article-header {{
            border-bottom: 3px solid #0066cc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .article-header h1 {{
            margin: 0 0 10px 0;
            color: #1a1a1a;
        }}
        .article-meta {{
            color: #666;
            font-size: 14px;
        }}
        .ticker-tag {{
            background: #0066cc;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            margin-left: 15px;
        }}
        h2 {{
            color: #0066cc;
            margin-top: 40px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #333;
            margin-top: 30px;
        }}
        h4 {{
            color: #555;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background: #0066cc;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        ul {{
            padding-left: 25px;
        }}
        li {{
            margin: 8px 0;
        }}
        strong {{
            color: #0066cc;
        }}
        .faq-item {{
            margin: 25px 0;
            padding: 15px;
            background: #f9f9f9;
            border-left: 4px solid #0066cc;
        }}
        .faq-question {{
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 10px;
        }}
        .metadata {{
            margin-top: 50px;
            padding: 20px;
            background: #f0f0f0;
            border-radius: 8px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    {article_html}
    
</body>
</html>
"""
        
        # Save HTML file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_document)
        
        # Save metadata as JSON
        metadata_file = output_path / f"{ticker}_metadata_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"   ✓ Article saved: {filepath}")
        print(f"   ✓ Metadata saved: {metadata_file}")
        
        return str(filepath)


def rewrite_stock_report(
    html_report_path: str,
    ticker: str,
    company_name: str,
    output_dir: str = "generated_articles"
) -> Tuple[str, Dict]:
    """
    Convenience function to rewrite a stock report from file.
    
    Args:
        html_report_path: Path to HTML report file
        ticker: Stock ticker symbol
        company_name: Full company name
        output_dir: Directory to save generated articles
        
    Returns:
        Tuple of (article_filepath, metadata_dict)
    """
    # Read HTML report
    with open(html_report_path, 'r', encoding='utf-8') as f:
        html_report = f.read()
    
    # Initialize rewriter
    rewriter = GeminiArticleRewriter()
    
    # Generate article
    article_html, metadata = rewriter.rewrite_report(
        html_report=html_report,
        ticker=ticker,
        company_name=company_name
    )
    
    # Save article
    article_path = rewriter.save_article(
        article_html=article_html,
        metadata=metadata,
        output_dir=output_dir
    )
    
    return article_path, metadata


def generate_article_from_pipeline(
    ticker: str,
    company_name: Optional[str] = None,
    timeframe: str = '1mo',
    output_dir: str = "generated_articles",
    app_root: Optional[str] = None,
    variation_number: int = 0
) -> Tuple[str, Dict]:
    """
    Complete pipeline: Generate stock report → Rewrite with Gemini AI.
    
    This is the main production function that:
    1. Runs the full analysis pipeline (Prophet model, technical analysis, etc.)
    2. Generates comprehensive HTML report
    3. Rewrites report into SEO-optimized article using Gemini
    4. Saves the final article with metadata
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        company_name: Full company name (auto-fetched if not provided)
        timeframe: Analysis timeframe (default: '1mo')
        output_dir: Directory to save generated articles
        app_root: Application root directory (auto-detected if not provided)
        variation_number: Article variation number (0=first, 1=second variation, etc.)
                         Used to generate different versions when same ticker published multiple times
        
    Returns:
        Tuple of (article_filepath, metadata_dict)
        
    Example:
        >>> article_path, metadata = generate_article_from_pipeline('AAPL')
        >>> print(f"Article saved: {article_path}")
        >>> print(f"Word count: {metadata['word_count']}")
    """
    from automation_scripts.pipeline import run_pipeline
    import yfinance as yf
    
    print(f"\n{'='*70}")
    print(f"COMPLETE ARTICLE GENERATION PIPELINE - {ticker}")
    print(f"{'='*70}\n")
    
    # Determine app_root
    if app_root is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_root = os.path.join(current_dir, '..', 'app')
    
    # Get company name if not provided
    if company_name is None:
        print(f"Step 1: Fetching company information for {ticker}...")
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            company_name = info.get('longName') or info.get('shortName') or ticker
            print(f"   ✓ Company: {company_name}")
        except Exception as e:
            print(f"   ⚠ Could not fetch company name: {e}")
            company_name = ticker
    else:
        print(f"Step 1: Using provided company name: {company_name}")
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Run the analysis pipeline
    print(f"\nStep 2: Running complete stock analysis pipeline...")
    print(f"   - Ticker: {ticker}")
    print(f"   - Timeframe: {timeframe}")
    print(f"   - Timestamp: {timestamp}")
    
    try:
        # Run pipeline: returns (model, forecast, report_path, report_html)
        model, forecast, report_path, report_html = run_pipeline(
            ticker=ticker,
            ts=timestamp,
            app_root=app_root
        )
        
        print(f"   ✓ Pipeline complete!")
        print(f"   ✓ Report generated: {os.path.basename(report_path) if report_path else 'N/A'}")
        print(f"   ✓ HTML report size: {len(report_html):,} characters")
        
    except Exception as e:
        print(f"   ✗ Pipeline failed: {e}")
        raise
    
    # Validate report
    if not report_html or "Error Generating Report" in report_html:
        raise RuntimeError(f"Pipeline generated invalid report for {ticker}")
    
    # Rewrite report with Gemini AI
    print(f"\nStep 3: Rewriting report with Gemini AI...")
    if variation_number > 0:
        print(f"   ⚙ Generating VARIATION #{variation_number + 1} (different perspective/temperature)")
    rewriter = GeminiArticleRewriter()
    
    article_html, metadata = rewriter.rewrite_report(
        html_report=report_html,
        ticker=ticker,
        company_name=company_name,
        variation_number=variation_number
    )
    
    # Save the article
    print(f"\nStep 4: Saving article...")
    article_path = rewriter.save_article(
        article_html=article_html,
        metadata=metadata,
        output_dir=output_dir
    )
    
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE PIPELINE SUCCESS!")
    print(f"{'='*70}")
    print(f"Article: {article_path}")
    print(f"Word Count: {metadata.get('word_count', 0):,}")
    print(f"Sections: {metadata.get('section_count', 0)}")
    # Dropped 'has_faq' check since we removed FAQ generation
    print(f"Has Schema: {'Yes' if metadata.get('has_schema', False) else 'No'}")
    print(f"{'='*70}\n")
    
    return article_path, metadata


if __name__ == "__main__":
    """
    Example usage for testing the article rewriter.
    """
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python article_rewriter.py <html_report_path> <ticker> <company_name>")
        print("Example: python article_rewriter.py report.html AAPL 'Apple Inc.'")
        sys.exit(1)
    
    html_path = sys.argv[1]
    ticker = sys.argv[2]
    company = sys.argv[3]
    
    try:
        article_path, metadata = rewrite_stock_report(
            html_report_path=html_path,
            ticker=ticker,
            company_name=company
        )
        
        print(f"\n✅ Success! Article generated with {metadata['word_count']:,} words")
        print(f"📄 File: {article_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
