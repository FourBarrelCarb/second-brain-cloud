"""
Hybrid Retrieval Engine - Cloud-Optimized
Vector + keyword search with time-weighting and MMR
"""

import numpy as np
from datetime import datetime, timedelta
import logging
import streamlit as st
from execution.db_manager import get_db_manager
from execution.local_embeddings import get_embeddings

logger = logging.getLogger(__name__)


class Document:
    """Retrieved document representation."""
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata


def hybrid_retrieve(query: str, conversation_id: str, turn_number: int, top_k: int = None):
    """
    Main hybrid retrieval function.
    
    Combines vector + keyword search with time-weighting and MMR diversity.
    """
    if top_k is None:
        top_k = int(st.secrets.get("RETRIEVAL_TOP_K", "6"))
    
    try:
        # Generate query embedding
        embeddings = get_embeddings()
        query_embedding = embeddings.embed_query(query)
        
        # Get configuration
        session_limit = int(st.secrets.get("SESSION_HISTORY_LIMIT", "10"))
        vector_k = int(st.secrets.get("VECTOR_SEARCH_K", "15"))
        keyword_k = int(st.secrets.get("KEYWORD_SEARCH_K", "10"))
        
        session_cutoff = turn_number - session_limit
        
        # Vector search
        vector_results = _vector_search(
            query_embedding,
            conversation_id,
            session_cutoff,
            vector_k
        )
        
        # Keyword search
        keyword_results = _keyword_search(
            query,
            conversation_id,
            session_cutoff,
            keyword_k
        )
        
        # Merge and score
        merged = _merge_results(vector_results, keyword_results)
        
        # Time-weight
        weighted = _apply_time_weighting(merged)
        
        # MMR diversity
        if len(weighted) > top_k:
            mmr_diversity = float(st.secrets.get("MMR_DIVERSITY", "0.3"))
            final = _mmr_select(weighted, query_embedding, top_k, mmr_diversity)
        else:
            final = weighted[:top_k]
        
        logger.info(f"Retrieved {len(final)} conversations")
        return final
        
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        return []  # Graceful degradation


def _vector_search(query_embedding, exclude_conv_id, exclude_turn, limit):
    """Execute vector similarity search."""
    db = get_db_manager()
    embedding_str = '[' + ','.join(str(float(x)) for x in query_embedding) + ']'
    
    query = """
    SELECT 
        id,
        title,
        full_transcript AS content,
        1 - (embedding <=> %s::vector) AS similarity,
        metadata,
        created_at::text AS timestamp
    FROM conversations
    WHERE NOT (
        metadata->>'conversation_id' = %s 
        AND COALESCE((metadata->>'turn_number')::int, 0) > %s
    )
    ORDER BY embedding <=> %s::vector
    LIMIT %s
    """
    
    results = db.execute_query(
        query,
        (embedding_str, exclude_conv_id, exclude_turn, embedding_str, limit)
    )
    
    return results if results else []


def _keyword_search(query, exclude_conv_id, exclude_turn, limit):
    """Execute keyword full-text search."""
    db = get_db_manager()
    
    search_query = """
    SELECT 
        id,
        title,
        full_transcript AS content,
        ts_rank(search_vector, websearch_to_tsquery('english', %s)) AS rank,
        metadata,
        created_at::text AS timestamp
    FROM conversations
    WHERE search_vector @@ websearch_to_tsquery('english', %s)
    AND NOT (
        metadata->>'conversation_id' = %s 
        AND COALESCE((metadata->>'turn_number')::int, 0) > %s
    )
    ORDER BY rank DESC
    LIMIT %s
    """
    
    results = db.execute_query(
        search_query,
        (query, query, exclude_conv_id, exclude_turn, limit)
    )
    
    return results if results else []


def _merge_results(vector_results, keyword_results):
    """Merge and deduplicate results."""
    seen_ids = set()
    merged_docs = []
    
    # Process vector results
    for row in vector_results:
        if row['id'] not in seen_ids:
            doc = Document(
                page_content=row['content'],
                metadata={
                    **row['metadata'],
                    'id': str(row['id']),
                    'title': row.get('title', 'Untitled'),
                    'score': float(row['similarity']),
                    'source': 'vector',
                    'timestamp': row['timestamp']
                }
            )
            merged_docs.append(doc)
            seen_ids.add(row['id'])
    
    # Process keyword results
    for row in keyword_results:
        if row['id'] not in seen_ids:
            score = min(float(row['rank']) / 0.3, 1.0)
            doc = Document(
                page_content=row['content'],
                metadata={
                    **row['metadata'],
                    'id': str(row['id']),
                    'title': row.get('title', 'Untitled'),
                    'score': score,
                    'source': 'keyword',
                    'timestamp': row['timestamp']
                }
            )
            merged_docs.append(doc)
            seen_ids.add(row['id'])
    
    # Sort by score
    merged_docs.sort(key=lambda d: d.metadata['score'], reverse=True)
    return merged_docs


def _apply_time_weighting(documents):
    """Apply time-based boost to scores."""
    recency_days = int(st.secrets.get("RECENCY_BOOST_DAYS", "7"))
    
    for doc in documents:
        try:
            timestamp = datetime.fromisoformat(doc.metadata['timestamp'].replace('Z', '+00:00'))
            age = datetime.now(timestamp.tzinfo) - timestamp
            
            if age <= timedelta(days=recency_days):
                boost = 1.2
            elif age <= timedelta(days=30):
                boost = 1.1
            else:
                boost = 1.0
            
            doc.metadata['score'] *= boost
            doc.metadata['time_boost'] = boost
        except:
            pass
    
    # Re-sort by new scores
    documents.sort(key=lambda d: d.metadata['score'], reverse=True)
    return documents


def _mmr_select(documents, query_embedding, k, diversity):
    """Maximum Marginal Relevance selection for diversity."""
    if len(documents) <= k:
        return documents
    
    embeddings_model = get_embeddings()
    
    # Get embeddings for all documents
    doc_embeddings = []
    for doc in documents:
        emb = embeddings_model.embed_query(doc.page_content[:500])
        doc_embeddings.append(emb)
    
    doc_embeddings = np.array(doc_embeddings)
    query_embedding = np.array(query_embedding).reshape(1, -1)
    
    # Calculate similarities
    similarities = (query_embedding @ doc_embeddings.T)[0]
    
    selected_indices = []
    remaining_indices = list(range(len(documents)))
    
    # Select first (highest similarity)
    best_idx = int(np.argmax(similarities))
    selected_indices.append(best_idx)
    remaining_indices.remove(best_idx)
    
    # Iteratively select k-1 more
    while len(selected_indices) < k and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            relevance = similarities[idx]
            selected_embs = doc_embeddings[selected_indices]
            redundancy = (doc_embeddings[idx:idx+1] @ selected_embs.T).max()
            mmr = (1 - diversity) * relevance - diversity * redundancy
            mmr_scores.append((idx, mmr))
        
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    return [documents[i] for i in selected_indices]
