"""
Conversation Saver - Cloud-Native
Stores complete chat sessions with embeddings
"""

import json
from datetime import datetime
from uuid import uuid4
import logging
from execution.db_manager import get_db_manager
from execution.local_embeddings import get_embeddings

logger = logging.getLogger(__name__)


def save_conversation(messages: list, conversation_id: str = None, metadata: dict = None):
    """
    Save complete conversation to database.
    
    Args:
        messages: List of {role, content, timestamp} dicts
        conversation_id: Optional UUID
        metadata: Optional additional metadata
        
    Returns:
        UUID of saved conversation or None on error
    """
    if not messages:
        logger.warning("No messages to save")
        return None
    
    try:
        # Format transcript
        transcript = _format_transcript(messages)
        
        # Generate title
        title = _generate_title(messages)
        
        # Generate embedding
        embeddings = get_embeddings()
        embedding = embeddings.embed_query(transcript)
        embedding_str = '[' + ','.join(str(float(x)) for x in embedding) + ']'
        
        # Extract topics
        topics = _extract_topics(transcript)
        
        # Build metadata
        total_tokens = sum(msg.get('tokens', 0) for msg in messages)
        conv_metadata = {
            "conversation_id": conversation_id or str(uuid4()),
            "start_time": messages[0].get('timestamp', datetime.now().isoformat()),
            "end_time": messages[-1].get('timestamp', datetime.now().isoformat()),
            "turn_count": len(messages),
            "total_tokens": total_tokens,
            "topics": topics,
            "participants": ["user", "claude"]
        }
        
        if metadata:
            conv_metadata.update(metadata)
        
        # Insert to database
        db = get_db_manager()
        query = """
        INSERT INTO conversations 
        (title, full_transcript, embedding, metadata)
        VALUES (%s, %s, %s::vector, %s)
        RETURNING id
        """
        
        result_id = db.execute_insert(
            query,
            (title, transcript, embedding_str, json.dumps(conv_metadata))
        )
        
        if result_id:
            logger.info(f"✓ Conversation saved: {title[:50]}...")
            return str(result_id)
        else:
            logger.error("Failed to save conversation")
            return None
            
    except Exception as e:
        logger.error(f"Error saving conversation: {e}", exc_info=True)
        return None


def _format_transcript(messages: list) -> str:
    """Format messages into readable transcript."""
    lines = []
    for msg in messages:
        role = msg.get('role', 'unknown').capitalize()
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                lines.append(f"[{time_str}] {role}: {content}")
            except:
                lines.append(f"{role}: {content}")
        else:
            lines.append(f"{role}: {content}")
    
    return '\n\n'.join(lines)


def _generate_title(messages: list, max_length: int = 100) -> str:
    """Generate title from first user message."""
    for msg in messages:
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            if content:
                if len(content) > max_length:
                    return content[:max_length-3] + '...'
                return content
    
    return f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"


def _extract_topics(transcript: str, max_topics: int = 5) -> list:
    """Extract topics from conversation (simple keyword extraction)."""
    investment_keywords = {
        'dividend', 'dividends', 'stock', 'stocks', 'portfolio', 'allocation',
        'risk', 'investing', 'investment', 'bonds', 'equity', 'value',
        'growth', 'income', 'retirement', 'diversification', 'market',
        'analysis', 'valuation', 'yield', 'returns', 'strategy'
    }
    
    words = transcript.lower().split()
    topic_counts = {}
    
    for word in words:
        clean_word = ''.join(c for c in word if c.isalnum())
        if clean_word in investment_keywords:
            topic_counts[clean_word] = topic_counts.get(clean_word, 0) + 1
    
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    return [topic for topic, count in sorted_topics[:max_topics]]
