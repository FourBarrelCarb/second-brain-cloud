"""
Local Embeddings - Free sentence-transformers
Uses BAAI/bge-small-en-v1.5 (384-dim)
"""

from sentence_transformers import SentenceTransformer
import streamlit as st
import logging

logger = logging.getLogger(__name__)


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
    return model
