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
        
        CRITICAL: Each content type MUST have UNIQUE text extraction logic to ensure 
        different feature images for jobs, admit cards, and results.
        
        Jobs: top=organization name+year, center=vacancy count, bottom="Apply Online"
        Admit Cards: top=exam name+ADMIT CARD+year, center="Released", bottom="Download Now"  
        Results: top=exam name+RESULT+year, center="Declared", bottom="Check Marks"
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
            # JOBS: Focus on organization/position name + vacancy count
            # Remove all job-specific keywords to get clean organization name
            exam_name = title
            # Remove ALL job-related keywords (not admit card or result keywords)
            exam_name = re.sub(r'-?\s*\d{1,3}(?:,\d{3})*\s*(?:Posts?|Vacancies|Vacancy).*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'\b(?:Recruitment|Notification|Apply|Online|Apply Online|Application)\b', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'-?\s*Out\b', '', exam_name, flags=re.IGNORECASE)  # Remove "Out" for jobs
            exam_name = exam_name.strip(' -.,').strip()
            
            # Limit to 6-7 words max for top
            words = exam_name.split()
            if len(words) > 7:
                exam_name = ' '.join(words[:7])
            
            # Ensure year is in headline for jobs
            if year not in exam_name:
                exam_name = f"{exam_name} {year}"
            
            # Center: ONLY vacancy count (NOT "Released" or "Declared")
            if vacancy_num:
                center_text = f"{vacancy_num} Vacancies"
            else:
                center_text = "Multiple Posts"
            
            return {
                'top': exam_name,
                'center': center_text,
                'bottom': 'Apply Online'  # UNIQUE to jobs
            }
            
        elif content_type == 'admit_cards':
            # ADMIT CARDS: Explicitly add "ADMIT CARD" keyword for distinction
            exam_name = title
            # Remove admit card-specific keywords (not job or result keywords)
            exam_name = re.sub(r'-?\s*(?:Download|Hall Ticket|Admit Card).*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'-?\s*Out\b', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'\b(?:Released)\b', '', exam_name, flags=re.IGNORECASE)
            exam_name = exam_name.strip(' -.,').strip()
            
            # Limit words to keep it concise
            words = exam_name.split()
            if len(words) > 5:
                exam_name = ' '.join(words[:5])
            
            # CRITICAL: Explicitly add "ADMIT CARD" to make it unique from jobs/results
            exam_name = f"{exam_name} ADMIT CARD"
            
            # Ensure year is included
            if year not in exam_name:
                exam_name = f"{exam_name} {year}"
            
            return {
                'top': exam_name,  # Includes "ADMIT CARD" keyword
                'center': 'Released',  # UNIQUE to admit cards (not "Vacancies" or "Declared")
                'bottom': 'Download Now'  # UNIQUE to admit cards
            }
            
        elif content_type == 'results':
            # RESULTS: Explicitly add "RESULT" keyword for distinction
            exam_name = title
            # Remove result-specific keywords (not job or admit card keywords)
            exam_name = re.sub(r'-?\s*(?:Result|Check|Download|PDF|Marks|Cut Off|Cut-off).*$', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'-?\s*Out\b', '', exam_name, flags=re.IGNORECASE)
            exam_name = re.sub(r'\b(?:Declared)\b', '', exam_name, flags=re.IGNORECASE)
            exam_name = exam_name.strip(' -&.,').strip()
            
            # Limit words
            words = exam_name.split()
            if len(words) > 5:
                exam_name = ' '.join(words[:5])
            
            # CRITICAL: Explicitly add "RESULT" to make it unique from jobs/admit cards
            exam_name = f"{exam_name} RESULT"
            
            # Ensure year is included
            if year not in exam_name:
                exam_name = f"{exam_name} {year}"
            
            return {
                'top': exam_name,  # Includes "RESULT" keyword
                'center': 'Declared',  # UNIQUE to results (not "Vacancies" or "Released")
                'bottom': 'Check Marks'  # UNIQUE to results
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
        
        # Create template based on content type
        if content_type == 'results':
            image = self._generate_results_template(
                text_info, site_name, site_url, colors
            )
        elif content_type == 'admit_cards':
            image = self._generate_admit_card_template(
                text_info, site_name, site_url, colors
            )
        else:
            # Default to jobs template (the professional layout)
            image = self._generate_jobs_template(
                text_info, site_name, site_url, colors
            )
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{content_type}_{timestamp}.jpg"
        filepath = self.output_dir / filename
        
        image.save(filepath, 'JPEG', quality=95, optimize=True)
        logger.info(f"✅ Feature image saved: {filepath}")
        
        return filepath
    
    
    def _generate_jobs_template(self, text_info: Dict[str, str], 
                               site_name: str, site_url: str,
                               colors: Dict) -> Image.Image:
        """
        Generate Jobs template (Classic Banner Layout).
        
        Layout:
        - Top: Colored banner with curved bottom + white text
        - Middle: Vacancy count (Large number)
        - Bottom: Apply Button
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
        
        # Create smooth curved/wavy bottom edge
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
        top_text = text_info['top'].upper()
        
        # Adjust font size based on text length
        if len(top_text) > 35:
            top_font = self._get_font(52, bold=True)
        elif len(top_text) > 25:
            top_font = self._get_font(58, bold=True)
        else:
            top_font = self._get_font(64, bold=True)

        # Check if text fits in one line, otherwise wrap
        max_width = width - 80
        top_bbox = top_font.getbbox(top_text)
        top_width = top_bbox[2] - top_bbox[0]

        if top_width > max_width:
            # Wrap text logic if too wide
            wrapped_lines = self._wrap_text(top_text, top_font, max_width)
            
            # Recalculate font size if still too many lines
            if len(wrapped_lines) > 2:
                top_font = self._get_font(40, bold=True) # Shrink font significantly
                wrapped_lines = self._wrap_text(top_text, top_font, max_width)
            
            # Calculate total height block
            line_heights = []
            for line in wrapped_lines:
                bbox = top_font.getbbox(line)
                line_heights.append(bbox[3] - bbox[1])
            
            total_text_height = sum(line_heights) + (len(wrapped_lines) - 1) * 10
            
            # Start Y position to center the block vertically in banner
            start_y = (banner_height - total_text_height) // 2 - 10
            
            for i, line in enumerate(wrapped_lines):
                bbox = top_font.getbbox(line)
                line_w = bbox[2] - bbox[0]
                line_h = bbox[3] - bbox[1]
                line_x = (width - line_w) // 2
                
                # Draw text with shadow
                draw.text((line_x + 2, start_y + 2), line, font=top_font, fill=(0, 0, 0, 80))
                draw.text((line_x, start_y), line, font=top_font, fill=(255, 255, 255))
                start_y += line_h + 10
        else:
            # Standard single line centering
            top_height = top_bbox[3] - top_bbox[1]
            top_x = (width - top_width) // 2
            top_y = (banner_height - top_height) // 2 - 20
            
            draw.text((top_x + 2, top_y + 2), top_text, font=top_font, fill=(0, 0, 0, 80))
            draw.text((top_x, top_y), top_text, font=top_font, fill=(255, 255, 255))
        
        # === MIDDLE SECTION: Vacancy Count ===
        center_text = text_info['center']
        if center_text:
            words = center_text.split()
            number_part = ""
            label_part = ""
            
            # Parsing specifically for vacancy structure "1234 Vacancies"
            if words and any(char.isdigit() for char in words[0]):
                number_part = words[0]
                label_part = ' '.join(words[1:]).upper() if len(words) > 1 else ""
            else:
                label_part = center_text.upper()
            
            middle_y_start = banner_height + 70
            
            # Large Number
            if number_part:
                number_font = self._get_font(140, bold=True)
                number_bbox = number_font.getbbox(number_part)
                number_width = number_bbox[2] - number_bbox[0]
                number_height = number_bbox[3] - number_bbox[1]
                number_x = (width - number_width) // 2
                number_y = middle_y_start
                
                # Shadow
                draw.text((number_x + 3, number_y + 3), number_part, font=number_font, fill=(200, 200, 200))
                # Main
                draw.text((number_x, number_y), number_part, font=number_font, fill=primary_color)
                
                middle_y_start = number_y + number_height + 25
            
            # Label
            if label_part:
                label_font = self._get_font(62, bold=True)
                label_bbox = label_font.getbbox(label_part)
                label_width = label_bbox[2] - label_bbox[0]
                label_x = (width - label_width) // 2
                
                # Center vertically if no number
                if not number_part:
                    middle_y_start = (height - banner_height - 100) // 2 + banner_height + 30
                
                draw.text((label_x, middle_y_start), label_part, font=label_font, fill=self._hex_to_rgb(colors['accent']))
        
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

    def _generate_results_template(self, text_info: Dict[str, str], 
                                  site_name: str, site_url: str,
                                  colors: Dict) -> Image.Image:
        """
        Generate Results template (Side Split Layout).
        
        Layout:
        - Left (30%): Solid color with vertical "RESULT" text
        - Right (70%): Exam Name + "Merit List" + Check Button
        """
        width, height = self.DEFAULT_SIZE
        
        # Create white background
        image = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        primary_color = self._hex_to_rgb(colors['primary'])
        accent_color = self._hex_to_rgb(colors['accent'])
        
        # === LEFT SIDEBAR ===
        sidebar_width = int(width * 0.28)
        draw.rectangle([0, 0, sidebar_width, height], fill=primary_color)
        
        # Vertical Text "RESULT"
        side_text = "RESULT"
        side_font_size = 110
        side_font = self._get_font(side_font_size, bold=True)
        
        # Check size and render vertically
        side_bbox = side_font.getbbox(side_text)
        text_w = side_bbox[2] - side_bbox[0]
        text_h = side_bbox[3] - side_bbox[1]
        
        txt_img = Image.new('RGBA', (text_w, text_h + 30), (0,0,0,0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((0, 0), side_text, font=side_font, fill=(255, 255, 255))
        
        rotated_txt = txt_img.rotate(90, expand=True)
        
        # Center in sidebar
        rot_w, rot_h = rotated_txt.size
        side_x = (sidebar_width - rot_w) // 2
        side_y = (height - rot_h) // 2
        
        # Paste with alpha mask
        image.paste(rotated_txt, (side_x, side_y), rotated_txt)
        
        # === RIGHT SIDE CONTENT ===
        content_x_start = sidebar_width + 80
        content_width = width - content_x_start - 50
        
        current_y = 80
        
        # 1. Exam Name (Top)
        top_text = text_info['top'].upper()
        if len(top_text) > 30:
            top_font = self._get_font(52, bold=True)
        else:
            top_font = self._get_font(60, bold=True)
            
        wrapped_lines = self._wrap_text(top_text, top_font, content_width)
        for line in wrapped_lines:
            draw.text((content_x_start, current_y), line, font=top_font, fill=(50, 50, 50))
            line_bbox = top_font.getbbox(line)
            current_y += (line_bbox[3] - line_bbox[1]) + 15
            
        current_y += 30
        
        # 2. "MERIT LIST" / Center Text
        center_text = text_info['center'].upper()
        if center_text:
            center_font = self._get_font(75, bold=True)
            draw.text((content_x_start, current_y), center_text, font=center_font, fill=accent_color)
            
            # Add decorative underline
            center_bbox = center_font.getbbox(center_text)
            text_width = center_bbox[2] - center_bbox[0]
            text_height = center_bbox[3] - center_bbox[1]
            draw.rectangle([content_x_start, current_y + text_height + 15, content_x_start + 100, current_y + text_height + 22], fill=primary_color)
            
            current_y += text_height + 80
        else:
            current_y += 100

        # 3. Button
        btn_text = text_info['bottom'].upper()
        btn_font = self._get_font(42, bold=True)
        btn_bbox = btn_font.getbbox(btn_text)
        btn_w = btn_bbox[2] - btn_bbox[0] + 80
        btn_h = btn_bbox[3] - btn_bbox[1] + 40
        
        self._draw_rounded_rectangle(draw, [content_x_start, current_y, content_x_start + btn_w, current_y + btn_h], radius=8, fill=primary_color)
        draw.text((content_x_start + 40, current_y + 20), btn_text, font=btn_font, fill=(255, 255, 255))
        
        # Watermark (Bottom Right)
        wm_font = self._get_font(20)
        wm_text = site_name
        wm_bbox = wm_font.getbbox(wm_text)
        wm_w = wm_bbox[2] - wm_bbox[0]
        draw.text((width - wm_w - 50, height - 50), wm_text, font=wm_font, fill=(150, 150, 150))
        
        return image

    def _generate_admit_card_template(self, text_info: Dict[str, str], 
                                     site_name: str, site_url: str,
                                     colors: Dict) -> Image.Image:
        """
        Generate Admit Card template (Center Card with Gradient).
        
        Layout:
        - Background: Diagonal Gradient
        - Center: White Card with details
        - Header: "ADMIT CARD" badge
        """
        width, height = self.DEFAULT_SIZE
        
        # Gradient Background
        image = self._create_gradient_background(
            self.DEFAULT_SIZE, 
            colors['bg_start'], 
            colors['bg_end'], 
            direction='diagonal'
        )
        # Add pattern
        image = self._add_geometric_patterns(image, colors)
        
        draw = ImageDraw.Draw(image)
        
        # === CENTER CARD ===
        card_w, card_h = 950, 450
        card_x = (width - card_w) // 2
        card_y = (height - card_h) // 2
        
        # Shadow
        self._draw_rounded_rectangle(draw, [card_x+10, card_y+10, card_x+card_w+10, card_y+card_h+10], radius=20, fill=(0, 0, 0, 30))
        # White Card
        self._draw_rounded_rectangle(draw, [card_x, card_y, card_x+card_w, card_y+card_h], radius=20, fill=(255, 255, 255))
        
        current_y = card_y + 60
        
        # 1. Badge "ADMIT CARD RELEASED"
        badge_text = "ADMIT CARD RELEASED"
        badge_font = self._get_font(30, bold=True)
        badge_bbox = badge_font.getbbox(badge_text)
        badge_text_w = badge_bbox[2] - badge_bbox[0]
        badge_text_h = badge_bbox[3] - badge_bbox[1]
        
        # Badge dimensions with padding
        badge_w = badge_text_w + 60
        badge_h = badge_text_h + 30
        badge_x = (width - badge_w) // 2
        
        primary_rgb = self._hex_to_rgb(colors['primary'])
        
        self._draw_rounded_rectangle(draw, [badge_x, current_y, badge_x + badge_w, current_y + badge_h], radius=15, fill=self._hex_to_rgb(colors['accent']))
        
        # Center text inside badge perfectly
        text_x = badge_x + (badge_w - badge_text_w) // 2
        text_y = current_y + (badge_h - badge_text_h) // 2 - 4  # Slight adjustment for baseline
        
        draw.text((text_x, text_y), badge_text, font=badge_font, fill=(255, 255, 255))
        
        current_y += 90
        
        # 2. Exam Name
        exam_text = text_info['top']
        # Limit length logic moved inside wrapping
        if len(exam_text) > 40:
             exam_font = self._get_font(50, bold=True)
        else:
             exam_font = self._get_font(60, bold=True)
             
        wrapped = self._wrap_text(exam_text, exam_font, card_w - 80)
        # If wrapped text takes too much space, reduce font size
        if len(wrapped) > 3: 
             exam_font = self._get_font(40, bold=True)
             wrapped = self._wrap_text(exam_text, exam_font, card_w - 80)

        for line in wrapped:
            # Centered text
            line_bbox = exam_font.getbbox(line)
            line_w = line_bbox[2] - line_bbox[0]
            line_x = (width - line_w) // 2
            draw.text((line_x, current_y), line, font=exam_font, fill=(30, 30, 30))
            current_y += (line_bbox[3] - line_bbox[1]) + 15
            
        # 3. Download Button
        current_y += 40
        btn_text = text_info['bottom'].upper()
        btn_font = self._get_font(42, bold=True)
        btn_bbox = btn_font.getbbox(btn_text)
        btn_text_w = btn_bbox[2] - btn_bbox[0]
        btn_text_h = btn_bbox[3] - btn_bbox[1]
        
        # Button dimensions
        btn_w = btn_text_w + 80
        btn_h = btn_text_h + 40
        btn_x = (width - btn_w) // 2
        
        self._draw_rounded_rectangle(draw, [btn_x, current_y, btn_x+btn_w, current_y+btn_h], radius=10, fill=primary_rgb)
        
        # Center text inside button perfectly
        btn_txt_x = btn_x + (btn_w - btn_text_w) // 2
        btn_txt_y = current_y + (btn_h - btn_text_h) // 2 - 4
        
        draw.text((btn_txt_x, btn_txt_y), btn_text, font=btn_font, fill=(255, 255, 255))
        
        # Watermark
        wm_text = site_name
        wm_font = self._get_font(18)
        wm_bbox = wm_font.getbbox(wm_text)
        wm_w = wm_bbox[2] - wm_bbox[0]
        draw.text(((width - wm_w)//2, card_y + card_h - 40), wm_text, font=wm_font, fill=(150, 150, 150))
        
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
