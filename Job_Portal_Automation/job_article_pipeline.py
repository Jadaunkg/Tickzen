"""
Job Article Generation Pipeline (Phase 3)
-----------------------------------------
Generates structured articles using API details, optional research, and Gemini.
Includes:
- Detail fetching from external API
- Research collection from Perplexity AI
- SEO-optimized article generation with proper structure
- Internal linking system integration
- WordPress-ready HTML output

Flow:
1. Fetch job/result/admit card details from external API
2. Collect related research from Perplexity AI
3. Generate comprehensive article with Gemini
4. Add internal links from existing website articles
5. Publish to WordPress with proper formatting
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple

import google.generativeai as genai

from Job_Portal_Automation.api.perplexity_client import PerplexityResearchCollector

logger = logging.getLogger(__name__)


class GeminiArticleGenerator:
    """Gemini-backed generator with fallback to deterministic template."""

    def __init__(
        self,
        model_names: Optional[List[str]] = None,
        temperature: float = 0.35,
        api_key: Optional[str] = None,
    ):
        self.temperature = temperature
        self.model_names = model_names or [
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_index = 0
        self.model = None

        logger.info(f"🔧 Initializing GeminiArticleGenerator...")
        logger.info(f"   API Key present: {'✅ Yes' if self.api_key else '❌ No'}")
        if self.api_key:
            logger.info(f"   API Key source: {'GEMINI_API_KEY' if os.getenv('GEMINI_API_KEY') else 'GOOGLE_API_KEY' if os.getenv('GOOGLE_API_KEY') else 'Provided'}")
            logger.info(f"   API Key length: {len(self.api_key)} chars")

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_names[self.model_index])
                logger.info(f"   ✅ Gemini model '{self.model_names[self.model_index]}' initialized successfully")
            except Exception as exc:
                logger.warning(f"   ❌ Gemini init failed, using template fallback: {exc}")
                self.model = None
        else:
            logger.warning("   ⚠️  GEMINI_API_KEY/GOOGLE_API_KEY not set, using template fallback")

    def _switch_fallback(self) -> bool:
        self.model_index += 1
        if self.model_index >= len(self.model_names):
            return False
        try:
            self.model = genai.GenerativeModel(self.model_names[self.model_index])
            logger.info(f"Switched to fallback Gemini model {self.model_names[self.model_index]}")
            return True
        except Exception as exc:
            logger.warning(f"Failed to init fallback model: {exc}")
            return False

    @staticmethod
    def _extract_text(value: Any) -> str:
        if isinstance(value, dict) and "raw" in value:
            return value.get("raw") or ""
        return value or ""

    @staticmethod
    def _normalize_links(raw_links: Any) -> List[Tuple[str, str]]:
        links: List[Tuple[str, str]] = []
        if isinstance(raw_links, dict):
            for label, url in raw_links.items():
                if url:
                    links.append((str(label), str(url)))
        elif isinstance(raw_links, list):
            for entry in raw_links:
                if isinstance(entry, dict):
                    label = entry.get("label") or entry.get("title") or entry.get("name") or entry.get("text") or "Link"
                    url = entry.get("url") or entry.get("link")
                    if url:
                        links.append((str(label), str(url)))
                elif isinstance(entry, str):
                    links.append((entry, entry))
        return links

    @staticmethod
    def _normalize_research(research: Dict[str, Any]) -> Tuple[str, List[str], List[str]]:
        # Returns (summary_text, bullet_points, sources)
        summary = research.get("summary") or ""
        bullets = research.get("bullets") or []
        sources: List[str] = []

        # Try to pull content from nested structures
        research_blob = research.get("research") or research
        if not summary:
            content = research_blob.get("content") if isinstance(research_blob, dict) else None
            if not content and isinstance(research_blob, dict):
                content = research_blob.get("research", {}).get("content")
            if not content and isinstance(research_blob, dict):
                content = research_blob.get("research", {}).get("summary")
            content = content or ""
            summary = content[:600] if content else ""
        if not bullets:
            bullets = GeminiArticleGenerator._derive_bullets_from_text(summary) if summary else []

        # Gather sources/citations
        if isinstance(research_blob, dict):
            if research_blob.get("sources"):
                sources = [str(s) for s in research_blob.get("sources") if s]
            elif research_blob.get("citations"):
                sources = [c.get("url") for c in research_blob.get("citations") if isinstance(c, dict) and c.get("url")]

        return summary, bullets, [s for s in sources if s]

    @staticmethod
    def _derive_bullets_from_text(text: str, max_items: int = 6) -> List[str]:
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        return sentences[:max_items]

    def _build_prompt(
        self,
        content_type: str,
        title: str,
        summary: str,
        bullets: List[str],
        details: Dict[str, Any],
        research_sources: List[str],
    ) -> str:
        """
        Build a human-focused prompt for natural, readable article generation.
        Focus on 10th grade readability, no robotic keywords, proper WordPress formatting.
        Pass data naturally in context without explicit labels.
        """
        # Extract all data from details dictionary
        important_dates = details.get("important_dates") or {}
        eligibility = self._extract_text(details.get("eligibility")) or ""
        how_to_apply = self._extract_text(details.get("how_to_apply")) or ""
        application_fee = self._extract_text(details.get("application_fee")) or ""
        key_details = details.get("key_details") or {}
        tables = details.get("tables") or []
        full_description = self._extract_text(details.get("full_description")) or ""

        # Extract official links for embedding in text
        important_links = self._normalize_links(details.get("important_links") or [])
        
        # Filter links - remove social media/promotional links
        filtered_links = []
        skip_keywords = ['whatsapp', 'telegram', 'twitter', 'facebook', 'instagram', 'youtube', 'social', 'join', 'group', 'channel']
        for label, url in important_links:
            if not any(skip in label.lower() for skip in skip_keywords):
                filtered_links.append((label, url))
        
        # Limit to maximum 5 links
        filtered_links = filtered_links[:5]
        
        # Build natural context prompt - data passed without explicit labels
        context_lines = []
        
        if full_description:
            context_lines.append(full_description)
        
        if important_dates:
            dates_text = []
            for k, v in important_dates.items():
                dates_text.append(f"{k}: {v}")
            context_lines.append("Important dates: " + ", ".join(dates_text))
        
        if key_details:
            details_text = []
            for k, v in key_details.items():
                v_str = self._extract_text(v) if not isinstance(v, str) else v
                details_text.append(f"{k}: {v_str}")
            context_lines.append(", ".join(details_text))
        
        if eligibility:
            context_lines.append(f"Eligibility requirements: {eligibility}")
        
        if application_fee:
            context_lines.append(f"Application fee: {application_fee}")
        
        if how_to_apply:
            context_lines.append(f"How to apply: {how_to_apply}")
        
        # Prepare data tables info
        tables_context = ""
        if tables:
            tables_context = "\nData tables to include:\n"
            for table in tables:
                if isinstance(table, dict):
                    title_str = table.get('title', 'Data')
                    if isinstance(table.get("rows"), list):
                        rows_str = "\n".join([str(row) for row in table.get("rows", [])])
                        tables_context += f"{title_str}:\n{rows_str}\n"
        
        # Prepare links context
        links_context = ""
        if filtered_links:
            links_context = "\nOfficial links to reference:\n"
            for label, url in filtered_links:
                links_context += f"- {label}: {url}\n"
        
        # Build the prompt
        prompt = [
            "WRITE A CLEAR, HUMAN-WRITTEN ARTICLE FOR A 10TH GRADE READER",
            "=" * 80,
            "",
            "GUIDELINES:",
            "✓ Write naturally - like explaining to a friend, not a robot",
            "✓ Use simple, clear language",
            "✓ Explain what, when, and how in a straightforward way",
            "✓ No marketing language or robotic phrases",
            "✓ Use ONLY the information provided below",
            "✓ Organize with proper HTML headings and formatting",
            "✓ Make it ready for WordPress publishing",
            "",
            "FORBIDDEN (Do NOT use these):",
            "✗ 'This represents a golden opportunity'",
            "✗ 'Significant recruitment drive' (just say what it is)",
            "✗ 'Understanding this...' or 'Candidates should know...'",
            "✗ Flowery descriptions or motivational language",
            "✗ Phrases like 'is sure to', 'can help you', 'best chance'",
            "",
            "HTML FORMATTING - MANDATORY:",
            "- Use <h1> for the main title (top of article)",
            "- Use <h2> for section headings",
            "- Use <h3> for subsections",
            "- Use <strong> for numbers, dates, amounts: <strong>₹500</strong>, <strong>32,679</strong>, <strong>Jan 30</strong>",
            "- Use <p> for paragraphs (keep them short - 2-3 sentences max)",
            "- Use <ul><li> for bullet point lists",
            "- Use <ol><li> for numbered steps (like application process)",
            "- Use <table> for all data with proper <thead>, <tbody>, <tr>, <td> structure",
            "- Use <a href=\"URL\" target=\"_blank\"> for links - embed them naturally in text",
            "",
            "TABLE EXAMPLE:",
            "<table style=\"width: 100%; border-collapse: collapse;\">"
            "  <thead>"
            "    <tr style=\"background-color: #f5f5f5;\">"
            "      <th style=\"border: 1px solid #ddd; padding: 10px;\">Event</th>"
            "      <th style=\"border: 1px solid #ddd; padding: 10px;\">Date</th>"
            "    </tr>"
            "  </thead>"
            "  <tbody>"
            "    <tr>"
            "      <td style=\"border: 1px solid #ddd; padding: 10px;\">Applications Open</td>"
            "      <td style=\"border: 1px solid #ddd; padding: 10px;\"><strong>Dec 31, 2025</strong></td>"
            "    </tr>"
            "  </tbody>"
            "</table>",
            "",
            "LINK EXAMPLE (embed naturally, don't create separate links section):",
            "Instead of: Links: [URL1], [URL2]",
            "Write: You can <a href=\"URL\" target=\"_blank\">apply online on the official website</a>.",
            "",
            "ARTICLE STRUCTURE:",
            "1. Start with a clear intro - what is this about?",
            "2. Important dates (use table)",
            "3. Eligibility (use list or brief paragraphs)",
            "4. How many positions and where (use table if lots of data)",
            "5. Application fee (if applicable)",
            "6. How to apply (numbered steps with link embedded)",
            "7. Physical tests/selection process (if applicable)",
            "8. Any other important info",
            "",
            "TONE & READABILITY:",
            "- Explain clearly, not condescendingly",
            "- Use short sentences",
            "- One main idea per paragraph",
            "- Sound like a helpful person explaining, not an AI",
            "",
            "=" * 80,
            "INFORMATION PROVIDED (use this context for your article):",
            "=" * 80,
            "",
            f"Title: {title}",
            f"Type: {content_type}",
            "",
            "\n".join(context_lines),
            "",
        ]
        
        if tables_context:
            prompt.append(tables_context)
        
        if links_context:
            prompt.append(links_context)
        
        prompt.extend([
            "=" * 80,
            "WRITE THE ARTICLE NOW:",
            "=" * 80,
            "Start with <h1>{title}</h1>",
            "Then write clear, simple paragraphs and sections with proper HTML tags.",
            "Make it informative, easy to read, and properly formatted for WordPress.",
            "Target: 600-900 words",
            "",
        ])
        
        return "\n".join(prompt)
    def _generate_with_gemini(
        self,
        content_type: str,
        title: str,
        details: Dict[str, Any],
        research: Dict[str, Any],
        config: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if not self.model:
            return None

        summary, bullets, sources = self._normalize_research(research)
        prompt = self._build_prompt(content_type, title, summary, bullets, details, sources)

        generation_config = {
            "temperature": config.get("temperature", self.temperature) if config else self.temperature,
            "top_p": 0.9,
            "top_k": 50,
            "max_output_tokens": 8192,  # Increased to allow full article completion
        }

        attempts = len(self.model_names)
        for attempt in range(attempts):
            try:
                logger.info(f"   📡 Sending prompt to Gemini (attempt {attempt + 1}/{attempts})...")
                response = self.model.generate_content(prompt, generation_config=generation_config)
                if response and getattr(response, "text", None):
                    logger.info(f"   ✅ Gemini generated {len(response.text)} characters successfully")
                    return response.text
                raise ValueError("Empty Gemini response")
            except Exception as exc:
                logger.warning(f"   ❌ Gemini generation failed (attempt {attempt + 1}): {exc}")
                if not self._switch_fallback():
                    break
        logger.error("   ❌ All Gemini attempts exhausted, returning None for template fallback")
        return None

    def generate(
        self,
        content_type: str,
        title: str,
        details: Dict[str, Any],
        research: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive SEO-optimized HTML article using Gemini, falling back to template."""
        logger.info(f"🎯 Starting article generation for: {title[:60]}")
        logger.info(f"   Model available: {'✅ Gemini' if self.model else '❌ Template fallback'}")
        if self.model:
            logger.info(f"   Using model: {self.model_names[self.model_index]}")
        
        article_config = config or {}
        publish_status = article_config.get("publish_status", "draft")
        article_length = article_config.get("article_length", "medium")

        summary, key_points, sources = self._normalize_research(research)

        # Extract data with proper type handling
        important_dates_raw = details.get("important_dates") or {}
        important_dates = important_dates_raw if isinstance(important_dates_raw, dict) else {}
        eligibility = self._extract_text(details.get("eligibility")) or "Not specified"
        how_to_apply = self._extract_text(details.get("how_to_apply")) or "Refer to official instructions"
        important_links = self._normalize_links(details.get("important_links") or [])
        key_details_raw = details.get("key_details") or {}
        key_details = key_details_raw if isinstance(key_details_raw, dict) else {}
        if key_details:
            key_details = {k: self._extract_text(v) for k, v in key_details.items()}

        # Attempt Gemini generation first
        logger.info("🤖 Attempting Gemini generation...")
        html_content = self._generate_with_gemini(content_type, title, details, research, article_config)

        if not html_content:
            logger.warning("⚠️  Gemini generation returned empty, using template fallback")
            # Fallback: structured template
            sections: List[str] = []
            sections.append(f"<h1>{title}</h1>")
            sections.append(
                "<p style=\"background-color: #f0f0f0; padding: 10px; border-left: 4px solid #ff9800; margin: 10px 0; display: none;\">"
            )
            sections.append(f"<strong>Content Type:</strong> {content_type} | ")
            sections.append(f"<strong>Status:</strong> {publish_status} | ")
            sections.append(f"<strong>Length:</strong> {article_length}")
            sections.append("</p>")
            sections.append("<h2>Overview</h2>")
            sections.append(f"<p>{summary or details.get('full_description') or 'No summary available'}</p>")
            if key_points:
                sections.append("<h2>Key Highlights</h2>")
                sections.append("<ul>")
                for point in key_points:
                    sections.append(f"<li>{point}</li>")
                sections.append("</ul>")
            if important_dates:
                sections.append("<h2>Important Dates</h2>")
                sections.append(
                    "<table style=\"width: 100%; border-collapse: collapse; margin: 15px 0;\">"
                )
                sections.append(
                    "<thead><tr style=\"background-color: #f5f5f5;\"><th style=\"border: 1px solid #ddd; padding: 10px; text-align: left;\">Event</th><th style=\"border: 1px solid #ddd; padding: 10px; text-align: left;\">Date</th></tr></thead>"
                )
                sections.append("<tbody>")
                for label, date_val in important_dates.items():
                    sections.append(
                        f"<tr><td style=\"border: 1px solid #ddd; padding: 10px;\">{label}</td><td style=\"border: 1px solid #ddd; padding: 10px;\">{date_val}</td></tr>"
                    )
                sections.append("</tbody>")
                sections.append("</table>")
            sections.append("<h2>Eligibility Criteria</h2>")
            sections.append(f"<p>{eligibility}</p>")
            sections.append("<h2>Application Process</h2>")
            sections.append(f"<p>{how_to_apply}</p>")
            if key_details:
                sections.append("<h2>Key Details</h2>")
                sections.append("<ul>")
                for label, val in key_details.items():
                    sections.append(f"<li><strong>{label}:</strong> {val}</li>")
                sections.append("</ul>")
            if important_links:
                sections.append("<h2>Important Links & Resources</h2>")
                sections.append("<ul>")
                for label, url in important_links:
                    sections.append(
                        f"<li><a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{label}</a></li>"
                    )
                sections.append("</ul>")
            sections.append("<h2>Frequently Asked Questions</h2>")
            sections.append("<p><strong>Q: How do I apply?</strong><br/>")
            sections.append(f"A: {how_to_apply}</p>")
            sections.append("<p><strong>Q: What are the eligibility requirements?</strong><br/>")
            sections.append(f"A: {eligibility}</p>")
            sections.append(
                "<p style=\"background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0;\">"
            )
            sections.append(
                "<strong>📢 Don't miss out!</strong> Make sure to apply before the deadline. For more details, visit the official website using the links provided above."
            )
            sections.append("</p>")
            html_content = "\n".join(sections)
            logger.info(f"   📝 Template fallback generated {len(html_content)} characters")
        else:
            logger.info(f"   ✅ Using Gemini-generated content ({len(html_content)} characters)")

        keywords = self._derive_keywords(title, key_points, key_details)
        meta = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model": self.model_names[self.model_index] if self.model else "template",
            "temperature": self.temperature,
            "keywords": keywords,
            "type": content_type,
            "status": publish_status,
            "sources": sources,
        }

        return {
            "title": title,
            "content": html_content,
            "meta": meta,
            "summary": summary,
            "keywords": keywords,
        }

    @staticmethod
    def _derive_keywords(title: str, key_points: List[str], key_details: Dict[str, Any]) -> List[str]:
        """Extract SEO keywords from title, key points, and details."""
        keywords = []
        
        # Keywords from title (first 5 words)
        if title:
            keywords.extend(title.split()[:5])
        
        # Keywords from key points
        if key_points:
            keywords.extend([kp.split()[0] for kp in key_points if kp])
        
        # Keywords from key details
        if key_details:
            keywords.extend(list(key_details.keys())[:5])
        
        # Deduplicate while preserving order and removing common words
        seen = set()
        ordered = []
        common_words = {'the', 'a', 'an', 'and', 'or', 'is', 'of', 'to', 'for'}
        
        for kw in keywords:
            kw_lower = kw.lower().rstrip('s.,')  # Normalize keyword
            if kw_lower not in seen and kw_lower not in common_words and len(kw_lower) > 2:
                seen.add(kw_lower)
                ordered.append(kw)
        
        return ordered[:10]


