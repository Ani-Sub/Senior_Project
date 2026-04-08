"""
Embedding utilities using Ollama.

Provides vector embeddings for claims to enable:
- Semantic similarity matching
- Narrative centroid calculation
- Incremental claim assignment
"""

import logging
import requests
from typing import Optional

from config import EMBEDDING_MODEL, EMBEDDING_URL, EMBEDDING_DIMENSIONS

log = logging.getLogger(__name__)


def get_embedding(text: str) -> Optional[list[float]]:
    """
    Get embedding vector for text using Ollama.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats (embedding vector) or None if failed
    """
    if not text or not text.strip():
        return None
    
    try:
        response = requests.post(
            EMBEDDING_URL,
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text.strip()
            },
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        embedding = data.get("embedding")
        
        if embedding and len(embedding) == EMBEDDING_DIMENSIONS:
            return embedding
        else:
            log.warning(f"Unexpected embedding dimensions: {len(embedding) if embedding else 0}")
            return None
            
    except requests.exceptions.ConnectionError:
        log.error(f"Cannot connect to Ollama. Is it running? (URL: {EMBEDDING_URL})")
        return None
    except Exception as e:
        log.warning(f"Embedding failed: {e}")
        return None


def get_embeddings_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """
    Get embeddings for multiple texts.
    
    Note: Ollama doesn't support batch embeddings natively,
    so this calls the API sequentially.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors (or None for failed items)
    """
    embeddings = []
    for text in texts:
        embeddings.append(get_embedding(text))
    return embeddings


def calculate_centroid(embeddings: list[list[float]]) -> Optional[list[float]]:
    """
    Calculate centroid (average) of multiple embedding vectors.
    
    Args:
        embeddings: List of embedding vectors (all same dimensions)
        
    Returns:
        Centroid vector or None if no valid embeddings
    """
    # Filter out None values
    valid_embeddings = [e for e in embeddings if e is not None]
    
    if not valid_embeddings:
        return None
    
    if len(valid_embeddings) == 1:
        return valid_embeddings[0]
    
    # Calculate average across all dimensions
    num_embeddings = len(valid_embeddings)
    num_dimensions = len(valid_embeddings[0])
    
    centroid = []
    for dim in range(num_dimensions):
        dim_sum = sum(emb[dim] for emb in valid_embeddings)
        centroid.append(dim_sum / num_embeddings)
    
    return centroid


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Returns:
        Similarity score between -1 and 1 (1 = identical)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def find_closest_narrative(
    claim_embedding: list[float],
    narrative_centroids: dict[str, list[float]],
    threshold: float = 0.5
) -> Optional[str]:
    """
    Find the closest narrative for a claim based on embedding similarity.
    
    Args:
        claim_embedding: Embedding vector of the claim
        narrative_centroids: Dict mapping narrative_id to centroid vector
        threshold: Minimum similarity to match (0-1)
        
    Returns:
        narrative_id of closest match, or None if below threshold
    """
    if not claim_embedding or not narrative_centroids:
        return None
    
    best_match = None
    best_similarity = threshold
    
    for narrative_id, centroid in narrative_centroids.items():
        similarity = cosine_similarity(claim_embedding, centroid)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = narrative_id
    
    return best_match


def check_embedding_service() -> bool:
    """
    Check if the Ollama embedding service is available.
    
    Returns:
        True if service is ready, False otherwise
    """
    try:
        # Try a simple embedding request
        response = requests.post(
            EMBEDDING_URL,
            json={
                "model": EMBEDDING_MODEL,
                "prompt": "test"
            },
            timeout=10
        )
        return response.status_code == 200
    except:
        return False
