"""
Sports News Categorization System
Automatically categorizes news into Cricket, Football, and Basketball
Creates separate databases for each sport category
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Set
import os
from pathlib import Path

class SportsNewsCategorizer:
    def __init__(self, source_database: str = "sports_news_database.json"):
        self.source_database = source_database
        
        # Ensure source_database is a Path object
        if isinstance(source_database, str):
            self.source_database = Path(source_database)
        else:
            self.source_database = source_database
            
        # Get data directory - always use Sports_Article_Automation/data
        if str(self.source_database).endswith('sports_news_database.json'):
            self.data_dir = Path(self.source_database).parent
        else:
            # Default to Sports_Article_Automation/data
            project_root = Path(__file__).parent.parent.parent
            self.data_dir = project_root / "Sports_Article_Automation" / "data"
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.categories = {
            'cricket': {
                'filename': self.data_dir / 'cricket_news_database.json',
                'keywords': {
                    # Cricket-specific terms
                    'cricket', 'wicket', 'wickets', 'batting', 'bowling', 'bowler', 'batsman', 'batsmen',
                    'innings', 'over', 'overs', 'run', 'runs', 'century', 'half-century', 'duck',
                    'stumps', 'catch', 'caught', 'lbw', 'boundary', 'six', 'four', 'maiden',
                    
                    # Cricket formats
                    'test', 'odi', 'twenty20', 't20', 'ipl', 'county', 'ashes', 'world cup cricket',
                    
                    # Cricket positions
                    'captain', 'keeper', 'wicket-keeper', 'all-rounder', 'spinner', 'pace',
                    
                    # Cricket competitions
                    'bbl', 'psl', 'cpl', 'hundred', 'county championship', 'ranji',
                    
                    # Cricket teams/boards
                    'england cricket', 'india cricket', 'australia cricket', 'pakistan cricket',
                    'south africa cricket', 'new zealand cricket', 'sri lanka cricket', 'bangladesh cricket',
                    'west indies cricket', 'afghanistan cricket', 'ireland cricket',
                    
                    # Cricket venues
                    'lords', 'oval', 'old trafford', 'headingley', 'trent bridge', 'edgbaston',
                    'mcg', 'scg', 'waca', 'gabba', 'adelaide oval',
                    
                    # Cricket personalities (add major current players)
                    'kohli', 'sharma', 'dhoni', 'bumrah', 'ashwin', 'jadeja',
                    'root', 'stokes', 'anderson', 'broad', 'bairstow',
                    'smith', 'warner', 'cummins', 'starc', 'hazlewood',
                    'williamson', 'boult', 'southee',
                    'babar', 'rizwan', 'shaheen'
                },
                'sources': {
                    'espncricinfo', 'bbc cricket', 'sky sports cricket', 'cricket australia',
                    'cricinfo', 'wisden', 'cricket world'
                }
            },
            
            'football': {
                'filename': self.data_dir / 'football_news_database.json', 
                'keywords': {
                    # Football terms
                    'football', 'soccer', 'goal', 'goals', 'penalty', 'free kick', 'corner',
                    'offside', 'yellow card', 'red card', 'referee', 'var', 'substitute',
                    'transfer', 'signing', 'contract', 'loan', 'bid', 'deal',
                    
                    # Positions
                    'goalkeeper', 'defender', 'midfielder', 'striker', 'winger', 'forward',
                    'centre-back', 'full-back', 'attacking midfielder', 'defensive midfielder',
                    
                    # Competitions
                    'premier league', 'championship', 'fa cup', 'carabao cup', 'community shield',
                    'champions league', 'europa league', 'conference league', 'uefa',
                    'la liga', 'serie a', 'bundesliga', 'ligue 1', 'eredivisie',
                    'world cup', 'euros', 'copa america', 'african cup',
                    
                    # Teams (major clubs)
                    'manchester united', 'manchester city', 'liverpool', 'arsenal', 'chelsea',
                    'tottenham', 'newcastle', 'brighton', 'west ham', 'aston villa',
                    'real madrid', 'barcelona', 'atletico madrid', 'sevilla',
                    'juventus', 'inter milan', 'ac milan', 'napoli', 'roma',
                    'bayern munich', 'borussia dortmund', 'rb leipzig',
                    'psg', 'monaco', 'marseille', 'lyon',
                    
                    # Football personalities
                    'messi', 'ronaldo', 'mbappe', 'haaland', 'neymar', 'benzema',
                    'salah', 'kane', 'son', 'de bruyne', 'modric', 'lewandowski',
                    'guardiola', 'klopp', 'arteta', 'ancelotti', 'mourinho'
                },
                'sources': {
                    'bbc sport football', 'bbc football', 'guardian football', 'espn fc',
                    'sky sports football', 'sky sports premier league', 'football365'
                }
            },
            
            'basketball': {
                'filename': self.data_dir / 'basketball_news_database.json',
                'keywords': {
                    # Basketball terms
                    'basketball', 'nba', 'wnba', 'ncaa basketball', 'euroleague',
                    'dunk', 'three-pointer', 'free throw', 'rebound', 'assist', 'steal',
                    'block', 'foul', 'technical', 'flagrant', 'playoff', 'playoffs',
                    'draft', 'rookie', 'veteran', 'trade', 'waiver',
                    
                    # Positions
                    'point guard', 'shooting guard', 'small forward', 'power forward', 'center',
                    'guard', 'forward', 'sixth man',
                    
                    # NBA Teams
                    'lakers', 'warriors', 'celtics', 'heat', 'bulls', 'knicks', 'nets',
                    'sixers', 'bucks', 'raptors', 'magic', 'hawks', 'hornets',
                    'pistons', 'pacers', 'cavaliers', 'wizards',
                    'nuggets', 'timberwolves', 'thunder', 'blazers', 'jazz', 'kings',
                    'suns', 'clippers', 'mavericks', 'rockets', 'spurs', 'grizzlies', 'pelicans',
                    
                    # Basketball personalities
                    'lebron', 'curry', 'durant', 'giannis', 'jokic', 'tatum', 'doncic',
                    'embiid', 'kawhi', 'davis', 'harden', 'westbrook', 'paul', 'lillard',
                    'jimmy butler', 'kyrie', 'klay', 'green', 'thompson',
                    
                    # Competitions
                    'nba finals', 'all-star', 'mvp', 'dpoy', 'roty', 'sixth man award',
                    'march madness', 'final four', 'elite eight'
                },
                'sources': {
                    'the athletic nba', 'yahoo sports nba', 'espn nba', 'nba.com',
                    'bleacher report', 'sportingnews nba'
                }
            }
        }
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def load_source_database(self) -> Dict:
        """Load the main sports news database"""
        try:
            with open(self.source_database, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Source database {self.source_database} not found")
            return {'articles': [], 'metadata': {}}

    def categorize_article(self, article: Dict) -> str:
        """
        Categorize a single article into Cricket, Football, or Basketball ONLY
        Returns category name or 'uncategorized' (will be discarded)
        
        STRICT RULES:
        - Only Cricket, Football, Basketball are valid categories
        - Articles must clearly belong to one of these sports
        - Uncategorized articles are NOT saved (other sports filtered out)
        """
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower() 
        source = article.get('source_name', '').lower()
        
        # Combine all text for analysis
        text_content = f"{title} {summary}"
        
        # Score each category
        category_scores = {}
        
        for category, config in self.categories.items():
            score = 0
            
            # Source-based scoring (highest priority - very strong signal)
            for source_keyword in config['sources']:
                if source_keyword.lower() in source:
                    score += 15  # Increased weight for source match
                    break
            
            # Keyword-based scoring with weighted importance
            for keyword in config['keywords']:
                # Exact word matches (not partial)
                if re.search(rf'\b{re.escape(keyword.lower())}\b', text_content):
                    # Weight by keyword importance and specificity
                    if len(keyword) > 10:  # Very specific keywords
                        score += 5
                    elif len(keyword) > 8:  # Longer keywords are more specific
                        score += 3
                    elif len(keyword) > 5:
                        score += 2
                    else:
                        score += 1
            
            category_scores[category] = score
        
        # Return category with highest score, but ONLY if confident
        if category_scores:
            max_score = max(category_scores.values())
            
            # Stricter threshold: must score at least 5 to be categorized
            if max_score >= 5:
                best_category = max(category_scores, key=category_scores.get)
                
                # Check for ambiguous categorization (two categories very close)
                sorted_scores = sorted(category_scores.values(), reverse=True)
                if len(sorted_scores) >= 2:
                    # If second best is within 30% of best, it's ambiguous - reject
                    if sorted_scores[1] >= (sorted_scores[0] * 0.7):
                        logging.debug(f"Ambiguous categorization rejected: {article.get('title', '')[:50]}")
                        return 'uncategorized'
                
                return best_category
        
        # Not confident enough in any category - reject
        return 'uncategorized'
        if category_scores:
            max_score = max(category_scores.values())
            if max_score >= 3:  # Minimum threshold for categorization
                return max(category_scores, key=category_scores.get)
        
        return 'uncategorized'

    def categorize_all_articles(self, save_individual_files: bool = True) -> Dict:
        """Categorize all articles and optionally save to individual category files"""
        
        # Load source database
        source_db = self.load_source_database()
        articles = source_db.get('articles', [])
        
        if not articles:
            logging.warning("No articles found in source database")
            return {}
        
        # Initialize category databases
        categorized_data = {}
        for category in self.categories.keys():
            categorized_data[category] = {
                'articles': [],
                'metadata': {
                    'category': category,
                    'created_date': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'total_articles': 0,
                    'sources': [],
                    'parent_database': str(self.source_database)
                }
            }
        
        # Add uncategorized bucket
        categorized_data['uncategorized'] = {
            'articles': [],
            'metadata': {
                'category': 'uncategorized',
                'created_date': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'total_articles': 0,
                'sources': [],
                'parent_database': str(self.source_database)
            }
        }
        
        # Categorize each article
        categorization_stats = {
            'total_articles': len(articles),
            'categorized': {cat: 0 for cat in self.categories.keys()},
            'uncategorized': 0
        }
        
        logging.info(f"Categorizing {len(articles)} articles...")
        
        for article in articles:
            category = self.categorize_article(article)
            
            # Add category info to article
            article_copy = article.copy()
            article_copy['category'] = category
            article_copy['categorization_date'] = datetime.now().isoformat()
            
            # Add to appropriate category
            categorized_data[category]['articles'].append(article_copy)
            categorization_stats['categorized'][category] = categorization_stats['categorized'].get(category, 0) + 1
            
            if category == 'uncategorized':
                categorization_stats['uncategorized'] += 1
        
        # Update metadata for each category
        for category, data in categorized_data.items():
            data['metadata']['total_articles'] = len(data['articles'])
            data['metadata']['sources'] = list(set(article.get('source_name', '') for article in data['articles']))
            
            # Copy relevant metadata from source database
            if 'metadata' in source_db:
                source_meta = source_db['metadata']
                data['metadata']['importance_distribution'] = self.calculate_category_importance_distribution(data['articles'])
                data['metadata']['source_database_info'] = {
                    'last_updated': source_meta.get('last_updated'),
                    'scoring_applied': source_meta.get('scoring_applied'),
                    'last_deduplication': source_meta.get('last_deduplication')
                }
        
        # Save individual category files (ONLY cricket, football, basketball)
        if save_individual_files:
            for category in self.categories.keys():
                filename = self.categories[category]['filename']
                self.save_category_database(categorized_data[category], filename)
                logging.info(f"✅ Saved {category}: {len(categorized_data[category]['articles'])} articles")
        
        # DO NOT save uncategorized articles - they are filtered out
        # Uncategorized = other sports we don't support (tennis, hockey, etc.)
        if categorization_stats['uncategorized'] > 0:
            logging.info(f"🗑️  Filtered out {categorization_stats['uncategorized']} uncategorized articles (other sports)")
        
        # Log results
        logging.info("=" * 70)
        logging.info("CATEGORIZATION RESULTS (CRICKET, FOOTBALL, BASKETBALL ONLY):")
        logging.info("=" * 70)
        for category, count in categorization_stats['categorized'].items():
            if count > 0 and category in self.categories:
                logging.info(f"  ✅ {category.capitalize()}: {count} articles")
        if categorization_stats['uncategorized'] > 0:
            logging.info(f"  🗑️  Filtered out: {categorization_stats['uncategorized']} articles (other sports)")
        logging.info("=" * 70)
        
        return {
            'categorized_data': categorized_data,
            'stats': categorization_stats
        }

    def calculate_category_importance_distribution(self, articles: List[Dict]) -> Dict:
        """Calculate importance distribution for a category"""
        distribution = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Minimal': 0}
        
        for article in articles:
            tier = article.get('importance_tier', 'Minimal')
            distribution[tier] = distribution.get(tier, 0) + 1
        
        return distribution

    def save_category_database(self, category_data: Dict, filename):
        """Save a category database to file"""
        try:
            # Convert Path object to string if needed
            filepath = str(filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(category_data, f, indent=2, ensure_ascii=False)
            logging.info(f"Saved {len(category_data['articles'])} articles to {filepath}")
        except Exception as e:
            logging.error(f"Error saving {filename}: {e}")

    def get_category_summary(self) -> Dict:
        """Get summary of all category databases"""
        summary = {}
        
        for category, config in self.categories.items():
            filename = config['filename']
            # Convert Path to string if needed
            filepath = str(filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    summary[category] = {
                        'filename': filepath,
                        'article_count': len(data.get('articles', [])),
                        'last_updated': data.get('metadata', {}).get('last_updated'),
                        'importance_distribution': data.get('metadata', {}).get('importance_distribution', {}),
                        'top_sources': data.get('metadata', {}).get('sources', [])[:5]
                    }
            except FileNotFoundError:
                summary[category] = {
                    'filename': filename,
                    'article_count': 0,
                    'status': 'not_created'
                }
        
        return summary

    def update_main_database_with_categories(self):
        """Update the main database to include category information"""
        source_db = self.load_source_database()
        articles = source_db.get('articles', [])
        
        logging.info("Adding category information to main database...")
        
        updated_count = 0
        for article in articles:
            if 'category' not in article:
                category = self.categorize_article(article)
                article['category'] = category
                article['categorization_date'] = datetime.now().isoformat()
                updated_count += 1
        
        # Update metadata
        if 'metadata' not in source_db:
            source_db['metadata'] = {}
        
        source_db['metadata']['last_categorization'] = datetime.now().isoformat()
        source_db['metadata']['categorization_stats'] = {
            'articles_updated': updated_count,
            'categories_available': list(self.categories.keys()) + ['uncategorized']
        }
        
        # Save updated main database
        try:
            with open(self.source_database, 'w', encoding='utf-8') as f:
                json.dump(source_db, f, indent=2, ensure_ascii=False)
            logging.info(f"Updated main database with category information for {updated_count} articles")
        except Exception as e:
            logging.error(f"Error updating main database: {e}")


def main():
    """Run the categorization system"""
    categorizer = SportsNewsCategorizer()
    
    logging.info("=" * 60)
    logging.info("SPORTS NEWS CATEGORIZATION SYSTEM")
    logging.info("=" * 60)
    
    # Categorize all articles
    result = categorizer.categorize_all_articles(save_individual_files=True)
    
    # Update main database with category info
    categorizer.update_main_database_with_categories()
    
    # Show summary
    logging.info("\n" + "=" * 60)
    logging.info("CATEGORIZATION SUMMARY")
    logging.info("=" * 60)
    
    summary = categorizer.get_category_summary()
    for category, info in summary.items():
        logging.info(f"{category.upper()}:")
        logging.info(f"  File: {info['filename']}")
        logging.info(f"  Articles: {info['article_count']}")
        if 'top_sources' in info:
            logging.info(f"  Sources: {', '.join(info['top_sources'][:3])}")
        logging.info("")
    
    logging.info("✅ Categorization completed successfully!")
    logging.info("🏏 Cricket articles → cricket_news_database.json")
    logging.info("⚽ Football articles → football_news_database.json") 
    logging.info("🏀 Basketball articles → basketball_news_database.json")
    logging.info("📰 Other articles → uncategorized_news_database.json")


if __name__ == "__main__":
    main()