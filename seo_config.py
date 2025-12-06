# Production configuration for SEO-related values
# Use environment variables in production for security

# Google Analytics Configuration
# Use environment variable for production: os.getenv('GOOGLE_ANALYTICS_ID', 'GA_MEASUREMENT_ID')
GOOGLE_ANALYTICS_ID = "GA_MEASUREMENT_ID"  # Replace with your actual GA4 measurement ID

# Search Console Verification Codes
# Use environment variables in production for security
GOOGLE_VERIFICATION_CODE = "YOUR_GOOGLE_VERIFICATION_CODE"  # From Google Search Console
BING_VERIFICATION_CODE = "YOUR_BING_VERIFICATION_CODE"      # From Bing Webmaster Tools

# Social Media Handles
TWITTER_HANDLE = "@tickzen"
FACEBOOK_PAGE = "tickzen"
LINKEDIN_COMPANY = "tickzen"

# Contact Information
SUPPORT_EMAIL = "support@tickzen.app"
BUSINESS_PHONE = "+1-XXX-XXX-XXXX"

# Business Information
COMPANY_NAME = "Tickzen"
COMPANY_FOUNDED = "2024"
COMPANY_ADDRESS_COUNTRY = "US"

# SEO Settings
DEFAULT_KEYWORDS = "stock analysis, AI stock predictions, investment research, financial reports, technical analysis"
DEFAULT_AUTHOR = "Tickzen"
DEFAULT_LANGUAGE = "English"
DEFAULT_REGION = "US"

# Structured Data Settings
AGGREGATE_RATING = {
    "ratingValue": "4.8",
    "reviewCount": "127",
    "bestRating": "5",
    "worstRating": "1"
}

# Performance Settings
PRELOAD_FONTS = True
ENABLE_GZIP = True
CACHE_STATIC_FILES = True

# Instructions for updating:
# 1. Replace GOOGLE_ANALYTICS_ID with your actual GA4 measurement ID
#    Format: G-XXXXXXXXXX (Get from https://analytics.google.com/)
# 2. Get verification codes from Google Search Console and Bing Webmaster Tools
#    Google: https://search.google.com/search-console (HTML tag method)
#    Bing: https://www.bing.com/webmasters (Meta tag method)
# 3. Update social media handles to match your actual profiles
# 4. Replace placeholder phone number and email with real contact info
# 5. Update review counts and ratings based on actual customer feedback
# 6. After making changes, restart the Flask application
# 7. Run `python validate_seo_setup.py` to verify the setup
