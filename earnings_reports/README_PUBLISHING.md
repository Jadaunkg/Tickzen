# Earnings Articles Publishing Integration

## Overview

This integration enables automated publishing of earnings articles alongside stock analysis articles, using the same smart writer rotation and record-keeping system.

## Features

✅ **Unified Writer Rotation** - Both earnings and stock analysis articles share the same author rotation queue
✅ **Daily Publishing Limits** - Combined tracking across all article types
✅ **Article Type Selection** - Configure profiles for different article types
✅ **Record Keeping** - All articles tracked in unified publishing history
✅ **WordPress Integration** - Seamless publishing to WordPress with proper formatting

## Article Types Supported

1. **Stock Analysis** (`stock_analysis`) - Default comprehensive stock analysis with technical indicators, forecasts, and fundamentals
2. **Earnings Report** (`earnings`) - Full earnings analysis with financial metrics and insights
3. **Pre-Earnings Preview** (`pre_earnings`) - Forward-looking earnings preview article
4. **Post-Earnings Review** (`post_earnings`) - Post-earnings analysis and market reaction

## Configuration

### Profile Setup

Add `article_type` to your profile configuration in `profiles_config.json`:

```json
{
  "profile_id": "earnings_site_1",
  "profile_name": "Earnings Analysis Blog",
  "site_url": "https://your-earnings-blog.com",
  "article_type": "earnings",
  "authors": [
    {
      "wp_username": "analyst1",
      "wp_user_id": 1,
      "app_password": "your-app-password"
    }
  ],
  "stockforecast_category_id": 5,
  "min_scheduling_gap_minutes": 45,
  "max_scheduling_gap_minutes": 68
}
```

### Article Type Options

```json
{
  "article_type": "stock_analysis"  // Default - comprehensive stock analysis
  "article_type": "earnings"        // Full earnings report
  "article_type": "pre_earnings"    // Pre-earnings preview
  "article_type": "post_earnings"   // Post-earnings review
}
```

## Usage

### Via Auto Publisher

The auto_publisher automatically detects article type from profile configuration:

```python
from automation_scripts.auto_publisher import trigger_publishing_run

# Configure profiles with different article types
profiles = [
    {
        "profile_id": "stock_blog",
        "article_type": "stock_analysis",
        # ... other config
    },
    {
        "profile_id": "earnings_blog",
        "article_type": "earnings",
        # ... other config
    }
]

# Run publishing (writer rotation applies to all)
result = trigger_publishing_run(
    user_uid="user123",
    profiles_to_process_data_list=profiles,
    articles_to_publish_per_profile_map={
        "stock_blog": 2,
        "earnings_blog": 3
    }
)
```

### Direct Earnings Article Generation

```python
from earnings_reports.earnings_publisher import generate_earnings_article_for_autopublisher

# Generate earnings article
html, title, metadata = generate_earnings_article_for_autopublisher(
    ticker="AAPL",
    article_type="earnings"
)

if html and title:
    print(f"Title: {title}")
    print(f"Words: {metadata['word_count']}")
    print(f"Company: {metadata['company_name']}")
```

### Standalone Earnings Writer

```python
from earnings_reports.gemini_earnings_writer import GeminiEarningsWriter

writer = GeminiEarningsWriter()
result = writer.generate_complete_report("AAPL")

if result['success']:
    print(f"Article saved to: {result['file_path']}")
    print(f"Words: {result['word_count']}")
```

## Writer Rotation Logic

The system uses a unified rotation across all article types:

1. **Profile-Level Tracking** - Each profile maintains `last_author_index_by_profile`
2. **Cyclic Rotation** - Authors rotate in round-robin fashion
3. **Persistent State** - Rotation state persists across runs (Firestore or pickle)
4. **Mixed Articles** - Stock analysis and earnings articles can be published from same profile with continuous rotation

### Example Rotation Flow

