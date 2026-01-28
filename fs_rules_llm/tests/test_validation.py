"""
Unit tests for chunk validation.

Tests validation logic and error detection.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.validate_chunks import ChunkValidator, ValidationError


class TestChunkValidator:
    """Test suite for ChunkValidator."""
    
    def test_valid_chunk(self):
        """Test that a valid chunk passes validation."""
        validator = ChunkValidator(min_words=150, max_words=400, strict=True)
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            'document_name': 'FSAE_Rules_2024.pdf',
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': ' '.join(['word'] * 200),
            'page_number': 1,
            'section_title': 'Test Section',
            'clause_id': 'T.1.1',
            'is_table': False,
            'word_count': 200
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should have no errors
        assert len(errors) == 0
    
    def test_missing_required_field(self):
        """Test that missing required fields are detected."""
        validator = ChunkValidator()
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            # Missing 'document_name'
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': 'Test text',
            'page_number': 1
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should have error for missing document_name
        assert len(errors) > 0
        assert any(e.error_type == 'missing_field' for e in errors)
    
    def test_empty_required_field(self):
        """Test that empty required fields are detected."""
        validator = ChunkValidator()
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            'document_name': '',  # Empty
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': 'Test text',
            'page_number': 1
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should have error for empty document_name
        assert len(errors) > 0
        assert any(e.error_type == 'empty_field' for e in errors)
    
    def test_chunk_too_short(self):
        """Test that chunks below minimum size trigger warning."""
        validator = ChunkValidator(min_words=150, max_words=400)
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            'document_name': 'test.pdf',
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': 'Short text',  # Only 2 words
            'page_number': 1,
            'word_count': 2,
            'is_table': False
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should have warning for being too short
        assert len(errors) > 0
        assert any(e.error_type == 'too_short' for e in errors)
        assert any(e.severity == 'warning' for e in errors)
    
    def test_chunk_too_long(self):
        """Test that chunks above maximum size trigger error."""
        validator = ChunkValidator(min_words=150, max_words=400)
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            'document_name': 'test.pdf',
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': ' '.join(['word'] * 500),
            'page_number': 1,
            'word_count': 500,
            'is_table': False
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should have error for being too long
        assert len(errors) > 0
        assert any(e.error_type == 'too_long' for e in errors)
        assert any(e.severity == 'error' for e in errors)
    
    def test_table_can_be_short(self):
        """Test that tables are allowed to be short."""
        validator = ChunkValidator(min_words=150, max_words=400)
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            'document_name': 'test.pdf',
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': 'Header | Value\nRow1 | Data1',
            'page_number': 1,
            'word_count': 6,
            'is_table': True
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should not have too_short error for tables
        assert not any(e.error_type == 'too_short' for e in errors)
    
    def test_corrupted_text_detection(self):
        """Test detection of corrupted text."""
        validator = ChunkValidator()
        
        # Text with excessive special characters
        corrupted_text = '@#$%^&*()_+{}|:<>?~`'
        
        chunk = {
            'chunk_id': '2024_FSAE_00001',
            'document_name': 'test.pdf',
            'season': '2024',
            'competition': 'FSAE',
            'chunk_text': corrupted_text,
            'page_number': 1,
            'word_count': 1
        }
        
        errors = validator.validate_chunk(chunk)
        
        # Should detect corruption
        assert len(errors) > 0
        assert any(e.error_type == 'corrupted_text' for e in errors)
    
    def test_validate_chunks_strict_mode(self):
        """Test validation in strict mode (rejects warnings)."""
        validator = ChunkValidator(min_words=150, max_words=400, strict=True)
        
        chunks = [
            # Valid chunk
            {
                'chunk_id': '2024_FSAE_00001',
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'chunk_text': ' '.join(['word'] * 200),
                'page_number': 1,
                'word_count': 200,
                'is_table': False
            },
            # Chunk with warning (too short)
            {
                'chunk_id': '2024_FSAE_00002',
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'chunk_text': 'Short',
                'page_number': 2,
                'word_count': 1,
                'is_table': False
            }
        ]
        
        valid_chunks, errors = validator.validate_chunks(chunks)
        
        # In strict mode, chunk with warning should be rejected
        assert len(valid_chunks) == 1
        assert len(errors) > 0
    
    def test_validate_chunks_non_strict_mode(self):
        """Test validation in non-strict mode (accepts warnings)."""
        validator = ChunkValidator(min_words=150, max_words=400, strict=False)
        
        chunks = [
            # Valid chunk
            {
                'chunk_id': '2024_FSAE_00001',
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'chunk_text': ' '.join(['word'] * 200),
                'page_number': 1,
                'word_count': 200,
                'is_table': False
            },
            # Chunk with warning (too short, but it's a table)
            {
                'chunk_id': '2024_FSAE_00002',
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'chunk_text': 'Header | Value',
                'page_number': 2,
                'word_count': 3,
                'is_table': True
            }
        ]
        
        valid_chunks, errors = validator.validate_chunks(chunks)
        
        # In non-strict mode, chunk with warning should be accepted
        assert len(valid_chunks) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
