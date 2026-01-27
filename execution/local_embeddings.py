"""
Local Embeddings - sentence-transformers
Uses BAAI/bge-small-en-v1.5 (384-dim)
"""

from sentence_transformers import SentenceTransformer
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class EmbeddingsWrapper:
    def __init__(self, model: SentenceTransformer):
        self.model = model

    def embed_query(self, text: str):
        return self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()

    def embed_documents(self, texts: list[str]):
        return [
            self.model.encode(
                t,
                convert_to_numpy=True,
                normalize_embeddings=True
            ).tolist()
            for t in texts
        ]


@st.cache_resource
def get_embeddings():
    """
    Load and cache the sentence transformer model.
    """
    logger.info("Loading embeddings model...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    logger.info("Embeddings model loaded")
    return EmbeddingsWrapper(model)
