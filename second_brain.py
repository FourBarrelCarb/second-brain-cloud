"""
Second Brain "Athena" - Phase 2B+C Enhanced
Cloud-Native Application with Grok Integration, Proactive Insights, and Voice
"""

import streamlit as st
from datetime import datetime
from uuid import uuid4
import logging

# Execution modules
from execution.retrieve_chats import hybrid_retrieve
from execution.save_conversation import save_conversation
from execution.call_claude import get_claude_client
from execution.voice_handler import get_voice_handler
from execution.audio_recorder import audio_recorder_component
from execution.grok_handler import hybrid_query
from execution.insights_engine import get_insights_engine

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Athena - Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
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

    # Voice (restored from Phase 2A)
    if "voice_input_enabled" not in st.session_state:
        st.session_state.voice_input_enabled = False

    if "voice_output_enabled" not in st.session_state:
        st.session_state.voice_output_enabled = False

    if "selected_voice" not in st.session_state:
        st.session_state.selected_voice = "onyx"

    if "tts_model" not in st.session_state:
        st.session_state.tts_model = "tts-1"

    if "voice_cost" not in st.session_state:
        st.session_state.voice_cost = 0.0

    # Grok
    if "grok_cost" not in st.session_state:
        st.session_state.grok_cost = 0.0

    # Insights
    if "digest_viewed" not in st.session_state:
        st.session_state.digest_viewed = False


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def count_tokens_approx(text: str) -> int:
    return int(len(text.split()) * 1.3)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = input_tokens * (3.00 / 1_000_000)
    output_cost = output_tokens * (15.00 / 1_000_000)
    return input_cost + output_cost


def format_retrieved_memories(documents) -> str:
    if not documents:
        return "No relevant past conversations found."

    formatted = "=== RELEVANT PAST CONVERSATIONS ===\n\n"
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        content = doc.page_content if hasattr(doc, "page_content") else ""
        formatted += (
            f"[Memory {i}] ({meta.get('timestamp','')[:10]})\n"
            f"{content}\n\n"
        )
    return formatted


# -----------------------------------------------------------------------------
# VOICE
# -----------------------------------------------------------------------------
def process_voice_input() -> str:
    st.markdown("### 🎤 Voice Input")
    audio_data = audio_recorder_component(key="voice_recorder")

    if not audio_data:
        return ""

    try:
        with st.spinner("Transcribing audio..."):
            vh = get_voice_handler()
            text = vh.transcribe_audio(audio_data, "wav")

            cost = vh.estimate_transcription_cost(audio_data)
            st.session_state.voice_cost += cost

            if text:
                st.success(f"✓ Transcribed: {text}")
                st.caption(f"Voice cost: ${cost:.4f}")
                return text
    except Exception as e:
        logger.error(f"Voice input error: {e}", exc_info=True)
        st.error("Voice transcription failed")

    return ""


def generate_voice_output(text: str):
    try:
        vh = get_voice_handler()
        with st.spinner("Generating voice response..."):
            audio = vh.generate_speech(
                text=text,
                voice=st.session_state.selected_voice,
                model=st.session_state.tts_model,
            )

            if audio:
                cost = vh.estimate_tts_cost(text, st.session_state.tts_model)
                st.session_state.voice_cost += cost
                st.audio(audio, format="audio/wav")
                st.caption(f"TTS cost: ${cost:.4f}")
    except Exception as e:
        logger.warning(f"Voice output failed: {e}")


# -----------------------------------------------------------------------------
# INSIGHTS
# -----------------------------------------------------------------------------
def display_weekly_digest():
    if st.session_state.digest_viewed:
        return

    insights = get_insights_engine()
    digest = insights.get_latest_digest()
    if not digest:
        return

    with st.expander("📊 Weekly Digest Available", expanded=True):
        st.markdown(digest["digest_content"])
        if st.button("Mark as Read"):
            st.session_state.digest_viewed = True
            st.rerun()


def display_alerts():
    insights = get_insights_engine()
    alerts = insights.get_pending_alerts()
    if not alerts:
        return

    st.sidebar.subheader("⚠️ Insights Alerts")
    for alert in alerts:
        with st.sidebar.expander(alert["title"]):
            st.markdown(alert["content"])
            if st.button("Dismiss", key=f"d_{alert['id']}"):
                insights.dismiss_alert(alert["id"])
                st.rerun()


# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
def main():
    init_session_state()

    st.title("🧠 Athena")
    st.caption("Perfect memory • Voice • Real-time data • Weekly insights")

    display_weekly_digest()

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.header("📊 Session Info")
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

        # Voice controls (RESTORED)
        st.subheader("🎙️ Voice Settings")
        st.session_state.voice_input_enabled = st.toggle(
            "Enable Voice Input", st.session_state.voice_input_enabled
        )
        st.session_state.voice_output_enabled = st.toggle(
            "Enable Voice Output", st.session_state.voice_output_enabled
        )

        if st.session_state.voice_output_enabled:
            st.session_state.selected_voice = st.selectbox(
                "Voice",
                ["onyx", "alloy", "echo", "fable", "nova", "shimmer"],
                index=0,
            )
            st.session_state.tts_model = st.radio(
                "Quality", ["tts-1", "tts-1-hd"], horizontal=True
            )

        st.divider()
        display_alerts()

    # ---------------- CHAT ----------------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = (
        process_voice_input()
        if st.session_state.voice_input_enabled
        else st.chat_input("Ask me anything…")
    )

    if not prompt:
        return

    st.session_state.turn_number += 1
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        status = st.empty()
        output = st.empty()

        # Grok
        grok_result = hybrid_query(prompt)
        grok_data = None
        if grok_result["use_grok"]:
            grok_data = grok_result["grok_data"]
            st.session_state.grok_cost += grok_result["cost"]

        # Retrieval
        docs = hybrid_retrieve(
            prompt,
            st.session_state.conversation_id,
            st.session_state.turn_number,
        )
        memories = format_retrieved_memories(docs)

        system_prompt = f"""You are Athena.

{memories}
"""
        if grok_data:
            system_prompt += f"\n=== REAL-TIME DATA ===\n{grok_data}"

        full_response = ""
        client = get_claude_client()

        for chunk in client.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt,
        ):
            full_response += chunk
            output.markdown(full_response + "▌")

        output.markdown(full_response)

        if st.session_state.voice_output_enabled:
            generate_voice_output(full_response)

        # Cost
        input_tokens = count_tokens_approx(prompt + memories)
        output_tokens = count_tokens_approx(full_response)
        st.session_state.total_tokens += input_tokens + output_tokens
        st.session_state.total_cost += estimate_cost(input_tokens, output_tokens)

        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
