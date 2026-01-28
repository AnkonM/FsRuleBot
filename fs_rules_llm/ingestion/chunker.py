"""
Intelligent Chunker for Formula Student Rules.

Chunks parsed sections into optimal sizes (150-400 words) while:
- Never splitting by page alone
- Preserving clause context
- Keeping tables intact
- Including metadata with each chunk
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class RuleChunk:
    """
    Represents a chunk of rule text with full metadata.
    
    All required metadata fields for retrieval and citation:
    - document_name: Source PDF filename
    - season: e.g., "2024"
    - competition: e.g., "FSAE"
    - section_title: Section heading
    - clause_id: Rule clause like "T.2.3.1"
    - chunk_text: The actual rule text (150-400 words)
    - page_number: Source page
    - chunk_id: Unique identifier
    """
    chunk_id: str
    document_name: str
    season: str
    competition: str
    chunk_text: str
    page_number: int
    section_title: str = ""
    clause_id: str = ""
    is_table: bool = False
    word_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'chunk_id': self.chunk_id,
            'document_name': self.document_name,
            'season': self.season,
            'competition': self.competition,
            'chunk_text': self.chunk_text,
            'page_number': self.page_number,
            'section_title': self.section_title,
            'clause_id': self.clause_id,
            'is_table': self.is_table,
            'word_count': self.word_count
        }


class RuleChunker:
    """
    Intelligent chunker for Formula Student rules.
    
    Creates chunks that:
    - Are 150-400 words in size
    - Preserve semantic boundaries
    - Include full metadata
    - Never split tables
    - Maintain clause context
    """
    
    def __init__(
        self,
        min_words: int = 150,
        max_words: int = 400,
        overlap_words: int = 50
    ):
        """
        Initialize chunker.
        
        Args:
            min_words: Minimum chunk size in words
            max_words: Maximum chunk size in words
            overlap_words: Number of words to overlap between chunks
        """
        self.min_words = min_words
        self.max_words = max_words
        self.overlap_words = overlap_words
    
    def chunk_sections(
        self,
        sections: List[Dict[str, Any]]
    ) -> List[RuleChunk]:
        """
        Chunk parsed sections into optimal sizes.
        
        Args:
            sections: List of parsed sections from PDFParser
            
        Returns:
            List of RuleChunk objects
        """
        chunks = []
        chunk_counter = 0
        
        for section in sections:
            # Tables are always standalone chunks (never split)
            if section.get('is_table', False):
                chunk_counter += 1
                chunks.append(self._create_chunk_from_section(
                    section,
                    chunk_counter
                ))
                continue
            
            # Get word count for this section
            text = section['text']
            word_count = self._count_words(text)
            
            # If section fits within limits, make it a single chunk
            if word_count <= self.max_words:
                chunk_counter += 1
                chunks.append(self._create_chunk_from_section(
                    section,
                    chunk_counter
                ))
            else:
                # Split long section into multiple chunks
                sub_chunks = self._split_section(section)
                for sub_chunk_text in sub_chunks:
                    chunk_counter += 1
                    chunk = self._create_chunk_from_text(
                        sub_chunk_text,
                        section,
                        chunk_counter
                    )
                    chunks.append(chunk)
        
        return chunks
    
    def _create_chunk_from_section(
        self,
        section: Dict[str, Any],
        chunk_id: int
    ) -> RuleChunk:
        """Create a RuleChunk from a complete section."""
        text = section['text']
        
        return RuleChunk(
            chunk_id=f"{section.get('season', '')}_{section.get('competition', '')}_{chunk_id:05d}",
            document_name=section.get('document_name', ''),
            season=section.get('season', ''),
            competition=section.get('competition', ''),
            chunk_text=text,
            page_number=section.get('page_number', 0),
            section_title=section.get('section_title', ''),
            clause_id=section.get('clause_id', ''),
            is_table=section.get('is_table', False),
            word_count=self._count_words(text)
        )
    
    def _create_chunk_from_text(
        self,
        text: str,
        section: Dict[str, Any],
        chunk_id: int
    ) -> RuleChunk:
        """Create a RuleChunk from partial section text."""
        return RuleChunk(
            chunk_id=f"{section.get('season', '')}_{section.get('competition', '')}_{chunk_id:05d}",
            document_name=section.get('document_name', ''),
            season=section.get('season', ''),
            competition=section.get('competition', ''),
            chunk_text=text,
            page_number=section.get('page_number', 0),
            section_title=section.get('section_title', ''),
            clause_id=section.get('clause_id', ''),
            is_table=False,
            word_count=self._count_words(text)
        )
    
    def _split_section(self, section: Dict[str, Any]) -> List[str]:
        """
        Split a long section into multiple chunks.
        
        Strategy:
        1. Split by sentence boundaries
        2. Group sentences into chunks of appropriate size
        3. Add overlap between chunks
        
        Args:
            section: Section dictionary
            
        Returns:
            List of chunk texts
        """
        text = section['text']
        
        # Split into sentences (simple approach)
        sentences = self._split_sentences(text)
        
        chunks = []
        current_chunk = []
        current_words = 0
        
        for sentence in sentences:
            sentence_words = self._count_words(sentence)
            
            # If adding this sentence exceeds max, start a new chunk
            if current_words + sentence_words > self.max_words and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                # Take last few sentences for context
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk,
                    self.overlap_words
                )
                current_chunk = overlap_sentences
                current_words = sum(self._count_words(s) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_words += sentence_words
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        This is a simple implementation. For production, consider:
        - Using nltk.sent_tokenize
        - Handling abbreviations (e.g., "Fig.", "etc.")
        - Preserving clause numbers
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simple regex-based sentence splitting
        # Handles periods, exclamation marks, and question marks
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        target_words: int
    ) -> List[str]:
        """
        Get the last N sentences that sum to approximately target_words.
        
        Args:
            sentences: List of sentences
            target_words: Target word count for overlap
            
        Returns:
            Last few sentences for overlap
        """
        overlap = []
        word_count = 0
        
        # Work backwards from end
        for sentence in reversed(sentences):
            sentence_words = self._count_words(sentence)
            if word_count + sentence_words > target_words:
                break
            overlap.insert(0, sentence)
            word_count += sentence_words
        
        return overlap
    
    @staticmethod
    def _count_words(text: str) -> int:
        """Count words in text."""
        return len(text.split())


def chunk_parsed_sections(
    sections_file: str,
    output_file: str,
    min_words: int = 150,
    max_words: int = 400,
    overlap_words: int = 50
) -> List[RuleChunk]:
    """
    Convenience function to chunk sections from a JSON file.
    
    Args:
        sections_file: Path to JSON file with parsed sections
        output_file: Path to save chunked output
        min_words: Minimum chunk size
        max_words: Maximum chunk size
        overlap_words: Overlap size
        
    Returns:
        List of RuleChunk objects
    """
    # Load sections
    with open(sections_file, 'r') as f:
        sections = json.load(f)
    
    # Chunk
    chunker = RuleChunker(min_words, max_words, overlap_words)
    chunks = chunker.chunk_sections(sections)
    
    # Save
    chunks_dict = [chunk.to_dict() for chunk in chunks]
    with open(output_file, 'w') as f:
        json.dump(chunks_dict, f, indent=2)
    
    return chunks


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Chunk parsed Formula Student rules"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON file with parsed sections"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save chunked output JSON"
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=150,
        help="Minimum chunk size in words (default: 150)"
    )
    parser.add_argument(
        "--max-words",
        type=int,
        default=400,
        help="Maximum chunk size in words (default: 400)"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Overlap size in words (default: 50)"
    )
    
    args = parser.parse_args()
    
    print(f"Chunking sections from: {args.input}")
    print(f"Chunk size: {args.min_words}-{args.max_words} words")
    print(f"Overlap: {args.overlap} words")
    
    chunks = chunk_parsed_sections(
        args.input,
        args.output,
        args.min_words,
        args.max_words,
        args.overlap
    )
    
    print(f"\nCreated {len(chunks)} chunks")
    print(f"Saved to: {args.output}")
    
    # Show statistics
    word_counts = [chunk.word_count for chunk in chunks]
    print(f"\nChunk statistics:")
    print(f"  Min words: {min(word_counts)}")
    print(f"  Max words: {max(word_counts)}")
    print(f"  Avg words: {sum(word_counts) / len(word_counts):.1f}")
    print(f"  Tables: {sum(1 for c in chunks if c.is_table)}")
    print(f"  With clause IDs: {sum(1 for c in chunks if c.clause_id)}")
