"""
Configuration loader for Formula Student Rules Compliance System.

Loads and validates season/competition configurations from seasons.yaml.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """
    Configuration manager for the rules compliance system.
    
    Loads configuration from seasons.yaml and provides access to
    season/competition settings, embedding parameters, and LLM settings.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to seasons.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default to config/seasons.yaml in the same directory as this file
            config_dir = Path(__file__).parent
            config_path = config_dir / "seasons.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate required sections
        required_sections = ['seasons', 'default', 'embeddings', 'chunking', 'retrieval', 'llm']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        return config
    
    def get_seasons(self) -> Dict[str, Any]:
        """Get all available seasons."""
        return self._config['seasons']
    
    def get_season(self, season: str) -> Dict[str, Any]:
        """
        Get configuration for a specific season.
        
        Args:
            season: Season identifier (e.g., "2024")
            
        Returns:
            Season configuration dictionary
            
        Raises:
            ValueError: If season is not configured
        """
        if season not in self._config['seasons']:
            available = list(self._config['seasons'].keys())
            raise ValueError(
                f"Season '{season}' not found in configuration. "
                f"Available seasons: {available}"
            )
        return self._config['seasons'][season]
    
    def get_competition(self, season: str, competition: str) -> Dict[str, Any]:
        """
        Get configuration for a specific competition within a season.
        
        Args:
            season: Season identifier (e.g., "2024")
            competition: Competition identifier (e.g., "FSAE")
            
        Returns:
            Competition configuration dictionary
            
        Raises:
            ValueError: If season or competition is not configured
        """
        season_config = self.get_season(season)
        
        if 'competitions' not in season_config:
            raise ValueError(f"Season '{season}' has no competitions configured")
        
        if competition not in season_config['competitions']:
            available = list(season_config['competitions'].keys())
            raise ValueError(
                f"Competition '{competition}' not found in season '{season}'. "
                f"Available competitions: {available}"
            )
        
        return season_config['competitions'][competition]
    
    def validate_season_competition(self, season: str, competition: str) -> bool:
        """
        Validate that a season/competition pair is configured.
        
        Args:
            season: Season identifier
            competition: Competition identifier
            
        Returns:
            True if valid, raises ValueError if not
        """
        self.get_competition(season, competition)
        return True
    
    @property
    def default_season(self) -> str:
        """Get default season."""
        return self._config['default']['season']
    
    @property
    def default_competition(self) -> str:
        """Get default competition."""
        return self._config['default']['competition']
    
    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        return self._config['embeddings']['model']
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._config['embeddings']['dimension']
    
    @property
    def chunk_min_words(self) -> int:
        """Get minimum chunk size in words."""
        return self._config['chunking']['min_words']
    
    @property
    def chunk_max_words(self) -> int:
        """Get maximum chunk size in words."""
        return self._config['chunking']['max_words']
    
    @property
    def chunk_overlap_words(self) -> int:
        """Get chunk overlap size in words."""
        return self._config['chunking']['overlap_words']
    
    @property
    def retrieval_top_k(self) -> int:
        """Get number of chunks to retrieve."""
        return self._config['retrieval']['top_k']
    
    @property
    def retrieval_max_k(self) -> int:
        """Get maximum number of chunks to retrieve."""
        return self._config['retrieval']['max_k']
    
    @property
    def retrieval_threshold(self) -> float:
        """Get similarity threshold for retrieval."""
        return self._config['retrieval']['similarity_threshold']
    
    @property
    def llm_provider(self) -> str:
        """Get LLM provider name."""
        return self._config['llm']['provider']
    
    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self._config['llm']['model']
    
    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature (0.0 for deterministic)."""
        return self._config['llm']['temperature']
    
    @property
    def llm_max_tokens(self) -> int:
        """Get LLM max tokens."""
        return self._config['llm']['max_tokens']


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Configuration instance
    """
    global _config_instance
    
    if _config_instance is None or config_path is not None:
        _config_instance = Config(config_path)
    
    return _config_instance
