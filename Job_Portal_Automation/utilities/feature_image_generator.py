"""
Feature Image Generator for Job Portal Automation
==================================================

Generates professional feature images with:
- Job title overlay
- Website branding/watermark
- Category-specific color schemes
- Multiple design templates
- High-quality output for WordPress

Supports:
- Jobs (Blue theme)
- Results (Green theme)
- Admit Cards (Orange theme)
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL/Pillow not installed. Run: pip install Pillow")

logger = logging.getLogger(__name__)


class FeatureImageGenerator:
    """
    Generate branded feature images for job portal articles.
    
    Features:
    - Dynamic text rendering with word wrapping
    - Category-specific color themes
    - Website watermark/branding
    - Multiple design templates
    - Gradient backgrounds
    - Professional typography
    """
    
    # Standard WordPress featured image size
    DEFAULT_SIZE = (1200, 628)
    
    # Professional color schemes with gradients and glow effects
    COLOR_SCHEMES = {
        'jobs': {
            'bg_start': '#E0F2FE',         # Light blue
            'bg_end': '#BFDBFE',           # Slightly darker blue
            'primary': '#1E40AF',          # Dark blue
            'secondary': '#3B82F6',        # Medium blue  
            'accent': '#10B981',           # Green accent
            'glow': '#60A5FA',             # Blue glow
            'text': '#1F2937',             # Dark grey text
            'highlight': '#3B82F6'         # Highlight color
        },
        'results': {
            'bg_start': '#D1FAE5',         # Light green
            'bg_end': '#A7F3D0',           # Slightly darker green
            'primary': '#059669',          # Dark green
            'secondary': '#10B981',        # Medium green
            'accent': '#1E40AF',           # Blue accent
            'glow': '#34D399',             # Green glow
            'text': '#1F2937',             # Dark grey text
            'highlight': '#10B981'         # Highlight color
        },
        'admit_cards': {
            'bg_start': '#FEF3C7',         # Light yellow
            'bg_end': '#FDE68A',           # Orange-yellow
            'primary': '#D97706',          # Dark orange
            'secondary': '#F59E0B',        # Orange
            'accent': '#1E40AF',           # Blue accent
            'glow': '#FBBF24',             # Yellow glow
            'text': '#1F2937',             # Dark grey text
            'highlight': '#F59E0B'         # Highlight color
        }
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize feature image generator.
        
        Args:
            output_dir: Directory to save generated images (default: generated_data/feature_images/)
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow is required. Install with: pip install Pillow")
        
        self.output_dir = output_dir or Path(__file__).parent.parent / "generated_data" / "feature_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ Feature Image Generator initialized")
        logger.info(f"   Output directory: {self.output_dir}")
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _create_gradient_background(self, size: Tuple[int, int], 
                                   color1: str, color2: str, 
                                   direction: str = 'diagonal') -> Image.Image:
        """
        Create a gradient background with various directions.
        
        Args:
            size: Image size (width, height)
            color1: Start color (hex)
            color2: End color (hex)
            direction: Gradient direction ('vertical', 'horizontal', 'diagonal')
            
        Returns:
            PIL Image with gradient background
        """
        base = Image.new('RGB', size, color1)
        top = Image.new('RGB', size, color2)
        mask = Image.new('L', size)
        mask_data = []
        
        width, height = size
        
        # Create gradient mask based on direction
        if direction == 'horizontal':
            for y in range(height):
                for x in range(width):
                    mask_data.append(int(255 * (x / width)))
        elif direction == 'vertical':
            for y in range(height):
                mask_data.extend([int(255 * (y / height))] * width)
        elif direction == 'diagonal':
            for y in range(height):
                for x in range(width):
                    # Diagonal gradient from top-left to bottom-right
                    progress = (x / width + y / height) / 2
                    mask_data.append(int(255 * progress))
        else:  # radial
            center_x, center_y = width // 2, height // 2
            max_dist = ((width/2)**2 + (height/2)**2)**0.5
            for y in range(height):
                for x in range(width):
                    dist = ((x - center_x)**2 + (y - center_y)**2)**0.5
                    mask_data.append(int(255 * min(dist / max_dist, 1.0)))
        
        mask.putdata(mask_data)
        
        # Composite with gradient
        base.paste(top, (0, 0), mask)
        return base
    
    def _add_geometric_patterns(self, image: Image.Image, colors: Dict) -> Image.Image:
        """Add subtle geometric patterns for visual interest."""
        width, height = image.size
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Add semi-transparent circles in corners
        accent_color = self._hex_to_rgb(colors['accent'])
        
        # Top-right circle
        draw.ellipse([width - 300, -150, width + 150, 300], 
                    fill=(*accent_color, 20))
        
        # Bottom-left circle
        draw.ellipse([-150, height - 300, 300, height + 150], 
                    fill=(*accent_color, 15))
        
        # Add diagonal lines pattern
        for i in range(0, width + height, 100):
            draw.line([(i, 0), (i - height, height)], 
                     fill=(*accent_color, 10), width=2)
        
        # Composite overlay
        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        return image
    
    def _draw_rounded_rectangle(self, draw: ImageDraw.ImageDraw, 
                               coords: list, radius: int, fill: tuple):
        """Draw a rounded rectangle with smoother corners."""
        x1, y1, x2, y2 = coords
        
        # Draw rounded rectangle using circles and rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        
        # Draw four corner circles
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """
        Get Poppins/Inter/Montserrat font with fallback.
        
        Args:
            size: Font size
            bold: Use bold font
            
        Returns:
            PIL Font object
        """
        # Try to use recommended fonts: Poppins, Inter, Montserrat
        font_paths = [
            # Poppins (preferred)
            "C:/Windows/Fonts/Poppins-Bold.ttf" if bold else "C:/Windows/Fonts/Poppins-Regular.ttf",
            "C:/Windows/Fonts/Poppins-SemiBold.ttf" if bold else "C:/Windows/Fonts/Poppins-Regular.ttf",
            # Arial Black / Arial (fallback)
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/ariblk.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            # Verdana
            "C:/Windows/Fonts/verdanab.ttf" if bold else "C:/Windows/Fonts/verdana.ttf",
            # Linux fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except Exception:
                continue
        
        # Fallback to default font
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()
    
    def _extract_key_info(self, title: str, content_type: str) -> Dict[str, str]:
        """
        Extract key information with actual stats for image text.
        
        Jobs: top=exam name+year, center=vacancy count, bottom=apply online
        Results: top=exam name+result+year, center=merit list pdf, bottom=check marks  
        Admit Cards: top=exam name+admit card+year, center=(empty), bottom=download now
        """
        import re
        
        title = title.strip()
        
        # Extract vacancy numbers
        vacancy_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(?:Posts?|Vacancies|Vacancy)', title, re.IGNORECASE)
        vacancy_num = vacancy_match.group(1) if vacancy_match else None
        
        # Extract year
        year_match = re.search(r'\b(20\d{2})\b', title)
        year = year_match.group(1) if year_match else "2026"
        
        if content_type == 'jobs':
            # Extract exam/position name WITH year for top banner
            exam_name = title
            # Remove vacancy count and extra text
            exam_name = re.sub(r'-?\s*\d{1,3}(?:,\d{3})*\s*(?:Posts?|Vacancies|Vacancy).*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'Recruitment|Notification', '', exam_name, flags=re.IGNORECASE)
            exam_name = exam_name.strip(' -.,').strip()
            
            # Limit to 6-7 words max for top
            words = exam_name.split()
            if len(words) > 7:
                exam_name = ' '.join(words[:7])
            
            # Ensure year is in headline
            if year not in exam_name:
                exam_name = f"{exam_name} {year}"
            
            # Center: ONLY vacancy count
            if vacancy_num:
                center_text = f"{vacancy_num} Vacancies"
            else:
                center_text = "Multiple Posts"
            
            return {
                'top': exam_name,
                'center': center_text,
                'bottom': 'Apply Online'
            }
            
        elif content_type == 'admit_cards':
            # Extract exam name + Admit Card + year for top banner
            exam_name = title
            # Remove download/hall ticket text
            exam_name = re.sub(r'-?\s*Download.*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'-?\s*Hall Ticket.*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = exam_name.strip(' -.,').strip()
            
            # Limit words
            words = exam_name.split()
            if len(words) > 6:
                exam_name = ' '.join(words[:6])
            
            # Ensure year is included
            if year not in exam_name:
                exam_name = f"{exam_name} {year}"
            
            # Simple: headline at top, button at bottom, released in middle
            return {
                'top': exam_name,
                'center': 'Released',  # Add released text for admit cards
                'bottom': 'Download Now'
            }
            
        elif content_type == 'results':
            # Extract exam name + Result + year for top banner
            exam_name = title
            # Remove extra text but keep Result
            exam_name = re.sub(r'-?\s*(?:Check|Download|PDF).*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'-?\s*Marks.*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'-?\s*Cut Off.*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = exam_name.strip(' -&.,').strip()
            
            # Limit words
            words = exam_name.split()
            if len(words) > 6:
                exam_name = ' '.join(words[:6])
            
            # Ensure year is included
            if year not in exam_name:
                exam_name = f"{exam_name} {year}"
            
            return {
                'top': exam_name,
                'center': 'Merit List PDF',  # Fixed text for results
                'bottom': 'Check Marks'
            }
        
        # Fallback
        return {
            'top': title[:40],
            'center': 'View Details',
            'bottom': 'Click Here'
        }
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, 
                   max_width: int) -> list:
        """
        Wrap text to fit within max width.
        
        Args:
            text: Text to wrap
            font: Font to use
            max_width: Maximum width in pixels
            
        Returns:
            List of wrapped text lines
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _add_text_with_shadow(self, draw: ImageDraw.ImageDraw, 
                             position: Tuple[int, int], text: str,
                             font: ImageFont.FreeTypeFont, 
                             fill: str, shadow_offset: int = 3):
        """
        Draw text with shadow effect.
        
        Args:
            draw: ImageDraw object
            position: (x, y) position
            text: Text to draw
            font: Font to use
            fill: Text color
            shadow_offset: Shadow offset in pixels
        """
        x, y = position
        # Draw shadow
        draw.text((x + shadow_offset, y + shadow_offset), text, 
                 font=font, fill='#000000')
        # Draw text
        draw.text((x, y), text, font=font, fill=fill)
    
    def generate(self, 
                title: str,
                content_type: str = 'jobs',
                site_name: str = 'Job Portal',
                site_url: str = '',
                template: str = 'professional') -> Path:
        """
        Generate professional CTR-optimized feature image.
        
        Args:
            title: Article title
            content_type: Type of content (jobs, results, admit_cards)
            site_name: Website name for watermark
            site_url: Website URL for watermark
            template: Design template (default: 'professional')
            
        Returns:
            Path to saved image file
        """
        logger.info(f"🎨 Generating CTR-optimized feature image...")
        logger.info(f"   Title: {title[:60]}...")
        logger.info(f"   Type: {content_type}")
        
        # Get color scheme
        colors = self.COLOR_SCHEMES.get(content_type, self.COLOR_SCHEMES['jobs'])
        
        # Extract key information (6-8 words max)
        text_info = self._extract_key_info(title, content_type)
        
        # Create professional template (only one clean design)
        image = self._generate_professional_template(
            text_info, content_type, site_name, site_url, colors
        )
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{content_type}_{timestamp}.jpg"
        filepath = self.output_dir / filename
        
        image.save(filepath, 'JPEG', quality=95, optimize=True)
        logger.info(f"✅ Feature image saved: {filepath}")
        
        return filepath
    
    
    def _generate_professional_template(self, text_info: Dict[str, str], 
                                       content_type: str,
                                       site_name: str, site_url: str,
                                       colors: Dict) -> Image.Image:
        """
        Generate professional template matching reference design.
        
        Layout (matching reference):
        - Top: Colored banner with curved bottom + white text
        - Middle: White/light section with stats (number + label in different colors)
        - Bottom: Solid colored button + subtle watermark
        """
        width, height = self.DEFAULT_SIZE
        
        # Create white/light background
        image = Image.new('RGB', (width, height), (245, 245, 245))
        draw = ImageDraw.Draw(image)
        
        # === TOP BANNER: Colored section with curved bottom edge ===
        banner_height = 180
        primary_color = self._hex_to_rgb(colors['primary'])
        
        # Draw main banner rectangle
        draw.rectangle([0, 0, width, banner_height - 30], fill=primary_color)
        
        # Create smooth curved/wavy bottom edge (like reference image)
        curve_points = []
        num_points = 60
        for i in range(num_points + 1):
            x = (width * i) // num_points
            # Parabolic curve for smooth wave
            normalized = (i / num_points - 0.5) * 2  # -1 to 1
            wave_offset = int(30 * (1 - normalized ** 2))  # Parabola shape
            y = banner_height - 30 + wave_offset
            curve_points.append((x, y))
        
        # Complete polygon (close the shape)
        curve_points.append((width, 0))
        curve_points.append((0, 0))
        draw.polygon(curve_points, fill=primary_color)
        
        # Add thin top accent line
        draw.rectangle([0, 0, width, 6], fill=self._hex_to_rgb(colors['accent']))
        
        # === TOP TEXT: Category/Exam name (white, bold, centered in banner) ===
        top_text = text_info['top'].upper()  # Uppercase for impact
        
        # Adjust font size based on text length to prevent cutoff
        if len(top_text) > 35:
            top_font = self._get_font(52, bold=True)  # Smaller for long text
        elif len(top_text) > 25:
            top_font = self._get_font(58, bold=True)  # Medium
        else:
            top_font = self._get_font(64, bold=True)  # Large for short text
        
        top_bbox = top_font.getbbox(top_text)
        top_width = top_bbox[2] - top_bbox[0]
        top_height = top_bbox[3] - top_bbox[1]
        
        # Ensure text fits within banner width with padding
        max_width = width - 80  # 40px padding on each side
        if top_width > max_width:
            # Further reduce font size if still too wide
            top_font = self._get_font(46, bold=True)
            top_bbox = top_font.getbbox(top_text)
            top_width = top_bbox[2] - top_bbox[0]
            top_height = top_bbox[3] - top_bbox[1]
        
        top_x = (width - top_width) // 2
        top_y = (banner_height - top_height) // 2 - 20
        
        # Draw text with subtle shadow for depth
        draw.text((top_x + 2, top_y + 2), top_text, font=top_font, fill=(0, 0, 0, 80))
        draw.text((top_x, top_y), top_text, font=top_font, fill=(255, 255, 255))
        
        # === MIDDLE SECTION: Stats with contrasting colors ===
        center_text = text_info['center']
        
        # Only show middle section if there's content (admit cards have empty center for simplicity)
        if center_text:
            # Parse into number and label (e.g., "1445 VACANCIES" or "MERIT LIST PDF")
            words = center_text.split()
            number_part = ""
            label_part = ""
            
            # Check if first word is a number
            if words and any(char.isdigit() for char in words[0]):
                number_part = words[0]
                label_part = ' '.join(words[1:]).upper() if len(words) > 1 else ""
            else:
                # No number - treat all as label (e.g., "MERIT LIST PDF")
                label_part = center_text.upper()
            
            middle_y_start = banner_height + 70
            
            # Draw NUMBER (very large, primary color) - only for jobs
            if number_part:
                number_font = self._get_font(140, bold=True)
                number_bbox = number_font.getbbox(number_part)
                number_width = number_bbox[2] - number_bbox[0]
                number_height = number_bbox[3] - number_bbox[1]
                number_x = (width - number_width) // 2
                number_y = middle_y_start
                
                # Shadow for depth
                draw.text((number_x + 3, number_y + 3), number_part, 
                         font=number_font, fill=(200, 200, 200))
                # Main text
                draw.text((number_x, number_y), number_part, 
                         font=number_font, fill=primary_color)
                
                # Add proper spacing after number (increase gap to prevent touching)
                middle_y_start = number_y + number_height + 25  # Increased from 15 to 25 for more space
            
            # Draw LABEL (medium-large, accent color)
            if label_part:
                label_font = self._get_font(62, bold=True)
                label_bbox = label_font.getbbox(label_part)
                label_width = label_bbox[2] - label_bbox[0]
                label_x = (width - label_width) // 2
                
                # For results/admit cards without number, center vertically better
                if not number_part:
                    middle_y_start = (height - banner_height - 100) // 2 + banner_height + 30
                
                draw.text((label_x, middle_y_start), label_part, 
                         font=label_font, fill=self._hex_to_rgb(colors['accent']))
        
        # === BOTTOM BUTTON: Solid colored button with centered text ===
        button_color = self._hex_to_rgb(colors['highlight'])
        bottom_font = self._get_font(46, bold=True)
        bottom_text = text_info['bottom'].upper()
        
        # Calculate button dimensions with proper text metrics
        btn_text_bbox = bottom_font.getbbox(bottom_text)
        btn_text_width = btn_text_bbox[2] - btn_text_bbox[0]
        btn_text_height = btn_text_bbox[3] - btn_text_bbox[1]
        
        btn_padding_x = 55
        btn_padding_y = 22
        btn_width = btn_text_width + (btn_padding_x * 2)
        btn_height = btn_text_height + (btn_padding_y * 2)
        
        btn_x = (width - btn_width) // 2
        btn_y = height - btn_height - 65
        
        # Draw button with rounded corners
        self._draw_rounded_rectangle(
            draw,
            [btn_x, btn_y, btn_x + btn_width, btn_y + btn_height],
            radius=10,
            fill=button_color
        )
        
        # Draw button text - PROPERLY CENTERED (horizontal and vertical)
        text_x = btn_x + (btn_width - btn_text_width) // 2
        text_y = btn_y + (btn_height - btn_text_height) // 2 - 2  # Slight adjustment for visual balance
        
        draw.text((text_x, text_y), bottom_text, 
                 font=bottom_font, fill=(255, 255, 255))
        
        # === WATERMARK ===
        watermark_font = self._get_font(22, bold=False)
        watermark_text = site_name
        watermark_bbox = watermark_font.getbbox(watermark_text)
        watermark_width = watermark_bbox[2] - watermark_bbox[0]
        watermark_x = (width - watermark_width) // 2
        watermark_y = height - 32
        
        draw.text((watermark_x, watermark_y), watermark_text, 
                 font=watermark_font, fill=(120, 120, 120))
        
        return image
    
    def _generate_modern_template(self, text_info: Dict[str, str],
                                  content_type: str,
                                  site_name: str, site_url: str,
                                  colors: Dict) -> Image.Image:
        """Generate modern gradient template with overlay and geometric patterns."""
        width, height = self.DEFAULT_SIZE
        
        # Create diagonal gradient background
        image = self._create_gradient_background(
            self.DEFAULT_SIZE,
            colors['primary'],
            colors['secondary'],
            direction='diagonal'
        )
        
        draw = ImageDraw.Draw(image)
        
        # Add decorative top bar
        bar_height = 8
        
        # Add content type badge with icon
        badge_text = content_type.replace('_', ' ').title()
        badge_font = self._get_font(36, bold=True)
        badge_bbox = badge_font.getbbox(badge_text)
        badge_width = badge_bbox[2] - badge_bbox[0]
        badge_height = badge_bbox[3] - badge_bbox[1]
        
        badge_x = 70
        badge_y = 70
        badge_padding_x = 30
        badge_padding_y = 15
        
        # Draw badge with rounded corners and shadow
        shadow_offset = 5
        # Shadow
        self._draw_rounded_rectangle(
            draw,
            [badge_x - badge_padding_x + shadow_offset, 
             badge_y - badge_padding_y + shadow_offset,
             badge_x + badge_width + badge_padding_x + shadow_offset, 
             badge_y + badge_height + badge_padding_y + shadow_offset],
            radius=15,
            fill=(0, 0, 0, 80)
        )
        # Badge background
        self._draw_rounded_rectangle(
            draw,
            [badge_x - badge_padding_x, badge_y - badge_padding_y,
             badge_x + badge_width + badge_padding_x, badge_y + badge_height + badge_padding_y],
            radius=15,
            fill=self._hex_to_rgb(colors['accent'])
        )
        
        # Add icon/emoji before badge text
        icon_map = {
            'jobs': '💼',
            'results': '📊',
            'admit_cards': '🎫'
        }
        icon = icon_map.get(content_type, '📄')
        icon_font = self._get_font(32)
        draw.text((badge_x - badge_padding_x + 10, badge_y - 2), icon, font=icon_font, fill=colors['text'])
        
        draw.text((badge_x + 30, badge_y), badge_text, font=badge_font, fill=colors['text'])
        
        # Add title with enhanced styling
        title_font = self._get_font(64, bold=True)
        max_width = width - 140
        wrapped_lines = self._wrap_text(title, title_font, max_width)
        
        # Limit to 3 lines
        if len(wrapped_lines) > 3:
            wrapped_lines = wrapped_lines[:3]
            if len(wrapped_lines[-1]) > 40:
                wrapped_lines[-1] = wrapped_lines[-1][:37] + '...'
        
        # Calculate positioning
        line_height = 80
        total_text_height = len(wrapped_lines) * line_height
        start_y = (height - total_text_height) // 2 + 20
        
        # Draw title with enhanced shadow
        for i, line in enumerate(wrapped_lines):
            y = start_y + (i * line_height)
            # Multi-layer shadow for depth
            for offset in [(6, 6), (4, 4), (2, 2)]:
                draw.text((70 + offset[0], y + offset[1]), line, 
                         font=title_font, fill=(0, 0, 0, 150))
            # Main text
            draw.text((70, y), line, font=title_font, fill=colors['text'])
        
        # Add decorative line under title
        line_y = start_y + total_text_height + 20
        line_width = 200
        draw.rectangle([70, line_y, 70 + line_width, line_y + 6], 
                      fill=self._hex_to_rgb(colors['accent']))
        
        # Add website branding in a card at bottom
        watermark_text = site_name if site_name else site_url
        if watermark_text:
            watermark_font = self._get_font(32, bold=True)
            watermark_bbox = watermark_font.getbbox(watermark_text)
            watermark_width = watermark_bbox[2] - watermark_bbox[0]
            watermark_height = watermark_bbox[3] - watermark_bbox[1]
            
            # Create bottom card
            card_padding_x = 40
            card_padding_y = 20
            card_x = (width - watermark_width - card_padding_x * 2) // 2
            card_y = height - 100
            
            # Card shadow
            self._draw_rounded_rectangle(
                draw,
                [card_x + 4, card_y + 4,
                 card_x + watermark_width + card_padding_x * 2 + 4,
                 card_y + watermark_height + card_padding_y * 2 + 4],
                radius=12,
                fill=(0, 0, 0, 100)
            )
            # Card background
            self._draw_rounded_rectangle(
                draw,
                [card_x, card_y,
                 card_x + watermark_width + card_padding_x * 2,
                 card_y + watermark_height + card_padding_y * 2],
                radius=12,
                fill=(*self._hex_to_rgb(colors['accent']), 230)
            )
            
            # Add globe icon
            globe_icon = '🌐'
            globe_font = self._get_font(28)
            draw.text((card_x + card_padding_x - 30, card_y + card_padding_y - 2), 
                     globe_icon, font=globe_font, fill=colors['text'])
            
            # Watermark text
            draw.text((card_x + card_padding_x, card_y + card_padding_y), 
                     watermark_text, font=watermark_font, fill=colors['text'])
        
        return image
    
    def _generate_minimal_template(self, title: str, content_type: str,
                                   site_name: str, site_url: str,
                                   colors: Dict) -> Image.Image:
        """Generate minimal clean template with modern card design."""
        width, height = self.DEFAULT_SIZE
        
        # Solid background with subtle texture
        image = Image.new('RGB', self.DEFAULT_SIZE, self._hex_to_rgb(colors['primary']))
        
        # Add subtle noise/texture
        import random
        pixels = image.load()
        for y in range(0, height, 3):
            for x in range(0, width, 3):
                noise = random.randint(-8, 8)
                r, g, b = pixels[x, y]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )
        
        draw = ImageDraw.Draw(image)
        
        # Add large decorative accent bar on left with gradient effect
        accent_color = self._hex_to_rgb(colors['accent'])
        secondary_color = self._hex_to_rgb(colors['secondary'])
        bar_width = 25
        
        for i in range(bar_width):
            opacity = int(255 * (1 - i / bar_width))
            color = tuple(int(accent_color[j] * (i / bar_width) + secondary_color[j] * (1 - i / bar_width)) 
                         for j in range(3))
            draw.rectangle([i, 0, i + 1, height], fill=color)
        
        # Add floating card effect for content
        card_margin = 100
        card_x = card_margin
        card_y = 120
        card_width = width - card_margin * 2
        card_height = height - card_y - 150
        
        # Card shadow (multi-layer for depth)
        for offset in [(12, 12), (8, 8), (4, 4)]:
            shadow_alpha = 20
            shadow_rect = Image.new('RGBA', (card_width, card_height), 
                                   (0, 0, 0, shadow_alpha))
            image.paste(shadow_rect, (card_x + offset[0], card_y + offset[1]), shadow_rect)
        
        # Card background with slight transparency
        card_img = Image.new('RGBA', (card_width, card_height), 
                            (*self._hex_to_rgb(colors['primary']), 250))
        image = image.convert('RGBA')
        image.paste(card_img, (card_x, card_y), card_img)
        image = image.convert('RGB')
        
        draw = ImageDraw.Draw(image)
        
        # Add border around card
        border_color = self._hex_to_rgb(colors['accent'])
        draw.rectangle([card_x, card_y, card_x + card_width, card_y + card_height],
                      outline=border_color, width=3)
        
        # Add category tag at top with icon
        tag_font = self._get_font(28, bold=True)
        tag_text = content_type.replace('_', ' ').upper()
        tag_bbox = tag_font.getbbox(tag_text)
        tag_width = tag_bbox[2] - tag_bbox[0]
        
        # Tag background
        tag_padding_x = 25
        tag_padding_y = 12
        tag_x = 90
        tag_y = 50
        
        self._draw_rounded_rectangle(
            draw,
            [tag_x - tag_padding_x, tag_y - tag_padding_y,
             tag_x + tag_width + tag_padding_x + 40, tag_y + 30],
            radius=8,
            fill=accent_color
        )
        
        # Add icon
        icon_map = {'jobs': '💼', 'results': '📊', 'admit_cards': '🎫'}
        icon = icon_map.get(content_type, '📄')
        icon_font = self._get_font(24)
        draw.text((tag_x - tag_padding_x + 8, tag_y - 2), icon, font=icon_font, fill=colors['text'])
        
        draw.text((tag_x + 20, tag_y), tag_text, font=tag_font, fill=colors['text'])
        
        # Add title with better spacing
        title_font = self._get_font(58, bold=True)
        max_width = card_width - 80
        wrapped_lines = self._wrap_text(title, title_font, max_width)
        
        if len(wrapped_lines) > 3:
            wrapped_lines = wrapped_lines[:3]
            if len(wrapped_lines[-1]) > 35:
                wrapped_lines[-1] = wrapped_lines[-1][:32] + '...'
        
        line_height = 72
        total_text_height = len(wrapped_lines) * line_height
        start_y = card_y + (card_height - total_text_height) // 2 - 20
        
        # Draw title with subtle shadow
        for i, line in enumerate(wrapped_lines):
            y = start_y + (i * line_height)
            # Shadow
            draw.text((card_x + 42, y + 2), line, font=title_font, fill=(0, 0, 0, 100))
            # Text
            draw.text((card_x + 40, y), line, font=title_font, fill=colors['text'])
        
        # Add decorative accent line under title
        accent_line_y = start_y + total_text_height + 15
        accent_line_width = 180
        for i in range(5):
            opacity = 255 - (i * 40)
            draw.rectangle([card_x + 40, accent_line_y + i, 
                          card_x + 40 + accent_line_width, accent_line_y + i + 1],
                         fill=(*accent_color, opacity))
        
        # Add watermark at bottom with icon
        watermark_font = self._get_font(28, bold=True)
        watermark_text = site_name if site_name else site_url
        if watermark_text:
            watermark_y = height - 90
            
            # Icon
            web_icon = '🌐'
            web_font = self._get_font(26)
            draw.text((card_x + 40, watermark_y - 2), web_icon, font=web_font, fill=colors['accent'])
            
            # Text
            draw.text((card_x + 75, watermark_y), watermark_text, 
                     font=watermark_font, fill=colors['text'])
        
        return image
    
    def _generate_bold_template(self, title: str, content_type: str,
                               site_name: str, site_url: str,
                               colors: Dict) -> Image.Image:
        """Generate bold, high-impact template with modern design elements."""
        width, height = self.DEFAULT_SIZE
        
        # Create vibrant gradient background
        image = self._create_gradient_background(
            self.DEFAULT_SIZE,
            colors['secondary'],
            colors['primary'],
            direction='horizontal'
        )
        
        # Add dynamic geometric shapes
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        
        accent_color = self._hex_to_rgb(colors['accent'])
        
        # Large circles for visual interest
        draw_overlay.ellipse([width - 400, -200, width + 200, 400], 
                           fill=(*accent_color, 40))
        draw_overlay.ellipse([-200, height - 400, 400, height + 200], 
                           fill=(*accent_color, 35))
        
        # Add triangle shapes
        primary_rgb = self._hex_to_rgb(colors['primary'])
        draw_overlay.polygon([(0, 0), (300, 0), (0, 250)], 
                           fill=(*primary_rgb, 60))
        draw_overlay.polygon([(width, height), (width - 300, height), (width, height - 250)], 
                           fill=(*primary_rgb, 60))
        
        # Composite overlay
        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(image)
        
        # Add bold top stripe
        stripe_height = 12
        gradient_colors = [self._hex_to_rgb(colors['accent']), 
                          self._hex_to_rgb(colors['secondary'])]
        for i in range(stripe_height):
            ratio = i / stripe_height
            color = tuple(int(gradient_colors[0][j] * (1 - ratio) + gradient_colors[1][j] * ratio) 
                         for j in range(3))
            draw.rectangle([0, i, width, i + 1], fill=color)
        
        # Add large category badge with icon
        badge_font = self._get_font(52, bold=True)
        badge_text = content_type.replace('_', ' ').title()
        badge_bbox = badge_font.getbbox(badge_text)
        badge_width = badge_bbox[2] - badge_bbox[0]
        badge_height = badge_bbox[3] - badge_bbox[1]
        
        badge_x = 70
        badge_y = 60
        badge_padding_x = 40
        badge_padding_y = 20
        
        # Badge with 3D effect
        for offset in [(6, 6), (4, 4), (2, 2)]:
            self._draw_rounded_rectangle(
                draw,
                [badge_x - badge_padding_x + offset[0], 
                 badge_y - badge_padding_y + offset[1],
                 badge_x + badge_width + badge_padding_x + 60 + offset[0], 
                 badge_y + badge_height + badge_padding_y + offset[1]],
                radius=18,
                fill=(0, 0, 0, 120)
            )
        
        # Badge background
        self._draw_rounded_rectangle(
            draw,
            [badge_x - badge_padding_x, badge_y - badge_padding_y,
             badge_x + badge_width + badge_padding_x + 60, 
             badge_y + badge_height + badge_padding_y],
            radius=18,
            fill=accent_color
        )
        
        # Add icon
        icon_map = {'jobs': '💼', 'results': '📊', 'admit_cards': '🎫'}
        icon = icon_map.get(content_type, '📄')
        icon_font = self._get_font(42)
        draw.text((badge_x - badge_padding_x + 15, badge_y - 5), 
                 icon, font=icon_font, fill=colors['text'])
        
        # Badge text
        draw.text((badge_x + 35, badge_y), badge_text, font=badge_font, fill=colors['text'])
        
        # Add title with dramatic effect
        title_font = self._get_font(70, bold=True)
        max_width = width - 140
        wrapped_lines = self._wrap_text(title, title_font, max_width)
        
        if len(wrapped_lines) > 2:
            wrapped_lines = wrapped_lines[:2]
            if len(wrapped_lines[-1]) > 30:
                wrapped_lines[-1] = wrapped_lines[-1][:27] + '...'
        
        line_height = 90
        total_text_height = len(wrapped_lines) * line_height
        start_y = (height - total_text_height) // 2 + 30
        
        # Draw title with multi-layer shadow for 3D effect
        for i, line in enumerate(wrapped_lines):
            y = start_y + (i * line_height)
            
            # Multiple shadow layers
            for offset, opacity in [((8, 8), 60), ((6, 6), 80), ((4, 4), 100), ((2, 2), 120)]:
                draw.text((70 + offset[0], y + offset[1]), line, 
                         font=title_font, fill=(0, 0, 0, opacity))
            
            # Outline effect
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((70 + dx, y + dy), line, 
                         font=title_font, fill=self._hex_to_rgb(colors['secondary']))
            
            # Main text
            draw.text((70, y), line, font=title_font, fill=colors['text'])
        
        # Add dynamic accent bars under title
        bars_y = start_y + total_text_height + 25
        bar_colors = [accent_color, self._hex_to_rgb(colors['secondary']), primary_rgb]
        bar_widths = [280, 220, 160]
        bar_spacing = 12
        
        for idx, (bar_color, bar_width) in enumerate(zip(bar_colors, bar_widths)):
            bar_y = bars_y + (idx * bar_spacing)
            self._draw_rounded_rectangle(
                draw,
                [70, bar_y, 70 + bar_width, bar_y + 8],
                radius=4,
                fill=bar_color
            )
        
        # Add prominent website branding card
        watermark_text = site_name if site_name else site_url
        if watermark_text:
            watermark_font = self._get_font(38, bold=True)
            watermark_bbox = watermark_font.getbbox(watermark_text)
            watermark_width = watermark_bbox[2] - watermark_bbox[0]
            watermark_height = watermark_bbox[3] - watermark_bbox[1]
            
            # Create prominent branding box
            box_padding_x = 50
            box_padding_y = 22
            box_x = 70
            box_y = height - 110
            
            # Box shadow
            for offset in [(6, 6), (3, 3)]:
                self._draw_rounded_rectangle(
                    draw,
                    [box_x + offset[0], box_y + offset[1],
                     box_x + watermark_width + box_padding_x * 2 + 50 + offset[0],
                     box_y + watermark_height + box_padding_y * 2 + offset[1]],
                    radius=15,
                    fill=(0, 0, 0, 140)
                )
            
            # Box background
            self._draw_rounded_rectangle(
                draw,
                [box_x, box_y,
                 box_x + watermark_width + box_padding_x * 2 + 50,
                 box_y + watermark_height + box_padding_y * 2],
                radius=15,
                fill=accent_color
            )
            
            # Globe icon
            globe_icon = '🌐'
            globe_font = self._get_font(34)
            draw.text((box_x + box_padding_x - 35, box_y + box_padding_y - 4), 
                     globe_icon, font=globe_font, fill=colors['text'])
            
            # Watermark text
            draw.text((box_x + box_padding_x, box_y + box_padding_y), 
                     watermark_text, font=watermark_font, fill=colors['text'])
        
        return image


