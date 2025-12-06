"""
Sports News Article Importance Scoring System
Multi-factor algorithm to rank articles by public importance and readability demand
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set
import math
import logging
from collections import Counter, defaultdict

class ArticleImportanceScorer:
    def __init__(self):
        # High-impact keywords with weights (1-10 scale)
        self.keyword_weights = {
            # Transfer/Contract keywords (highest impact)
            'transfer': 10, 'signing': 9, 'contract': 8, 'deal': 7, 'move': 6,
            'bid': 8, 'offer': 7, 'target': 6, 'link': 5, 'interest': 4,
            
            # Breaking news keywords
            'breaking': 10, 'urgent': 9, 'confirmed': 8, 'official': 8,
            'exclusive': 7, 'latest': 6, 'update': 5,
            
            # Injury/Medical keywords
            'injury': 9, 'injured': 8, 'out': 7, 'surgery': 8, 'hospital': 9,
            'recovery': 6, 'fitness': 5, 'medical': 6,
            
            # Competition/Results keywords
            'final': 10, 'semi-final': 8, 'quarter-final': 7, 'derby': 9,
            'title': 9, 'championship': 8, 'cup': 7, 'league': 6,
            'relegation': 8, 'promotion': 7, 'playoff': 7,
            
            # Performance keywords
            'record': 9, 'milestone': 7, 'achievement': 6, 'best': 6, 'worst': 7,
            'debut': 6, 'retirement': 8, 'comeback': 7,
            
            # Controversy/Drama keywords
            'scandal': 10, 'controversy': 9, 'banned': 9, 'suspended': 8,
            'investigation': 8, 'charge': 8, 'fine': 7, 'appeal': 6,
            'dispute': 7, 'crisis': 8, 'shock': 7,
            
            # Score-related keywords
            'goal': 6, 'goals': 6, 'win': 5, 'victory': 6, 'defeat': 5,
            'draw': 4, 'loss': 5, 'score': 4, 'result': 4,
            
            # Manager/Coach keywords
            'manager': 7, 'coach': 6, 'sacked': 9, 'appointed': 7,
            'resign': 8, 'replacement': 6,
        }
        
        # Source authority rankings (1-10 scale)
        self.source_authority = {
            'BBC Sport': 10, 'BBC Cricket': 9, 'BBC': 9,
            'ESPN': 9, 'ESPN FC': 9, 'ESPN NBA': 9, 'ESPNCricinfo': 9,
            'Sky Sports': 9, 'Sky Sports Cricket': 8,
            'Guardian Football': 8, 'The Guardian': 8,
            'The Athletic': 8, 'The Athletic NBA': 8,
            'Reuters': 9, 'Associated Press': 9, 'AP': 9,
            'Yahoo Sports': 7, 'Yahoo Sports NBA': 7,
            'Goal.com': 6, 'Talksport': 6,
            'Mirror': 5, 'Sun': 4, 'Daily Mail': 5,
        }
        
        # Category importance multipliers
        self.category_multipliers = {
            'Breaking News': 2.0, 'News Story': 1.5, 'Transfer News': 1.8,
            'Match Report': 1.2, 'Report': 1.2, 'Analysis': 1.0,
            'Preview': 0.8, 'Review': 0.9, 'Opinion': 0.7,
            'Video': 0.6, 'Highlights': 0.5, 'Interview': 1.1,
            'Liveblog': 1.3, 'Live': 1.4
        }
        
        # Popular teams/entities (can be expanded)
        self.popular_teams = {
            # Premier League (top tier)
            'manchester united': 10, 'man utd': 10, 'united': 8,
            'liverpool': 10, 'arsenal': 9, 'chelsea': 9,
            'manchester city': 9, 'man city': 9, 'city': 7,
            'tottenham': 8, 'spurs': 8, 'newcastle': 7,
            
            # Other major teams
            'barcelona': 10, 'real madrid': 10, 'bayern munich': 9,
            'juventus': 8, 'psg': 8, 'ac milan': 7,
            
            # International teams
            'england': 9, 'brazil': 9, 'argentina': 9, 'france': 8,
            'germany': 8, 'spain': 8, 'italy': 7,
            
            # NBA teams (popular ones)
            'lakers': 9, 'warriors': 8, 'celtics': 8, 'heat': 7,
            'bulls': 7, 'knicks': 7,
            
            # Cricket teams
            'india': 9, 'australia': 8, 'england cricket': 8,
        }
        
        # Star players (can be expanded)
        self.star_players = {
            'messi': 10, 'ronaldo': 10, 'neymar': 9, 'mbappe': 9,
            'haaland': 9, 'salah': 8, 'kane': 8, 'benzema': 8,
            'lebron': 10, 'curry': 9, 'durant': 9, 'giannis': 8,
            'kohli': 9, 'root': 7, 'smith': 7, 'williamson': 7,
        }

    def calculate_content_score(self, title: str, summary: str) -> float:
        """Calculate score based on content keywords and quality"""
        text = f"{title} {summary}".lower()
        
        # Keyword scoring
        keyword_score = 0
        for keyword, weight in self.keyword_weights.items():
            if keyword in text:
                # Count occurrences and apply diminishing returns
                count = text.count(keyword)
                keyword_score += weight * (1 + 0.5 * (count - 1))
        
        # Content quality factors
        quality_score = 0
        
        # Title length (optimal 50-80 characters)
        title_len = len(title)
        if 50 <= title_len <= 80:
            quality_score += 2
        elif 30 <= title_len < 50 or 80 < title_len <= 100:
            quality_score += 1
        
        # Summary richness
        if summary:
            summary_len = len(summary)
            if summary_len > 100:
                quality_score += 3
            elif summary_len > 50:
                quality_score += 2
            elif summary_len > 20:
                quality_score += 1
        
        # Numbers in title (often indicate specific events/scores)
        if re.search(r'\d+', title):
            quality_score += 1
        
        return min(keyword_score + quality_score, 50)  # Cap at 50

    def calculate_source_authority_score(self, source_name: str) -> float:
        """Calculate score based on source credibility"""
        # Direct match
        if source_name in self.source_authority:
            return self.source_authority[source_name]
        
        # Partial match
        source_lower = source_name.lower()
        for source, score in self.source_authority.items():
            if source.lower() in source_lower or source_lower in source.lower():
                return score * 0.8  # Slightly reduce for partial match
        
        return 5  # Default moderate score

    def calculate_temporal_score(self, published_date: str, collected_date: str) -> float:
        """Calculate score based on article age and timing"""
        try:
            # Parse dates
            if published_date:
                # Handle different date formats
                if 'GMT' in published_date:
                    pub_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S GMT')
                else:
                    pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            else:
                pub_date = datetime.fromisoformat(collected_date)
            
            current_time = datetime.now()
            age_hours = (current_time - pub_date.replace(tzinfo=None)).total_seconds() / 3600
            
            # Recency scoring with decay
            if age_hours <= 1:
                return 10  # Very fresh
            elif age_hours <= 6:
                return 9   # Fresh
            elif age_hours <= 24:
                return 7   # Recent
            elif age_hours <= 48:
                return 5   # Somewhat recent
            elif age_hours <= 168:  # 1 week
                return 3   # Old
            else:
                return 1   # Very old
                
        except Exception:
            return 5  # Default score if date parsing fails

    def calculate_engagement_score(self, title: str, summary: str) -> float:
        """Calculate predicted engagement based on teams, players, and content type"""
        text = f"{title} {summary}".lower()
        engagement_score = 0
        
        # Team popularity scoring
        for team, score in self.popular_teams.items():
            if team in text:
                engagement_score += score * 0.8
        
        # Star player scoring
        for player, score in self.star_players.items():
            if player in text:
                engagement_score += score * 1.2  # Players often drive more engagement
        
        # Emotional/engaging content indicators
        emotional_words = ['shocking', 'amazing', 'incredible', 'devastating', 
                          'brilliant', 'disaster', 'triumph', 'heartbreak']
        for word in emotional_words:
            if word in text:
                engagement_score += 3
        
        # Question marks often increase engagement
        if '?' in title:
            engagement_score += 2
        
        # Superlatives
        superlatives = ['best', 'worst', 'greatest', 'biggest', 'smallest', 'first', 'last']
        for sup in superlatives:
            if sup in text:
                engagement_score += 1.5
        
        return min(engagement_score, 30)  # Cap at 30

    def calculate_category_multiplier(self, categories: List[str]) -> float:
        """Calculate category-based multiplier"""
        if not categories:
            return 1.0
        
        max_multiplier = 1.0
        for category in categories:
            multiplier = self.category_multipliers.get(category, 1.0)
            max_multiplier = max(max_multiplier, multiplier)
        
        return max_multiplier

    def detect_trending_topics(self, articles: List[Dict]) -> Dict[str, float]:
        """Detect trending topics and calculate boost factors"""
        # Extract keywords from recent articles (last 24 hours)
        recent_articles = []
        current_time = datetime.now()
        
        for article in articles:
            try:
                if article.get('collected_date'):
                    collected = datetime.fromisoformat(article['collected_date'])
                    if (current_time - collected).total_seconds() < 86400:  # 24 hours
                        recent_articles.append(article)
            except:
                continue
        
        # Count keyword frequency in recent articles
        keyword_counts = Counter()
        total_recent = len(recent_articles)
        
        for article in recent_articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            words = re.findall(r'\b\w{4,}\b', text)  # Words with 4+ characters
            keyword_counts.update(words)
        
        # Calculate trending boosts
        trending_boosts = {}
        for keyword, count in keyword_counts.items():
            if count >= 3 and total_recent > 0:  # Minimum threshold
                frequency = count / total_recent
                trending_boosts[keyword] = min(frequency * 10, 2.0)  # Cap at 2x boost
        
        return trending_boosts

    def calculate_importance_score(self, article: Dict, trending_boosts: Dict[str, float] = None) -> Dict:
        """Calculate comprehensive importance score for an article"""
        if trending_boosts is None:
            trending_boosts = {}
        
        # Extract article data
        title = article.get('title', '')
        summary = article.get('summary', '')
        source = article.get('source_name', '')
        categories = article.get('categories', [])
        published_date = article.get('published_date', '')
        collected_date = article.get('collected_date', '')
        
        # Calculate individual scores
        content_score = self.calculate_content_score(title, summary)
        source_score = self.calculate_source_authority_score(source)
        temporal_score = self.calculate_temporal_score(published_date, collected_date)
        engagement_score = self.calculate_engagement_score(title, summary)
        category_multiplier = self.calculate_category_multiplier(categories)
        
        # Calculate trending boost
        text = f"{title} {summary}".lower()
        trending_boost = 1.0
        for keyword, boost in trending_boosts.items():
            if keyword in text:
                trending_boost = max(trending_boost, 1 + boost)
        
        # Weighted combination
        base_score = (
            content_score * 0.4 +
            source_score * 0.25 +
            temporal_score * 0.2 +
            engagement_score * 0.15
        )
        
        # Apply multipliers
        final_score = base_score * category_multiplier * trending_boost
        
        # Create detailed scoring breakdown
        scoring_details = {
            'final_score': round(final_score, 2),
            'base_score': round(base_score, 2),
            'breakdown': {
                'content_score': round(content_score, 2),
                'source_authority': round(source_score, 2),
                'temporal_factor': round(temporal_score, 2),
                'engagement_predictor': round(engagement_score, 2),
                'category_multiplier': round(category_multiplier, 2),
                'trending_boost': round(trending_boost, 2)
            },
            'importance_tier': self.get_importance_tier(final_score)
        }
        
        return scoring_details

    def get_importance_tier(self, score: float) -> str:
        """Classify articles into importance tiers"""
        if score >= 80:
            return 'Critical'
        elif score >= 60:
            return 'High'
        elif score >= 40:
            return 'Medium'
        elif score >= 20:
            return 'Low'
        else:
            return 'Minimal'

    def score_all_articles(self, json_file_path: str) -> Dict:
        """Score all articles in the database"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = data.get('articles', [])
            if not articles:
                return {'error': 'No articles found'}
            
            # Detect trending topics
            trending_boosts = self.detect_trending_topics(articles)
            
            # Score each article
            scored_articles = []
            tier_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Minimal': 0}
            
            for article in articles:
                scoring = self.calculate_importance_score(article, trending_boosts)
                
                # Add scoring to article
                article_with_score = article.copy()
                article_with_score['importance_score'] = scoring['final_score']
                article_with_score['importance_tier'] = scoring['importance_tier']
                article_with_score['scoring_breakdown'] = scoring['breakdown']
                
                scored_articles.append(article_with_score)
                tier_counts[scoring['importance_tier']] += 1
            
            # Sort by importance score (descending)
            scored_articles.sort(key=lambda x: x['importance_score'], reverse=True)
            
            # Update data structure
            data['articles'] = scored_articles
            data['metadata']['scoring_applied'] = datetime.now().isoformat()
            data['metadata']['trending_keywords'] = list(trending_boosts.keys())
            data['metadata']['importance_distribution'] = tier_counts
            
            return data
            
        except Exception as e:
            logging.error(f"Error scoring articles: {e}")
            return {'error': str(e)}

    def save_scored_articles(self, scored_data: Dict, output_file: str = None):
        """Save scored articles to JSON file"""
        if output_file is None:
            output_file = "sports_news_database_scored.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(scored_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Scored articles saved to {output_file}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving scored articles: {e}")
            return False

    def generate_scoring_report(self, scored_data: Dict) -> str:
        """Generate a comprehensive scoring report"""
        if 'error' in scored_data:
            return f"Error in scoring: {scored_data['error']}"
        
        articles = scored_data['articles']
        metadata = scored_data['metadata']
        tier_counts = metadata.get('importance_distribution', {})
        trending = metadata.get('trending_keywords', [])
        
        report_lines = []
        report_lines.append("="*60)
        report_lines.append("ARTICLE IMPORTANCE SCORING REPORT")
        report_lines.append("="*60)
        report_lines.append(f"Total Articles Scored: {len(articles)}")
        report_lines.append(f"Scoring Applied: {metadata.get('scoring_applied', 'Unknown')}")
        report_lines.append("")
        
        # Importance distribution
        report_lines.append("IMPORTANCE DISTRIBUTION:")
        report_lines.append("-" * 30)
        for tier, count in tier_counts.items():
            percentage = (count / len(articles)) * 100 if articles else 0
            report_lines.append(f"{tier:>8}: {count:>4} articles ({percentage:5.1f}%)")
        report_lines.append("")
        
        # Trending topics
        if trending:
            report_lines.append("TRENDING KEYWORDS:")
            report_lines.append("-" * 20)
            report_lines.append(", ".join(trending[:10]))  # Show top 10
            report_lines.append("")
        
        # Top 10 articles
        report_lines.append("TOP 10 MOST IMPORTANT ARTICLES:")
        report_lines.append("-" * 40)
        for i, article in enumerate(articles[:10], 1):
            score = article.get('importance_score', 0)
            tier = article.get('importance_tier', 'Unknown')
            title = article.get('title', 'No title')[:60]
            source = article.get('source_name', 'Unknown')
            
            report_lines.append(f"{i:2d}. [{tier}] Score: {score:5.1f} | {source}")
            report_lines.append(f"    {title}...")
            report_lines.append("")
        
        return "\n".join(report_lines)

def main():
    """Main function to score articles"""
    import os
    
    # File paths
    input_file = "sports_news_database.json"
    output_file = "sports_news_database_scored.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return
    
    print("🏆 Sports News Article Importance Scorer")
    print("="*50)
    print("Analyzing articles and calculating importance scores...")
    
    # Initialize scorer
    scorer = ArticleImportanceScorer()
    
    # Score all articles
    scored_data = scorer.score_all_articles(input_file)
    
    if 'error' in scored_data:
        print(f"Error: {scored_data['error']}")
        return
    
    # Save scored articles
    success = scorer.save_scored_articles(scored_data, output_file)
    
    if success:
        # Generate and display report
        report = scorer.generate_scoring_report(scored_data)
        print("\n" + report)
        
        print(f"\n✅ Articles scored and saved to: {output_file}")
        print(f"📊 {len(scored_data['articles'])} articles processed")
        
        # Show distribution
        dist = scored_data['metadata'].get('importance_distribution', {})
        print(f"📈 Critical: {dist.get('Critical', 0)}, High: {dist.get('High', 0)}, Medium: {dist.get('Medium', 0)}")
    else:
        print("❌ Error saving scored articles")

if __name__ == "__main__":
    main()