class JobArticlePipeline:
    """Pipeline orchestrating details fetch, research collection, and article generation.
    
    Process:
    1. Fetch item details from external API (job details, exam results, etc.)
    2. Collect AI research from Perplexity (background information, recent updates)
    3. Generate comprehensive article with Gemini using both contexts
    4. Prepare for internal linking and WordPress publishing
    """

    def __init__(self, perplexity_client: Optional[PerplexityResearchCollector] = None, gemini_client: Optional[GeminiArticleGenerator] = None):
        self.perplexity_client = perplexity_client
        self.gemini_client = gemini_client or GeminiArticleGenerator()
        self.logger = logging.getLogger(__name__)

    def collect_research(self, title: str, content_type: str) -> Dict[str, Any]:
        """Collect AI research from Perplexity for additional context.
        
        This provides:
        - Current information about the job/exam/organization
        - Recent news and updates
        - Expert insights
        - Industry context
        """
        if not self.perplexity_client:
            self.logger.warning("Perplexity client not available, skipping research collection")
            return {"summary": None, "bullets": []}
        
        try:
            if content_type == "jobs":
                return self.perplexity_client.collect_research_for_job(title)
            elif content_type == "results":
                return self.perplexity_client.collect_research_for_result(title)
            elif content_type == "admit_cards":
                return self.perplexity_client.collect_research_for_admit_card(title)
        except Exception as exc:
            self.logger.warning(f"Research collection failed: {exc}")
        
        return {"summary": None, "bullets": []}

    def generate_article(self, item: Dict[str, Any], details: Dict[str, Any], content_type: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive article using:
        - Item data (title, basic info)
        - API details (eligibility, dates, links)
        - Gemini generation (structure, formatting, SEO)
        
        Note: Perplexity research is currently disabled to use only API details.
        """
        title = item.get("title") or details.get("title") or "Untitled"
        
        self.logger.info(f"Generating article for: {title}")
        
        # COMMENTED OUT: Perplexity research - using only API details now
        # research = self.collect_research(title, content_type)
        # self.logger.info(f"Research collected - summary present: {bool(research.get('summary'))}, points: {len(research.get('bullets', []))}")
        
        # Create empty research object
        research = {
            'summary': '',
            'bullets': [],
            'sources': []
        }
        
        self.logger.info(f"Using only API details (Perplexity research disabled)")
        
        # Generate article using API details only
        article = self.gemini_client.generate(
            content_type=content_type,
            title=title,
            details=details or {},
            research=research,
            config=config
        )
        
        self.logger.info(f"Article generated - length: {len(article.get('content', ''))} chars, keywords: {len(article.get('keywords', []))}")
        
        return {
            "title": article.get("title", title),
            "content": article.get("content", ""),
            "meta": article.get("meta", {}),
            "summary": article.get("summary"),
            "keywords": article.get("keywords", []),
            "research": research,
        }
