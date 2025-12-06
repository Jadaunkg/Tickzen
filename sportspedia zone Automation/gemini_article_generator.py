"""
Gemini AI Integration for SEO-Optimized Article Generation
Uses Google Gemini AI to generate professional, SEO-optimized articles
based on research information collected from Perplexity AI

Role: Article Generation with SEO Optimization
Input: Research data from Perplexity AI
Output: Professional, human-written, SEO-optimized articles

Using official google-generativeai library for reliable API calls
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure console can handle UTF-8 output to avoid encoding errors on Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    # If reconfigure is unsupported, continue with default encoding
    pass

# Import Google Generative AI
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("google-generativeai not installed. Install with: pip install google-generativeai")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_article_generation.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


class GeminiArticleGenerator:
    """
    Generates SEO-optimized articles using Google Gemini AI
    Takes research data from Perplexity and creates professional articles
    Uses official google-generativeai library for reliable calls
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini Article Generator
        
        Args:
            api_key (str): Google Gemini API key. If None, reads from GEMINI_API_KEY env var
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            logging.warning("⚠️  GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables")
            logging.info("ℹ️  To use Google Gemini AI:")
            logging.info("   1. Get API key from https://ai.google.dev/")
            logging.info("   2. Set environment variable: set GEMINI_API_KEY=your_key")
        
        # Configure Gemini API
        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
        
        # Use requested Gemini model
        self.model_name = "gemini-2.5-flash"  # Requested model for stock/sports articles
        self.timeout = 60
        
    def generate_article_from_research(self, research_context: Dict) -> Dict:
        """
        Generate SEO-optimized article from research context
        
        Args:
            research_context (Dict): Research data and context from Perplexity
            
        Returns:
            Dict: Generated article with SEO optimization
        """
        try:
            if not self.api_key:
                logging.error("❌ Gemini API key not configured")
                return self._get_placeholder_article(research_context, "API key not configured")
            
            if not GENAI_AVAILABLE:
                logging.error("❌ google-generativeai library not available")
                return self._get_placeholder_article(research_context, "google-generativeai not installed")
            
            logging.info(f"\n{'='*70}")
            logging.info(f"ARTICLE GENERATION PHASE (Gemini AI)")
            logging.info(f"{'='*70}")
            
            headline = research_context.get('article_headline', '')
            logging.info(f"Headline: {headline}")
            logging.info(f"Category: {research_context.get('article_category', 'General')}")
            logging.info(f"Model: {self.model_name}")
            
            # Step 1: Prepare article generation prompt
            logging.info(f"\nStep 1: Preparing article generation prompt...")
            prompt = self._build_article_prompt(research_context)
            
            # Step 2: Call Gemini API
            logging.info(f"Step 2: Calling Gemini API for article generation...")
            article_content = self._call_gemini_api(prompt)
            
            if not article_content or article_content.get('status') != 'success':
                error_msg = article_content.get('error', 'Unknown error') if article_content else 'No response'
                return self._get_placeholder_article(research_context, error_msg)
            
            # Step 3: Prepare article data
            logging.info(f"Step 3: Preparing final article format...")
            article_data = {
                'headline': headline,
                'category': research_context.get('article_category', ''),
                'article_content': article_content.get('content', ''),
                'seo_metadata': self._extract_seo_metadata(article_content.get('content', ''), headline),
                'sources': research_context.get('research_data', {}).get('compiled_sources', []),
                'citations': research_context.get('research_data', {}).get('compiled_citations', []),
                'generated_at': datetime.now().isoformat(),
                'status': 'success'
            }
            
            logging.info(f"Article generation complete!")
            logging.info(f"Content length: {len(article_data['article_content'])} characters")
            logging.info(f"Sources cited: {len(article_data['sources'])}")
            
            return article_data
            
        except Exception as e:
            logging.error(f"Error generating article: {e}")
            return self._get_placeholder_article(research_context, str(e))
    
    def _build_article_prompt(self, research_context: Dict) -> str:
        """
        Build a comprehensive prompt for Gemini to generate the article
        
        Args:
            research_context (Dict): Research data and context
            
        Returns:
            str: Complete prompt for article generation
        """
        headline = research_context.get('article_headline', '')
        category = research_context.get('article_category', '')
        
        research_data = research_context.get('research_data', {})
        comprehensive_research = research_data.get('research_sections', {}).get('comprehensive', {}).get('content', '')
        sources = research_data.get('compiled_sources', [])
        
        # Format sources for natural embedding (limit to top 3)
        source_links = []
        for i, source in enumerate(sources[:3]):
            if isinstance(source, str) and source.startswith('http'):
                source_links.append(source)
        
        sources_text = "\n".join([f"- {link}" for link in source_links])
        
        # Extract potential focus keywords from headline
        focus_keyword_hint = headline.split(':')[0] if ':' in headline else headline[:50]
        
        prompt = f"""You are a passionate sports writer creating content that sounds 100% human-written. Write like a real person who loves sports and wants to share the story with friends.

TOPIC: {headline}
CATEGORY: {category}
FOCUS KEYWORD: {focus_keyword_hint}

RESEARCH INFORMATION:
{comprehensive_research}

AVAILABLE SOURCE LINKS (embed 2-3 naturally):
{sources_text}

CRITICAL WRITING RULES:

1. **HUMAN WRITING - NO AI PATTERNS:**
   - Write with personality and emotion
   - Use casual language and natural flow
   - Vary sentence structure (some short, some a bit longer)
   - Include personal observations ("You can feel the tension", "It's hard not to wonder")
   - Use everyday expressions ("Let's be honest", "Here's the thing", "What's really going on")
   - Add occasional informal phrases ("pretty much", "kind of", "sort of")
   - NO perfect grammar everywhere - write naturally
   - NO AI phrases like "delve into", "landscape", "realm", "tapestry", "robust"

2. **SIMPLE HEADING STRUCTURE:**
   
   USE ONLY:
   - ONE H1 headline (# in markdown) - make it catchy with focus keyword
   - 3-4 H2 sections (## in markdown) - main story parts
   - MAXIMUM 1-2 H3 subsections (### in markdown) - ONLY if absolutely necessary
   - NO H4 headings
   
   KEEP IT SIMPLE:
   # Main Headline (natural, not robotic)
   
   [Opening paragraphs - hook the reader]
   
   ## What Actually Happened
   [Tell the story]
   
   ## Why People Are Talking About This
   [The controversy or impact]
   
   ### The Big Moment (only if needed)
   [Key detail]
   
   ## What Happens Next
   [Future implications]

3. **WRITE LIKE A HUMAN:**
   - Start sentences different ways (don't repeat patterns)
   - Mix short and medium sentences
   - Use "you" to talk to readers
   - Add your "voice" and opinions
   - Sound spontaneous, not scripted
   - Include transitions that feel natural ("But here's where it gets interesting...")
   - Ask rhetorical questions
   - Use contractions always (it's, don't, can't, won't)

4. **PARAGRAPH STYLE:**
   - Keep paragraphs 2-3 sentences
   - Some can be just ONE sentence for impact
   - Break up thoughts naturally
   - Don't make it too structured or perfect
   - Let it flow like you're telling a story

5. **VOCABULARY - SIMPLE & REAL:**
   - Use common words everyone knows
   - Avoid fancy vocabulary
   - NO business speak or formal language
   - Talk like a sports fan, not a journalist
   - Examples: "beat" not "defeated", "win" not "victory", "said" not "stated"
   - Be direct and clear

6. **EMBED SOURCES NATURALLY:**
   - Weave 2-3 links into sentences naturally
   - "Reports from [ESPN](link) show..." or "[The Athletic](link) broke the news..."
   - Make it feel natural, not forced
   - NO citation numbers or formal references

7. **CONTENT FLOW:**
   - Opening: Jump right in with a hook (2 paragraphs)
   - Body: 3-4 H2 sections telling the story
   - Use H3 sparingly - only 1-2 if story needs it
   - Closing: End naturally, no "in conclusion"
   - Target: 700-1000 words (don't overwrite)

8. **STRICTLY AVOID (AI RED FLAGS):**
   - NO words like: "delve", "meticulous", "meticulously", "navigating", "complexities", "realm", "landscape", "testament", "tailored", "robust", "holistic", "leveraging", "streamlined"
   - NO perfect transitions every time
   - NO formulaic structures
   - NO overly complex sentences
   - NO formal conclusions
   - NO list-heavy writing
   - NO repetitive sentence patterns

9. **BE HUMAN:**
   - Show emotion ("This is wild", "Nobody saw this coming")
   - Add personality ("Let's be real here")
   - Use sports slang when appropriate
   - Sound excited or surprised when it fits
   - Don't be neutral - have a perspective
   - Use **bold** for 2-3 key points only (don't overdo it)

EXAMPLE OF GOOD HUMAN WRITING:

# Messi Does It Again: Miami's in the Finals

The stadium went absolutely crazy. You should've seen it.

Messi just scored what might be the goal of the season. Miami's heading to the finals, and nobody can quite believe how it happened. One moment they were struggling, the next - pure magic.

## What Happened in the 89th Minute

Here's the thing about Messi. He waits for the perfect moment...

[Continue naturally, like telling a friend]

Now write the article. Sound like a REAL PERSON, not an AI. Use mostly H2 headings (3-4 max), only add H3 if absolutely necessary (1-2 max). Make it engaging, natural, and impossible to detect as AI-written:"""
        
        return prompt
    
    def _call_gemini_api(self, prompt: str) -> Optional[Dict]:
        """
        Make API call to Google Gemini using official library
        
        Args:
            prompt (str): Article generation prompt
            
        Returns:
            Dict: API response or None if failed
        """
        try:
            # Initialize the model
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 4096,
                }
            )
            
            # Generate content
            response = model.generate_content(
                prompt,
                stream=False,
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
            )
            
            if response and response.text:
                generated_text = response.text
                
                logging.info(f"Gemini API successful - Generated {len(generated_text)} characters")
                
                return {
                    'status': 'success',
                    'content': generated_text,
                    'usage': {
                        'prompt_tokens': len(prompt.split()),
                        'completion_tokens': len(generated_text.split())
                    }
                }
            else:
                logging.warning("No content in Gemini response")
                return {'status': 'error', 'error': 'No content generated'}
            
        except Exception as e:
            logging.error(f"Gemini API error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _extract_seo_metadata(self, article_content: str, headline: str) -> Dict:
        """
        Extract SEO metadata from generated article
        
        Args:
            article_content (str): Generated article content
            headline (str): Article headline
            
        Returns:
            Dict: SEO metadata
        """
        try:
            lines = article_content.split('\n')
            
            # Extract H1 headline from article (first # heading)
            article_headline = headline
            for line in lines:
                if line.startswith('# ') and not line.startswith('##'):
                    article_headline = line.replace('# ', '').strip()
                    break
            
            # Extract focus keyword (first 3-5 words of headline)
            focus_keyword = ' '.join(article_headline.split()[:3])
            
            # Extract meta description from first non-heading paragraph
            description = ""
            paragraph_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('*') and not stripped.startswith('-'):
                    paragraph_lines.append(stripped)
                    if len(' '.join(paragraph_lines)) >= 150:
                        break
            
            if paragraph_lines:
                description = ' '.join(paragraph_lines)[:155] + '...'
            
            # Extract keywords from all heading levels and bold text
            keywords = []
            h2_headings = []
            h3_headings = []
            
            for line in lines:
                # H2 headings (##)
                if line.startswith('## ') and not line.startswith('###'):
                    keyword = line.replace('## ', '').strip()
                    if keyword and len(keyword) > 3 and '?' not in keyword:
                        keywords.append(keyword)
                        h2_headings.append(keyword)
                
                # H3 headings (###)
                elif line.startswith('### ') and not line.startswith('####'):
                    keyword = line.replace('### ', '').strip()
                    if keyword and len(keyword) > 3 and '?' not in keyword:
                        keywords.append(keyword)
                        h3_headings.append(keyword)
                
                # Bold text for additional keywords
                if '**' in line:
                    import re
                    bold_matches = re.findall(r'\*\*(.*?)\*\*', line)
                    for match in bold_matches:
                        if len(match) > 3 and len(match) < 30 and match not in keywords:
                            keywords.append(match)
            
            # Count heading hierarchy for SEO validation
            h1_count = len([l for l in lines if l.startswith('# ') and not l.startswith('##')])
            h2_count = len([l for l in lines if l.startswith('## ') and not l.startswith('###')])
            h3_count = len([l for l in lines if l.startswith('### ') and not l.startswith('####')])
            h4_count = len([l for l in lines if l.startswith('#### ') and not l.startswith('#####')])
            
            metadata = {
                'title': article_headline[:60],
                'meta_description': description,
                'focus_keyword': focus_keyword,
                'keywords': keywords[:8],
                'word_count': len(article_content.split()),
                'reading_time_minutes': max(1, len(article_content.split()) // 200),
                'original_headline': headline,
                'seo_headline': article_headline,
                'heading_structure': {
                    'h1_count': h1_count,
                    'h2_count': h2_count,
                    'h3_count': h3_count,
                    'h4_count': h4_count,
                    'h2_headings': h2_headings,
                    'h3_headings': h3_headings
                },
                'seo_score': self._calculate_seo_score(h1_count, h2_count, h3_count, len(keywords), len(article_content.split()))
            }
            
            return metadata
            
        except Exception as e:
            logging.warning(f"Error extracting SEO metadata: {e}")
            return {}
    
    def _calculate_seo_score(self, h1_count: int, h2_count: int, h3_count: int, keyword_count: int, word_count: int) -> int:
        """
        Calculate basic SEO score (0-100)
        
        Args:
            h1_count: Number of H1 headings (should be 1)
            h2_count: Number of H2 headings
            h3_count: Number of H3 headings
            keyword_count: Number of keywords found
            word_count: Total word count
            
        Returns:
            int: SEO score out of 100
        """
        score = 0
        
        # H1 heading (only 1 is ideal)
        if h1_count == 1:
            score += 25
        
        # H2 headings (3-4 is ideal for simpler structure)
        if 3 <= h2_count <= 4:
            score += 30
        elif h2_count > 0:
            score += 20
        
        # H3 headings (0-2 is ideal for natural human writing)
        if h3_count <= 2:
            score += 20
        elif h3_count > 0:
            score += 10
        
        # Keyword usage
        if keyword_count >= 5:
            score += 15
        elif keyword_count >= 3:
            score += 10
        
        # Word count (700-1000 is ideal for natural articles)
        if 700 <= word_count <= 1000:
            score += 10
        elif 600 <= word_count <= 1200:
            score += 5
        
        return min(score, 100)
    
    def _get_placeholder_article(self, research_context: Dict, error: str) -> Dict:
        """
        Return a placeholder article when API is not available
        
        Args:
            research_context (Dict): Research context
            error (str): Error message
            
        Returns:
            Dict: Placeholder article structure
        """
        headline = research_context.get('article_headline', 'Article')
        
        return {
            'headline': headline,
            'category': research_context.get('article_category', ''),
            'article_content': f"""# {headline}

[This is a placeholder article. Configure Gemini API for real article generation.]

## Introduction
This article would contain professional, SEO-optimized content generated from the research data collected by Perplexity AI.

## About This Article
- **Status**: Placeholder (awaiting Gemini API configuration)
- **Error**: {error}
- **Timestamp**: {datetime.now().isoformat()}

## Next Steps
1. Configure GEMINI_API_KEY environment variable
2. Ensure google-generativeai is installed: pip install google-generativeai
3. Run the article generation again

The research data is ready and will be used to generate this article once Gemini AI is configured.""",
            'sources': research_context.get('research_data', {}).get('compiled_sources', []),
            'status': 'placeholder',
            'error': error,
            'generated_at': datetime.now().isoformat()
        }


def main():
    """
    Demonstration of Gemini article generation
    """
    logging.info("="*70)
    logging.info("GEMINI AI ARTICLE GENERATION - DEMONSTRATION")
    logging.info("="*70)
    
    # Initialize Gemini client
    gemini_client = GeminiArticleGenerator()
    
    # Create sample research context
    sample_context = {
        'article_headline': 'Messi scores stunning goal in Inter Miami campaign',
        'article_source': 'ESPN',
        'article_category': 'football',
        'article_url': 'https://example.com',
        'published_date': datetime.now().isoformat(),
        'importance_score': 75.5,
        'research_data': {
            'research_sections': {
                'comprehensive': {
                    'content': 'Messi scored in Inter Miami latest match helping them advance.',
                    'sources': ['espn.com', 'goal.com']
                }
            },
            'compiled_sources': ['espn.com', 'goal.com', 'mls.com']
        }
    }
    
    logging.info(f"\nTesting article generation with sample research...\n")
    
    # Generate article
    article = gemini_client.generate_article_from_research(sample_context)
    
    # Display results
    logging.info(f"\nGENERATION RESULTS:")
    logging.info(f"Status: {article.get('status')}")
    logging.info(f"SEO Metadata: {article.get('seo_metadata')}")
    
    # Save output
    output_file = "gemini_article_demo_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(article, f, indent=2, ensure_ascii=False)
    logging.info(f"\nDemo output saved to {output_file}")


if __name__ == "__main__":
    main()
