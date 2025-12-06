"""
Article Deduplication System
Removes duplicate articles and keeps only the best source for each unique story
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Set
import re
from difflib import SequenceMatcher
import hashlib

class ArticleDeduplicator:
    def __init__(self, database_file: str = "sports_news_database.json"):
        self.database_file = database_file
        self.database = self.load_database()
        
        # Source priority ranking (higher = better)
        self.source_priority = {
            'ESPN': 10,
            'BBC Sport': 9,
            'The Athletic': 8,
            'Guardian': 7,
            'Sky Sports': 6,
            'Yahoo Sports': 5,
            'ESPNCricinfo': 4,
            'BBC Cricket': 3,
            'ESPN FC': 2
        }
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def load_database(self) -> Dict:
        """Load the articles database"""
        try:
            with open(self.database_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Database file {self.database_file} not found")
            return {'articles': [], 'metadata': {}}
    
    def save_database(self):
        """Save the updated database"""
        with open(self.database_file, 'w', encoding='utf-8') as f:
            json.dump(self.database, f, indent=2, ensure_ascii=False)
        logging.info(f"Database saved with {len(self.database['articles'])} articles")

    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison by removing noise words and formatting"""
        if not title:
            return ""
        
        # Convert to lowercase
        normalized = title.lower()
        
        # Remove common punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common noise words that don't affect story identity
        noise_words = {
            'live', 'latest', 'update', 'news', 'breaking', 'report', 'reports', 
            'says', 'confirms', 'announces', 'reveals', 'exclusive', 'video',
            'watch', 'photos', 'gallery', 'analysis', 'opinion', 'comment',
            'transfer', 'rumour', 'rumours', 'gossip', 'speculation'
        }
        
        words = normalized.split()
        words = [word for word in words if word not in noise_words and len(word) > 2]
        
        return ' '.join(words)

    def calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Additional checks for common patterns
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if len(words1) < 3 or len(words2) < 3:
            # For short titles, require higher similarity
            return similarity if similarity >= 0.8 else 0.0
        
        # Check word overlap
        common_words = words1.intersection(words2)
        word_overlap = len(common_words) / min(len(words1), len(words2))
        
        # Combine sequence similarity and word overlap
        combined_score = (similarity * 0.7) + (word_overlap * 0.3)
        
        return combined_score

    def get_source_priority(self, source_name: str) -> int:
        """Get priority score for a source"""
        # Check for partial matches in source priority
        for source, priority in self.source_priority.items():
            if source.lower() in source_name.lower():
                return priority
        return 1  # Default priority for unknown sources

    def find_duplicates(self, similarity_threshold: float = 0.75) -> List[List[Dict]]:
        """Find groups of duplicate articles"""
        articles = self.database['articles']
        duplicate_groups = []
        processed = set()
        
        logging.info(f"Analyzing {len(articles)} articles for duplicates...")
        
        for i, article1 in enumerate(articles):
            if i in processed:
                continue
            
            duplicates = [article1]
            article1_title = article1.get('title', '')
            
            for j, article2 in enumerate(articles[i+1:], i+1):
                if j in processed:
                    continue
                
                article2_title = article2.get('title', '')
                similarity = self.calculate_similarity(article1_title, article2_title)
                
                if similarity >= similarity_threshold:
                    duplicates.append(article2)
                    processed.add(j)
            
            if len(duplicates) > 1:
                duplicate_groups.append(duplicates)
                for idx, dup in enumerate(duplicates):
                    if i + idx < len(articles):
                        processed.add(i + idx)
        
        logging.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups

    def select_best_article(self, duplicate_group: List[Dict]) -> Dict:
        """Select the best article from a group of duplicates"""
        
        # Sort by multiple criteria:
        # 1. Source priority (highest first)
        # 2. Importance score (highest first) 
        # 3. Publication date (newest first)
        # 4. Summary length (longer is better)
        
        def scoring_function(article):
            source_priority = self.get_source_priority(article.get('source_name', ''))
            importance_score = article.get('importance_score', 0)
            
            # Parse publication date
            try:
                pub_date = article.get('published_date', '')
                if pub_date:
                    if isinstance(pub_date, str):
                        pub_timestamp = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).timestamp()
                    else:
                        pub_timestamp = 0
                else:
                    pub_timestamp = 0
            except:
                pub_timestamp = 0
            
            summary_length = len(article.get('summary', ''))
            
            # Weighted scoring
            total_score = (
                source_priority * 1000 +      # Source priority is most important
                importance_score * 100 +      # Then importance score
                pub_timestamp / 1000 +        # Then recency (normalized)
                summary_length               # Then content richness
            )
            
            return total_score
        
        # Sort and select best
        best_article = max(duplicate_group, key=scoring_function)
        
        return best_article

    def deduplicate_articles(self, similarity_threshold: float = 0.75, backup: bool = True) -> Dict:
        """Remove duplicate articles and keep only the best version of each story"""
        
        # Create backup if requested
        if backup:
            backup_file = f"{self.database_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.database, f, indent=2, ensure_ascii=False)
            logging.info(f"Backup created: {backup_file}")
        
        original_count = len(self.database['articles'])
        
        # Find duplicate groups
        duplicate_groups = self.find_duplicates(similarity_threshold)
        
        # Track removal statistics
        kept_articles = []
        removed_count = 0
        source_removals = {}
        
        # Process duplicates
        processed_articles = set()
        
        for group in duplicate_groups:
            # Select best article from group
            best_article = self.select_best_article(group)
            kept_articles.append(best_article)
            
            # Track which articles were kept/removed
            for article in group:
                article_id = article.get('id')
                if article_id:
                    processed_articles.add(article_id)
                    
                if article != best_article:
                    source_name = article.get('source_name', 'Unknown')
                    source_removals[source_name] = source_removals.get(source_name, 0) + 1
                    removed_count += 1
        
        # Add non-duplicate articles
        for article in self.database['articles']:
            article_id = article.get('id')
            if article_id not in processed_articles:
                kept_articles.append(article)
        
        # Update database
        self.database['articles'] = kept_articles
        
        # Update metadata
        final_count = len(kept_articles)
        self.database['metadata']['last_deduplication'] = datetime.now().isoformat()
        self.database['metadata']['total_articles'] = final_count
        self.database['metadata']['deduplication_stats'] = {
            'original_count': original_count,
            'duplicate_groups_found': len(duplicate_groups),
            'articles_removed': removed_count,
            'final_count': final_count,
            'similarity_threshold': similarity_threshold,
            'source_removals': source_removals
        }
        
        # Save updated database
        self.save_database()
        
        # Return statistics
        stats = {
            'original_count': original_count,
            'final_count': final_count,
            'removed_count': removed_count,
            'duplicate_groups': len(duplicate_groups),
            'source_removals': source_removals,
            'similarity_threshold': similarity_threshold
        }
        
        logging.info(f"Deduplication complete:")
        logging.info(f"  Original articles: {original_count}")
        logging.info(f"  Duplicate groups found: {len(duplicate_groups)}")
        logging.info(f"  Articles removed: {removed_count}")
        logging.info(f"  Final articles: {final_count}")
        logging.info(f"  Space saved: {removed_count/original_count*100:.1f}%")
        
        if source_removals:
            logging.info("  Removals by source:")
            for source, count in sorted(source_removals.items(), key=lambda x: x[1], reverse=True):
                logging.info(f"    {source}: {count} articles")
        
        return stats

    def show_duplicate_examples(self, limit: int = 5):
        """Show examples of duplicate groups for review"""
        duplicate_groups = self.find_duplicates()
        
        logging.info(f"\n=== DUPLICATE EXAMPLES (showing {min(limit, len(duplicate_groups))} groups) ===")
        
        for i, group in enumerate(duplicate_groups[:limit]):
            logging.info(f"\nDuplicate Group {i+1} ({len(group)} articles):")
            
            for j, article in enumerate(group):
                similarity_scores = []
                for other in group:
                    if other != article:
                        sim = self.calculate_similarity(article.get('title', ''), other.get('title', ''))
                        similarity_scores.append(sim)
                
                avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
                
                logging.info(f"  {j+1}. [{article.get('source_name', 'Unknown'):15}] "
                           f"Score: {article.get('importance_score', 0):5.1f} "
                           f"Sim: {avg_similarity:.2f} - "
                           f"{article.get('title', 'No title')[:80]}...")


def main():
    """Run the deduplication process"""
    deduplicator = ArticleDeduplicator()
    
    # Show some examples first
    logging.info("Analyzing duplicates...")
    deduplicator.show_duplicate_examples(3)
    
    # Run deduplication
    logging.info("\nStarting deduplication process...")
    stats = deduplicator.deduplicate_articles(similarity_threshold=0.75, backup=True)
    
    logging.info("\n✅ Deduplication completed successfully!")


if __name__ == "__main__":
    main()