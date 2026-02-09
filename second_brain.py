"""
Second Brain "Athena" - Phase 2B+C Enhanced (FIXED)
Cloud-Native Application with Grok Integration & Proactive Insights

✔ Restored Voice Output Toggle (from Phase 2 reference)
✔ Decoupled Voice Input and Voice Output
"""

import streamlit as st
from datetime import datetime
from uuid import uuid4
import logging

# Import execution modules
from execution.retrieve_chats import hybrid_retrieve
from execution.save_conversation import save_conversation
from execution.call_claude import get_claude_client
from execution.voice_handler import get_voice_handler, create_tts_audio
from execution.audio_recorder import audio_recorder_component
from execution.grok_handler import hybrid_query
from execution.insights_engine import get_insights_engine

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Second Brain - Athena",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
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

    # ---- VOICE STATES (Phase 2 compatible) ----
    if "voice_mode" not in st.session_state:              # input
        st.session_state.voice_mode = False

    if "voice_output_enabled" not in st.session_state:    # output
        st.session_state.voice_output_enabled = False

    if "selected_voice" not in st.session_state:
        st.session_state.selected_voice = "onyx"

    if "tts_model" not in st.session_state:
        st.session_state.tts_model = "tts-1"

    if "voice_cost" not in st.session_state:
        st.session_state.voice_cost = 0.0

    # ---- GROK / INSIGHTS ----
    if "grok_cost" not in st.session_state:
        st.session_state.grok_cost = 0.0

    if "digest_viewed" not in st.session_state:
        st.session_state.digest_viewed = False

    # Warm Grok (avoid first-call delay)
    @st.cache_resource
    def warm_grok():
        try:
            hybrid_query("ping")
        except Exception:
            pass

    warm_grok()

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def count_tokens_approx(text: str) -> int:
    return int(len(text.split()) * 1.3)

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * (3.00 / 1_000_000)
        + output_tokens * (15.00 / 1_000_000)
    )

def format_retrieved_memories(documents):
    if not documents:
        return "No relevant past conversations found."

    formatted = "=== RELEVANT PAST CONVERSATIONS ===\n\n"
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata
        formatted += (
            f"[Memory {i}] ({meta.get('timestamp','')[:10]}, "
            f"relevance: {meta.get('score',0):.2f})\n"
            f"Title: {meta.get('title','Untitled')}\n"
            f"{doc.page_content}\n\n"
        )
    return formatted

def process_voice_input():
    st.subheader("🎤 Voice Input")
    audio = audio_recorder_component(key="voice_recorder")

    if not audio:
        return ""

    try:
        with st.spinner("Transcribing audio..."):
            vh = get_voice_handler()
            text = vh.transcribe_audio(audio, "wav")
            cost = vh.estimate_transcription_cost(audio)
            st.session_state.voice_cost += cost

            if text:
                st.success(f"✓ Transcribed: {text}")
                st.caption(f"Voice cost: ${cost:.4f}")
                return text

    except Exception as e:
        logger.error(e, exc_info=True)
        st.error(f"Voice input failed: {e}")

    return ""

# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
def main():
    init_session_state()

    st.title("🧠 Athena - Your Second Brain")
    st.caption("Perfect memory • Voice enabled • Real-time data • Weekly insights")

    # -------------------------------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.header("📊 Session Info")

        st.metric("Conversation", st.session_state.conversation_id[:8])
        st.metric("Turns", st.session_state.turn_number)
        st.metric("Tokens", f"{st.session_state.total_tokens:,}")

        total_cost = (
            st.session_state.total_cost
            + st.session_state.voice_cost
            + st.session_state.grok_cost
        )

        st.metric("Claude Cost", f"${st.session_state.total_cost:.4f}")
        st.metric("Voice Cost", f"${st.session_state.voice_cost:.4f}")
        st.metric("Grok Cost", f"${st.session_state.grok_cost:.4f}")
        st.metric("Total Cost", f"${total_cost:.4f}")

        st.divider()

        # ---- VOICE INPUT ----
        st.subheader("🎤 Voice Input")
        st.session_state.voice_mode = st.toggle(
            "Enable Voice Input",
            value=st.session_state.voice_mode
        )

        # ---- VOICE OUTPUT (RESTORED FROM PHASE 2) ----
        st.subheader("🔊 Voice Output")
        st.session_state.voice_output_enabled = st.toggle(
            "Enable Voice Output",
            value=st.session_state.voice_output_enabled,
            help="Athena will speak responses using TTS"
        )

        if st.session_state.voice_output_enabled:
            voice_map = {
                "Onyx (Deep male)": "onyx",
                "Alloy (Neutral)": "alloy",
                "Echo (Male)": "echo",
                "Fable (British male)": "fable",
                "Nova (Female)": "nova",
                "Shimmer (Soft female)": "shimmer"
            }

            label = st.selectbox("Voice", list(voice_map.keys()))
            st.session_state.selected_voice = voice_map[label]

            model = st.radio(
                "Quality",
                ["tts-1 (Standard)", "tts-1-hd (High quality)"],
                index=0
            )
            st.session_state.tts_model = (
                "tts-1-hd" if "hd" in model else "tts-1"
            )

        st.divider()

        if st.session_state.voice_mode:
            st.success("✓ Voice input active")
        if st.session_state.voice_output_enabled:
            st.success("✓ Voice output active")
        if not st.session_state.voice_mode and not st.session_state.voice_output_enabled:
            st.info("Voice features disabled")

    # -------------------------------------------------------------------------
    # CHAT UI
    # -------------------------------------------------------------------------
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
        status = st.empty()
        output = st.empty()

        grok = hybrid_query(prompt)
        grok_data = None

        if grok["use_grok"]:
            status.info("🔍 Fetching real-time data...")
            grok_data = grok["grok_data"]
            st.session_state.grok_cost += grok["cost"]

        memories = hybrid_retrieve(
            prompt,
            st.session_state.conversation_id,
            st.session_state.turn_number
        )

        context = format_retrieved_memories(memories)

        system_prompt = f"""
You are Athena, a helpful AI assistant.

{context}
"""

        if grok_data:
            system_prompt += f"\n=== REAL-TIME DATA ===\n{grok_data}\n"

        client = get_claude_client()
        response = ""

        for chunk in client.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt
        ):
            response += chunk
            output.markdown(response + "▌")

        output.markdown(response)
        status.empty()

        # ---- VOICE OUTPUT (FIXED) ----
        if st.session_state.voice_output_enabled:
            st.components.v1.html(
                create_tts_audio(response),
                height=0
            )

        # Cost tracking
        tokens_in = count_tokens_approx(prompt + context)
        tokens_out = count_tokens_approx(response)
        st.session_state.total_tokens += tokens_in + tokens_out
        st.session_state.total_cost += estimate_cost(tokens_in, tokens_out)

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