# Testing and CLI interface
def main():
    """Test the feature image generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate feature images for job portal articles')
    parser.add_argument('--title', type=str, required=True, help='Article title')
    parser.add_argument('--type', type=str, default='jobs', 
                       choices=['jobs', 'results', 'admit_cards'],
                       help='Content type')
    parser.add_argument('--site-name', type=str, default='Job Portal', 
                       help='Website name')
    parser.add_argument('--site-url', type=str, default='', 
                       help='Website URL')
    parser.add_argument('--template', type=str, default='modern',
                       choices=['modern', 'minimal', 'bold'],
                       help='Design template')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create generator
    output_dir = Path(args.output_dir) if args.output_dir else None
    generator = FeatureImageGenerator(output_dir=output_dir)
    
    # Generate image
    filepath = generator.generate(
        title=args.title,
        content_type=args.type,
        site_name=args.site_name,
        site_url=args.site_url,
        template=args.template
    )
    
    print(f"\n✅ Feature image generated successfully!")
    print(f"📁 Location: {filepath}")
    print(f"📏 Size: 1200x630 pixels")
    print(f"\nYou can now:")
    print(f"  1. Open the image to preview")
    print(f"  2. Upload to WordPress as featured image")
    print(f"  3. Test different templates (modern, minimal, bold)")


if __name__ == '__main__':
    main()