```
Profile: "Finance Blog" with 3 authors: [Alice, Bob, Carol]

Article 1 (Stock): AAPL → Alice
Article 2 (Earnings): MSFT → Bob
Article 3 (Stock): GOOGL → Carol
Article 4 (Earnings): TSLA → Alice (rotation continues)
```

## Record Keeping

### Publishing Status Tracking

All articles tracked with:
- ✅ Ticker symbol
- ✅ Article type (stock_analysis, earnings, etc.)
- ✅ Generation timestamp
- ✅ Scheduled publish time
- ✅ Writer username
- ✅ Publishing status
- ✅ Profile ID

### Daily Limits

```python
# Combined limit across all article types
MAX_POSTS_PER_DAY_PER_SITE = 20  # From environment variable

# Tracking per profile
state['posts_today_by_profile'][profile_id]  # Increments for any article type
```

### Publishing History

```python
# Detailed log per profile
state['processed_tickers_detailed_log_by_profile'][profile_id] = [
    {
        'ticker': 'AAPL',
        'status': 'Scheduled',
        'article_type': 'earnings',  # NEW: Article type tracked
        'generated_at': '2025-11-25T10:30:00Z',
        'published_at': '2025-11-25T14:00:00Z',
        'writer_username': 'analyst1'
    },
    # ... more entries
]
```

## WordPress Integration

### Article Formatting

Both article types generate WordPress-ready HTML:
- ✅ No document structure tags (html, head, body)
- ✅ Proper heading hierarchy (h2 → h3 → h4)
- ✅ SEO-optimized content
- ✅ External links to trusted sources
- ✅ FAQ sections with schema markup support
- ✅ Feature image compatible

### Post Creation

```python
# Same workflow for both article types
create_wordpress_post(
    site_url=profile['site_url'],
    author=current_author,
    title=article_title,  # Generated by system
    content=html_content,
    sched_time=next_schedule_time,
    ticker=ticker,
    company_name=company_name  # For SEO slug
)
```

## Testing

### Test Earnings Article Generation

```bash
cd Tickzen/earnings_reports
python earnings_publisher.py AAPL --type earnings
```

### Test Auto Publisher with Mixed Articles

```bash
cd Tickzen/automation_scripts
python auto_publisher.py
# Configure profiles_config.json with mixed article types
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Auto Publisher Core                     │
│  - Writer Rotation (Unified)                            │
│  - Record Keeping (Unified)                             │
│  - Scheduling Logic                                     │
│  - Daily Limits Tracking                                │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
             ▼                            ▼
┌─────────────────────────┐  ┌──────────────────────────┐
│  Stock Analysis System  │  │  Earnings Article System │
│  - Prophet Forecasting  │  │  - Earnings Data Collect │
│  - Technical Analysis   │  │  - Financial Processing  │
│  - Gemini Rewriter     │  │  - Gemini Writer        │
└─────────────────────────┘  └──────────────────────────┘
             │                            │
             └────────────┬───────────────┘
                          ▼
             ┌─────────────────────────┐
             │    WordPress Posts      │
             │  - Scheduled Publishing │
             │  - SEO Optimization     │
             │  - Feature Images       │
             └─────────────────────────┘
```

## Benefits

1. **Consistency** - Same quality and formatting across all article types
2. **Efficiency** - Unified workflow reduces complexity
3. **Flexibility** - Easy to switch article types per profile
4. **Scalability** - Add new article types without changing core logic
5. **Reliability** - Shared rotation and tracking ensures no duplicate authors or posts

## Future Enhancements

- [ ] Quarterly earnings calendar integration
- [ ] Automatic article type selection based on earnings date proximity
- [ ] Multi-ticker comparison earnings articles
- [ ] Earnings surprise analysis articles
- [ ] Sector-wide earnings trend articles

## Support

For issues or questions:
- Check logs in `logs/auto_publisher.log`
- Review Firestore state for user publishing history
- Test individual components before full publishing run
- Verify profile configuration includes `article_type` field
