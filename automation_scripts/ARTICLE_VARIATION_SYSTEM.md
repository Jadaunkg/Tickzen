# Article Variation System Documentation

## Overview

The Article Variation System allows the **same ticker to publish different versions of articles** when published multiple times on the **same site**. This prevents duplicate content issues while allowing maximum flexibility for multi-site publishing.

## Problem Solved

### Old Behavior (Incorrect):
- Same ticker → Skip if already published on this site
- Result: Lost publishing opportunities, inflexible system

### New Behavior (Correct):
- Same ticker published on **Site A** → Generates **Version 1**
- Same ticker published **again on Site A** → Generates **Version 2** (different wording/perspective)
- Same ticker published on **Site B** → Generates **Version 1** (fresh article for new site)
- Result: Unique content for each publish, no duplicate content penalties

## Key Concept

**✅ ALLOWED: Same ticker on multiple sites** (each site gets Version 1)  
**✅ ALLOWED: Same ticker republished on same site** (generates Variation 2, 3, etc.)  
**❌ PREVENTED: Exact duplicate content on same domain**

## How It Works

### 1. Per-Profile Tracking
```python
state['ticker_publish_count_by_profile'][profile_id][ticker] = count
```
- Tracks how many times each ticker has been published per profile (site)
- Each site has independent counts
- Resets daily

### 2. Variation Number Calculation
```python
# First publish on Site A
variation_number = 0  # Version 1

# Second publish on Site A (same ticker)
variation_number = 1  # Version 2

# First publish on Site B (same ticker)
variation_number = 0  # Version 1 (different site!)
```

### 3. Article Generation Differences

#### Stock Analysis Articles
```python
# Different temperature for each variation
config.temperature = 0.7   # Base (variation 0)
config.temperature = 0.85  # Variation 1
config.temperature = 1.0   # Variation 2
```

#### Earnings Articles
```python
# Same temperature adjustment + prompt instructions
config.temperature = 0.7 + (variation_number * 0.15)
```

### 4. Prompt Modifications

**Variation 0 (First Version):**
- Standard prompt
- Temperature: 0.7
- Focus: Comprehensive analysis

**Variation 1 (Second Version):**
- Adds variation instructions to prompt:
  * "Use DIFFERENT wording and explanations"
  * "Present same data from fresh angle"
  * "Change sentence structures and flow"
  * "Focus on different aspects (e.g., risks vs opportunities)"
- Temperature: 0.85
- Focus: Alternative perspective

**Variation 2 (Third Version):**
- Same variation instructions with more emphasis
- Temperature: 1.0 (maximum diversity)
- Focus: Maximum differentiation

## Structure Preservation

**CRITICAL:** All variations maintain the **exact same 23-section structure**:

✅ Same sections (Executive Summary, Revenue Analysis, etc.)  
✅ Same heading hierarchy (h2 → h3 → h4)  
✅ Same data points covered  
✅ Same external links requirement (3-4 reputable sources)  

❌ Different wording and explanations  
❌ Different perspectives and emphasis  
❌ Different sentence structures  

## Code Flow

### 1. Auto Publisher (`auto_publisher.py`)
```python
# Check if ticker already published on this site
if ticker in state['published_tickers_log_by_profile'][profile_id]:
    # Get variation number (how many times already published)
    variation_number = state['ticker_publish_count_by_profile'][profile_id].get(ticker, 0) + 1
    msg = f"Generating VARIATION #{variation_number + 1}"
else:
    variation_number = 0

# Pass to generation system
article_html, title, metadata = generate_article(
    ticker=ticker,
    variation_number=variation_number  # NEW!
)

# After successful publish
state['ticker_publish_count_by_profile'][profile_id][ticker] = current_count + 1
```

### 2. Stock Analysis Pipeline (`article_rewriter.py`)
```python
def generate_article_from_pipeline(..., variation_number=0):
    # Pass to rewriter
    article_html, metadata = rewriter.rewrite_report(
        html_report=report_html,
        ticker=ticker,
        company_name=company_name,
        variation_number=variation_number
    )

def rewrite_report(..., variation_number=0):
    # Adjust temperature
    config.temperature = min(1.0, 0.7 + (variation_number * 0.15))
    
    # Add variation instructions to prompt
    if variation_number > 0:
        prompt = add_variation_instructions(prompt, variation_number)
    
    response = model.generate_content(prompt, generation_config=config)
```

