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
    """Wrapper for XAI Grok API with enforced real-time routing."""

    def __init__(self):
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

    # ------------------------------------------------------------------
    # STRICT REAL-TIME DETECTION
    # ------------------------------------------------------------------

    def requires_real_time(self, query: str) -> bool:
        """
        Determine if the query requires live data.
        This is STRICT. If True, Claude must not answer.
        """

        query_lower = query.lower()

        financial_keywords = [
            "current price",
            "stock price",
            "price of",
            "trading at",
            "market cap",
            "earnings today",
            "dividend yield",
            "ticker",
            "latest price",
            "right now",
            "today's price"
        ]

        for keyword in financial_keywords:
            if keyword in query_lower:
                logger.info(f"Real-time financial query detected: '{keyword}'")
                return True

        return False

    # ------------------------------------------------------------------
    # GROK QUERY
    # ------------------------------------------------------------------

    def query_grok(self, prompt: str, max_tokens: int = 500) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Grok, providing real-time market data. "
                            "Be concise and factual. Include dates when giving prices."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.2
            )

            result = {
                "text": response.choices[0].message.content,
                "total_tokens": response.usage.total_tokens
            }

            logger.info(f"✓ Grok query successful: {result['total_tokens']} tokens")
            return result

        except Exception as e:
            logger.error(f"Grok API error: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # COST ESTIMATION
    # ------------------------------------------------------------------

    def estimate_cost(self, tokens: int) -> float:
        return (tokens / 1_000_000) * 5.00


# ----------------------------------------------------------------------
# GLOBAL CLIENT
# ----------------------------------------------------------------------

@st.cache_resource
def get_grok_client():
    return GrokClient()


# ----------------------------------------------------------------------
# HYBRID QUERY (ENFORCED VERSION)
# ----------------------------------------------------------------------

def hybrid_query(user_query: str) -> Dict[str, Any]:
    """
    Enforced routing logic:
    - If query requires real-time → MUST use Grok
    - If Grok fails → BLOCK response
    """

    grok = get_grok_client()

    requires_live = grok.requires_real_time(user_query)

    # --------------------------------------------------------------
    # Case 1: Does NOT require live data
    # --------------------------------------------------------------
    if not requires_live:
        return {
            "requires_live": False,
            "use_grok": False,
            "grok_data": None,
            "cost": 0.0
        }

    # --------------------------------------------------------------
    # Case 2: Requires live data → MUST use Grok
    # --------------------------------------------------------------
    logger.info("Real-time query detected. Routing to Grok...")

    grok_response = grok.query_grok(user_query)

    if not grok_response:
        logger.error("Grok failed — blocking real-time response.")

        return {
            "requires_live": True,
            "use_grok": True,
            "grok_data": None,
            "error": "Real-time data unavailable",
            "cost": 0.0
        }

    cost = grok.estimate_cost(grok_response["total_tokens"])

    return {
        "requires_live": True,
        "use_grok": True,
        "grok_data": grok_response["text"],
        "cost": cost
    }
