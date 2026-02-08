import requests
import logging
import streamlit as st

logger = logging.getLogger("grok")

XAI_API_KEY = st.secrets.get("XAI_API_KEY")

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-beta"
COST_PER_1K_TOKENS = 0.01


def hybrid_query(prompt: str) -> dict:
    realtime_keywords = [
        "latest", "today", "current", "news",
        "price", "market", "now", "breaking"
    ]

    use_grok = any(k in prompt.lower() for k in realtime_keywords)

    if not use_grok:
        return {
            "use_grok": False,
            "grok_data": None,
            "cost": 0.0
        }

    if not XAI_API_KEY:
        raise RuntimeError("XAI_API_KEY missing in Streamlit secrets")

    logger.info("✅ Grok triggered")

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": "You provide real-time information."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
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

    content = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", 0)
    cost = (tokens / 1000) * COST_PER_1K_TOKENS

    logger.info(f"✅ Grok success | tokens={tokens} | cost=${cost:.4f}")

    return {
        "use_grok": True,
        "grok_data": content,
        "cost": cost
    }
