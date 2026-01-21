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
import re
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
            "gemini-2.5-flash",           # Primary model (fast, high quality)
            "gemini-3-flash-preview",     # Fallback 1 (latest preview, 20 RPD available)
            "gemini-2.5-flash-lite",      # Fallback 2 (lighter version, 20 RPD available)
            "gemini-2.0-flash-lite"       # Fallback 3 (stable lite version)
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
        site_url: Optional[str] = None,
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
        
        # Filter links - remove social media/promotional links, keep only official links
        filtered_links = []
        skip_keywords = ['whatsapp', 'telegram', 'twitter', 'facebook', 'instagram', 'youtube', 'social', 'join', 'group', 'channel', 'download', 'app']
        keep_keywords = ['apply', 'official', 'website', 'notification', 'portal', 'admit', 'result', 'syllabus', 'exam']
        
        for label, url in important_links:
            # Skip social media and promotional links
            if any(skip in label.lower() for skip in skip_keywords):
                continue
            # Prefer official links, otherwise check if URL contains domain info
            if any(keep in label.lower() for keep in keep_keywords) or 'gov' in url.lower() or 'official' in label.lower():
                filtered_links.append((label, url))
        
        # Limit to maximum 3 external links (only official ones)
        filtered_links = filtered_links[:3]
        
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
            "✓ Start IMMEDIATELY with key facts - no conversational greetings",
            "✓ No marketing language or robotic phrases",
            "✓ Use ONLY the information provided below",
            "✓ Organize with proper HTML headings and formatting",
            "✓ Include ONLY dofollow links (all links are official - use them as is)",
            "✓ Use MAXIMUM 3 external links only - each link must appear ONLY ONCE",
            "✓ Embed links naturally in the text flow - do NOT create a separate links section",
            "✓ Only include official links (apply portal, notification, official website, etc.)",
            "",
            "FORBIDDEN OPENING PHRASES (NEVER start with these):",
            "✗ 'Hey there! If you're looking for...'",
            "✗ 'Are you interested in...'",
            "✗ 'Looking for job opportunities?'",
            "✗ 'Great news for job seekers!'",
            "✗ 'Attention candidates!'",
            "✗ Any greeting or conversational opener",
            "",
            "INSTEAD, START DIRECTLY WITH:",
            "✓ '[Organization name] has announced [number] openings for [position]...'",
            "✓ 'Applications for [position] at [organization] open on [date]...'",
            "✓ '[Exam/Result name] will be conducted on [date]...'",
            "✓ State the main facts immediately in the first sentence",
            "",
            "OTHER FORBIDDEN PHRASES:",
            "✗ 'This represents a golden opportunity'",
            "✗ 'Significant recruitment drive' (just say what it is)",
            "✗ 'Understanding this...' or 'Candidates should know...'",
            "✗ Flowery descriptions or motivational language",
            "✗ Phrases like 'is sure to', 'can help you', 'best chance'",
            "",
            "HTML FORMATTING - MANDATORY:",
            "- Use <h2> for section headings",
            "- Use <h3> for subsections",
            "- Use <strong> for bold text (numbers, dates, amounts): <strong>₹500</strong>, <strong>32,679</strong>, <strong>Jan 30</strong>",
            "- STRICTLY FORBIDDEN: Do NOT use markdown bold syntax (**text**). It breaks the layout.",
            "- ALWAYS use HTML tags: <strong>text</strong> for bold.",
            "- Use <p> for paragraphs (keep them short - 2-3 sentences max)",
            "- Use <ul><li> for bullet point lists",
            "- Use <ol><li> for numbered steps (like application process)",
            "- Use <table> for all data with proper <thead>, <tbody>, <tr>, <td> structure",
            "- Use <a href=\"URL\" target=\"_blank\" rel=\"dofollow\"> for ALL links - embed them naturally in text",
            "",
            "CRITICAL LINK INSTRUCTIONS:",
            "- You have MAXIMUM 3 official links to use (already filtered)",
            "- Embed each link ONLY ONCE in the natural flow of the article",
            "- Use rel=\"dofollow\" attribute for all links",
            "- Never repeat the same link multiple times",
            "- Embed links in context: 'You can <a href=\"URL\">apply on the official website</a>'",
            "- Do NOT create a separate 'Important Links' section",
            "- Do NOT list links at the end",
            "- If you don't need all 3 links, that's fine - only use links that fit naturally",
            "",
            "FORMATTING EXAMPLES:",
            "✓ CORRECT: The BCECEB has announced <strong>1445</strong> openings for Junior Resident positions.",
            "✓ CORRECT: Applications started on <strong>January 16, 2026</strong>, and the last date is <strong>February 06, 2026</strong>.",
            "✓ CORRECT LINK: You can <a href=\"https://example.com/apply\" target=\"_blank\" rel=\"dofollow\">apply online on the official portal</a>.",
            "✗ WRONG: The BCECEB has announced **1445** openings (DO NOT USE ** for bold)",
            "✗ WRONG: Applications started on **January 16, 2026** (ONLY use <strong> tags)",
            "✗ WRONG LINK: <a href=\"URL\" target=\"_blank\"> (ALWAYS add rel=\"dofollow\")",
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
            "IMPORTANT - DO NOT REPEAT THE TITLE:",
            "- The title will be handled separately by WordPress as the post heading",
            "- Do NOT include <h1> tag or repeat the title text in the article body",
            "- Start DIRECTLY with the main content using <h2> for first section if needed",
            "",
            "CRITICAL REMINDERS ABOUT LINKS:",
            "- You have MAXIMUM 3 official links available",
            "- EACH LINK MUST APPEAR ONLY ONCE in the entire article",
            "- Embed links NATURALLY in the text, not as a list",
            "- Use rel=\"dofollow\" attribute for one link only and for other no follow link",
            "- Example: 'Candidates can <a href=\"URL\" target=\"_blank\" rel=\"dofollow\">apply online here</a>.'",
            "- DO NOT create a separate 'Important Links' or 'Links' section",
            "- DO NOT list links at the bottom or anywhere else",
            "- If a link doesn't fit naturally, skip it - don't force it",
            "- A clear opening paragraph that immediately states the key facts",
            "- DO NOT use conversational phrases like 'Hey there!', 'If you're looking for', 'Are you interested in', etc.",
            "- Get straight to the point with factual information",
            "- Example: 'The Bihar Combined Entrance Competitive Examination Board (BCECEB) has announced [number] openings for Junior Resident positions. Applications open on [date]...'",
            "",
            "Then continue with clear, organized sections using proper HTML tags:",
            "- Use <h2> for major section headings",
            "- Use <h3> for subsections",
            "- Use <p> for paragraphs, <ul>/<ol> for lists, <table> for data",
            "Make it informative, easy to read, and properly formatted for WordPress.",
            "Target: 600-900 words",
            "",
        ])
        
        # Add closing message instruction if site_url is provided
        if site_url:
            prompt.extend([
                "IMPORTANT - END YOUR ARTICLE WITH THIS:",
                f"Add a final highlighted paragraph encouraging readers to bookmark {site_url} and visit regularly for more job updates, admit cards, and results.",
                "Format it as: <p style=\"background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0;\"><strong>📢 Stay Updated!</strong> [Natural closing message mentioning {site_url}]</p>",
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
        site_url: Optional[str] = None,
    ) -> Optional[str]:
        if not self.model:
            return None

        summary, bullets, sources = self._normalize_research(research)
        prompt = self._build_prompt(content_type, title, summary, bullets, details, sources, site_url)

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
                    content = response.text
                    # Forced fix: Replace markdown bold (**text**) with HTML strong tags (<strong>text</strong>)
                    # This handles edge cases where the LLM ignores the prompt instructions
                    content_fixed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content, flags=re.DOTALL)
                    if content_fixed != content:
                        logger.info("   🔧 Fixed Markdown bold syntax in generated content")
                    return content_fixed
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
        
        # Extract site_url from config profiles
        site_url = None
        profiles = article_config.get("profiles", [])
        if profiles and len(profiles) > 0:
            site_url = profiles[0].get("site_url")
        logger.info(f"   Publishing site: {site_url or 'Not specified'}")

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
        html_content = self._generate_with_gemini(content_type, title, details, research, article_config, site_url)

        if not html_content:
            logger.warning("⚠️  Gemini generation returned empty, using template fallback")
            # Fallback: structured template (no <h1> as title is handled separately)
            sections: List[str] = []
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
            if site_url:
                sections.append(
                    f"<strong>📢 Don't miss out!</strong> Bookmark <a href=\"{site_url}\" target=\"_blank\">{site_url}</a> and visit regularly for the latest job updates, admit cards, and results."
                )
            else:
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
    def _generate_seo_slug(title: str, content_type: str, details: Dict[str, Any]) -> str:
        """
        Generate SEO-optimized slug for URL (maximum 75 characters).
        
        Focus on main information only:
        - Job name and position
        - Admit card and exam name
        - Result and organization
        
        Args:
            title: Article title
            content_type: Type (jobs, admit_cards, results)
            details: Dictionary with additional details
            
        Returns:
            SEO slug (max 75 characters, lowercase, hyphenated)
        """
        import re
        
        # Helper to clean and slugify text
        def slugify(text):
            # Convert to lowercase
            text = text.lower()
            # Remove special characters except spaces and hyphens
            text = re.sub(r'[^\w\s-]', '', text)
            # Replace spaces with hyphens
            text = re.sub(r'[\s_]+', '-', text)
            # Remove multiple hyphens
            text = re.sub(r'-+', '-', text)
            return text.strip('-')
        
        # Remove common suffixes and redundant words
        clean_title = title
        for suffix in [" – Out", " - Out", " Out", " (Out)",
                      " – Apply Online", " - Apply Online", " Apply Online",
                      " – Apply Now", " - Apply Now", " Apply Now",
                      " – Apply", " - Apply", " Apply",
                      " – Download", " - Download", " Download",
                      " – Check Result", " - Check Result",
                      " – Start", " - Start", " Start",
                      " Recruitment", " 2026", " 2025", " 2027",
                      " Online Form", " Online", " Form"]:
            clean_title = clean_title.replace(suffix, "")
        
        # Further reduce verbosity - remove common words that don't add SEO value
        clean_title = clean_title.replace(" Enforcement", "")
        clean_title = clean_title.replace(" Level 1", "")
        clean_title = clean_title.replace(" Date", "")
        clean_title = clean_title.replace(" Card", "")
        clean_title = clean_title.replace(" Now", "")
        
        # Remove extra spaces caused by removals
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # Add content type indicator
        if content_type == "jobs":
            type_suffix = "recruitment"
        elif content_type == "admit_cards":
            type_suffix = "admit-card"
        elif content_type == "results":
            type_suffix = "result"
        else:
            type_suffix = ""
        
        # Build slug
        base_slug = slugify(clean_title)
        
        # Add type suffix if not already present
        if type_suffix and type_suffix not in base_slug:
            slug = f"{base_slug}-{type_suffix}"
        else:
            slug = base_slug
        
        # Add year if not present (important for SEO and uniqueness)
        if "2026" not in slug and "2026" in title:
            slug = f"{slug}-2026"
        
        # Trim to target length (max 75 characters)
        if len(slug) > 75:
            # Try to cut at last hyphen before 75 chars
            truncate_at = slug[:75].rfind('-')
            if truncate_at > 40:  # Ensure we keep meaningful content
                slug = slug[:truncate_at]
            else:
                slug = slug[:75].rstrip('-')
        
        return slug

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

    @staticmethod
    def _enhance_headline(original_title: str, content_type: str, details: Dict[str, Any]) -> str:
        """
        Create SEO-optimized headline with dynamic details based on content type.
        
        SEO Optimizations:
        - Keeps length under 60 characters for full Google display
        - Uses power words (Out, Live, Latest) for higher CTR
        - Front-loads important keywords
        - Includes specific dates and numbers
        - Adds compelling call-to-action
        
        Args:
            original_title: Original scraped title from sarkariresult
            content_type: Type of content (jobs, results, admit_cards)
            details: Dictionary containing important dates, eligibility, etc.
            
        Returns:
            SEO-optimized headline (50-60 characters ideal)
        """
        # Extract key information from details
        important_dates = details.get("important_dates", {})
        key_details = details.get("key_details", {})
        
        # Helper function to extract text from various formats
        def extract_text(value):
            if isinstance(value, dict) and "raw" in value:
                return value.get("raw") or ""
            return str(value) if value else ""
        
        # Helper to shorten date format (e.g., "31 January 2026" -> "Jan 31")
        def shorten_date(date_str):
            if not date_str:
                return ""
            # Extract date components
            import re
            # Match patterns like "31 January 2026", "31-01-2026", "2026-01-31"
            months_map = {
                'january': 'Jan', 'february': 'Feb', 'march': 'Mar', 'april': 'Apr',
                'may': 'May', 'june': 'Jun', 'july': 'Jul', 'august': 'Aug',
                'september': 'Sep', 'october': 'Oct', 'november': 'Nov', 'december': 'Dec'
            }
            
            date_lower = date_str.lower().strip()
            for full_month, short_month in months_map.items():
                if full_month in date_lower:
                    # Extract day
                    day_match = re.search(r'\b(\d{1,2})\b', date_str)
                    if day_match:
                        return f"{short_month} {day_match.group(1)}"
                    return short_month
            
            # If no month name, try to extract just day and month from numeric format
            date_match = re.search(r'(\d{1,2})[-/](\d{1,2})', date_str)
            if date_match:
                return f"{date_match.group(1)}/{date_match.group(2)}"
            
            return date_str[:10]  # Fallback: just take first 10 chars
        
        # Extract clean title base (remove year, recruitment, etc. for brevity)
        def extract_core_title(title):
            # Remove common suffixes and year
            clean = title
            for suffix in [" – Out", " - Out", " Out", " (Out)", 
                          " – Apply Online", " - Apply Online", " Apply Online",
                          " – Apply", " - Apply", " Apply",
                          " Recruitment", " 2026", " 2025", " 2027"]:
                clean = clean.replace(suffix, "")
            
            # Further shorten if still too long
            # Remove verbose words
            clean = clean.replace(" Enforcement", "")
            clean = clean.replace(" Date", "")
            clean = clean.replace(" Level 1", "")
            
            return clean.strip()
        
        core_title = extract_core_title(original_title)
        
        # Build SEO-optimized headline based on content type
        if content_type == "jobs":
            # For jobs: [Org/Post]: [Vacancy], Apply by [Date]
            # Target: "UP Police 2026: 5000 Posts, Apply by Jan 31"
            
            vacancy_info = None
            for key in ["Total Posts", "Vacancies", "Posts", "total_posts", "vacancies", "Total Vacancy"]:
                if key in key_details:
                    vacancy_info = extract_text(key_details[key])
                    break
            
            last_date = None
            for key in ["Last Date", "Application End Date", "Closing Date", "last_date", "Last Date to Apply"]:
                if key in important_dates:
                    last_date = extract_text(important_dates[key])
                    break
            
            # Build parts
            parts = []
            
            # Add vacancy if available
            if vacancy_info:
                # Clean vacancy number (remove commas for brevity if needed)
                vacancy_clean = vacancy_info.strip().replace(',', '')
                parts.append(f"{vacancy_clean} Posts")
            
            # Add last date if available
            if last_date:
                short_date = shorten_date(last_date)
                parts.append(f"Apply by {short_date}")
            elif not parts:
                # Fallback: add generic CTA
                parts.append("Apply Now")
            
            # Construct headline: ensure 2026 is in title
            if "2026" not in core_title and "2026" in original_title:
                core_title += " 2026"
            
            if parts:
                # Vary punctuation for natural look
                if len(parts) == 1:
                    # Single part - use dash for simplicity
                    headline = f"{core_title} - {parts[0]}"
                else:
                    # Multiple parts - use colon with comma separator
                    headline = f"{core_title}: {', '.join(parts)}"
            else:
                headline = f"{core_title} - Apply Online"
            
            return headline
        
        elif content_type == "admit_cards":
            # For admit cards: [Org] Admit Card Out: Exam [Date] - Download
            # Target: "SSC CGL Admit Card Out: Exam Jan 25 - Download"
            
            exam_date = None
            for key in ["Exam Date", "Test Date", "exam_date", "Admit Card Available"]:
                if key in important_dates:
                    exam_date = extract_text(important_dates[key])
                    break
            
            # Add power word "Out" if not already present
            status = "Out" if "out" not in core_title.lower() else ""
            
            # Construct headline with varied punctuation
            if exam_date:
                short_date = shorten_date(exam_date)
                if status:
                    headline = f"{core_title} {status} - Exam {short_date}, Download"
                else:
                    headline = f"{core_title} - Exam {short_date}, Download"
                
                # If still too long, remove "Download" and use shorter format
                if len(headline) > 60:
                    if status:
                        headline = f"{core_title} {status} - Exam on {short_date}"
                    else:
                        headline = f"{core_title} - Exam {short_date}"
            else:
                # Fallback
                if status:
                    headline = f"{core_title} {status} - Download Link"
                else:
                    headline = f"{core_title} - Download Active"
            
            return headline
        
        elif content_type == "results":
            # For results: [Org] Result Out: Check Score & Cut-off
            # Target: "RRB Group D Result Out: Check Score & Cut-off"
            
            result_date = None
            for key in ["Result Date", "Declaration Date", "result_date", "Result Declared"]:
                if key in important_dates:
                    result_date = extract_text(important_dates[key])
                    break
            
            # Add power word "Out" or "Declared"
            status = ""
            if "out" not in core_title.lower() and "declared" not in core_title.lower():
                status = "Out"
            
            if result_date:
                short_date = shorten_date(result_date)
                if status:
                    headline = f"{core_title} {status} - Declared {short_date}"
                else:
                    headline = f"{core_title} - Check Score & Cut-off"
            else:
                # Fallback - emphasize checking
                if status:
                    headline = f"{core_title} {status} - Check Score & Cut-off"
                else:
                    headline = f"{core_title} - Direct Link to Check Marks"
            
            return headline
        
        # Fallback: return original if content type not recognized
        return original_title


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
        # Get original title from item or details
        original_title = item.get("title") or details.get("title") or "Untitled"
        
        # Enhance the headline with dynamic information
        enhanced_title = self.gemini_client._enhance_headline(
            original_title=original_title,
            content_type=content_type,
            details=details
        )
        
        self.logger.info(f"Generating article for: {enhanced_title}")
        self.logger.info(f"Original title: {original_title}")
        
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
        
        # Generate article using API details and enhanced title
        article = self.gemini_client.generate(
            content_type=content_type,
            title=enhanced_title,  # Use enhanced title
            details=details or {},
            research=research,
            config=config
        )
        
        # Generate SEO-optimized slug
        seo_slug = self.gemini_client._generate_seo_slug(
            title=enhanced_title,
            content_type=content_type,
            details=details
        )
        
        self.logger.info(f"Article generated - length: {len(article.get('content', ''))} chars, keywords: {len(article.get('keywords', []))}")
        self.logger.info(f"✅ SEO SLUG GENERATED: '{seo_slug}' ({len(seo_slug)} chars)")
        self.logger.info(f"   Enhanced title: '{enhanced_title}'")
        
        return {
            "title": article.get("title", enhanced_title),  # Use enhanced title as fallback
            "slug": seo_slug,  # Add SEO-optimized slug
            "content": article.get("content", ""),
            "meta": article.get("meta", {}),
            "summary": article.get("summary"),
            "keywords": article.get("keywords", []),
            "research": research,
        }
