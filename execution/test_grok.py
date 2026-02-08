import requests
import streamlit as st

XAI_API_KEY = st.secrets["XAI_API_KEY"]

resp = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "grok-beta",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ]
    },
    timeout=30
)

print(resp.status_code)
print(resp.text)