### 3. Earnings Pipeline (`gemini_earnings_writer.py`)
```python
def generate_complete_report(..., variation_number=0):
    # Pass to Gemini generator
    article_html = self.generate_article_with_gemini(
        ticker, 
        earnings_context, 
        variation_number=variation_number
    )

def generate_article_with_gemini(..., variation_number=0):
    # Adjust temperature
    config.temperature = min(1.0, 0.7 + (variation_number * 0.15))
    
    # Add variation instructions to prompt
    if variation_number > 0:
        prompt += variation_instructions
    
    response = self.model.generate_content(prompt, generation_config=config)
```

## State Management

### Daily Reset
```python
# firestore_state_manager.py
if new_day:
    # Reset publish counts for fresh variations
    for profile in state['ticker_publish_count_by_profile']:
        state['ticker_publish_count_by_profile'][profile] = {}
```

### Firestore Compatibility
```python
# ticker_publish_count_by_profile stored as:
{
    "profile_123": {
        "AAPL": 2,  # Published twice
        "MSFT": 1,  # Published once
        "TSLA": 3   # Published three times (variations!)
    }
}
```

## Testing Scenarios

### Scenario 1: Single Site, Multiple Publishes
```
Site A: AAPL → Variation 0 ✅
Site A: AAPL → Variation 1 ✅ (different content!)
Site A: AAPL → Variation 2 ✅ (even more different!)
```

### Scenario 2: Multiple Sites, Same Ticker
```
Site A: AAPL → Variation 0 ✅
Site B: AAPL → Variation 0 ✅ (independent tracking!)
Site C: AAPL → Variation 0 ✅
```

### Scenario 3: Multiple Sites + Republishing
```
Site A: AAPL → Variation 0 ✅
Site A: AAPL → Variation 1 ✅
Site B: AAPL → Variation 0 ✅
Site B: AAPL → Variation 1 ✅
```

## Benefits

1. **No Duplicate Content**: Each publish generates unique content
2. **SEO Safe**: Different articles = no penalties
3. **Flexible Publishing**: Republish same ticker as needed
4. **Multi-Site Support**: Each site gets independent tracking
5. **Daily Fresh Start**: Counts reset overnight for new variations
6. **Quality Maintained**: Same 23-section structure preserved
7. **Data Freshness**: All variations use 2-3 day fresh data
8. **Professional Quality**: Temperature adjustments maintain quality while varying style

## Monitoring

### Log Messages
```
[ARTICLE_VARIATION] Ticker 'AAPL' already published 1 time(s) on 'Site A'. Generating VARIATION #2.
[VARIATION_TRACKER] AAPL published 2 time(s) on Site A
Temperature set to 0.85 for variation #1
```

### Status Messages
```
"Variation" - Generating different version
"Scheduled" - Successfully published variation
```

## Configuration

No configuration needed! System automatically:
- Tracks publish counts per profile
- Calculates variation numbers
- Adjusts temperatures
- Modifies prompts
- Resets daily

## Comparison with Old System

| Feature | Old (Global Tracking) | New (Variation System) |
|---------|----------------------|------------------------|
| Same ticker on Site A | ✅ Allowed | ✅ Allowed |
| Same ticker on Site B | ❌ Blocked | ✅ Allowed |
| Republish on Site A | ❌ Skipped | ✅ Generates Variation |
| Content uniqueness | N/A | ✅ Different versions |
| Multi-site support | ❌ Limited | ✅ Full support |
| Flexibility | ❌ Low | ✅ High |

## Summary

The Article Variation System **removes publishing restrictions** while **preventing duplicate content**. It allows maximum flexibility for multi-site publishing and handles republishing scenarios intelligently by generating unique variations that maintain structural consistency while varying presentation and language.

**Key Principle**: Same structure, different story. Same data, different perspective.
