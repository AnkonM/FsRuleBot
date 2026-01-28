"""
FAISS Vector Store for Formula Student Rules.

Local vector storage with strict season/competition filtering.
Never mixes rules from different seasons.
"""

import json
import pickle
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import faiss


class VectorStore:
    """
    FAISS-based vector store for rule chunks.
    
    Key features:
    - Local storage (no external dependencies)
    - Strict metadata filtering by season/competition
    - Efficient similarity search
    - Separate indices per season for isolation
    """
    
    def __init__(
        self,
        embedding_dim: int = 384,
        season: str = None,
        competition: str = None
    ):
        """
        Initialize vector store.
        
        Args:
            embedding_dim: Dimension of embeddings
            season: Season identifier for this index
            competition: Competition identifier for this index
        """
        self.embedding_dim = embedding_dim
        self.season = season
        self.competition = competition
        
        # FAISS index (using L2 distance)
        self.index = faiss.IndexFlatL2(embedding_dim)
        
        # Metadata storage (parallel to index)
        # Maps index position to chunk metadata
        self.chunks: List[Dict[str, Any]] = []
    
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray
    ):
        """
        Add chunks and their embeddings to the index.
        
        Args:
            chunks: List of chunk dictionaries
            embeddings: NumPy array of embeddings (num_chunks, embedding_dim)
        """
        # Validate inputs
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match "
                f"number of embeddings ({embeddings.shape[0]})"
            )
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension ({embeddings.shape[1]}) must match "
                f"index dimension ({self.embedding_dim})"
            )
        
        # If season/competition are set, validate all chunks match
        if self.season or self.competition:
            for chunk in chunks:
                if self.season and chunk.get('season') != self.season:
                    raise ValueError(
                        f"Chunk season '{chunk.get('season')}' does not match "
                        f"index season '{self.season}'. "
                        "Never mix seasons in the same index!"
                    )
                if self.competition and chunk.get('competition') != self.competition:
                    raise ValueError(
                        f"Chunk competition '{chunk.get('competition')}' does not match "
                        f"index competition '{self.competition}'. "
                        "Never mix competitions in the same index!"
                    )
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Add to metadata storage
        self.chunks.extend(chunks)
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        season_filter: str = None,
        competition_filter: str = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector (embedding_dim,)
            top_k: Number of results to return
            season_filter: Filter by season (must match index season if set)
            competition_filter: Filter by competition
            
        Returns:
            List of (chunk, distance) tuples, sorted by similarity
        """
        # Validate filters match index
        if self.season and season_filter and season_filter != self.season:
            raise ValueError(
                f"Cannot search season '{season_filter}' in index for season '{self.season}'. "
                "Use the correct index for the target season!"
            )
        
        if self.competition and competition_filter and competition_filter != self.competition:
            raise ValueError(
                f"Cannot search competition '{competition_filter}' in index for competition '{self.competition}'. "
                "Use the correct index for the target competition!"
            )
        
        if self.index.ntotal == 0:
            return []
        
        # Reshape query to (1, dim) for FAISS
        query = query_embedding.reshape(1, -1).astype('float32')
        
        # Search
        # Get more than top_k in case we need to filter
        k = min(top_k * 2, self.index.ntotal)
        distances, indices = self.index.search(query, k)
        
        # Collect results with metadata filtering
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            
            chunk = self.chunks[idx]
            
            # Apply additional metadata filters if needed
            # (though ideally the index is already filtered by season/competition)
            if season_filter and chunk.get('season') != season_filter:
                continue
            if competition_filter and chunk.get('competition') != competition_filter:
                continue
            
            results.append((chunk, float(distance)))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def save(self, index_dir: str):
        """
        Save the vector store to disk.
        
        Args:
            index_dir: Directory to save index files
        """
        index_path = Path(index_dir)
        index_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss_file = index_path / "index.faiss"
        faiss.write_index(self.index, str(faiss_file))
        
        # Save metadata
        metadata_file = index_path / "metadata.pkl"
        metadata = {
            'chunks': self.chunks,
            'embedding_dim': self.embedding_dim,
            'season': self.season,
            'competition': self.competition
        }
        with open(metadata_file, 'wb') as f:
            pickle.dump(metadata, f)
        
        print(f"Saved index to {index_dir}")
        print(f"  Total chunks: {len(self.chunks)}")
        print(f"  Season: {self.season}")
        print(f"  Competition: {self.competition}")
    
    @classmethod
    def load(cls, index_dir: str) -> 'VectorStore':
        """
        Load a vector store from disk.
        
        Args:
            index_dir: Directory containing index files
            
        Returns:
            VectorStore instance
        """
        index_path = Path(index_dir)
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index directory not found: {index_dir}")
        
        # Load metadata
        metadata_file = index_path / "metadata.pkl"
        with open(metadata_file, 'rb') as f:
            metadata = pickle.load(f)
        
        # Create instance
        store = cls(
            embedding_dim=metadata['embedding_dim'],
            season=metadata['season'],
            competition=metadata['competition']
        )
        
        # Load FAISS index
        faiss_file = index_path / "index.faiss"
        store.index = faiss.read_index(str(faiss_file))
        
        # Load chunks
        store.chunks = metadata['chunks']
        
        print(f"Loaded index from {index_dir}")
        print(f"  Total chunks: {len(store.chunks)}")
        print(f"  Season: {store.season}")
        print(f"  Competition: {store.competition}")
        
        return store
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Dictionary with index statistics
        """
        return {
            'total_chunks': len(self.chunks),
            'embedding_dim': self.embedding_dim,
            'season': self.season,
            'competition': self.competition,
            'has_clause_ids': sum(1 for c in self.chunks if c.get('clause_id')),
            'has_section_titles': sum(1 for c in self.chunks if c.get('section_title')),
            'tables': sum(1 for c in self.chunks if c.get('is_table'))
        }


def build_vector_store(
    chunks_file: str,
    embeddings_file: str,
    output_dir: str,
    season: str,
    competition: str,
    embedding_dim: int = 384
) -> VectorStore:
    """
    Build and save a vector store from chunks and embeddings.
    
    Args:
        chunks_file: Path to JSON file with chunks
        embeddings_file: Path to .npy file with embeddings
        output_dir: Directory to save the index
        season: Season identifier
        competition: Competition identifier
        embedding_dim: Embedding dimension
        
    Returns:
        VectorStore instance
    """
    # Load chunks
    with open(chunks_file, 'r') as f:
        chunks = json.load(f)
    
    # Load embeddings
    embeddings = np.load(embeddings_file)
    
    print(f"Building index for {season} - {competition}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Embeddings: {embeddings.shape}")
    
    # Create vector store
    store = VectorStore(
        embedding_dim=embedding_dim,
        season=season,
        competition=competition
    )
    
    # Add chunks
    store.add_chunks(chunks, embeddings)
    
    # Save
    store.save(output_dir)
    
    # Print stats
    stats = store.get_stats()
    print("\nIndex statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return store


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build FAISS vector store for Formula Student rules"
    )
    parser.add_argument(
        "--chunks",
        required=True,
        help="Path to JSON file with validated chunks"
    )
    parser.add_argument(
        "--embeddings",
        required=True,
        help="Path to .npy file with embeddings"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Directory to save the index"
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
        "--embedding-dim",
        type=int,
        default=384,
        help="Embedding dimension (default: 384)"
    )
    
    args = parser.parse_args()
    
    store = build_vector_store(
        args.chunks,
        args.embeddings,
        args.output,
        args.season,
        args.competition,
        args.embedding_dim
    )
    
    print("\nVector store built successfully!")
