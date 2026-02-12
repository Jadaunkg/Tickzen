# Perplexity AI Client - SEO Enhancement Guide

## ✅ Errors Fixed

### 1. **Duplicate Parameter Error**
- **Issue**: `_call_perplexity_api()` had duplicate `domain_filter` and `sport_context` parameters
- **Fixed**: Removed duplicates - now has clean parameter list

### 2. **Duplicate Method Error**
- **Issue**: `_extract_sources()` method was defined twice
- **Fixed**: Removed duplicate definition

---

## 🎯 New SEO Keyword Extraction Feature

### Overview
The Perplexity AI client now **automatically extracts highly searched SEO keywords** from research content and provides keyword-rich sentences for article optimization.

### How It Works

#### 1. **Automatic Category Detection**
When a user selects an article from any category page, the system:
- Detects the sport category (football, cricket, basketball, etc.)
- Automatically routes to the appropriate sport-specific research method
- Uses 20 dedicated domains for that sport

#### 2. **Sport-Specific Research Methods**
Three specialized research methods with dedicated domains:

```python
collect_football_research_for_headline()    # 20 football-specific domains
collect_cricket_research_for_headline()     # 20 cricket-specific domains
collect_basketball_research_for_headline()  # 20 basketball-specific domains
```

#### 3. **SEO Keyword Extraction Process**

After collecting research, the system:

**a) Extracts Keywords:**
- Single words (highly relevant terms)
- 2-word phrases (bigrams) - better for SEO
- Prioritizes keywords that appear in the headline
- Filters out common stop words

**b) Returns:**
- **Top 10 SEO keywords** - most relevant search terms
- **Keyword-rich sentences** - 1-2 sentences containing each top keyword
- **Top keyword** - the single most important keyword
- **Headline-relevant keywords** - keywords that already appear in headline

---

## 📊 Usage in Article Generation System

### Research Data Structure

```python
research_data = {
    'headline': 'Original article headline',
    'source': 'ESPN',
    'category': 'football',
    'sport_type': 'football',
    'compiled_sources': [...],
    'compiled_citations': [...],
    
    # NEW: SEO Optimization Data
    'seo_optimization': {
        'seo_keywords': [
            'transfer window',
            'manchester united',
            'premier league',
            'record signing',
            'contract',
            ...
        ],
        'keyword_sentences': {
            'transfer window': 'Manchester United completed their record signing during the summer transfer window.',
            'premier league': 'The club aims to strengthen their Premier League title challenge with this acquisition.',
            ...
        },
        'top_keyword': 'transfer window',
        'headline_relevant_keywords': ['manchester', 'united', 'transfer']
    }
}
```

### How to Use SEO Data for Article Optimization

#### 1. **Optimize Main Headline**
```python
seo_data = research_data['seo_optimization']
top_keywords = seo_data['seo_keywords'][:3]  # Top 3 keywords

# Example: Original headline: "Manchester United Signs New Player"
# Optimized: "Manchester United Transfer Window: Record Premier League Signing Completed"
# Includes: 'transfer window', 'manchester united', 'premier league' - all highly searched terms
```

#### 2. **Optimize Article Content**
```python
# Extract keyword-rich sentences to include in article
keyword_sentences = seo_data['keyword_sentences']

# Use these sentences as basis for article paragraphs
# They already contain highly searched keywords naturally
for keyword, sentence in keyword_sentences.items():
    # Incorporate these sentences into your article content
    print(f"Include in content: {sentence}")
```

#### 3. **SEO Meta Tags**
```python
# Use keywords for meta tags, descriptions, tags
meta_keywords = ', '.join(seo_data['seo_keywords'][:5])
meta_description = list(seo_data['keyword_sentences'].values())[0]  # First keyword sentence
```

---

## 🔄 Automatic Workflow

### When User Selects Article:

```
1. User selects article from category-specific page (e.g., Cricket page)
   ↓
2. System detects category: "cricket"
   ↓
3. Automatic routing: collect_cricket_research_for_headline() is called
   ↓
4. Uses 20 cricket-specific domains for research
   ↓
5. Perplexity AI gathers research with SEO-optimized queries
   ↓
6. System extracts SEO keywords from research content
   ↓
7. Returns research + SEO data with:
   - Top 10 relevant keywords
   - Keyword-rich sentences
   - Top keyword for headline optimization
   ↓
8. Article generation uses this data to create SEO-optimized content
```

