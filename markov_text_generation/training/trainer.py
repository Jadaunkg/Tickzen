"""
Model Trainer
=============

Training pipeline for Markov models on financial text corpus.
Supports batch training, validation, and model versioning.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ..core.engine import MarkovEngine
from ..core.model_manager import ModelManager
from .data_processor import DataProcessor

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Comprehensive training pipeline for Markov models.
    
    Features:
    - Train models on large text corpus
    - Validate model quality
    - Automatic versioning
    - Training progress tracking
    """
    
    def __init__(self,
                 data_processor: DataProcessor,
                 model_manager: ModelManager,
                 validation_split: float = 0.1):
        """
        Initialize Model Trainer.
        
        Args:
            data_processor: DataProcessor instance
            model_manager: ModelManager instance
            validation_split: Fraction of data for validation
        """
        self.processor = data_processor
        self.manager = model_manager
        self.validation_split = validation_split
        
        logger.info("ModelTrainer initialized")
    
    def train_model(self,
                   section_type: str,
                   order: int = 2,
                   min_samples: int = 10,
                   version_notes: str = "") -> Optional[MarkovEngine]:
        """
        Train a model for specific section type.
        
        Args:
            section_type: Type of section ('introduction', 'technical_analysis', etc.)
            order: N-gram order
            min_samples: Minimum number of training samples required
            version_notes: Notes for this model version
        
        Returns:
            Trained MarkovEngine or None if insufficient data
        """
        logger.info(f"Training {section_type} model (order={order})")
        
        # Get processed texts
        texts = self.processor.get_processed_texts(section_type)
        
        if len(texts) < min_samples:
            logger.warning(f"Insufficient samples for {section_type}: {len(texts)} < {min_samples}")
            return None
        
        # Split into training and validation
        split_idx = int(len(texts) * (1 - self.validation_split))
        train_texts = texts[:split_idx]
        val_texts = texts[split_idx:]
        
        logger.info(f"Training on {len(train_texts)} samples, validating on {len(val_texts)}")
        
        # Create and train model
        model = self.manager.create_model(
            model_type=section_type,
            order=order,
            description=f"Model trained on {len(train_texts)} financial {section_type} samples"
        )
        
        model.train(train_texts)
        
        # Validate model
        validation_score = self._validate_model(model, val_texts)
        
        logger.info(f"Validation score: {validation_score:.2f}")
        
        # Save model with version
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        notes = f"{version_notes}\nTrained: {len(train_texts)} samples\nValidation: {validation_score:.2f}"
        
        self.manager.save_model(
            model=model,
            model_type=section_type,
            version=version,
            notes=notes
        )
        
        logger.info(f"Model saved: {section_type} v{version}")
        
        return model
    
    def train_all_sections(self, 
                          order: int = 2,
                          min_samples: int = 10) -> Dict[str, Optional[MarkovEngine]]:
        """
        Train models for all section types.
        
        Args:
            order: N-gram order
            min_samples: Minimum samples per section
        
        Returns:
            Dict mapping section type to trained model
        """
        section_types = [
            'introduction',
            'technical_analysis',
            'fundamental_analysis',
            'valuation',
            'conclusion'
        ]
        
        models = {}
        
        for section_type in section_types:
            try:
                model = self.train_model(
                    section_type=section_type,
                    order=order,
                    min_samples=min_samples,
                    version_notes=f"Batch training {datetime.now().isoformat()}"
                )
                models[section_type] = model
                
            except Exception as e:
                logger.error(f"Error training {section_type}: {e}")
                models[section_type] = None
        
        successful = sum(1 for m in models.values() if m is not None)
        logger.info(f"Batch training complete: {successful}/{len(section_types)} models trained")
        
        return models
    
    def retrain_model(self,
                     section_type: str,
                     additional_texts: Optional[List[str]] = None,
                     version_notes: str = "Retrained model") -> Optional[MarkovEngine]:
        """
        Retrain an existing model with new or updated data.
        
        Args:
            section_type: Type of section
            additional_texts: Additional training texts (optional)
            version_notes: Version notes
        
        Returns:
            Retrained model
        """
        logger.info(f"Retraining {section_type} model")
        
        # Get all existing processed texts
        texts = self.processor.get_processed_texts(section_type)
        
        # Add additional texts if provided
        if additional_texts:
            texts.extend(additional_texts)
            logger.info(f"Added {len(additional_texts)} new texts")
        
        # Load existing model info
        model_info = self.manager.get_model_info(section_type)
        order = model_info.get('order', 2) if model_info else 2
        
        # Train new model
        return self.train_model(
            section_type=section_type,
            order=order,
            min_samples=len(texts),
            version_notes=version_notes
        )
    
    def _validate_model(self, model: MarkovEngine, validation_texts: List[str]) -> float:
        """
        Validate model quality.
        
        Args:
            model: Trained model
            validation_texts: Validation text samples
        
        Returns:
            Validation score (0-100, higher is better)
        """
        if not validation_texts:
            return 0.0
        
        scores = []
        
        for text in validation_texts[:min(10, len(validation_texts))]:  # Sample up to 10 texts
            try:
                # Generate variation
                generated = model.generate_variation(
                    min_length=50,
                    max_length=200,
                    temperature=0.7
                )
                
                # Score based on:
                # 1. Generation success (0 or 50 points)
                # 2. Length appropriateness (0-25 points)
                # 3. Coherence/uniqueness (0-25 points)
                
                if not generated:
                    scores.append(0)
                    continue
                
                score = 50  # Base score for successful generation
                
                # Length score
                words = len(generated.split())
                if 50 <= words <= 200:
                    score += 25
                elif 30 <= words <= 250:
                    score += 15
                
                # Uniqueness score (compare to validation text)
                val_words = set(text.lower().split())
                gen_words = set(generated.lower().split())
                overlap = len(val_words & gen_words) / max(len(val_words), 1)
                
                if 0.3 <= overlap <= 0.7:  # Good balance
                    score += 25
                elif 0.2 <= overlap <= 0.8:
                    score += 15
                
                scores.append(score)
                
            except Exception as e:
                logger.warning(f"Validation error: {e}")
                scores.append(0)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def benchmark_model(self, 
                       section_type: str,
                       num_generations: int = 20) -> Dict[str, float]:
        """
        Benchmark model performance.
        
        Args:
            section_type: Type of section
            num_generations: Number of test generations
        
        Returns:
            Benchmark statistics
        """
        model = self.manager.get_model(section_type)
        
        if not model:
            logger.error(f"Model not found: {section_type}")
            return {}
        
        logger.info(f"Benchmarking {section_type} model ({num_generations} generations)")
        
        stats = {
            'successful_generations': 0,
            'avg_length': 0,
            'avg_uniqueness': 0,
            'generation_times': []
        }
        
        generated_texts = []
        
        for i in range(num_generations):
            import time
            start = time.time()
            
            try:
                text = model.generate_variation(
                    min_length=50,
                    max_length=200,
                    temperature=0.7
                )
                
                if text:
                    stats['successful_generations'] += 1
                    generated_texts.append(text)
                    stats['avg_length'] += len(text.split())
                
                stats['generation_times'].append(time.time() - start)
                
            except Exception as e:
                logger.warning(f"Benchmark generation {i} failed: {e}")
        
        # Calculate averages
        if stats['successful_generations'] > 0:
            stats['avg_length'] /= stats['successful_generations']
            
            # Calculate uniqueness (average pairwise difference)
            uniqueness_scores = []
            for i, text1 in enumerate(generated_texts):
                for text2 in generated_texts[i+1:]:
                    words1 = set(text1.lower().split())
                    words2 = set(text2.lower().split())
                    similarity = len(words1 & words2) / max(len(words1 | words2), 1)
                    uniqueness_scores.append(1 - similarity)
            
            if uniqueness_scores:
                stats['avg_uniqueness'] = sum(uniqueness_scores) / len(uniqueness_scores)
        
        stats['avg_generation_time'] = sum(stats['generation_times']) / len(stats['generation_times'])
        stats['success_rate'] = stats['successful_generations'] / num_generations
        
        logger.info(f"Benchmark results: {stats}")
        
        return stats


def create_trainer(base_dir: str = "markov_text_generation") -> ModelTrainer:
    """
    Create a configured ModelTrainer instance.
    
    Args:
        base_dir: Base directory for markov system
    
    Returns:
        Configured ModelTrainer
    """
    processor = DataProcessor(
        raw_data_dir=f"{base_dir}/training_data/raw",
        processed_data_dir=f"{base_dir}/training_data/processed"
    )
    
    manager = ModelManager(
        models_dir=f"{base_dir}/models"
    )
    
    return ModelTrainer(processor, manager)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    trainer = create_trainer()
    
    # Train all section models
    models = trainer.train_all_sections(order=2, min_samples=5)
    
    # Benchmark a model
    if models.get('introduction'):
        benchmark = trainer.benchmark_model('introduction', num_generations=10)
        print(f"Benchmark results: {benchmark}")
