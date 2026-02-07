# Athena – Phase 2A upgraded with Phase 2B features (stable voice)
# ---------------------------------------------------------------
# This version STARTS from your Phase 2A code and ADDS:
# - Grok real-time routing
# - Weekly insights + contradiction alerts
# - Unified voice mode (input + output)
# - Grok + voice cost tracking
# - Safe TTS path (no missing functions)
#
# Voice input + output WILL WORK assuming execution.voice_handler is unchanged

import streamlit as st
from datetime import datetime
from uuid import uuid4
import logging

# ============================
# EXECUTION MODULES
# ============================
from execution.retrieve_chats import hybrid_retrieve
from execution.save_conversation import save_conversation
from execution.call_claude import get_claude_client
from execution.voice_handler import get_voice_handler, create_tts_audio
from execution.audio_recorder import audio_recorder_component
from execution.grok_handler import hybrid_query
from execution.insights_engine import get_insights_engine

# ============================
# LOGGING
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================
# PAGE CONFIG
# ============================
st.set_page_config(
    page_title="Athena – Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================
# SESSION STATE
# ============================

def init_state():
    defaults = {
        "conversation_id": str(uuid4()),
        "turn_number": 0,
        "messages": [],
        "total_tokens": 0,
        "claude_cost": 0.0,
        "voice_cost": 0.0,
        "grok_cost": 0.0,
        "voice_mode": False,
        "digest_viewed": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ============================
# UTILITIES
# ============================

def count_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def estimate_claude_cost(inp: int, out: int) -> float:
    return (inp * 3 + out * 15) / 1_000_000


def format_memories(docs):
    if not docs:
        return "No relevant memories found."

    out = "=== RELEVANT MEMORY ===\n"
    for i, d in enumerate(docs, 1):
        meta = d.metadata
        out += f"[{i}] {meta.get('title','')} ({meta.get('score',0):.2f})\n"
        out += d.page_content + "\n\n"
    return out

# ============================
# VOICE INPUT
# ============================

def handle_voice_input():
    audio = audio_recorder_component(key="voice")
    if not audio:
        return ""

    vh = get_voice_handler()
    text = vh.transcribe_audio(audio, "wav")
    st.session_state.voice_cost += vh.estimate_transcription_cost(audio)
    return text or ""

# ============================
# WEEKLY INSIGHTS
# ============================

def handle_insights():
    engine = get_insights_engine()

    if engine.should_generate_weekly_digest():
        engine.generate_weekly_digest()
        st.session_state.digest_viewed = False

    if not st.session_state.digest_viewed:
        digest = engine.get_latest_digest()
        if digest:
            with st.expander("📊 Weekly Digest", expanded=True):
                st.markdown(digest["digest_content"])
                if st.button("Mark as read"):
                    st.session_state.digest_viewed = True
                    st.rerun()

# ============================
# MAIN APP
# ============================

def main():
    init_state()
    handle_insights()

    st.title("🧠 Athena")
    st.caption("Memory-driven • Voice-enabled • Real-time aware")

    # --------------------
    # SIDEBAR
    # --------------------
    with st.sidebar:
        st.subheader("Session")
        st.metric("Turns", st.session_state.turn_number)
        st.metric("Tokens", st.session_state.total_tokens)
        st.metric("Claude", f"${st.session_state.claude_cost:.4f}")
        st.metric("Voice", f"${st.session_state.voice_cost:.4f}")
        st.metric("Grok", f"${st.session_state.grok_cost:.4f}")

        st.divider()
        st.session_state.voice_mode = st.toggle("🎤 Voice Mode", st.session_state.voice_mode)

        st.divider()
        if st.button("🔄 New Chat"):
            if st.session_state.messages:
                save_conversation(st.session_state.messages, st.session_state.conversation_id)
            st.session_state.clear()
            st.rerun()

    # --------------------
    # HISTORY
    # --------------------
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # --------------------
    # INPUT
    # --------------------
    if st.session_state.voice_mode:
        prompt = handle_voice_input()
    else:
        prompt = st.chat_input("Ask Athena…")

    if not prompt:
        return

    st.session_state.turn_number += 1
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        status = st.empty()
        output = st.empty()

        # ---- GROK ROUTING ----
        grok = hybrid_query(prompt)
        grok_data = None
        if grok["use_grok"]:
            status.info("Fetching real-time data…")
            grok_data = grok["grok_data"]
            st.session_state.grok_cost += grok["cost"]

        # ---- MEMORY ----
        status.info("Searching memory…")
        docs = hybrid_retrieve(prompt, st.session_state.conversation_id, st.session_state.turn_number)
        memories = format_memories(docs)

        system = f"You are Athena. Use memory naturally.\n\n{memories}"
        if grok_data:
            system += f"\n\n=== REAL-TIME DATA ===\n{grok_data}"

        # ---- CLAUDE STREAM ----
        client = get_claude_client()
        response = ""

        for chunk in client.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system
        ):
            response += chunk
            output.markdown(response + "▌")

        output.markdown(response)
        status.empty()

        # ---- VOICE OUTPUT ----
        if st.session_state.voice_mode:
            st.components.v1.html(create_tts_audio(response), height=0)

        # ---- COST ----
        inp = count_tokens(prompt + memories)
        if grok_data:
            inp += count_tokens(grok_data)
        out = count_tokens(response)

        st.session_state.total_tokens += inp + out
        st.session_state.claude_cost += estimate_claude_cost(inp, out)

        st.session_state.messages.append({"role": "assistant", "content": response})

        # ---- CONTRADICTIONS ----
        try:
            get_insights_engine().check_for_contradictions(prompt, st.session_state.conversation_id)
        except Exception:
            pass


# ============================
# ENTRY
# ============================
if __name__ == "__main__":
    main()
