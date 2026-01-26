"""
Claude API Client
Streaming wrapper for Anthropic API
"""

import anthropic
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Claude API with streaming support."""
    
    def __init__(self):
        """Initialize Anthropic client."""
        self.client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        self.model = st.secrets.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.temperature = float(st.secrets.get("TEMPERATURE", "0.7"))
        self.max_tokens = int(st.secrets.get("MAX_TOKENS", "4096"))
    
    def chat_stream(self, messages: list, system_prompt: str = None):
        """
        Stream chat completion from Claude.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            
        Yields:
            Text chunks from Claude's response
        """
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt if system_prompt else "",
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"API error: {e}")
            raise


@st.cache_resource
def get_claude_client():
    """Get or create the global Claude client instance."""
    return ClaudeClient()
