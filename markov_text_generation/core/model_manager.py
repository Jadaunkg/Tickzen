"""
Model Manager
=============

Handles model versioning, loading, saving, and lifecycle management.
Supports multiple specialized models for different financial text types.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
import logging

from .engine import MarkovEngine

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages multiple Markov models for different financial text sections.
    
    Features:
    - Model versioning and metadata tracking
    - Hot-swapping of models
    - Automatic model selection based on section type
    - Model performance tracking
    """
    
    # Predefined model types for financial analysis
    MODEL_TYPES = [
        'introduction',
        'technical_analysis',
        'fundamental_analysis',
        'valuation',
        'conclusion',
        'risk_analysis',
        'general',
        # NEW: 18 additional section types
        'sector_analysis',
        'competitive_positioning',
        'growth_prospects',
        'dividend_analysis',
        'earnings_analysis',
        'revenue_breakdown',
        'profit_margins',
        'cash_flow_analysis',
        'balance_sheet_strength',
        'management_quality',
        'market_sentiment',
        'analyst_consensus',
        'historical_performance',
        'future_catalysts',
        'regulatory_environment',
        'esg_sustainability',
        'investment_thesis',
        'quarterly_earnings',
        'sentiment_analysis'
    ]
    
    def __init__(self, models_dir: str):
        """
        Initialize Model Manager.
        
        Args:
            models_dir: Directory where models are stored
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache of loaded models {model_type: MarkovEngine}
        self.loaded_models: Dict[str, MarkovEngine] = {}
        
        # Model metadata
        self.metadata_file = self.models_dir / 'models_metadata.json'
        self.metadata = self._load_metadata()
    
    def create_model(self, 
                    model_type: str,
                    order: int = 2,
                    description: str = "") -> MarkovEngine:
        """
        Create a new model for a specific section type.
        
        Args:
            model_type: Type of model (e.g., 'introduction', 'technical_analysis')
            order: N-gram order
            description: Model description
        
        Returns:
            New MarkovEngine instance
        """
        if model_type not in self.MODEL_TYPES:
            logger.warning(f"Non-standard model type: {model_type}")
        
        model = MarkovEngine(order=order)
        
        # Update metadata
        if model_type not in self.metadata:
            self.metadata[model_type] = {
                'created_at': datetime.now().isoformat(),
                'versions': []
            }
        
        self.metadata[model_type]['description'] = description
        self.metadata[model_type]['order'] = order
        self.metadata[model_type]['last_modified'] = datetime.now().isoformat()
        
        self._save_metadata()
        
        logger.info(f"Created new {model_type} model (order={order})")
        return model
    
    def save_model(self, 
                   model: MarkovEngine,
                   model_type: str,
                   version: Optional[str] = None,
                   notes: str = "") -> str:
        """
        Save a model with versioning.
        
        Args:
            model: Trained MarkovEngine instance
            model_type: Type of model
            version: Version string (auto-generated if None)
            notes: Version notes
        
        Returns:
            Path to saved model
        """
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create model subdirectory
        model_dir = self.models_dir / model_type
        model_dir.mkdir(exist_ok=True)
        
        # Save model file
        model_filename = f"{model_type}_v{version}.json"
        model_path = model_dir / model_filename
        
        model.save(str(model_path))
        
        # Update metadata
        if model_type not in self.metadata:
            self.metadata[model_type] = {
                'created_at': datetime.now().isoformat(),
                'versions': []
            }
        
        version_info = {
            'version': version,
            'filename': model_filename,
            'saved_at': datetime.now().isoformat(),
            'notes': notes,
            'stats': model.get_stats()
        }
        
        self.metadata[model_type]['versions'].append(version_info)
        self.metadata[model_type]['latest_version'] = version
        self.metadata[model_type]['last_modified'] = datetime.now().isoformat()
        
        self._save_metadata()
        
        logger.info(f"Saved {model_type} model version {version}")
        return str(model_path)
    
    def load_model(self, 
                   model_type: str,
                   version: Optional[str] = None,
                   cache: bool = True) -> MarkovEngine:
        """
        Load a model by type and version.
        
        Args:
            model_type: Type of model to load
            version: Specific version (loads latest if None)
            cache: Cache the loaded model
        
        Returns:
            Loaded MarkovEngine instance
        """
        # Check cache first
        if cache and model_type in self.loaded_models:
            logger.debug(f"Using cached {model_type} model")
            return self.loaded_models[model_type]
        
        # Get version info
        if model_type not in self.metadata:
            raise ValueError(f"No models found for type: {model_type}")
        
        if version is None:
            version = self.metadata[model_type].get('latest_version')
            if not version:
                raise ValueError(f"No versions found for {model_type}")
        
        # Find model file
        version_info = None
        for v in self.metadata[model_type]['versions']:
            if v['version'] == version:
                version_info = v
                break
        
        if not version_info:
            raise ValueError(f"Version {version} not found for {model_type}")
        
        model_path = self.models_dir / model_type / version_info['filename']
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Load model
        model = MarkovEngine()
        model.load(str(model_path))
        
        # Cache if requested
        if cache:
            self.loaded_models[model_type] = model
        
        logger.info(f"Loaded {model_type} model version {version}")
        return model
    
    def get_model(self, model_type: str) -> Optional[MarkovEngine]:
        """
        Get a model by type (loads if not cached).
        
        Args:
            model_type: Type of model
        
        Returns:
            MarkovEngine instance or None if not found
        """
        try:
            return self.load_model(model_type, cache=True)
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Could not load {model_type} model: {e}")
            return None
    
    def list_models(self) -> List[Dict]:
        """
        List all available models.
        
        Returns:
            List of model information dictionaries
        """
        models = []
        for model_type, info in self.metadata.items():
            models.append({
                'type': model_type,
                'created_at': info.get('created_at'),
                'last_modified': info.get('last_modified'),
                'num_versions': len(info.get('versions', [])),
                'latest_version': info.get('latest_version'),
                'description': info.get('description', '')
            })
        return models
    
    def get_model_info(self, model_type: str) -> Optional[Dict]:
        """Get detailed information about a specific model."""
        return self.metadata.get(model_type)
    
    def delete_model_version(self, model_type: str, version: str):
        """
        Delete a specific model version.
        
        Args:
            model_type: Type of model
            version: Version to delete
        """
        if model_type not in self.metadata:
            raise ValueError(f"Model type not found: {model_type}")
        
        # Find and remove version
        versions = self.metadata[model_type]['versions']
        version_info = None
        for i, v in enumerate(versions):
            if v['version'] == version:
                version_info = versions.pop(i)
                break
        
        if not version_info:
            raise ValueError(f"Version not found: {version}")
        
        # Delete file
        model_path = self.models_dir / model_type / version_info['filename']
        if model_path.exists():
            model_path.unlink()
        
        # Update metadata
        if not versions:
            self.metadata[model_type]['latest_version'] = None
        else:
            self.metadata[model_type]['latest_version'] = versions[-1]['version']
        
        self._save_metadata()
        
        logger.info(f"Deleted {model_type} version {version}")
    
    def clear_cache(self):
        """Clear all cached models from memory."""
        self.loaded_models.clear()
        logger.info("Model cache cleared")
    
    def backup_models(self, backup_dir: str):
        """
        Create a backup of all models.
        
        Args:
            backup_dir: Directory to store backup
        """
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"models_backup_{timestamp}"
        backup_full_path = backup_path / backup_name
        
        shutil.copytree(self.models_dir, backup_full_path)
        
        logger.info(f"Backup created: {backup_full_path}")
        return str(backup_full_path)
    
    def _load_metadata(self) -> Dict:
        """Load metadata from file."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)


if __name__ == "__main__":
    # Test the manager
    manager = ModelManager("test_models")
    
    # Create and save a test model
    model = manager.create_model('introduction', order=2, description="Test intro model")
    model.train(["This is a test sentence."])
    
    manager.save_model(model, 'introduction', notes="Initial test version")
    
    # Load and test
    loaded = manager.load_model('introduction')
    print("Model loaded successfully")
    print(manager.list_models())
