"""
RAIYA Embed Tool — BGE-large-en-v1.5 embedding with chunk_hash Redis caching.
"""

import json
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.db.redis_client import cache_get, cache_set, CacheKeys
from app.core.logging_config import get_logger

logger = get_logger("EmbedTool")

# Lazy-loaded model instance
_model = None


def _get_model():
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_PRIMARY}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_PRIMARY)
        logger.info("Embedding model loaded")
    return _model


def embed_texts(texts: List[str], normalize: bool = True) -> List[List[float]]:
    """
    Embed a list of texts using BGE-large-en-v1.5.
    
    Args:
        texts: List of text strings to embed
        normalize: Whether to L2-normalize embeddings
    
    Returns:
        List of embedding vectors (768-dim)
    """
    model = _get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=normalize,
        show_progress_bar=False,
        batch_size=32,
    )
    return [emb.tolist() for emb in embeddings]


async def embed_chunks_with_cache(
    chunks: List[Dict[str, Any]],
) -> List[List[float]]:
    """
    Embed chunks with Redis caching per chunk_hash.
    
    Args:
        chunks: List of chunk dicts with 'text' and 'chunk_hash' keys
    
    Returns:
        List of embedding vectors matching chunk order
    """
    embeddings = []
    texts_to_embed = []
    indices_to_embed = []

    # Check cache for each chunk
    for i, chunk in enumerate(chunks):
        chunk_hash = chunk.get("chunk_hash", "")
        if chunk_hash:
            cache_key = CacheKeys.embedding(chunk_hash)
            cached = await cache_get(cache_key)
            if cached:
                embeddings.append(json.loads(cached))
                continue

        texts_to_embed.append(chunk.get("text", ""))
        indices_to_embed.append(i)
        embeddings.append(None)  # Placeholder

    # Embed uncached texts
    if texts_to_embed:
        logger.info(f"Embedding {len(texts_to_embed)} uncached chunks")
        new_embeddings = embed_texts(texts_to_embed)

        for j, idx in enumerate(indices_to_embed):
            embeddings[idx] = new_embeddings[j]
            # Cache the embedding
            chunk_hash = chunks[idx].get("chunk_hash", "")
            if chunk_hash:
                cache_key = CacheKeys.embedding(chunk_hash)
                await cache_set(cache_key, new_embeddings[j], ttl_key="embedding")
    else:
        logger.info(f"All {len(chunks)} chunks served from cache")

    return embeddings


def embed_single(text: str, normalize: bool = True) -> List[float]:
    """Embed a single text string."""
    return embed_texts([text], normalize=normalize)[0]
