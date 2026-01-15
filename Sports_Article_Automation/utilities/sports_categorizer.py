"""
Sports News Categorization System
Automatically categorizes news into Cricket, Football, and Basketball
Creates separate databases for each sport category
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List
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
                    # Cricket-specific core terms (highest weight)
                    'cricket', 'wicket', 'wickets', 'batting', 'bowling', 'bowler', 'batsman', 'batsmen',
                    'innings', 'over', 'overs', 'century', 'half-century', 'duck',
                    'stumps', 'lbw', 'maiden over', 'cricket boundary',
                    
                    # Cricket formats (very specific)
                    'test cricket', 'odi cricket', 'twenty20', 't20 cricket', 'ipl', 'test match',
                    'one day international', 'ashes cricket', 'cricket world cup', 'county cricket',
                    
                    # Cricket positions (specific to cricket)
                    'wicket-keeper', 'cricket captain', 'all-rounder', 'cricket spinner', 'pace bowler',
                    'opening batsman', 'middle order', 'tail ender',
                    
                    # Cricket competitions (unambiguous)
                    'big bash league', 'pakistan super league', 'caribbean premier league', 
                    'the hundred cricket', 'county championship', 'ranji trophy', 'sheffield shield',
                    'indian premier league',
                    
                    # Cricket-specific terms (avoid generic)
                    'cricket team', 'cricket match', 'cricket player', 'cricket ground',
                    'cricket ball', 'cricket bat', 'cricket pitch', 'cricket field',
                    
                    # Cricket venues (specific)
                    'lords cricket', 'the oval cricket', 'old trafford cricket', 'headingley cricket',
                    'trent bridge', 'edgbaston cricket', 'melbourne cricket ground', 'sydney cricket ground',
                    'waca ground', 'the gabba', 'adelaide oval cricket',
                    
                    # Cricket personalities (with context when possible)
                    'virat kohli', 'rohit sharma', 'ms dhoni', 'jasprit bumrah', 'ravichandran ashwin', 'ravindra jadeja',
                    'joe root', 'ben stokes', 'james anderson', 'stuart broad', 'jonny bairstow',
                    'steve smith cricket', 'david warner cricket', 'pat cummins', 'mitchell starc', 'josh hazlewood',
                    'kane williamson', 'trent boult', 'tim southee',
                    'babar azam', 'mohammad rizwan', 'shaheen afridi'
                },
                'sources': {
                    'espncricinfo', 'cricinfo', 'wisden.com', 'cricket.com.au', 'cricbuzz.com',
                    'bbc cricket', 'sky sports cricket', 'cricket australia', 'cricket world',
                    'icc-cricket.com', 'cricket.com', 'the cricketer'
                }
            },
            
            'football': {
                'filename': self.data_dir / 'football_news_database.json', 
                'keywords': {
                    # Football terms (soccer - be specific to avoid American football)
                    'soccer', 'football match', 'football game', 'football player', 'football team',
                    'penalty kick', 'free kick', 'corner kick', 'offside', 'yellow card', 'red card',
                    'var football', 'football referee', 'football substitute', 'football transfer',
                    
                    # Football-specific actions
                    'football goal', 'header goal', 'volley goal', 'penalty shootout',
                    'football dribble', 'football tackle', 'football cross', 'football pass',
                    
                    # Positions (football-specific)
                    'goalkeeper', 'football defender', 'midfielder', 'striker', 'winger',
                    'centre-back', 'full-back', 'attacking midfielder', 'defensive midfielder',
                    'centre-forward', 'left-back', 'right-back',
                    
                    # Competitions (unambiguous)
                    'premier league', 'english premier league', 'fa cup', 'carabao cup', 'community shield',
                    'champions league', 'uefa champions league', 'europa league', 'conference league',
                    'la liga', 'serie a', 'bundesliga', 'ligue 1', 'eredivisie',
                    'fifa world cup', 'european championship', 'copa america', 'african cup of nations',
                    
                    # Teams (major clubs with context)
                    'manchester united fc', 'manchester city fc', 'liverpool fc', 'arsenal fc', 'chelsea fc',
                    'tottenham hotspur', 'newcastle united', 'brighton football', 'west ham united', 'aston villa fc',
                    'real madrid cf', 'fc barcelona', 'atletico madrid', 'sevilla fc',
                    'juventus fc', 'inter milan', 'ac milan', 'napoli fc', 'as roma',
                    'bayern munich', 'borussia dortmund', 'rb leipzig',
                    'paris saint-germain', 'psg football', 'as monaco', 'marseille', 'lyon',
                    
                    # Football personalities (with context)
                    'lionel messi', 'cristiano ronaldo', 'kylian mbappe', 'erling haaland', 'neymar jr', 'karim benzema',
                    'mohamed salah', 'harry kane', 'heung-min son', 'kevin de bruyne', 'luka modric', 'robert lewandowski',
                    'pep guardiola', 'jurgen klopp', 'mikel arteta', 'carlo ancelotti', 'jose mourinho'
                },
                'sources': {
                    'bbc sport football', 'bbc football', 'guardian football', 'espn fc',
                    'sky sports football', 'sky sports premier league', 'football365',
                    'goal.com', 'fourfourtwo', 'talksport football', 'the athletic football',
                    'premierleague.com', 'uefa.com', 'fifa.com', 'marca', 'as.com'
                }
            },
            
            'basketball': {
                'filename': self.data_dir / 'basketball_news_database.json',
                'keywords': {
                    # Basketball terms (be very specific)
                    'basketball', 'nba', 'wnba', 'ncaa basketball', 'euroleague basketball',
                    'basketball dunk', 'three-pointer', 'three-point shot', 'free throw', 'basketball rebound',
                    'basketball assist', 'steal basketball', 'basketball block', 'basketball foul',
                    'technical foul', 'flagrant foul', 'nba playoffs', 'nba draft',
                    
                    # Basketball-specific actions
                    'slam dunk', 'basketball shot', 'basketball pass', 'basketball turnover',
                    'double-double', 'triple-double', 'basketball layup', 'basketball crossover',
                    
                    # Positions (basketball-specific)
                    'point guard', 'shooting guard', 'small forward', 'power forward', 'center basketball',
                    'basketball guard', 'basketball forward', 'sixth man basketball',
                    
                    # NBA Teams (with full names when possible)
                    'los angeles lakers', 'golden state warriors', 'boston celtics', 'miami heat', 'chicago bulls',
                    'new york knicks', 'brooklyn nets', 'philadelphia 76ers', 'milwaukee bucks', 'toronto raptors',
                    'orlando magic', 'atlanta hawks', 'charlotte hornets', 'detroit pistons', 'indiana pacers',
                    'cleveland cavaliers', 'washington wizards', 'denver nuggets', 'minnesota timberwolves',
                    'oklahoma city thunder', 'portland trail blazers', 'utah jazz', 'sacramento kings',
                    'phoenix suns', 'la clippers', 'dallas mavericks', 'houston rockets', 'san antonio spurs',
                    'memphis grizzlies', 'new orleans pelicans',
                    
                    # Basketball personalities (with full names)
                    'lebron james', 'stephen curry', 'kevin durant', 'giannis antetokounmpo', 'nikola jokic',
                    'jayson tatum', 'luka doncic', 'joel embiid', 'kawhi leonard', 'anthony davis',
                    'james harden', 'russell westbrook', 'chris paul', 'damian lillard', 'jimmy butler',
                    'kyrie irving', 'klay thompson', 'draymond green',
                    
                    # Competitions (basketball-specific)
                    'nba finals', 'nba all-star', 'nba mvp', 'defensive player of the year',
                    'rookie of the year basketball', 'sixth man of the year',
                    'march madness', 'ncaa final four', 'elite eight basketball'
                },
                'sources': {
                    'the athletic nba', 'yahoo sports nba', 'espn nba', 'nba.com',
                    'bleacher report nba', 'sportingnews nba', 'cbs sports nba',
                    'fox sports nba', 'basketball reference', 'hoopshype',
                    'slam magazine', 'nbc sports basketball'
                }
            }
        }
        
        # Configure module-level logger (safe for library use)
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:  # Avoid duplicate handlers
            self.logger.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - [CATEGORIZER] %(message)s')
            )
            self.logger.addHandler(console_handler)
            
            # File handler
            file_handler = logging.FileHandler(self.data_dir / 'sports_categorization.log')
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - [CATEGORIZER] %(message)s')
            )
            self.logger.addHandler(file_handler)

    def load_source_database(self) -> Dict:
        """Load the main sports news database"""
        try:
            with open(self.source_database, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Source database {self.source_database} not found")
            return {'articles': [], 'metadata': {}}

    def categorize_article(self, article: Dict) -> str:
        """
        Categorize a single article into Cricket, Football, or Basketball ONLY
        Returns category name or 'uncategorized' (will be discarded)
        
        STRICT RULES:
        - Only Cricket, Football, Basketball are valid categories
        - Articles must clearly belong to one of these sports
        - Strong exclusion rules to prevent cross-contamination
        - Uncategorized articles are NOT saved (other sports filtered out)
        """
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower() 
        source_raw = article.get('source_name', '').lower()
        
        # Normalize source for better matching
        source = re.sub(r'[^a-z0-9 ]', ' ', source_raw).strip()
        
        # Combine all text for analysis
        text_content = f"{title} {summary}"
        
        # FIRST: Check for exclusion patterns (other sports that should be rejected)
        exclusion_patterns = {
            'tennis': ['tennis', 'wimbledon', 'us open tennis', 'french open', 'australian open tennis', 'atp', 'wta', 'federer', 'nadal', 'djokovic', 'serena'],
            'golf': ['golf', 'pga tour', 'masters tournament', 'us open golf', 'british open', 'ryder cup', 'tiger woods', 'mcilroy'],
            'baseball': ['baseball', 'mlb', 'world series', 'home run', 'pitcher', 'batter', 'inning', 'yankees', 'red sox'],
            'ice_hockey': ['hockey', 'nhl', 'stanley cup', 'puck', 'goalie', 'ice hockey', 'rangers', 'bruins'],
            'american_football': ['nfl', 'super bowl', 'quarterback', 'touchdown', 'patriots', 'cowboys', 'packers'],
            'motorsport': ['formula 1', 'f1', 'nascar', 'motogp', 'hamilton', 'verstappen', 'racing'],
            'boxing': ['boxing match', 'boxing fight', 'heavyweight boxer', 'knockout punch', 'boxing round', 'boxing champion'],  # More specific boxing terms
            'mma': ['ufc', 'mixed martial arts', 'octagon', 'fight night'],
            'swimming': ['swimming', 'olympics swimming', 'freestyle', 'butterfly stroke'],
            'athletics': ['track and field', 'marathon', 'sprint', '100m', 'olympics athletics']
        }
        
        # Collect exclusion matches but don't immediately reject
        exclusion_matches = []
        for sport, patterns in exclusion_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text_content:
                    exclusion_matches.append((sport, pattern))
                    self.logger.debug(f"Found {sport} keyword '{pattern}': {article.get('title', '')[:50]}")
        
        # Score each target category (cricket, football, basketball)
        category_scores = {}
        
        for category, config in self.categories.items():
            score = 0
            keyword_matches = []
            
            # Source-based scoring (highest priority - very strong signal)
            source_match = False
            source_tokens = source.split()
            for source_keyword in config['sources']:
                source_keyword_tokens = source_keyword.lower().split()
                if all(token in source_tokens for token in source_keyword_tokens):
                    score += 20  # Strong weight for source match
                    source_match = True
                    break
            
            # Keyword-based scoring with phrase-safe matching
            for keyword in config['keywords']:
                if keyword.lower() in text_content:
                    keyword_matches.append(keyword)
                    
                    # Sport-specific keyword weighting (only using keywords from actual sets)
                    if category == 'cricket':
                        # Cricket-specific high-value terms
                        high_value_cricket = {'wicket', 'wickets', 'innings', 'bowling', 'batsman', 'century', 'stumps', 'lbw', 'maiden over', 'ashes cricket', 'ipl', 't20 cricket', 'virat kohli', 'test cricket', 'test match'}
                        medium_value_cricket = {'cricket', 'over', 'overs'}
                        
                        if keyword in high_value_cricket:
                            score += 8
                        elif keyword in medium_value_cricket:
                            score += 5
                        else:
                            score += 2
                    
                    elif category == 'football':
                        # Football-specific high-value terms
                        high_value_football = {'premier league', 'champions league', 'europa league', 'var football', 'offside', 'penalty kick', 'free kick'}
                        medium_value_football = {'soccer', 'football match', 'football game', 'football goal'}
                        
                        if keyword in high_value_football:
                            score += 8
                        elif keyword in medium_value_football:
                            score += 5
                        else:
                            score += 2
                    
                    elif category == 'basketball':
                        # Basketball-specific high-value terms
                        high_value_basketball = {'nba', 'wnba', 'three-pointer', 'basketball dunk', 'nba playoffs', 'nba mvp', 'nba finals'}
                        medium_value_basketball = {'basketball', 'basketball rebound', 'basketball assist', 'nba draft'}
                        
                        if keyword in high_value_basketball:
                            score += 8
                        elif keyword in medium_value_basketball:
                            score += 5
                        else:
                            score += 2
            
            # Bonus for multiple relevant keywords
            if len(keyword_matches) >= 3:
                score += 5
            elif len(keyword_matches) >= 2:
                score += 2
            
            category_scores[category] = score
            
            # Log detailed scoring for debugging
            if score > 0:
                self.logger.debug(f"{category}: score={score}, source_match={source_match}, keywords={keyword_matches[:5]}")
        
        # Return category with highest score, but check exclusions first
        if category_scores:
            max_score = max(category_scores.values())
            
            # Apply exclusions only if no category scores high enough
            if max_score < 8 and exclusion_matches:
                self.logger.debug(f"Article excluded due to {len(exclusion_matches)} exclusion matches: {article.get('title', '')[:50]}")
                return 'uncategorized'
            
            # Much stricter threshold: must score at least 8 to be categorized
            if max_score >= 8:
                best_category = max(category_scores, key=category_scores.get)
                
                # Stricter ambiguity check: if second best is within 50% of best, it's ambiguous
                sorted_scores = sorted(category_scores.values(), reverse=True)
                if len(sorted_scores) >= 2:
                    if sorted_scores[1] >= (sorted_scores[0] * 0.5):
                        logging.debug(f"Ambiguous categorization rejected (scores: {sorted_scores[:2]}): {article.get('title', '')[:50]}")
                        return 'uncategorized'
                
                logging.debug(f"Article categorized as {best_category} (score: {max_score}): {article.get('title', '')[:50]}")
                return best_category
            else:
                logging.debug(f"Score too low ({max_score} < 10): {article.get('title', '')[:50]}")
        
        # Not confident enough in any category - reject
        return 'uncategorized'

    def categorize_all_articles(self, save_individual_files: bool = True) -> Dict:
        """Categorize all articles and optionally save to individual category files"""
        
        # Load source database
        source_db = self.load_source_database()
        articles = source_db.get('articles', [])
        
        if not articles:
            self.logger.warning("No articles found in source database")
            return {}
        
        # Initialize category databases
        categorized_data = {}
        current_time = datetime.now().isoformat()
        
        for category in self.categories.keys():
            # Check if file exists to preserve created_date
            existing_created_date = current_time
            try:
                with open(self.categories[category]['filename'], 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_created_date = existing_data.get('metadata', {}).get('created_date', current_time)
            except FileNotFoundError:
                pass
                
            categorized_data[category] = {
                'articles': [],
                'metadata': {
                    'category': category,
                    'created_date': existing_created_date,
                    'last_updated': current_time,
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
                'created_date': current_time,
                'last_updated': current_time,
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
        
        self.logger.info(f"Categorizing {len(articles)} articles...")
        
        # Track progress
        last_progress_log = 0
        
        for idx, article in enumerate(articles, 1):
            category = self.categorize_article(article)
            
            # Add category info to article (create copy to avoid mutation)
            article_copy = article.copy()
            article_copy['category'] = category
            article_copy['categorization_date'] = current_time
            
            # Add to appropriate category
            categorized_data[category]['articles'].append(article_copy)
            
            # Fix statistics counting
            if category in self.categories:
                categorization_stats['categorized'][category] += 1
            else:
                categorization_stats['uncategorized'] += 1
            
            # Log progress every 10% of articles
            progress_percent = int((idx / len(articles)) * 100)
            if progress_percent >= last_progress_log + 10:
                last_progress_log = progress_percent
                self.logger.info(f"  Categorization progress: {progress_percent}% ({idx}/{len(articles)} articles)")
        
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
            self.logger.info("Saving categorized articles to individual sport databases...")
            for category in self.categories.keys():
                article_count = len(categorized_data[category]['articles'])
                if article_count > 0:
                    filename = self.categories[category]['filename']
                    self.save_category_database(categorized_data[category], filename)
                else:
                    self.logger.info(f"Skipping {category} - no articles to save")
        
        # DO NOT save uncategorized articles - they are filtered out
        # Uncategorized = other sports we don't support (tennis, hockey, etc.)
        if categorization_stats['uncategorized'] > 0:
            self.logger.info(f"Filtered out {categorization_stats['uncategorized']} uncategorized articles (other sports)")
        
        # Log results
        self.logger.info("=" * 70)
        self.logger.info("CATEGORIZATION RESULTS (CRICKET, FOOTBALL, BASKETBALL ONLY):")
        self.logger.info("=" * 70)
        for category, count in categorization_stats['categorized'].items():
            if count > 0 and category in self.categories:
                self.logger.info(f"  {category.capitalize()}: {count} articles")
        if categorization_stats['uncategorized'] > 0:
            self.logger.info(f"  Filtered out: {categorization_stats['uncategorized']} articles (other sports)")
        self.logger.info("=" * 70)
        
        return {
            'categorized_data': categorized_data,
            'stats': categorization_stats
        }

    def calculate_category_importance_distribution(self, articles: List[Dict]) -> Dict:
        """Calculate importance distribution for a category"""
        valid_tiers = {'Critical', 'High', 'Medium', 'Low', 'Minimal'}
        distribution = {tier: 0 for tier in valid_tiers}
        
        for article in articles:
            tier = article.get('importance_tier', 'Minimal')
            # Validate tier and normalize to Minimal if invalid
            if tier not in valid_tiers:
                tier = 'Minimal'
            distribution[tier] += 1
        
        return distribution

    def save_category_database(self, category_data: Dict, filename):
        """Save a category database to file"""
        try:
            # Convert Path object to string if needed
            filepath = str(filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(category_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(category_data['articles'])} articles to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving {filename}: {e}")

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
        
        self.logger.info("Adding category information to main database...")
        
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
            self.logger.info(f"Updated main database with category information for {updated_count} articles")
        except Exception as e:
            self.logger.error(f"Error updating main database: {e}")

# Alias for backward compatibility
SportsCategorizer = SportsNewsCategorizer


def main():
    """Run the categorization system"""
    categorizer = SportsNewsCategorizer()
    
    categorizer.logger.info("=" * 60)
    categorizer.logger.info("SPORTS NEWS CATEGORIZATION SYSTEM")
    categorizer.logger.info("=" * 60)
    
    # Categorize all articles
    result = categorizer.categorize_all_articles(save_individual_files=True)
    
    # Update main database with category info
    categorizer.update_main_database_with_categories()
    
    # Show summary
    categorizer.logger.info("\n" + "=" * 60)
    categorizer.logger.info("CATEGORIZATION SUMMARY")
    categorizer.logger.info("=" * 60)
    
    summary = categorizer.get_category_summary()
    for category, info in summary.items():
        categorizer.logger.info(f"{category.upper()}:")
        categorizer.logger.info(f"  File: {info['filename']}")
        categorizer.logger.info(f"  Articles: {info['article_count']}")
        if 'top_sources' in info:
            categorizer.logger.info(f"  Sources: {', '.join(info['top_sources'][:3])}")
        categorizer.logger.info("")
    
    categorizer.logger.info("Categorization completed successfully!")
    categorizer.logger.info("Cricket articles → cricket_news_database.json")
    categorizer.logger.info("Football articles → football_news_database.json") 
    categorizer.logger.info("Basketball articles → basketball_news_database.json")
    categorizer.logger.info("Other articles → uncategorized_news_database.json")

if __name__ == "__main__":
    main()