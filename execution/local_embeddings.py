"""
Local Embeddings - Free sentence-transformers
Uses BAAI/bge-small-en-v1.5 (384-dim)
"""

from sentence_transformers import SentenceTransformer
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class EmbeddingsWrapper:
    """Wrapper to make SentenceTransformer compatible with our code."""
    
    def __init__(self, model):
        self.model = model
    
    def embed_query(self, text: str):
        """Embed a single query text."""
        return self.model.encode(text, convert_to_numpy=True).tolist()
    
    def embed_documents(self, texts: list):
        """Embed multiple documents."""
        return [self.model.encode(text, convert_to_numpy=True).tolist() for text in texts]


@st.cache_resource
def get_embeddings():
    """
    Load and cache the sentence transformer model.
    
    Model: BAAI/bge-small-en-v1.5
    - 384 dimensions
    - Fast inference
    - Good quality
    - Free (no API costs)
    """
    logger.info("Loading embeddings model...")
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    logger.info("✓ Embeddings model loaded")
    return EmbeddingsWrapper(model)
