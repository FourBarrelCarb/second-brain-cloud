"""
Second Brain "Athena" - Phase 2B+C Enhanced (FIXED GROK VERSION)
"""

import streamlit as st
from datetime import datetime
from uuid import uuid4
import logging
import os

# =============================================================================
# IMPORTS
# =============================================================================

from execution.retrieve_chats import hybrid_retrieve
from execution.save_conversation import save_conversation
from execution.call_claude import get_claude_client
from execution.voice_handler import get_voice_handler, create_tts_audio
from execution.audio_recorder import audio_recorder_component
from execution.grok_handler import hybrid_query
from execution.insights_engine import get_insights_engine

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("athena")

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Athena – Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
    defaults = {
        "conversation_id": str(uuid4()),
        "turn_number": 0,
        "messages": [],
        "total_tokens": 0,
        "total_cost": 0.0,
        "voice_mode": False,
        "voice_cost": 0.0,
        "grok_cost": 0.0,
        "digest_viewed": False,
        "force_grok": False
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# =============================================================================
# HELPERS
# =============================================================================

def count_tokens_approx(text: str) -> int:
    return int(len(text.split()) * 1.3)

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * (3.00 / 1_000_000)
        + output_tokens * (15.00 / 1_000_000)
    )

def format_retrieved_memories(docs):
    if not docs:
        return "No relevant past conversations."

    out = "=== RELEVANT PAST CONVERSATIONS ===\n\n"
    for i, d in enumerate(docs, 1):
        meta = getattr(d, "metadata", {})
        content = getattr(d, "page_content", "")
        out += f"[Memory {i}] {meta.get('title','Untitled')}\n{content}\n\n"
    return out

# =============================================================================
# VOICE INPUT
# =============================================================================

def process_voice_input():
    audio = audio_recorder_component(key="voice")
    if not audio:
        return ""

    try:
        vh = get_voice_handler()
        with st.spinner("Transcribing..."):
            text = vh.transcribe_audio(audio, "wav")
            st.session_state.voice_cost += vh.estimate_transcription_cost(audio)
            return text or ""
    except Exception as e:
        logger.error("Voice error", exc_info=True)
        return ""

# =============================================================================
# MAIN
# =============================================================================

def main():
    init_session_state()

    st.title("🧠 Athena")
    st.caption("Perfect memory • Grok real-time • Voice • Weekly insights")

    # =========================================================================
    # SIDEBAR
    # =========================================================================

    with st.sidebar:
        st.subheader("🧪 Debug")
        st.session_state.force_grok = st.toggle("Force Grok (debug)", value=False)

        st.divider()
        st.subheader("💰 Costs")
        st.metric("Claude", f"${st.session_state.total_cost:.4f}")
        st.metric("Voice", f"${st.session_state.voice_cost:.4f}")
        st.metric("Grok", f"${st.session_state.grok_cost:.4f}")

    # =========================================================================
    # CHAT HISTORY
    # =========================================================================

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # =========================================================================
    # INPUT
    # =========================================================================

    prompt = (
        process_voice_input()
        if st.session_state.voice_mode
        else st.chat_input("Ask anything…")
    )

    if not prompt:
        return

    st.session_state.turn_number += 1
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # =========================================================================
    # ASSISTANT
    # =========================================================================

    with st.chat_message("assistant"):
        status = st.empty()
        output = st.empty()

        try:
            # ---------------- GROK ROUTING ----------------
            grok_result = hybrid_query(prompt)

            if st.session_state.force_grok:
                grok_result["use_grok"] = True

            logger.info(f"GROK ROUTER → {grok_result}")

            grok_data = None
            if grok_result.get("use_grok"):
                status.info("🔍 Fetching real-time data (Grok)")
                grok_data = grok_result.get("grok_data") or ""
                st.session_state.grok_cost += grok_result.get("cost", 0.0)

                if not grok_data:
                    st.warning("⚠️ Grok returned no data")

                with st.expander("🔎 Raw Grok Output"):
                    st.code(grok_data or "EMPTY")

            # ---------------- MEMORY ----------------
            status.info("🔍 Searching memory…")
            docs = hybrid_retrieve(
                query=prompt,
                conversation_id=st.session_state.conversation_id,
                turn_number=st.session_state.turn_number
            )

            memories = format_retrieved_memories(docs)

            # ---------------- SYSTEM PROMPT ----------------
            system_prompt = f"""
You are Athena, a helpful AI with perfect memory.

{memories}
"""

            if grok_data:
                system_prompt += f"""
=== REAL-TIME DATA (Grok) ===
{grok_data}
"""

            system_prompt += "\nRespond naturally. Do not mention tools."

            # ---------------- CLAUDE STREAM ----------------
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

            # ---------------- VOICE OUTPUT ----------------
            if st.session_state.voice_mode:
                st.components.v1.html(create_tts_audio(response), height=0)

            # ---------------- COSTS ----------------
            it = count_tokens_approx(prompt + memories + (grok_data or ""))
            ot = count_tokens_approx(response)
            st.session_state.total_tokens += it + ot
            st.session_state.total_cost += estimate_cost(it, ot)

            # ---------------- SAVE ----------------
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            logger.error("Generation error", exc_info=True)
            st.error("Something went wrong. Check logs.")

# =============================================================================
# ENTRY
# =============================================================================

if __name__ == "__main__":
    main()
