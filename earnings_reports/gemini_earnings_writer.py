"""
Gemini-Powered Earnings Report Article Generator

This script:
1. Generates a comprehensive earnings report
2. Passes it to Gemini to research and fill missing information
3. Generates a professional, SEO-optimized article
4. Formats it for WordPress automation with proper tags and links
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from dotenv import load_dotenv

from earnings_reports.data_collector import EarningsDataCollector
from earnings_reports.data_processor import EarningsDataProcessor
from earnings_reports.earnings_config import EarningsConfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GeminiEarningsWriter:
    """Generate professional earnings analysis articles using Gemini AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini Earnings Writer
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env variable)
        """
        # Use GOOGLE_API_KEY to match existing integration
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini using existing setup pattern
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generation configuration for quality output
        self.generation_config = {
            'temperature': 0.7,  # Balanced for analytical yet engaging content
            'top_p': 0.95,
            'top_k': 50,
            'max_output_tokens': 32768,  # Handle long comprehensive reports
            'candidate_count': 1,
        }
        
        # Initialize earnings components
        self.config = EarningsConfig()
        self.collector = EarningsDataCollector(self.config)
        self.processor = EarningsDataProcessor(self.config)
        
        logger.info("Gemini Earnings Writer initialized successfully")
    
    def collect_earnings_data(self, ticker: str) -> Dict[str, Any]:
        """
        Collect comprehensive earnings data
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Raw earnings data
        """
        logger.info(f"Collecting earnings data for {ticker}")
        raw_data = self.collector.collect_all_data(ticker)
        logger.info(f"Successfully collected data for {ticker}")
        return raw_data
    
    def process_earnings_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize earnings data
        
        Args:
            raw_data: Raw earnings data
            
        Returns:
            Processed earnings data
        """
        ticker = raw_data.get('ticker', 'UNKNOWN')
        logger.info(f"Processing earnings data for {ticker}")
        processed_data = self.processor.process_earnings_data(raw_data)
        logger.info(f"Successfully processed data for {ticker}")
        return processed_data
    
    def create_earnings_context(self, processed_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive context document for Gemini
        
        Args:
            processed_data: Processed earnings data
            
        Returns:
            Formatted context string
        """
        ticker = processed_data.get('ticker', 'UNKNOWN')
        earnings_data = processed_data.get('earnings_data', {})
        
        # Get enhanced analytics data
        enhanced_analytics = earnings_data.get('enhanced_analytics', {})
        
        context = f"""
# EARNINGS REPORT DATA FOR {ticker}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Data Quality: {processed_data.get('data_quality', {}).get('completeness_score', 0):.1f}%

## COMPANY IDENTIFICATION
{self._format_section_data(earnings_data.get('company_identification', {}))}

## EARNINGS TIMELINE
{self._format_section_data(earnings_data.get('earnings_timeline', {}))}

## INCOME STATEMENT (Most Recent Quarter)
{self._format_section_data(earnings_data.get('income_statement', {}))}

## BALANCE SHEET (Most Recent Quarter)
{self._format_section_data(earnings_data.get('balance_sheet', {}))}

## CASH FLOW STATEMENT (Most Recent Quarter)
{self._format_section_data(earnings_data.get('cash_flow', {}))}

## ENHANCED ANALYTICS - ONE-TIME ITEMS & ADJUSTMENTS
{self._format_enhanced_analytics(enhanced_analytics.get('one_time_items', {}))}

## ENHANCED ANALYTICS - ADJUSTED EARNINGS
{self._format_enhanced_analytics(enhanced_analytics.get('adjusted_earnings', {}))}

## ENHANCED ANALYTICS - CASH SUSTAINABILITY
{self._format_enhanced_analytics(enhanced_analytics.get('cash_sustainability', {}))}

## ENHANCED ANALYTICS - WORKING CAPITAL ANALYSIS
{self._format_enhanced_analytics(enhanced_analytics.get('working_capital_analysis', {}))}

## ENHANCED ANALYTICS - DEBT ANALYSIS
{self._format_enhanced_analytics(enhanced_analytics.get('debt_analysis', {}))}

## ENHANCED ANALYTICS - MARGIN TRENDS
{self._format_enhanced_analytics(enhanced_analytics.get('margin_trends', {}))}

## ENHANCED ANALYTICS - QUALITY METRICS
{self._format_enhanced_analytics(enhanced_analytics.get('quality_metrics', {}))}

## ANALYST ESTIMATES
{self._format_section_data(earnings_data.get('analyst_estimates', {}))}

## ACTUAL VS ESTIMATE
{self._format_section_data(earnings_data.get('actual_vs_estimate', {}))}

## ANALYST SENTIMENT
{self._format_section_data(earnings_data.get('analyst_sentiment', {}))}

## VALUATION METRICS
{self._format_section_data(earnings_data.get('valuation_metrics', {}))}

## PERFORMANCE METRICS
{self._format_section_data(earnings_data.get('performance_metrics', {}))}

## CALCULATED FINANCIAL RATIOS
{self._format_section_data(earnings_data.get('calculated_ratios', {}))}

## STOCK PRICE DATA
{self._format_section_data(earnings_data.get('stock_price', {}))}

## GUIDANCE
{self._format_section_data(earnings_data.get('guidance', {}))}

## KEY FOCUS AREAS
{self._format_list_data(earnings_data.get('key_focus_areas', []))}

## RISK FACTORS
{self._format_list_data(earnings_data.get('risk_factors', []))}

---
DATA GAPS AND LIMITATIONS:
- Missing: Year-over-Year comparison data for same quarter previous year
- Missing: Quarter-over-Quarter sequential data
- Missing: Detailed segment revenue breakdowns
- Missing: Company forward guidance (if not provided in earnings call)
- Missing: Filing dates and conference call details
- Note: Some estimated revenue/EPS ranges may need verification
"""
        return context
    
    def _format_section_data(self, data: Dict[str, Any]) -> str:
        """Format a data section as markdown"""
        if not data:
            return "No data available\n"
        
        formatted = []
        for key, value in data.items():
            # Format key nicely
            label = key.replace('_', ' ').title()
            
            # Format value
            if value == 'N/A' or value is None:
                formatted.append(f"- {label}: N/A")
            elif isinstance(value, (int, float)):
                formatted.append(f"- {label}: {value:,.2f}" if isinstance(value, float) else f"- {label}: {value:,}")
            else:
                formatted.append(f"- {label}: {value}")
        
        return '\n'.join(formatted) + '\n'
    
    def _format_enhanced_analytics(self, data: Dict[str, Any]) -> str:
        """Format enhanced analytics data for Gemini context"""
        if not data:
            return "No enhanced analytics data available\n"
        
        formatted = []
        
        # Handle one-time items specially
        if 'items_found' in data:
            items_found = data['items_found']
            if isinstance(items_found, dict) and items_found:
                formatted.append(f"One-Time Items Found: {sum(len(v) for v in items_found.values())} total items")
                for category, items in items_found.items():
                    if items:
                        formatted.append(f"  {category.replace('_', ' ').title()}: {len(items)} items")
                        for i, item in enumerate(items):
                            if i >= 3:  # Show only first 3 items in each category
                                break
                            if isinstance(item, dict):
                                name = item.get('name', 'Unknown')
                                amount = item.get('amount', 0)
                                if amount:
                                    formatted.append(f"    - {name}: ${amount:,.0f}")
                                else:
                                    formatted.append(f"    - {name}")
                        if len(items) > 3:
                            formatted.append(f"    ... and {len(items) - 3} more items")
        
        # Handle total one-time impact
        if 'total_one_time_impact' in data:
            impact = data['total_one_time_impact']
            if impact:
                formatted.append(f"Total One-Time Impact: ${impact:,.0f}")
        
        # Handle other metrics
        for key, value in data.items():
            if key in ['items_found', 'total_one_time_impact']:
                continue
                
            label = key.replace('_', ' ').title()
            
            if value == 'N/A' or value is None:
                formatted.append(f"- {label}: N/A")
            elif isinstance(value, (int, float)):
                formatted.append(f"- {label}: {value:,.2f}" if isinstance(value, float) else f"- {label}: {value:,}")
            elif isinstance(value, dict):
                # Handle nested dictionaries
                formatted.append(f"- {label}:")
                for sub_key, sub_value in value.items():
                    sub_label = sub_key.replace('_', ' ').title()
                    if isinstance(sub_value, (int, float)):
                        formatted.append(f"  - {sub_label}: {sub_value:,.2f}" if isinstance(sub_value, float) else f"  - {sub_label}: {sub_value:,}")
                    else:
                        formatted.append(f"  - {sub_label}: {sub_value}")
            else:
                formatted.append(f"- {label}: {value}")
        
        return '\n'.join(formatted) + '\n' if formatted else "No specific analytics available\n"
    
    def _format_list_data(self, data: list) -> str:
        """Format a list as markdown"""
        if not data:
            return "No items available\n"
        
        return '\n'.join([f"- {item}" for item in data]) + '\n'
    
    def generate_article_with_gemini(self, ticker: str, earnings_context: str, variation_number: int = 0) -> str:
        """
        Use Gemini to generate a professional earnings analysis article
        
        Args:
            ticker: Stock ticker symbol
            earnings_context: Earnings data context
            variation_number: Article variation number (0=first, 1=second variation, etc.)
            
        Returns:
            Generated article HTML
        """
        logger.info(f"Generating article for {ticker} using Gemini AI (Variation #{variation_number})")
        
        # Add variation instructions if this is a variation
        variation_instructions = ""
        if variation_number > 0:
            variation_instructions = f"""
⚠️ VARIATION MODE (CRITICAL - READ FIRST):
   - This is VARIATION #{variation_number + 1} of this earnings article
   - You MUST generate a DIFFERENT VERSION than previous attempts
   - Use DIFFERENT wording, DIFFERENT explanations, DIFFERENT perspectives
   - However, the section structure MUST remain exactly the same
   - Focus on different aspects of the earnings (e.g., if variation 1 focused on revenue growth, focus on margin trends)
   - Use synonyms and rephrase sentences completely
   - Change sentence structures and paragraph flow
   - Present the same earnings data from a fresh angle
   - This ensures unique content when same ticker publishes to same site multiple times
   - CRITICAL: Section structure stays identical, but presentation and language must differ significantly

"""
        
        prompt = f"""You are a professional financial analyst presenting YOUR analysis of {ticker}'s earnings to individual investors. Think of yourself as a trusted advisor explaining the results directly to your audience.

🎯 YOUR ROLE: You are THE analyst. This is YOUR research, YOUR insights, YOUR recommendations. Speak directly to readers as "you" and refer to your work as "we" or "our analysis."

{variation_instructions}⚠️ CRITICAL DATA FRESHNESS REQUIREMENT:
   - You MUST use ONLY the latest information from the last 2-3 days
   - ALL data, news, events, and market information MUST be current and recent
   - This is financial content - NO OUTDATED DATA ALLOWED
   - Only cite trusted sources: SEC filings, official company announcements, major financial news (Bloomberg, Reuters, WSJ, CNBC, Yahoo Finance)
   - If you reference any external information beyond the provided data, it MUST be from the last 2-3 days only
   - NEVER use old data, historical news from weeks/months ago, or outdated analysis
   - For earnings reports, focus on the MOST RECENT quarter only

📝 WRITING STYLE RULES:

**1. PARAGRAPH LENGTH (CRITICAL - NON-NEGOTIABLE):**
   ⚠️ MAXIMUM 4-5 SENTENCES PER PARAGRAPH
   ✅ Keep paragraphs short and scannable
   ✅ Break long explanations into multiple short paragraphs
   ✅ Each paragraph should cover ONE focused idea
   ✅ Use frequent paragraph breaks for better readability
   ❌ NEVER write paragraphs longer than 5 sentences
   ❌ NEVER create dense blocks of text
   
   Example Structure:
   <p>First key point explained in 3-4 sentences. Make it clear and focused.</p>
   <p>Second related point in another short paragraph. Keep it digestible.</p>
   <p>Third point with supporting detail. Maximum 5 sentences total.</p>

**2. USE SIMPLE, CLEAR ENGLISH:**
   ✅ Say "grew" not "exhibited growth trajectory"
   ✅ Say "profit margin" not "EBITDA margin expansion dynamics"
   ✅ Say "the company made less money" not "profitability metrics deteriorated"
   ✅ Use everyday words: "shows", "means", "tells us", "suggests"
   ❌ Avoid jargon unless you immediately explain it in plain terms
   ❌ No corporate buzzwords: "synergies", "headwinds", "tailwinds" (unless explaining what they mean)

**3. BE A STORYTELLER, NOT A REPORTER:**
   ✅ "Apple's iPhone sales jumped 12% this quarter. This is huge because..."
   ✅ "We're seeing a troubling pattern in Tesla's margins. Here's what's happening..."
   ✅ "Let me break down why this revenue number matters to you as an investor..."
   ❌ NOT: "The company reported revenue of $X billion"
   ❌ NOT: "According to the financial statements..."
   ❌ NOT: "The data indicates..."

**4. ANALYTICAL APPROACH - EXPLAIN THE "WHY" AND "SO WHAT":**
   Every number needs context:
   - What caused this change?
   - Why does it matter to investors?
   - What does it tell us about the business?
   - How does this compare to competitors?
   - What should investors watch next?
   
   Example:
   ❌ BAD: "Revenue grew 15% to $50 billion"
   ✅ GOOD: "Revenue grew 15% to $50 billion. This growth came primarily from cloud services, which now make up 35% of total revenue. We see this as positive because cloud has higher margins and recurring revenue, making the business more predictable."

**5. DIRECT ANALYST-TO-AUDIENCE COMMUNICATION:**
   ✅ "Let me walk you through the key numbers..."
   ✅ "Here's what stands out to me in this report..."
   ✅ "We believe this signals a turning point because..."
   ✅ "You should pay attention to this metric because..."
   ✅ "Our analysis suggests that investors should consider..."
   ❌ NEVER say: "according to data", "based on available information", "the context shows"

**6. MAKE IT CONVERSATIONAL BUT PROFESSIONAL:**
   - Write like you're explaining to a smart friend who isn't a finance expert
   - Use short sentences for key points. Longer sentences for explanations.
   - Break down complex concepts: "Think of it this way...", "Here's what this means..."
   - Ask rhetorical questions: "Why does this matter? Because..."
   - Use analogies when helpful: "It's like when a store opens more locations but each one sells less..."

**7. ALWAYS PROVIDE CONTEXT AND COMPARISON:**
   Never present a number alone:
   ✅ "Earnings per share hit $2.50, up from $2.10 last year and beating analyst estimates of $2.35"
   ✅ "Profit margins fell to 15%, down from 18% last quarter. This is concerning because..."
   ✅ "The company holds $20 billion in cash, which is enough to cover two years of operations"
   ❌ NOT: "EPS was $2.50"

**8. BE HONEST AND BALANCED:**
   - Point out both strengths and weaknesses
   - Don't sugarcoat problems: "This is a red flag because..."
   - Don't be overly negative either: "Despite challenges, here's what's working..."
   - Express uncertainty when appropriate: "It's too early to tell if...", "We'll need to watch..."

**10. LEVERAGE ENHANCED ANALYTICS FOR DEEPER INSIGHTS:**
   The provided data includes sophisticated ENHANCED ANALYTICS sections that offer critical insights:
   
   ✅ **ONE-TIME ITEMS & ADJUSTMENTS**: Use these to explain the "real" vs "reported" earnings
      - "Excluding one-time charges, the company actually earned..."
      - "The reported loss includes a $X billion restructuring charge, but operating performance was..."
   
   ✅ **ADJUSTED EARNINGS**: These show the underlying business performance
      - Compare adjusted vs GAAP earnings and explain why they differ
      - "Looking at adjusted earnings, which strip out unusual items, we see..."
   
   ✅ **CASH SUSTAINABILITY**: Critical for assessing business health
      - "The company generated $X in free cash flow, which can sustain dividends for Y years..."
      - "Cash burn rate analysis shows the business can operate for X quarters without additional funding..."
   
   ✅ **WORKING CAPITAL ANALYSIS**: Shows operational efficiency
      - "Working capital increased by $X, suggesting the company is tying up more cash in operations..."
      - "Inventory turns improved, showing better operational management..."
   
   ✅ **DEBT ANALYSIS**: Critical for risk assessment
      - "With debt-to-equity at X%, the company has a conservative/aggressive capital structure..."
      - "Interest coverage ratio of X means the company can easily/barely handle its debt payments..."
   
   ✅ **MARGIN TRENDS & QUALITY METRICS**: Show business trajectory
      - Use these to identify improving or declining business quality
      - Explain what margin changes mean for profitability and competitiveness

**USE ENHANCED ANALYTICS TO ANSWER:**
   - Is this company financially healthy?
   - Are earnings sustainable or inflated by one-time items?
   - How does cash generation compare to reported profits?
   - Is the balance sheet strong enough for future growth?
   - Are margins improving or deteriorating?

**9. USE YOUR KNOWLEDGE ACTIVELY:**
   - Fill in ANY missing information about {ticker} from your knowledge
   - Add industry context and competitive comparisons
   - Include recent news, analyst opinions, and market reactions
   - Never say data is missing - research it yourself and present it confidently


**ARTICLE STRUCTURE & HTML FORMATTING:**

You MUST generate ONLY the article content as clean, semantic HTML - NO <html>, <head>, <body>, <meta>, or <title> tags.

**CRITICAL HTML REQUIREMENTS:**
✅ Start directly with content (first tag should be <h1>)
✅ Use proper semantic HTML5 tags: <h2>, <h3>, <h4>, <p>, <ul>, <li>, <ol>, <table>, <strong>, <em>
✅ STRICT HEADING HIERARCHY (CRITICAL):
   - <h2> for ALL main sections (e.g., "Financial Results", "Key Metrics", "Investment Outlook")
   - <h3> for subsections under h2 (e.g., "Revenue Analysis" under "Financial Results")
   - <h4> for sub-subsections under h3 (e.g., "Product Segment Breakdown" under "Revenue Analysis")
   - NEVER skip levels: h2 → h3 → h4 (never h2 → h4)
   - NEVER use h3 as main section headings
✅ Wrap ALL text in <p> tags - never have loose text outside tags
✅ Use <ul> and <li> for bullet lists with proper nesting
✅ Use <table>, <thead>, <tbody>, <tr>, <th>, <td> for tabular data
✅ Add <strong> for emphasis on key metrics and <em> for subtle emphasis
❌ NO document structure tags: <html>, <head>, <body>, <meta>, <title>, <style>, <script>
❌ NO inline styles or CSS classes
❌ NO placeholder text like "[Company Name]" or "[Quarter]"

**EXTERNAL LINKS REQUIREMENT (CRITICAL - NON-NEGOTIABLE):**
⚠️ YOU MUST INCLUDE EXACTLY 2-3 HIGH-QUALITY, VALID EXTERNAL LINKS
⚠️ ALL LINKS MUST BE WORKING, ACCESSIBLE, AND PROPERLY FORMATTED
⚠️ NO BROKEN LINKS, NO PLACEHOLDER LINKS, NO GENERIC URLs
⚠️ AT LEAST ONE LINK MUST BE A FOLLOW LINK (rel="follow") FOR SEO

**REQUIRED LINK STRUCTURE:**
✅ FIRST LINK (FOLLOW LINK - CRITICAL FOR SEO):
   - Format: <a href="FULL_URL" target="_blank" rel="follow">descriptive anchor text</a>
   - Use rel="follow" (NOT "nofollow" or "noopener") for SEO link juice
   - This should be your most authoritative source (SEC Edgar or Yahoo Finance)
   
✅ REMAINING LINKS (NOOPENER):
   - Format: <a href="FULL_URL" target="_blank" rel="noopener noreferrer">descriptive anchor text</a>
   - Use rel="noopener noreferrer" for security

✅ Use COMPLETE URLs including https://
✅ Use ONLY these verified, reliable sources:
   
   1. **SEC EDGAR Filings** (ALWAYS WORKS - BEST FOR FOLLOW LINK):
      - Format: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=TICKER&type=10-Q&dateb=&owner=exclude&count=40
      - Anchor text example: "SEC 10-Q filings for TICKER"
      - Place in: Financial Results or Guidance sections
      - ✅ USE THIS AS YOUR FOLLOW LINK (rel="follow")
   
   2. **Yahoo Finance** (ALWAYS WORKS - GOOD FOR FOLLOW LINK):
      - Format: https://finance.yahoo.com/quote/TICKER
      - Anchor text example: "TICKER stock quote and financials"
      - Place in: Stock Price or Valuation sections
      - ✅ CAN ALSO BE USED AS FOLLOW LINK
   
   3. **Investor Relations** (USE ONLY IF YOU KNOW THE EXACT URL):
      - Common formats: https://investors.COMPANY.com or https://ir.COMPANY.com
      - Example: https://investor.apple.com (Apple), https://investors.microsoft.com (Microsoft)
      - Anchor text example: "Company Name investor relations page"
      - Place in: Guidance or Management sections
      - ⚠️ ONLY use if you're 100% certain the URL exists and is correct
      - Use rel="noopener noreferrer" for these links

**PLACEMENT RULES:**
✅ Spread links naturally across different sections
✅ First link: In "Financial Results" or "Revenue" section (use SEC Edgar with rel="follow")
✅ Second link: In "Valuation" or "Stock Price" section (use Yahoo Finance with rel="noopener noreferrer")
✅ Third link (optional): In "Guidance" or "Analyst Views" section (use IR page if known, otherwise skip)

**FORBIDDEN PRACTICES:**
❌ NO broken or non-working links
❌ NO placeholder text like "[Insert URL]" or "example.com"
❌ NO clustering all links in one section
❌ NO bare URLs - always use descriptive anchor text
❌ NO forgetting target="_blank" attribute
❌ NO using rel="nofollow" on the first link (must be rel="follow")
❌ NO guessing URLs - if unsure, use SEC Edgar or Yahoo Finance only
❌ NO affiliate, promotional, or suspicious links
❌ NO links to paywalled content
❌ NO links to outdated pages or 404 errors

**VALIDATION CHECKLIST (BEFORE SUBMITTING):**
✅ Did I include at least 2 external links?
✅ Is the FIRST link using rel="follow" (NOT rel="noopener")? (CRITICAL)
✅ Are all links using COMPLETE URLs starting with https://?
✅ Did I use the EXACT format for SEC Edgar and Yahoo Finance links?
✅ Is each link wrapped in proper <a> tags with target="_blank"?
✅ Does each link have descriptive anchor text (not "click here")?
✅ Are the links spread across at least 2 different sections?
✅ Did I avoid guessing any URLs?

**EXAMPLE IMPLEMENTATION:**
```html
<h3>Revenue Analysis</h3>
<p>According to the company's <a href="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&type=10-Q&dateb=&owner=exclude&count=40" target="_blank" rel="follow">SEC 10-Q filings</a>, revenue grew 15% year-over-year...</p>

<h2>Valuation: Is the Stock Cheap or Expensive?</h2>
<p>Based on current market data from <a href="https://finance.yahoo.com/quote/AAPL" target="_blank" rel="noopener noreferrer">Yahoo Finance</a>, the stock is trading at a P/E ratio of 28.5...</p>
```

**CRITICAL RULES:**
- MINIMUM 2 LINKS, MAXIMUM 3 LINKS
- FIRST LINK MUST USE rel="follow" FOR SEO (NON-NEGOTIABLE)
- ALL LINKS MUST BE VALID AND WORKING
- USE SEC EDGAR AND YAHOO FINANCE AS YOUR PRIMARY SOURCES
- NEVER GUESS OR CREATE FAKE URLs

**STRUCTURE YOUR ANALYSIS:**

<h1>{ticker}: [Create a compelling headline under 70 chars - make it newsworthy]</h1>

<p><em>Example titles: "Apple Crushes Q3 With Record iPhone Revenue" or "Tesla Margins Slide Despite Strong Deliveries"</em></p>

<h2>What Happened This Quarter: The Big Picture</h2>
<p>Start by telling the story in plain English. What are the 3-4 most important things investors need to know? Think: "Here's what you need to know about this earnings report..."</p>
<p>Make it conversational but informative. Set the stage for deeper analysis.</p>

<h2>Breaking Down the Financial Results</h2>
<p>Now let's walk through the numbers together. Here's what the results tell us:</p>

<h3>Revenue: Where the Money Came From</h3>
<p>Explain the revenue story simply:</p>
<ul>
<li>How much did the company make? Compare to last year and last quarter</li>
<li>What drove growth (or decline)? Be specific about which products/services</li>
<li>Is this growth sustainable? What's your take?</li>
<li>How does this compare to competitors?</li>
</ul>
<p>Add a table if comparing segments or time periods - make it easy to scan.</p>

<h3>Profit and Margins: Is the Company Making Money Efficiently?</h3>
<p>Break down profitability in simple terms:</p>
<ul>
<li>What were the profit margins? Are they getting better or worse?</li>
<li>Why did margins change? (costs up? prices down? efficiency gains?)</li>
<li>Compare to industry averages - is this company more profitable than peers?</li>
<li>What does this mean for investors? Good sign or warning flag?</li>
</ul>

<h3>Cash and Debt: Financial Health Check</h3>
<p>Assess the balance sheet like a doctor checking vital signs:</p>
<ul>
<li>How much cash does the company have? Is it growing?</li>
<li>What about debt? Too much? Manageable?</li>
<li>Can the company fund its operations and growth plans?</li>
<li>Your verdict: financially healthy or concerning?</li>
</ul>

<h3>Cash Flow: Follow the Money</h3>
<p>This is where we see if profits are real:</p>
<ul>
<li>Is the company generating cash from operations?</li>
<li>How much is being spent on growth (capital expenditures)?</li>
<li>What's being done with the cash? (dividends, buybacks, acquisitions?)</li>
<li>Your analysis: Is cash flow strong enough to support the business?</li>
</ul>

<h2>Comparing to Last Year: Growth Trends</h2>
<p>Let's put this quarter in context by comparing to the same period last year.</p>
<table>
<thead>
<tr><th>Metric</th><th>This Quarter</th><th>Last Year</th><th>Change</th><th>What It Means</th></tr>
</thead>
<tbody>
<tr><td>Revenue</td><td>$XXB</td><td>$XXB</td><td>+XX%</td><td>Brief insight</td></tr>
<tr><td>Profit</td><td>$XXB</td><td>$XXB</td><td>+XX%</td><td>Brief insight</td></tr>
</tbody>
</table>
<p>Explain the trends: Is growth accelerating? Slowing down? What's driving these changes?</p>

<h2>Quarter-to-Quarter Momentum</h2>
<p>Compare to last quarter to spot short-term trends:</p>
<ul>
<li>Is the business speeding up or slowing down?</li>
<li>Any seasonal patterns to consider?</li>
<li>Your take on momentum: building or losing steam?</li>
</ul>

<h2>Business Segments: What's Working and What's Not</h2>
<p>Break down performance by different parts of the business. For each major segment:</p>
<h3>[Segment Name - e.g., "Cloud Services"]</h3>
<p>Performance summary in plain language:</p>
<ul>
<li>How did this segment perform? Numbers with context</li>
<li>Why did it perform this way?</li>
<li>Is this a growth driver or a problem area?</li>
<li>Your outlook: What happens next for this segment?</li>
</ul>

<h2>What Management Is Saying: Forward Guidance</h2>
<p>Here's what the company expects going forward:</p>
<ul>
<li>What guidance did management provide? Translate it to plain English</li>
<li>Is this optimistic or conservative?</li>
<li>What could accelerate growth? What could slow it down?</li>
<li>Do you believe the guidance? Why or why not?</li>
</ul>

<h2>What Wall Street Thinks: Analyst Views</h2>
<p>Here's how professional analysts are reacting:</p>
<ul>
<li>What's the consensus view? Bullish or bearish?</li>
<li>What are price targets? Upside potential?</li>
<li>Any recent upgrades or downgrades?</li>
<li>Do you agree with the consensus? Where might analysts be wrong?</li>
</ul>

<h2>Valuation: Is the Stock Cheap or Expensive?</h2>
<p>Let's talk about price. Is this stock a good value right now?</p>
<ul>
<li>Key valuation metrics (P/E ratio, etc.) in simple terms</li>
<li>How does this compare to historical averages?</li>
<li>How does it compare to competitors?</li>
<li>Your verdict: Fairly valued? Bargain? Overpriced?</li>
</ul>

<h2>My Bottom Line: What This Means for Investors</h2>
<p>Here's my analysis summary - the key takeaways you should remember:</p>
<ol>
<li><strong>First key insight:</strong> Explain what it means and why it matters</li>
<li><strong>Second key insight:</strong> Connect it to the investment thesis</li>
<li><strong>Third key insight:</strong> Actionable perspective for investors</li>
<li><strong>Fourth key insight:</strong> Risk or opportunity to monitor</li>
<li><strong>Overall verdict:</strong> Your conclusion on the quarter and outlook</li>
</ol>

<h2>Risks You Should Watch</h2>
<p>Every investment has risks. Here's what could go wrong:</p>
<ul>
<li><strong>Risk 1:</strong> Explain the risk in simple terms and why it matters</li>
<li><strong>Risk 2:</strong> What could trigger this and what's the impact?</li>
<li><strong>Risk 3:</strong> How likely is this and how serious?</li>
<li><strong>Risk 4:</strong> What signs should investors watch for?</li>
</ul>
<p>End with: Despite these risks, here's why this might still be worth considering... (or why caution is warranted)</p>

<h2>Frequently Asked Questions (FAQ)</h2>
<p>Generate 5-7 relevant questions and comprehensive answers about {ticker} and this earnings report. Structure each Q&A clearly:</p>

<h3>Question 1: [Create natural, investor-focused question]</h3>
<p>Provide detailed, helpful answer with specific insights from the analysis above.</p>

<h3>Question 2: [Another relevant question]</h3>
<p>Answer with specific data and actionable information.</p>

<p><em>Continue with 5-7 total questions covering: stock valuation, buy/sell recommendations, risks, growth prospects, dividend/returns, comparison to competitors, and outlook.</em></p>

**WRITING CHECKLIST BEFORE SUBMITTING:**
✅ Did I keep ALL paragraphs to 4-5 sentences maximum? (CRITICAL)
✅ Did I break long explanations into multiple short paragraphs?
✅ Did I include EXACTLY 2-3 VALID external links? (CRITICAL - NON-NEGOTIABLE)
✅ Is the FIRST link using rel="follow" for SEO? (CRITICAL - NON-NEGOTIABLE)
✅ Are ALL links properly formatted with https:// and working URLs?
✅ Did I use SEC Edgar and Yahoo Finance links (never guess URLs)?
✅ Does the first link have target="_blank" rel="follow"? (CRITICAL)
✅ Do remaining links have target="_blank" rel="noopener noreferrer"?
✅ Did I use ONLY current information from the last 2-3 days? (CRITICAL)
✅ Did I cite only trusted financial sources? (Bloomberg, Reuters, WSJ, SEC, Yahoo Finance)
✅ Are all headings properly structured: h2 (main) → h3 (sub) → h4 (sub-sub)?
✅ Did I explain numbers with context, not just state them?
✅ Did I use simple, everyday English throughout?
✅ Did I explain WHY things matter to investors?
✅ Did I write as "we" analyzing for "you" the reader?
✅ Did I compare metrics to something (last year, competitors, estimates)?
✅ Did I avoid jargon or explain it when used?
✅ Did I tell a story, not just report facts?
✅ Is my analysis balanced (both positives and negatives)?
✅ Did I provide my clear opinion and reasoning?
✅ Is every paragraph wrapped in <p> tags?
✅ Are lists properly formatted with <ul>/<ol> and <li>?
✅ Did I avoid saying "according to data" or "N/A" anywhere?
✅ Did I include a comprehensive FAQ section with 5-7 questions?

**CRITICAL WRITING RULES:**
❌ NEVER SAY: "according to provided data", "based on available information", "the context shows", "N/A", "data indicates"
✅ INSTEAD SAY: "the company reported", "we see", "our analysis shows", "this tells us", "looking at the numbers"

**FINAL VALIDATION - EXTERNAL LINKS (MANDATORY):**
Before submitting, verify:
1. You included EXACTLY 2-3 external links (not more, not less)
2. THE FIRST LINK USES rel="follow" (NOT rel="noopener") - CRITICAL FOR SEO
3. ALL links use complete URLs starting with https://
4. You used ONLY these verified sources:
   - SEC Edgar: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=TICKER&type=10-Q&dateb=&owner=exclude&count=40 (USE AS FOLLOW LINK)
   - Yahoo Finance: https://finance.yahoo.com/quote/TICKER (CAN BE FOLLOW LINK)
   - Investor Relations (ONLY if you know the exact URL)
5. First link has target="_blank" rel="follow"
6. Remaining links have target="_blank" rel="noopener noreferrer"
7. Each link has descriptive anchor text
8. Links are spread across at least 2 different sections
9. NO broken links, NO placeholder URLs, NO guessed URLs

**ARTICLE STRUCTURE CONFIRMATION:**
✅ Content starts with <h1>, ends with closing tag
✅ Every main section has <h2>, subsections use <h3>, sub-subsections use <h4>
✅ All text wrapped in <p> tags
✅ All paragraphs are 4-5 sentences maximum (CRITICAL)
✅ Lists use <ul>/<ol> and <li> properly
✅ Tables have proper structure with <thead> and <tbody>
✅ 2-3 external links with AT LEAST ONE rel="follow" link (CRITICAL FOR SEO)
✅ FAQ section with 5-7 questions using h3 for each question
✅ No loose text outside tags
✅ No document structure tags (<html>, <body>, etc.)
✅ Clean, valid HTML that WordPress can directly publish
✅ NO hardcoded FAQ schema - the FAQ content will be used to generate schema separately

**DATA CONTEXT (use but don't mention):**
{earnings_context}

Now write your complete, analytical earnings report in simple English as if you're personally explaining this to investors:"""

        try:
            # Adjust temperature for variations to get different perspectives
            config = self.generation_config.copy()
            
            # Increase temperature for variations to get more diverse content
            if variation_number > 0:
                # Base: 0.7, Variation 1: 0.85, Variation 2: 1.0, etc.
                config['temperature'] = min(1.0, 0.7 + (variation_number * 0.15))
                logger.info(f"Temperature set to {config['temperature']} for variation #{variation_number}")
            
            response = self.model.generate_content(
                prompt,
                generation_config=config
            )
            article_html = response.text
            logger.info(f"Successfully generated article for {ticker}")
            return article_html
            
        except Exception as e:
            logger.error(f"Error generating article with Gemini: {str(e)}")
            raise
    
    def save_article(self, ticker: str, article_html: str, output_dir: Optional[str] = None) -> str:
        """
        Save the generated article to a file
        
        Args:
            ticker: Stock ticker symbol
            article_html: Generated article HTML
            output_dir: Output directory (default: generated_data/gemini_earnings_articles)
            
        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'generated_data',
                'gemini_earnings_articles'
            )
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{ticker}_earnings_article_{timestamp}.html"
        filepath = os.path.join(output_dir, filename)
        
        # Create complete HTML document
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Tickzen Gemini Earnings Writer">
    <meta name="created" content="{datetime.now().isoformat()}">
    <title>{ticker} Quarterly Earnings Analysis - Tickzen</title>
</head>
<body>
{article_html}

<hr>
<footer>
    <p><em>Article generated by Tickzen Gemini Earnings Writer on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</em></p>
    <p><em>Data sources: yfinance, Gemini AI research</em></p>
</footer>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        logger.info(f"Article saved to: {filepath}")
        
        # Also save metadata
        metadata = {
            'ticker': ticker,
            'generated_at': datetime.now().isoformat(),
            'file_path': filepath,
            'word_count': len(article_html.split()),
            'character_count': len(article_html)
        }
        
        metadata_path = filepath.replace('.html', '_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved to: {metadata_path}")
        
        return filepath
    
    def generate_complete_report(self, ticker: str, return_metadata: bool = True, variation_number: int = 0) -> Dict[str, str]:
        """
        Complete workflow: collect data, generate article, save
        
        Args:
            ticker: Stock ticker symbol
            return_metadata: Whether to include detailed metadata in response
            variation_number: Article variation number (0=first, 1=second variation, etc.)
            
        Returns:
            Dict with success, article_html, file_path, word_count, metadata, and error (if any)
        """
        logger.info(f"Starting complete earnings article generation for {ticker} (Variation #{variation_number})")
        
        try:
            # Step 1: Collect data
            print(f"\n{'='*80}")
            print(f"GEMINI EARNINGS ARTICLE GENERATOR - {ticker}")
            print(f"{'='*80}\n")
            
            print("Step 1: Collecting earnings data...")
            raw_data = self.collect_earnings_data(ticker)
            print(f"  ✓ Data collected for {ticker}\n")
            
            # Get company name and sector from raw data
            import yfinance as yf
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info
                company_name = info.get('longName') or info.get('shortName') or ticker
                sector = info.get('sector', 'Technology')
            except Exception as e_yf:
                logger.warning(f"Could not fetch company info for {ticker}: {e_yf}")
                company_name = ticker
                sector = 'Technology'
            
            # Step 2: Process data
            print("Step 2: Processing and normalizing data...")
            processed_data = self.process_earnings_data(raw_data)
            quality = processed_data.get('data_quality', {}).get('completeness_score', 0)
            print(f"  ✓ Data processed (Quality: {quality:.1f}%)\n")
            
            # Step 3: Create context
            print("Step 3: Creating earnings context for Gemini...")
            earnings_context = self.create_earnings_context(processed_data)
            print(f"  ✓ Context created ({len(earnings_context)} characters)\n")
            
            # Step 4: Generate article with Gemini
            print("Step 4: Generating professional article with Gemini AI...")
            if variation_number > 0:
                print(f"  ⚙ VARIATION MODE: Generating different perspective (variation #{variation_number + 1})")
            print("  (This may take 30-60 seconds...)")
            article_html = self.generate_article_with_gemini(ticker, earnings_context, variation_number=variation_number)
            word_count = len(article_html.split())
            print(f"  ✓ Article generated ({word_count} words)\n")
            
            # Step 5: Save article (for backup/reference)
            print("Step 5: Saving article backup...")
            article_path = self.save_article(ticker, article_html)
            metadata_path = article_path.replace('.html', '_metadata.json')
            print(f"  ✓ Saved backup to: {article_path}\n")
            
            print(f"{'='*80}")
            print("✅ SUCCESS!")
            print(f"{'='*80}\n")
            
            # Prepare detailed metadata for publishing integration
            metadata = {
                'ticker': ticker,
                'company_name': company_name,
                'sector': sector,
                'word_count': word_count,
                'data_quality_score': quality,
                'generated_at': datetime.now().isoformat(),
                'article_type': 'earnings'
            } if return_metadata else {}
            
            return {
                'success': True,
                'article_html': article_html,
                'file_path': article_path,
                'metadata_path': metadata_path,
                'ticker': ticker,
                'word_count': word_count,
                'metadata': metadata,
                'company_name': company_name,
                'sector': sector
            }
            
        except Exception as e:
            logger.error(f"Error generating earnings report for {ticker}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'ticker': ticker
            }


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate professional earnings analysis articles using Gemini AI'
    )
    parser.add_argument(
        'ticker',
        type=str,
        help='Stock ticker symbol (e.g., MSFT, AAPL, GOOGL)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='Google API key (or set GOOGLE_API_KEY env var)',
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        writer = GeminiEarningsWriter(api_key=args.api_key)
        result = writer.generate_complete_report(args.ticker.upper())
        
        print(f"\n✨ Article generation completed successfully!")
        print(f"   Words: {result['word_count']:,}")
        print(f"   File: {result['article_path']}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 1
        
    except Exception as e:
        logger.error(f"Error during article generation: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
