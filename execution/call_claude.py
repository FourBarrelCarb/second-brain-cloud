"""
Claude API Wrapper - Cloud-Native
Uses Streamlit secrets for API key
"""

from anthropic import Anthropic, APIError, RateLimitError
import time
import logging
import streamlit as st

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Anthropic Claude API."""
    
    def __init__(self):
        api_key = st.secrets["ANTHROPIC_API_KEY"]
        self.client = Anthropic(api_key=api_key)
        self.model = st.secrets.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.temperature = float(st.secrets.get("TEMPERATURE", "0.7"))
        self.max_tokens = int(st.secrets.get("MAX_TOKENS", "4096"))
    
    def chat_stream(self, messages: list, system_prompt: str = None):
        """
        Stream chat completion from Claude.
        
        Args:
            messages: List of {role, content} dicts
            system_prompt: Optional system prompt
            
        Yields:
            Text chunks as they arrive
        """
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt or self._default_system_prompt(),
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except RateLimitError:
            logger.warning("Rate limit hit, waiting...")
            time.sleep(60)
            # Retry once
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt or self._default_system_prompt(),
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except APIError as e:
            logger.error(f"API error: {e}")
            raise
    
    def _default_system_prompt(self) -> str:
        """Default system prompt."""
        return """You are a helpful AI assistant with perfect memory of all past conversations.

Use retrieved memories naturally when relevant. Don't mention the retrieval system.
Be helpful, concise, and build on our conversation history."""


@st.cache_resource
def get_claude_client():
    """Cached Claude client instance."""
    return ClaudeClient()
