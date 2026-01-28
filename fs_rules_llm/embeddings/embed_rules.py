"""
Embedding Module for Formula Student Rules.

Generates vector embeddings for rule chunks using sentence transformers.
Never embeds user queries - only rule text.
"""

from typing import List, Dict, Any
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class RuleEmbedder:
    """
    Generates embeddings for rule chunks.
    
    Uses sentence transformers to create dense vector representations
    of rule text for semantic search.
    
    Key principles:
    - Only embed rule text, never user queries
    - Use consistent model across all seasons
    - Cache embeddings for efficiency
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedder.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for a list of chunks.
        
        Args:
            chunks: List of chunk dictionaries
            show_progress: Whether to show progress bar
            
        Returns:
            NumPy array of shape (num_chunks, embedding_dim)
        """
        # Extract text from chunks
        texts = [chunk['chunk_text'] for chunk in chunks]
        
        # Generate embeddings with progress bar
        if show_progress:
            print(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = self.model.encode(
                texts,
                show_progress_bar=True,
                convert_to_numpy=True,
                batch_size=32
            )
        else:
            embeddings = self.model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                batch_size=32
            )
        
        return embeddings
    
    def embed_single(self, text: str) -> np.ndarray:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            NumPy array of shape (embedding_dim,)
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def save_embeddings(
        self,
        embeddings: np.ndarray,
        output_path: str
    ):
        """
        Save embeddings to disk.
        
        Args:
            embeddings: NumPy array of embeddings
            output_path: Path to save embeddings (.npy file)
        """
        np.save(output_path, embeddings)
    
    @staticmethod
    def load_embeddings(embeddings_path: str) -> np.ndarray:
        """
        Load embeddings from disk.
        
        Args:
            embeddings_path: Path to embeddings file
            
        Returns:
            NumPy array of embeddings
        """
        return np.load(embeddings_path)


def embed_rules_from_file(
    chunks_file: str,
    output_embeddings: str,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> np.ndarray:
    """
    Convenience function to embed chunks from a JSON file.
    
    Args:
        chunks_file: Path to JSON file with chunks
        output_embeddings: Path to save embeddings (.npy)
        model_name: Sentence transformer model name
        
    Returns:
        NumPy array of embeddings
    """
    # Load chunks
    with open(chunks_file, 'r') as f:
        chunks = json.load(f)
    
    print(f"Loaded {len(chunks)} chunks from {chunks_file}")
    
    # Create embedder and generate embeddings
    embedder = RuleEmbedder(model_name)
    embeddings = embedder.embed_chunks(chunks)
    
    # Save embeddings
    embedder.save_embeddings(embeddings, output_embeddings)
    print(f"Saved embeddings to {output_embeddings}")
    print(f"Embedding shape: {embeddings.shape}")
    
    return embeddings


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate embeddings for Formula Student rule chunks"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON file with validated chunks"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save embeddings (.npy file)"
    )
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence transformer model name"
    )
    
    args = parser.parse_args()
    
    embeddings = embed_rules_from_file(
        args.input,
        args.output,
        args.model
    )
    
    print(f"\nEmbedding complete!")
    print(f"  Shape: {embeddings.shape}")
    print(f"  Dimension: {embeddings.shape[1]}")
