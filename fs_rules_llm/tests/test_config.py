"""
Unit tests for configuration loader.

Tests configuration loading and validation.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import Config


class TestConfig:
    """Test suite for Config class."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        config = Config()
        
        # Check that required sections are loaded
        assert config.default_season is not None
        assert config.default_competition is not None
        assert config.embedding_model is not None
    
    def test_get_season(self):
        """Test retrieving season configuration."""
        config = Config()
        
        # Should have 2024 season configured
        season_2024 = config.get_season('2024')
        
        assert season_2024 is not None
        assert 'competitions' in season_2024
    
    def test_get_invalid_season(self):
        """Test that invalid season raises error."""
        config = Config()
        
        with pytest.raises(ValueError, match="not found"):
            config.get_season('1999')
    
    def test_get_competition(self):
        """Test retrieving competition configuration."""
        config = Config()
        
        # Should have FSAE in 2024
        fsae_2024 = config.get_competition('2024', 'FSAE')
        
        assert fsae_2024 is not None
        assert 'full_name' in fsae_2024
    
    def test_get_invalid_competition(self):
        """Test that invalid competition raises error."""
        config = Config()
        
        with pytest.raises(ValueError, match="not found"):
            config.get_competition('2024', 'INVALID')
    
    def test_validate_season_competition(self):
        """Test season/competition validation."""
        config = Config()
        
        # Valid combination should return True
        assert config.validate_season_competition('2024', 'FSAE') is True
        
        # Invalid combination should raise error
        with pytest.raises(ValueError):
            config.validate_season_competition('2024', 'INVALID')
    
    def test_config_properties(self):
        """Test configuration property accessors."""
        config = Config()
        
        # Check embedding config
        assert config.embedding_model is not None
        assert config.embedding_dimension > 0
        
        # Check chunking config
        assert config.chunk_min_words > 0
        assert config.chunk_max_words > config.chunk_min_words
        assert config.chunk_overlap_words > 0
        
        # Check retrieval config
        assert config.retrieval_top_k > 0
        assert config.retrieval_max_k >= config.retrieval_top_k
        
        # Check LLM config
        assert config.llm_provider is not None
        assert config.llm_model is not None
        assert config.llm_temperature == 0.0  # Must be deterministic
    
    def test_get_seasons(self):
        """Test retrieving all seasons."""
        config = Config()
        
        seasons = config.get_seasons()
        
        assert isinstance(seasons, dict)
        assert '2024' in seasons
        assert '2023' in seasons


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
