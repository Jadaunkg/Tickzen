import base64
from PIL import Image, ImageDraw, ImageFont
import io
import os

def create_placeholder(text, color, size=(800, 400)):
    # Create a new image with the given background color
    image = Image.new('RGB', size, color)
    draw = ImageDraw.Draw(image)
    
    try:
        # Try to load a font (adjust path as needed)
        font = ImageFont.truetype('arial.ttf', 40)
    except IOError:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Calculate text position to center it using the newer API
    # For newer Pillow versions that don't have textsize
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        # Fall back to older method if available
        try:
            text_width, text_height = draw.textsize(text, font=font)
        except AttributeError:
            # Rough estimate if both methods fail
            text_width, text_height = len(text) * 20, 40
    
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    
    # Draw the text in white
    draw.text(position, text, fill='white', font=font)
    
    # Save the image in the current directory
    filename = f"{text.lower()}.jpg"
    image.save(filename)
    print(f"Created {filename}")

# Create placeholder images for each category
categories = {
    "Market": "#3b82f6",  # Blue
    "Economy": "#16a34a",  # Green
    "Crypto": "#f59e0b",   # Orange
    "Forex": "#9333ea",    # Purple
    "Earnings": "#64748b", # Gray
    "News": "#0f172a"      # Dark
}

for category, color in categories.items():
    create_placeholder(category, color)