---

## 📈 SEO Query Enhancements

All sport-specific queries now request:
- **Popular search terms** people use to find this type of news
- **Trending keywords** related to the topic
- **Key names and events** that drive searches

Example from Football Query:
```
**SEO Optimization:**
- Include popular search terms people use to find this type of news
- Mention key player names, team names, and event names that drive searches
- Use terminology that appears in trending football/soccer searches
```

---

## 💡 Benefits

### 1. **Better Search Rankings**
- Articles include highly searched keywords naturally
- Keywords are extracted from actual news content, not artificially inserted

### 2. **Sport-Specific Relevance**
- Each sport gets dedicated research domains
- Better quality sources per category

### 3. **Automated Category Detection**
- No manual category selection needed
- System automatically uses correct sport-specific method

### 4. **SEO-Optimized Headlines**
- Top keywords available for headline optimization
- Naturally integrate trending search terms

### 5. **Keyword-Rich Content**
- Sentences containing keywords provided
- Easy to incorporate into article naturally

---

## 🎯 Example: Cricket Article

### Original Research Request:
```python
headline = "Virat Kohli scores century in India vs Australia Test match"
category = "cricket"
```

### Automatic Processing:
1. Detects category: "cricket"
2. Calls: `collect_cricket_research_for_headline()`
3. Uses 20 cricket domains: espncricinfo.com, cricbuzz.com, wisden.com, etc.
4. Research collected with cricket-specific query template

### SEO Keywords Extracted:
```python
{
    'seo_keywords': [
        'virat kohli',
        'test match',
        'india australia',
        'century',
        'run chase',
        'innings',
        'batting average',
        'test series',
        'match result',
        'cricket score'
    ],
    'keyword_sentences': {
        'virat kohli': 'Virat Kohli reached his 29th Test century with a masterful innings against Australia.',
        'test match': 'The Test match saw India dominate with both bat and ball.',
        'india australia': 'India vs Australia Test series continues with high stakes.'
    },
    'top_keyword': 'virat kohli',
    'headline_relevant_keywords': ['virat', 'kohli', 'india', 'australia']
}
```

### Optimized Article:
**Headline**: "Virat Kohli Test Match Century: India vs Australia Run Chase Dominates Cricket Score"
- Contains: virat kohli, test match, india australia, run chase, cricket score

**Content**: Uses keyword-rich sentences as foundation
- Natural integration of all top keywords
- SEO-optimized without keyword stuffing

---

## 🔍 Logging Output

When research completes, you'll see:
```
✅ Cricket research complete!
   📚 Sources collected: 15
   🔗 Citations: 12
   🎯 Sport-specific domains: 20
   🔍 SEO Keywords extracted: 10
   🎯 Top keyword: virat kohli
   📰 Headline-relevant: virat, kohli, india
```

---

## 🚀 Integration with Article Generation

Use the SEO data when generating articles:

```python
# In your article generation code:
research_data = perplexity_client.collect_research_for_headline(
    headline=article['title'],
    source=article['source'],
    category=article['category']  # Automatically routes to correct method
)

# Extract SEO data
seo_optimization = research_data.get('seo_optimization', {})

# Optimize headline
optimized_headline = create_seo_headline(
    original=article['title'],
    keywords=seo_optimization['seo_keywords'][:3]
)

# Generate content with keyword focus
article_content = generate_article(
    research=research_data,
    keywords=seo_optimization['seo_keywords'],
    keyword_sentences=seo_optimization['keyword_sentences']
)
```

---

## ✨ Summary

**Fixed Issues:**
- ✅ Duplicate parameter errors resolved
- ✅ Duplicate method definitions removed

**New Features:**
- ✅ Automatic sport category detection
- ✅ SEO keyword extraction (top 10 keywords)
- ✅ Keyword-rich sentence extraction
- ✅ Headline-relevant keyword identification
- ✅ SEO-optimized query templates
- ✅ Automatic logging of SEO data

**Result:**
Your articles will now be **highly optimized for search engines** with naturally integrated keywords that people actually search for on Google!
