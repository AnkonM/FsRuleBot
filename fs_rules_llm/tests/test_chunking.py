"""
Unit tests for the chunking module.

Tests chunking logic, metadata preservation, and validation.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.chunker import RuleChunker, RuleChunk


class TestRuleChunker:
    """Test suite for RuleChunker."""
    
    def test_chunk_single_section_within_limits(self):
        """Test chunking a section that fits within size limits."""
        chunker = RuleChunker(min_words=150, max_words=400)
        
        # Create a section with ~200 words
        text = " ".join(["word"] * 200)
        sections = [
            {
                'text': text,
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 1,
                'section_title': 'Test Section',
                'clause_id': 'T.1.1',
                'is_table': False
            }
        ]
        
        chunks = chunker.chunk_sections(sections)
        
        assert len(chunks) == 1
        assert chunks[0].word_count == 200
        assert chunks[0].clause_id == 'T.1.1'
        assert chunks[0].season == '2024'
    
    def test_chunk_long_section_splits(self):
        """Test that long sections are split into multiple chunks."""
        chunker = RuleChunker(min_words=150, max_words=400)
        
        # Create a section with 800 words
        text = ". ".join([" ".join(["word"] * 10)] * 80)
        sections = [
            {
                'text': text,
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 1,
                'section_title': 'Long Section',
                'clause_id': 'T.2.1',
                'is_table': False
            }
        ]
        
        chunks = chunker.chunk_sections(sections)
        
        # Should be split into multiple chunks
        assert len(chunks) > 1
        
        # All chunks should have metadata
        for chunk in chunks:
            assert chunk.season == '2024'
            assert chunk.competition == 'FSAE'
            assert chunk.section_title == 'Long Section'
    
    def test_table_never_split(self):
        """Test that tables are never split, even if large."""
        chunker = RuleChunker(min_words=150, max_words=400)
        
        # Create a large table (>400 words)
        text = " ".join(["cell"] * 500)
        sections = [
            {
                'text': text,
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 1,
                'section_title': 'Table',
                'clause_id': 'T.3.1',
                'is_table': True
            }
        ]
        
        chunks = chunker.chunk_sections(sections)
        
        # Table should remain as single chunk despite size
        assert len(chunks) == 1
        assert chunks[0].is_table is True
        assert chunks[0].word_count == 500
    
    def test_chunk_metadata_preserved(self):
        """Test that all metadata is preserved in chunks."""
        chunker = RuleChunker()
        
        sections = [
            {
                'text': " ".join(["word"] * 200),
                'document_name': 'FSAE_Rules_2024.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 42,
                'section_title': 'Technical Rules - Chassis',
                'clause_id': 'T.2.3.1',
                'is_table': False
            }
        ]
        
        chunks = chunker.chunk_sections(sections)
        chunk = chunks[0]
        
        assert chunk.document_name == 'FSAE_Rules_2024.pdf'
        assert chunk.season == '2024'
        assert chunk.competition == 'FSAE'
        assert chunk.page_number == 42
        assert chunk.section_title == 'Technical Rules - Chassis'
        assert chunk.clause_id == 'T.2.3.1'
    
    def test_chunk_id_generation(self):
        """Test that chunk IDs are unique and sequential."""
        chunker = RuleChunker()
        
        sections = [
            {
                'text': " ".join(["word"] * 200),
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 1,
                'is_table': False
            },
            {
                'text': " ".join(["word"] * 200),
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 2,
                'is_table': False
            }
        ]
        
        chunks = chunker.chunk_sections(sections)
        
        # Check IDs are unique
        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))
        
        # Check IDs contain season and competition
        for chunk_id in chunk_ids:
            assert '2024' in chunk_id
            assert 'FSAE' in chunk_id
    
    def test_empty_sections(self):
        """Test handling of empty sections."""
        chunker = RuleChunker()
        
        sections = []
        chunks = chunker.chunk_sections(sections)
        
        assert len(chunks) == 0
    
    def test_word_count_accuracy(self):
        """Test that word count is accurate."""
        chunker = RuleChunker()
        
        text = "one two three four five"
        sections = [
            {
                'text': text,
                'document_name': 'test.pdf',
                'season': '2024',
                'competition': 'FSAE',
                'page_number': 1,
                'is_table': False
            }
        ]
        
        chunks = chunker.chunk_sections(sections)
        
        assert chunks[0].word_count == 5


class TestRuleChunk:
    """Test suite for RuleChunk data class."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        chunk = RuleChunk(
            chunk_id='2024_FSAE_00001',
            document_name='test.pdf',
            season='2024',
            competition='FSAE',
            chunk_text='Test text',
            page_number=1,
            section_title='Test',
            clause_id='T.1.1',
            is_table=False,
            word_count=2
        )
        
        chunk_dict = chunk.to_dict()
        
        assert chunk_dict['chunk_id'] == '2024_FSAE_00001'
        assert chunk_dict['season'] == '2024'
        assert chunk_dict['competition'] == 'FSAE'
        assert chunk_dict['word_count'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
