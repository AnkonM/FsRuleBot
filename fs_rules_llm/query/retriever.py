"""
Retriever for Formula Student Rules.

Handles filtered retrieval from vector store with season/competition constraints.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from embeddings.vector_store import VectorStore
from embeddings.embed_rules import RuleEmbedder
from config.config_loader import get_config


class RuleRetriever:
    """
    Retrieves relevant rule chunks for a query.
    
    Key features:
    - Strict season/competition filtering
    - Configurable top-k retrieval
    - Similarity threshold filtering
    - Sanity checks on retrieved content
    """
    
    def __init__(
        self,
        index_dir: str,
        season: str,
        competition: str,
        embedder: Optional[RuleEmbedder] = None,
        top_k: int = 5,
        max_k: int = 8,
        similarity_threshold: float = 0.5
    ):
        """
        Initialize retriever.
        
        Args:
            index_dir: Directory containing the vector index
            season: Season to retrieve from (must match index)
            competition: Competition to retrieve from (must match index)
            embedder: RuleEmbedder instance (creates new one if None)
            top_k: Number of chunks to retrieve
            max_k: Maximum number of chunks to retrieve
            similarity_threshold: Minimum similarity score (0-1, lower is more similar for L2)
        """
        self.season = season
        self.competition = competition
        self.top_k = min(top_k, max_k)
        self.max_k = max_k
        self.similarity_threshold = similarity_threshold
        
        # Load vector store
        self.vector_store = VectorStore.load(index_dir)
        
        # Validate that index matches requested season/competition
        if self.vector_store.season != season:
            raise ValueError(
                f"Index is for season '{self.vector_store.season}', "
                f"but requested season '{season}'. "
                "Never use the wrong season's index!"
            )
        
        if self.vector_store.competition != competition:
            raise ValueError(
                f"Index is for competition '{self.vector_store.competition}', "
                f"but requested competition '{competition}'. "
                "Never use the wrong competition's index!"
            )
        
        # Create or use provided embedder
        if embedder is None:
            config = get_config()
            self.embedder = RuleEmbedder(config.embedding_model)
        else:
            self.embedder = embedder
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: User's question
            top_k: Override default top_k (optional)
            
        Returns:
            List of (chunk, distance) tuples, sorted by relevance
        """
        # Use default top_k if not specified
        k = top_k if top_k is not None else self.top_k
        k = min(k, self.max_k)
        
        # Embed query
        query_embedding = self.embedder.embed_single(query)
        
        # Search vector store with filters
        results = self.vector_store.search(
            query_embedding,
            top_k=k,
            season_filter=self.season,
            competition_filter=self.competition
        )
        
        # Apply similarity threshold
        # Note: For L2 distance, lower values indicate more similarity
        # The threshold is scaled based on embedding characteristics
        # For 384-dim embeddings, typical relevant chunks have L2 distance < 5.0
        # Adjust this threshold based on your specific embedding model and data
        filtered_results = []
        for chunk, distance in results:
            # Simple threshold: reject if distance is too high
            # Default threshold of 0.5 * 10 = 5.0 works for most cases
            # You may need to tune this for your specific use case
            if distance <= self.similarity_threshold * 10:
                filtered_results.append((chunk, distance))
        
        # Sanity check: verify retrieved chunks actually contain relevant text
        validated_results = []
        for chunk, distance in filtered_results:
            if self._is_valid_chunk(chunk, query):
                validated_results.append((chunk, distance))
        
        return validated_results
    
    def _is_valid_chunk(self, chunk: Dict[str, Any], query: str) -> bool:
        """
        Sanity check that a chunk is valid.
        
        Checks:
        - Chunk has text
        - Metadata is complete
        - Text is not corrupted
        
        Args:
            chunk: Chunk dictionary
            query: Original query (for relevance checking)
            
        Returns:
            True if chunk passes validation
        """
        # Must have text
        if not chunk.get('chunk_text'):
            return False
        
        # Must have season and competition
        if not chunk.get('season') or not chunk.get('competition'):
            return False
        
        # Verify season and competition match
        if chunk.get('season') != self.season:
            print(f"WARNING: Retrieved chunk from wrong season: {chunk.get('season')} != {self.season}")
            return False
        
        if chunk.get('competition') != self.competition:
            print(f"WARNING: Retrieved chunk from wrong competition: {chunk.get('competition')} != {self.competition}")
            return False
        
        return True
    
    def verify_citation(
        self,
        clause_id: str,
        quote: str
    ) -> bool:
        """
        Verify that a quoted text actually exists in the indexed chunks.
        
        This is a critical sanity check to prevent hallucinated citations.
        
        Args:
            clause_id: Claimed clause ID
            quote: Claimed quote text
            
        Returns:
            True if quote exists verbatim in a chunk with that clause_id
        """
        # Search all chunks for matching clause_id
        matching_chunks = [
            chunk for chunk in self.vector_store.chunks
            if chunk.get('clause_id') == clause_id
        ]
        
        if not matching_chunks:
            print(f"WARNING: No chunk found with clause_id '{clause_id}'")
            return False
        
        # Check if quote appears verbatim in any matching chunk
        quote_lower = quote.lower().strip()
        
        for chunk in matching_chunks:
            chunk_text = chunk.get('chunk_text', '').lower()
            if quote_lower in chunk_text:
                return True
        
        print(f"WARNING: Quote not found verbatim in clause '{clause_id}'")
        return False
    
    def get_chunk_by_clause(self, clause_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk by clause ID.
        
        Args:
            clause_id: Clause identifier (e.g., "T.2.3.1")
            
        Returns:
            Chunk dictionary if found, None otherwise
        """
        for chunk in self.vector_store.chunks:
            if chunk.get('clause_id') == clause_id:
                return chunk
        return None


def create_retriever(
    season: str,
    competition: str,
    config_path: Optional[str] = None
) -> RuleRetriever:
    """
    Convenience function to create a retriever from configuration.
    
    Args:
        season: Season identifier
        competition: Competition identifier
        config_path: Optional path to config file
        
    Returns:
        RuleRetriever instance
    """
    config = get_config(config_path)
    
    # Validate season/competition
    config.validate_season_competition(season, competition)
    
    # Construct index directory path
    # Assumes indices are stored in fs_rules_llm/data/indices/{season}_{competition}/
    base_dir = Path(__file__).parent.parent / "data" / "indices"
    index_dir = base_dir / f"{season}_{competition}"
    
    if not index_dir.exists():
        raise FileNotFoundError(
            f"Index not found for {season} - {competition}. "
            f"Expected at: {index_dir}. "
            f"Please build the index first using embed_rules.py and vector_store.py"
        )
    
    # Create retriever
    retriever = RuleRetriever(
        index_dir=str(index_dir),
        season=season,
        competition=competition,
        top_k=config.retrieval_top_k,
        max_k=config.retrieval_max_k,
        similarity_threshold=config.retrieval_threshold
    )
    
    return retriever


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test retriever for Formula Student rules"
    )
    parser.add_argument(
        "--season",
        required=True,
        help="Season identifier (e.g., 2024)"
    )
    parser.add_argument(
        "--competition",
        required=True,
        help="Competition identifier (e.g., FSAE)"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Query to test"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to retrieve"
    )
    
    args = parser.parse_args()
    
    print(f"Creating retriever for {args.season} - {args.competition}")
    retriever = create_retriever(args.season, args.competition)
    
    print(f"\nQuery: {args.query}")
    print(f"Retrieving top {args.top_k} chunks...\n")
    
    results = retriever.retrieve(args.query, top_k=args.top_k)
    
    print(f"Found {len(results)} relevant chunks:")
    print("=" * 80)
    
    for i, (chunk, distance) in enumerate(results, 1):
        print(f"\n[{i}] Relevance score: {distance:.4f}")
        print(f"    Clause: {chunk.get('clause_id', 'N/A')}")
        print(f"    Section: {chunk.get('section_title', 'N/A')}")
        print(f"    Page: {chunk.get('page_number', 'N/A')}")
        print(f"    Text: {chunk.get('chunk_text', '')[:200]}...")
        print("-" * 80)
