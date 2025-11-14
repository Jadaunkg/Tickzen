"""
Core Markov Chain Engine
========================

Advanced Markov chain implementation optimized for financial text generation.
Supports multiple orders, weighted transitions, and context-aware generation.
"""

import random
import re
import pickle
import json
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkovEngine:
    """
    Advanced Markov Chain text generation engine.
    
    Features:
    - Variable order n-grams (2-4 recommended for financial text)
    - Weighted probability transitions
    - Context-aware generation
    - Data placeholder protection
    - Sentence structure preservation
    """
    
    def __init__(self, order: int = 2, min_sentence_length: int = 10):
        """
        Initialize Markov Engine.
        
        Args:
            order: N-gram order (2=bigram, 3=trigram). Higher = more coherent but less varied.
            min_sentence_length: Minimum words per generated sentence.
        """
        self.order = order
        self.min_sentence_length = min_sentence_length
        
        # Core chain structure: {state: [(next_token, frequency), ...]}
        self.chain = defaultdict(Counter)
        
        # Sentence starters: List of n-grams that begin sentences
        self.sentence_starters = []
        
        # Metadata
        self.vocabulary_size = 0
        self.total_transitions = 0
        self.trained = False
        
        # Placeholder patterns to protect during generation
        self.placeholder_patterns = [
            r'\{[A-Z_]+\}',  # {TICKER}, {PRICE}
            r'\$[\d,]+\.?\d*',  # $175.25
            r'[\d,]+\.?\d*%',  # 25.3%
            r'[\d,]+\.?\d*x',  # 28.5x
        ]
    
    def train(self, texts: List[str], incremental: bool = False):
        """
        Train the Markov model on text corpus.
        
        Args:
            texts: List of training texts (articles, summaries, etc.)
            incremental: If True, add to existing model. If False, replace.
        """
        if not incremental:
            self.chain.clear()
            self.sentence_starters.clear()
        
        logger.info(f"Training on {len(texts)} texts...")
        
        processed_count = 0
        for text in texts:
            if not text or len(text.strip()) < 20:
                continue
            
            # Split into sentences
            sentences = self._split_sentences(text)
            
            for sentence in sentences:
                tokens = self._tokenize(sentence)
                
                if len(tokens) < self.order + 1:
                    continue
                
                # Store sentence starter
                starter = tuple(tokens[:self.order])
                if starter not in self.sentence_starters:
                    self.sentence_starters.append(starter)
                
                # Build transitions
                for i in range(len(tokens) - self.order):
                    state = tuple(tokens[i:i + self.order])
                    next_token = tokens[i + self.order]
                    
                    # Increment counter for this transition
                    self.chain[state][next_token] += 1
                    self.total_transitions += 1
            
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count}/{len(texts)} texts")
        
        self.vocabulary_size = len(set(token for state in self.chain.keys() for token in state))
        self.trained = True
        
        logger.info(f"Training complete. Vocabulary: {self.vocabulary_size}, "
                   f"Transitions: {self.total_transitions}")
    
    def generate(self, 
                 seed_phrase: Optional[str] = None,
                 max_length: int = 100,
                 temperature: float = 1.0,
                 end_on_punctuation: bool = True) -> str:
        """
        Generate text using the trained model.
        
        Args:
            seed_phrase: Starting phrase (optional). If None, random starter used.
            max_length: Maximum number of words to generate.
            temperature: Randomness (0.5=more deterministic, 1.5=more random).
            end_on_punctuation: Stop at sentence boundary.
        
        Returns:
            Generated text string.
        """
        if not self.trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Initialize with seed or random starter
        if seed_phrase:
            tokens = self._tokenize(seed_phrase)
            if len(tokens) >= self.order:
                current = list(tokens[-self.order:])
            else:
                current = list(random.choice(self.sentence_starters))
        else:
            current = list(random.choice(self.sentence_starters))
        
        generated = list(current)
        
        # Generate tokens
        for _ in range(max_length - self.order):
            state = tuple(current[-self.order:])
            
            if state not in self.chain:
                # Dead end - try to recover or break
                break
            
            # Get next token using weighted random choice
            next_token = self._weighted_choice(
                self.chain[state],
                temperature=temperature
            )
            
            generated.append(next_token)
            current.append(next_token)
            
            # Check for natural ending
            if end_on_punctuation and next_token in ['.', '!', '?']:
                if len(generated) >= self.min_sentence_length:
                    break
        
        # Convert to text and clean
        text = self._detokenize(generated)
        return text
    
    def generate_sentence(self,
                         seed_phrase: Optional[str] = None,
                         target_length: int = 20,
                         temperature: float = 1.0) -> str:
        """
        Generate a single sentence.
        
        Args:
            seed_phrase: Starting phrase for the sentence.
            target_length: Approximate length in words.
            temperature: Randomness factor.
        
        Returns:
            Generated sentence.
        """
        return self.generate(
            seed_phrase=seed_phrase,
            max_length=target_length,
            temperature=temperature,
            end_on_punctuation=True
        )
    
    def generate_variation(self, 
                          template: str,
                          preserve_placeholders: bool = True) -> str:
        """
        Generate a variation of a template text while preserving data placeholders.
        
        Args:
            template: Template text with optional {PLACEHOLDERS}
            preserve_placeholders: If True, protect placeholders from modification
        
        Returns:
            Varied text with placeholders intact.
        """
        if preserve_placeholders:
            # Extract and protect placeholders
            placeholders = {}
            protected_template = template
            
            for i, pattern in enumerate(self.placeholder_patterns):
                for match in re.finditer(pattern, template):
                    placeholder_key = f"__PLACEHOLDER_{i}_{len(placeholders)}__"
                    placeholders[placeholder_key] = match.group()
                    protected_template = protected_template.replace(
                        match.group(), 
                        placeholder_key,
                        1
                    )
            
            # Generate variation
            # Parse narrative vs placeholder parts
            parts = re.split(r'(__PLACEHOLDER_\d+_\d+__)', protected_template)
            
            varied_parts = []
            for part in parts:
                if part.startswith('__PLACEHOLDER_'):
                    # Keep placeholder as-is
                    varied_parts.append(part)
                elif len(part.strip()) > 15:
                    # Vary narrative text
                    try:
                        varied = self.generate(
                            seed_phrase=part[:30],
                            max_length=len(part.split()),
                            temperature=1.2
                        )
                        varied_parts.append(varied)
                    except:
                        varied_parts.append(part)
                else:
                    varied_parts.append(part)
            
            # Reconstruct with original placeholders
            result = ''.join(varied_parts)
            for key, value in placeholders.items():
                result = result.replace(key, value)
            
            return result
        else:
            return self.generate(seed_phrase=template[:50])
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Improved sentence splitting
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words and punctuation.
        Preserves punctuation as separate tokens.
        """
        # Add spaces around punctuation
        text = re.sub(r'([.!?,;:()"\'])', r' \1 ', text)
        
        # Split and filter
        tokens = text.split()
        tokens = [t for t in tokens if t.strip()]
        
        return tokens
    
    def _detokenize(self, tokens: List[str]) -> str:
        """Convert tokens back to text."""
        text = ' '.join(tokens)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.!?,;:])', r'\1', text)
        
        # Remove spaces around quotes
        text = re.sub(r'"\s+', r'"', text)
        text = re.sub(r'\s+"', r'"', text)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        # Ensure ends with punctuation
        if text and text[-1] not in '.!?':
            text += '.'
        
        return text.strip()
    
    def _weighted_choice(self, 
                        counter: Counter, 
                        temperature: float = 1.0) -> str:
        """
        Select next token using weighted random choice.
        
        Args:
            counter: Counter of (token, frequency) pairs
            temperature: Controls randomness (lower = more deterministic)
        
        Returns:
            Selected token
        """
        if not counter:
            return '.'
        
        # Apply temperature to probabilities
        items = list(counter.items())
        tokens, weights = zip(*items)
        
        # Apply temperature scaling
        if temperature != 1.0:
            weights = [w ** (1.0 / temperature) for w in weights]
        
        # Normalize to probabilities
        total = sum(weights)
        probabilities = [w / total for w in weights]
        
        # Random choice based on probabilities
        return random.choices(tokens, weights=probabilities)[0]
    
    def get_stats(self) -> Dict:
        """Get model statistics."""
        return {
            'order': self.order,
            'vocabulary_size': self.vocabulary_size,
            'total_transitions': self.total_transitions,
            'num_states': len(self.chain),
            'num_sentence_starters': len(self.sentence_starters),
            'trained': self.trained
        }
    
    def save(self, filepath: str):
        """
        Save model to file.
        
        Args:
            filepath: Path to save model (supports .json or .pkl)
        """
        model_data = {
            'order': self.order,
            'min_sentence_length': self.min_sentence_length,
            'chain': {str(k): dict(v) for k, v in self.chain.items()},
            'sentence_starters': [list(s) for s in self.sentence_starters],
            'vocabulary_size': self.vocabulary_size,
            'total_transitions': self.total_transitions,
            'trained': self.trained
        }
        
        if filepath.endswith('.json'):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(model_data, f, indent=2)
        elif filepath.endswith('.pkl'):
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
        else:
            raise ValueError("Filepath must end with .json or .pkl")
        
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: str):
        """
        Load model from file.
        
        Args:
            filepath: Path to model file (.json or .pkl)
        """
        if filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
        elif filepath.endswith('.pkl'):
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
        else:
            raise ValueError("Filepath must end with .json or .pkl")
        
        self.order = model_data['order']
        self.min_sentence_length = model_data['min_sentence_length']
        self.vocabulary_size = model_data['vocabulary_size']
        self.total_transitions = model_data['total_transitions']
        self.trained = model_data['trained']
        
        # Reconstruct chain
        self.chain = defaultdict(Counter)
        for state_str, transitions in model_data['chain'].items():
            state = tuple(eval(state_str))
            self.chain[state] = Counter(transitions)
        
        # Reconstruct sentence starters
        self.sentence_starters = [tuple(s) for s in model_data['sentence_starters']]
        
        logger.info(f"Model loaded from {filepath}")


if __name__ == "__main__":
    # Test the engine
    engine = MarkovEngine(order=2)
    
    test_samples = [
        "The company demonstrates strong financial performance with robust revenue growth.",
        "Financial analysts expect solid earnings ahead based on market fundamentals.",
        "The enterprise exhibits remarkable operational efficiency and strategic positioning.",
    ]
    
    engine.train(test_samples)
    
    print("Generated text:")
    print(engine.generate(max_length=30))
    print("\nModel stats:")
    print(engine.get_stats())
