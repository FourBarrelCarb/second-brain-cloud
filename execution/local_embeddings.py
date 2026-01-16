"""
Local Embeddings - Cloud-Optimized
Uses Streamlit caching to load model once
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import streamlit as st

logger = logging.getLogger(__name__)


@st.cache_resource
def load_embeddings_model():
    """
    Load embeddings model (cached - loads once per deployment).
    
    Downloads ~90MB on first run, cached thereafter.
    """
    logger.info("Loading embedding model...")
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    logger.info("✓ Embedding model loaded")
    return model


class LocalEmbeddings:
    """Generate embeddings using cached local model."""
    
    def __init__(self):
        self.model = load_embeddings_model()
        self.dimension = 384
    
    def embed_query(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
        if not text or not text.strip():
            return np.zeros(self.dimension, dtype=np.float32)
        
        try:
            embedding = self.model.encode(
                text,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return np.zeros(self.dimension, dtype=np.float32)
    
    def embed_documents(self, texts: list, show_progress=False) -> list:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return [np.zeros(self.dimension, dtype=np.float32) for _ in texts]
        
        try:
            embeddings = self.model.encode(
                valid_texts,
                normalize_embeddings=True,
                show_progress_bar=show_progress,
                batch_size=32,
                convert_to_numpy=True
            )
            return [emb.astype(np.float32) for emb in embeddings]
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            return [np.zeros(self.dimension, dtype=np.float32) for _ in texts]


@st.cache_resource
def get_embeddings():
    """Cached embeddings instance."""
    return LocalEmbeddings()
