import requests
import logging
import re
import streamlit as st

logger = logging.getLogger("grok")

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

XAI_API_KEY = st.secrets.get("XAI_API_KEY")

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-3"

# Rough estimate – adjust if xAI publishes exact pricing
COST_PER_1K_TOKENS = 0.01


# -------------------------------------------------------------------
# ROUTING LOGIC
# -------------------------------------------------------------------

def should_use_grok(prompt: str) -> bool:
    """
    Decide if a prompt requires real-time data.
    This is intentionally aggressive for finance & news.
    """
    p = prompt.lower()

    # Obvious real-time intent
    if any(k in p for k in [
        "latest", "today", "current", "now",
        "breaking", "right now"
    ]):
        return True

    # Finance / stock price intent
    if any(k in p for k in [
        "stock", "share", "price", "trading",
        "market cap", "volume", "earnings"
    ]):
        return True

    # Ticker symbol detection (AMD, NVDA, AAPL, etc.)
    if re.search(r"\b[A-Z]{2,5}\b", prompt):
        return True

    return False


# -------------------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------------------

def hybrid_query(prompt: str) -> dict:
    """
    If needed, call Grok for real-time data.
    Returns a dict consumed by the main app.
    """

    use_grok = should_use_grok(prompt)

    if not use_grok:
        return {
            "use_grok": False,
            "grok_data": None,
            "cost": 0.0
        }

    if not XAI_API_KEY:
        raise RuntimeError("XAI_API_KEY missing in Streamlit secrets")

    logger.info("✅ Grok triggered for real-time query")

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # IMPORTANT: we explicitly instruct Grok to return numbers when relevant
    payload = {
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a real-time market data assistant. "
                    "If asked for prices, return the latest numeric value "
                    "with currency and timestamp if available."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1
    }

    resp = requests.post(
        GROK_API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Grok API error {resp.status_code}: {resp.text}"
        )

    data = resp.json()

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not content:
        logger.warning("⚠️ Grok returned empty content")

    usage = data.get("usage", {})
    tokens = usage.get("total_tokens", 0)
    cost = (tokens / 1000) * COST_PER_1K_TOKENS

    logger.info(f"✅ Grok success | tokens={tokens} | cost=${cost:.4f}")

    return {
        "use_grok": True,
        "grok_data": content,
        "cost": cost
    }
