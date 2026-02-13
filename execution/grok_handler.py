"""
Grok Handler - XAI API Integration
Handles real-time market data queries via Grok
"""

import streamlit as st
import openai
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class GrokClient:
    """Wrapper for XAI Grok API with smart query routing."""
    
    def __init__(self):
        """Initialize XAI client."""
        try:
            self.client = openai.OpenAI(
                api_key=st.secrets["XAI_API_KEY"],
                base_url="https://api.x.ai/v1"
            )
            self.model = "grok-3"
            logger.info("✓ Grok client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Grok client: {e}")
            raise
    
    def query_grok(self, prompt: str, max_tokens: int = 500) -> Optional[Dict[str, Any]]:
        """
        Send query to Grok and get real-time response.
        
        Args:
            prompt: User query
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with response text and token usage, or None on error
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Grok, providing real-time market data and current information. Be concise and factual. Include current prices, dates, and sources when relevant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.3  # Lower for factual responses
            )
            
            result = {
                "text": response.choices[0].message.content,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            logger.info(f"✓ Grok query successful: {result['total_tokens']} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Grok API error: {e}", exc_info=True)
            return {"error": str(e)}
    
    def should_use_grok(self, query: str) -> bool:
        """
        Determine if query should be routed to Grok based on keywords.

        Args:
            query: User's question

        Returns:
            True if Grok should handle it, False for Claude only
        """
        query_lower = query.lower().strip()

        # Explicit Grok routing - user forces it
        explicit_triggers = [
            "grok", "ask grok", "use grok", "real-time", "realtime",
            "real time", "live data", "look up", "search for"
        ]

        # Real-time/current data triggers
        time_triggers = [
            "current", "currently", "latest", "today", "right now",
            "now", "recent", "recently", "this week", "this month",
            "breaking", "up to date", "up-to-date", "as of"
        ]

        # Financial data triggers
        financial_triggers = [
            "price", "stock price", "stock", "market cap", "trading at",
            "earnings", "dividend", "p/e", "pe ratio", "share price",
            "volume", "market", "ticker", "crypto", "bitcoin", "btc",
            "eth", "ethereum", "forex", "exchange rate", "s&p",
            "nasdaq", "dow jones", "index"
        ]

        # News triggers
        news_triggers = [
            "news", "announcement", "announced", "reported",
            "earnings report", "press release", "headline",
            "what happened", "what's happening", "update on"
        ]

        # Weather / sports / live events
        live_triggers = [
            "weather", "forecast", "score", "game", "match",
            "election", "results"
        ]

        all_triggers = (
            explicit_triggers + time_triggers + financial_triggers
            + news_triggers + live_triggers
        )

        for trigger in all_triggers:
            if trigger in query_lower:
                logger.info(f"Grok trigger detected: '{trigger}' in query: {query_lower[:80]}")
                return True

        logger.debug(f"No Grok trigger matched for: {query_lower[:80]}")
        return False
    
    def estimate_cost(self, tokens: int) -> float:
        """
        Estimate cost for Grok API usage.
        
        Args:
            tokens: Total tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Grok pricing: ~$5 per 1M tokens (estimate)
        cost = (tokens / 1_000_000) * 5.00
        return cost


@st.cache_resource
def get_grok_client():
    """Get or create the global Grok client instance."""
    return GrokClient()


def hybrid_query(user_query: str, athena_context: str = "") -> Dict[str, Any]:
    """
    Execute hybrid query using both Grok and Claude.

    Args:
        user_query: User's question
        athena_context: Relevant context from Athena's memory

    Returns:
        Dict with grok_data, should_synthesize flag, and metadata
    """
    try:
        grok = get_grok_client()
    except Exception as e:
        logger.error(f"Grok client unavailable: {e}")
        return {
            "use_grok": False,
            "grok_data": None,
            "cost": 0.0,
            "error": f"Grok client init failed: {e}"
        }

    # Check if we should use Grok
    should_use = grok.should_use_grok(user_query)
    logger.info(f"should_use_grok('{user_query[:60]}') = {should_use}")

    if not should_use:
        return {
            "use_grok": False,
            "grok_data": None,
            "cost": 0.0
        }

    # Query Grok for real-time data
    logger.info("Routing query to Grok for real-time data...")
    grok_response = grok.query_grok(user_query)

    if not grok_response or "error" in grok_response:
        api_error = grok_response.get("error", "Unknown") if isinstance(grok_response, dict) else "No response"
        logger.warning(f"Grok query FAILED — {api_error}")
        return {
            "use_grok": False,
            "grok_data": None,
            "cost": 0.0,
            "error": f"Grok API: {api_error}"
        }

    # Calculate cost
    cost = grok.estimate_cost(grok_response["total_tokens"])

    logger.info(f"✓ Grok returned {grok_response['total_tokens']} tokens, cost ${cost:.4f}")
    return {
        "use_grok": True,
        "grok_data": grok_response["text"],
        "tokens": grok_response["total_tokens"],
        "cost": cost
    }
