# =========================
# Phase 2B + Voice Output Toggle (FIXED)
# =========================

import streamlit as st
from datetime import datetime
from uuid import uuid4
import logging

from execution.retrieve_chats import hybrid_retrieve
from execution.save_conversation import save_conversation
from execution.call_claude import get_claude_client
from execution.voice_handler import get_voice_handler, create_tts_audio
from execution.audio_recorder import audio_recorder_component
from execution.grok_handler import hybrid_query
from execution.insights_engine import get_insights_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Second Brain - Athena",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
def init_session_state():
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid4())

    if "turn_number" not in st.session_state:
        st.session_state.turn_number = 0

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0

    if "total_cost" not in st.session_state:
        st.session_state.total_cost = 0.0

    # Voice input (existing)
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False

    # 🔊 Voice output (RESTORED)
    if "voice_output_enabled" not in st.session_state:
        st.session_state.voice_output_enabled = False

    if "voice_cost" not in st.session_state:
        st.session_state.voice_cost = 0.0

    if "grok_cost" not in st.session_state:
        st.session_state.grok_cost = 0.0

    if "digest_viewed" not in st.session_state:
        st.session_state.digest_viewed = False

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def count_tokens_approx(text: str) -> int:
    return int(len(text.split()) * 1.3)

def estimate_cost(inp: int, out: int) -> float:
    return inp * (3 / 1_000_000) + out * (15 / 1_000_000)

def process_voice_input():
    st.subheader("🎤 Voice Input")
    audio = audio_recorder_component(key="voice_recorder")
    if not audio:
        return ""

    vh = get_voice_handler()
    text = vh.transcribe_audio(audio, "wav")
    st.session_state.voice_cost += vh.estimate_transcription_cost(audio)
    return text or ""

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    init_session_state()

    st.title("🧠 Athena - Your Second Brain")

    with st.sidebar:
        st.subheader("🎤 Voice Input")
        st.session_state.voice_mode = st.toggle(
            "Enable Voice Input",
            value=st.session_state.voice_mode
        )

        st.subheader("🔊 Voice Output")
        st.session_state.voice_output_enabled = st.toggle(
            "Enable Voice Output",
            value=st.session_state.voice_output_enabled
        )

        if st.session_state.voice_mode:
            st.success("✓ Voice input active")
        if st.session_state.voice_output_enabled:
            st.success("✓ Voice output active")
        if not st.session_state.voice_mode and not st.session_state.voice_output_enabled:
            st.info("Voice disabled")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = (
        process_voice_input()
        if st.session_state.voice_mode
        else st.chat_input("Ask me anything...")
    )

    if not prompt:
        return

    st.session_state.turn_number += 1
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response = ""
        client = get_claude_client()

        for chunk in client.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are Athena."
        ):
            response += chunk
            st.markdown(response + "▌")

        st.markdown(response)

        # 🔊 VOICE OUTPUT (FIXED)
        if st.session_state.voice_output_enabled:
            st.components.v1.html(
                create_tts_audio(response),
                height=0
            )

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )

# --------------------------------------------------
if __name__ == "__main__":
    main()
