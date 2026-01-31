"""
Second Brain "Athena" - Phase 2A Enhanced
Cloud-Native Application with OpenAI TTS Voice
Complete AI assistant with perfect memory and natural voice capabilities
"""

import tempfile
import os
import base64
import streamlit as st
from datetime import datetime
from uuid import uuid4
import logging

# Import execution modules
from execution.retrieve_chats import hybrid_retrieve
from execution.save_conversation import save_conversation
from execution.call_claude import get_claude_client
from execution.voice_handler import get_voice_handler
from execution.audio_recorder import audio_recorder_component

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Second Brain - Athena",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize all session state variables."""
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

    if "tts_audio" not in st.session_state:
        st.session_state.tts_audio = None

    if "tts_text_hash" not in st.session_state:
        st.session_state.tts_text_hash = None

    
    # Voice mode settings
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

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_retrieved_memories(documents) -> str:
    """Format retrieved documents for Claude's context."""
    if not documents:
        return "No relevant past conversations found."
    
    # DEBUG: Log what we retrieved
    logger.info(f"Formatting {len(documents)} retrieved documents")
    for i, doc in enumerate(documents, 1):
        if hasattr(doc, 'metadata'):
            title = doc.metadata.get('title', 'Untitled')[:50]
            score = doc.metadata.get('score', 0)
            logger.info(f"  Doc {i}: {title}... (score: {score:.3f})")
    
    formatted = "=== RELEVANT PAST CONVERSATIONS ===\n\n"
    
    for i, doc in enumerate(documents, 1):
        # Handle different document formats
        if hasattr(doc, 'metadata'):
            meta = doc.metadata
            content = doc.page_content
        elif isinstance(doc, dict):
            meta = doc.get('metadata', {})
            content = doc.get('page_content', doc.get('content', ''))
        else:
            continue
            
        timestamp = meta.get('timestamp', 'Unknown')[:10] if isinstance(meta, dict) else 'Unknown'
        score = meta.get('score', 0) if isinstance(meta, dict) else 0
        title = meta.get('title', 'Untitled')
        
        formatted += f"[Memory {i}] ({timestamp}, relevance: {score:.2f})\n"
        formatted += f"Title: {title}\n"
        formatted += f"{content}\n\n"
    
    logger.info(f"Total formatted memory length: {len(formatted)} characters")
    return formatted


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for Claude Sonnet 4."""
    input_cost = input_tokens * (3.00 / 1_000_000)
    output_cost = output_tokens * (15.00 / 1_000_000)
    return input_cost + output_cost


def count_tokens_approx(text: str) -> int:
    """Approximate token count (~1.3 tokens per word)."""
    return int(len(text.split()) * 1.3)


def process_voice_input() -> str:
    """
    Handle voice input recording and transcription.
    Returns transcribed text or empty string.
    """
    st.markdown("### 🎤 Voice Input")
    
    # Audio recorder component
    audio_data = audio_recorder_component(key="voice_recorder")
    
    if audio_data:
        try:
            # Show processing message
            with st.spinner("Transcribing audio..."):
                voice_handler = get_voice_handler()
                transcribed_text = voice_handler.transcribe_audio(audio_data, "wav")
                
                # Calculate cost
                voice_cost = voice_handler.estimate_transcription_cost(audio_data)
                st.session_state.voice_cost += voice_cost
                
                if transcribed_text:
                    st.success(f"✓ Transcribed: *{transcribed_text}*")
                    st.caption(f"Whisper cost: ${voice_cost:.4f}")
                    return transcribed_text
                else:
                    st.error("Failed to transcribe audio")
                    return ""
                    
        except Exception as e:
            logger.error(f"Voice input error: {e}", exc_info=True)
            st.error(f"Voice processing error: {e}")
            return ""
    
    return ""


def generate_voice_output(text: str):
    """
    Generate voice output using OpenAI TTS
    and store it safely for cross-device playback.
    """
    try:
        voice_handler = get_voice_handler()
        text_hash = hash(text)

        # Avoid regenerating the same audio on reruns
        if st.session_state.tts_text_hash == text_hash:
            return

        with st.spinner("Generating voice response..."):
            audio_bytes = voice_handler.generate_speech(
                text=text,
                voice=st.session_state.selected_voice,
                model=st.session_state.tts_model
            )

            if not audio_bytes:
                st.warning("Could not generate voice output")
                return

            # Store audio safely in session state
            st.session_state.tts_audio = audio_bytes
            st.session_state.tts_text_hash = text_hash

            # Cost tracking
            tts_cost = voice_handler.estimate_tts_cost(
                text,
                st.session_state.tts_model
            )
            st.session_state.voice_cost += tts_cost

            st.caption(f"TTS cost: ${tts_cost:.4f}")
            logger.info("✓ Voice output generated and stored")

    except Exception as e:
        logger.error(f"Voice output error: {e}", exc_info=True)
        st.warning("Voice output failed")

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main Streamlit application."""
    
    init_session_state()
    
    # Title
    st.title("🧠 Athena - Your Second Brain")
    st.caption("Perfect memory • Natural voice • Accessible from any device")
    
    # =========================================================================
    # SIDEBAR
    # =========================================================================

    
    with st.sidebar:
        st.header("📊 Session Info")
        
        # Metrics
        st.metric("Conversation", st.session_state.conversation_id[:8] + "...")
        st.metric("Turns", st.session_state.turn_number)
        st.metric("Tokens", f"{st.session_state.total_tokens:,}")
        st.metric("Claude Cost", f"${st.session_state.total_cost:.4f}")
        st.metric("Voice Cost", f"${st.session_state.voice_cost:.4f}")
        st.metric("Total Cost", f"${(st.session_state.total_cost + st.session_state.voice_cost):.4f}")
        
        st.divider()
        
        # Voice Settings
        st.subheader("🎙️ Voice Settings")
        
        # Voice Input Toggle
        voice_input = st.toggle(
            "Enable Voice Input", 
            value=st.session_state.voice_input_enabled,
            help="Use microphone to speak your questions"
        )
        st.session_state.voice_input_enabled = voice_input
        
        # Voice Output Toggle
        voice_output = st.toggle(
            "Enable Voice Output",
            value=st.session_state.voice_output_enabled,
            help="Athena will speak responses using OpenAI TTS"
        )
        st.session_state.voice_output_enabled = voice_output
        
        # Voice Selection (only show if output enabled)
        if voice_output:
            st.markdown("**Voice Selection:**")
            
            voice_options = {
                "Onyx (Deep male)": "onyx",
                "Alloy (Neutral)": "alloy",
                "Echo (Male)": "echo",
                "Fable (British male)": "fable",
                "Nova (Female)": "nova",
                "Shimmer (Soft female)": "shimmer"
            }
            
            selected_voice_label = st.selectbox(
                "Choose voice",
                options=list(voice_options.keys()),
                index=0,
                label_visibility="collapsed"
            )
            st.session_state.selected_voice = voice_options[selected_voice_label]
            
            # TTS Model Selection
            tts_model = st.radio(
                "Quality",
                options=["tts-1 (Standard)", "tts-1-hd (High quality)"],
                index=0 if st.session_state.tts_model == "tts-1" else 1,
                help="HD quality costs 2x but sounds better"
            )
            st.session_state.tts_model = "tts-1-hd" if "hd" in tts_model.lower() else "tts-1"
            
            # Test Voice Button
            if st.button("🔊 Test Voice", use_container_width=True):
                test_text = "Hello! This is how I sound. I'm Athena, your AI assistant with perfect memory."
                voice_handler = get_voice_handler()
                
                with st.spinner("Generating test..."):
                    audio = voice_handler.generate_speech(
                        test_text,
                        st.session_state.selected_voice,
                        st.session_state.tts_model
                    )
                    if audio:
                        st.audio(audio, format="audio/wav")
        
        # Status indicators
        if voice_input:
            st.success("✓ Voice input active")
        if voice_output:
            st.success("✓ Voice output active")
        if not voice_input and not voice_output:
            st.info("Voice features disabled")
        
        st.divider()
        
        # Actions
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 New Chat", use_container_width=True):
                if st.session_state.messages:
                    # Save current conversation
                    messages_to_save = [
                        {
                            'role': msg['role'],
                            'content': msg['content'],
                            'timestamp': datetime.now().isoformat()
                        }
                        for msg in st.session_state.messages
                    ]
                    try:
                        save_conversation(
                            messages_to_save,
                            st.session_state.conversation_id
                        )
                        st.success("✓ Saved to memory")
                    except Exception as e:
                        st.warning(f"Could not save: {e}")
                
                # Reset for new chat
                st.session_state.messages = []
                st.session_state.conversation_id = str(uuid4())
                st.session_state.turn_number = 0
                st.session_state.total_tokens = 0
                st.session_state.total_cost = 0.0
                # Keep voice_cost running total
                st.rerun()
        
        with col2:
            if st.button("💾 Save", use_container_width=True):
                if st.session_state.messages:
                    messages_to_save = [
                        {
                            'role': msg['role'],
                            'content': msg['content'],
                            'timestamp': datetime.now().isoformat()
                        }
                        for msg in st.session_state.messages
                    ]
                    try:
                        save_conversation(
                            messages_to_save,
                            st.session_state.conversation_id
                        )
                        st.success("✓ Saved")
                    except Exception as e:
                        st.error(f"Save failed: {e}")
                else:
                    st.warning("Nothing to save")
        
        st.divider()
        
        # System info
        with st.expander("⚙️ System Info", expanded=False):
            st.caption("**Model:** Claude Sonnet 4")
            st.caption("**Voice:** Whisper + OpenAI TTS")
            st.caption(f"**Retrieval:** Top {st.secrets.get('RETRIEVAL_TOP_K', 6)}")
            st.caption(f"**Context:** Last {st.secrets.get('SESSION_HISTORY_LIMIT', 10)} turns")
            st.caption(f"**Recency:** {st.secrets.get('RECENCY_BOOST_DAYS', 7)} days")
        
        st.divider()
        
        # Tips
        st.caption("💡 **Tips:**")
        st.caption("• Toggle voice settings above")
        st.caption("• All conversations auto-saved")
        st.caption("• Works on all devices")
        st.caption("• Voice output uses OpenAI TTS")
    
    # =========================================================================
    # CHAT INTERFACE
    # =========================================================================
    
    # Display message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input handling
    prompt = None
    
    # Voice Input Mode
    if st.session_state.voice_input_enabled:
        prompt = process_voice_input()
    else:
        # Text Input Mode
        prompt = st.chat_input("Ask me anything... I remember everything")
    
    # Process input (text or voice)
    if prompt:
        st.session_state.turn_number += 1
        
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            message_placeholder = st.empty()
            
            try:
                # Step 1: Retrieve relevant past conversations
                status_placeholder.info("🔍 Searching memories...")
                
                try:
                    retrieved_docs = hybrid_retrieve(
                        query=prompt,
                        conversation_id=st.session_state.conversation_id,
                        turn_number=st.session_state.turn_number
                    )
                except Exception as e:
                    logger.warning(f"Retrieval failed: {e}")
                    retrieved_docs = []
                
                # Format memories
                retrieved_memories = format_retrieved_memories(retrieved_docs)
                
                # Step 2: Build system prompt with context
                system_prompt = f"""You are Athena, a helpful AI assistant with perfect memory of all past conversations.

{retrieved_memories}

Use the above memories naturally when relevant. Don't mention the retrieval system.
Be helpful, concise, and build on our conversation history."""
                
                # Step 3: Prepare recent messages for Claude
                session_limit = int(st.secrets.get("SESSION_HISTORY_LIMIT", "10"))
                history_limit = session_limit * 2
                
                recent_messages = []
                for msg in st.session_state.messages[-history_limit:]:
                    if msg == st.session_state.messages[-1]:
                        continue
                    recent_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
                
                # Add current user message
                recent_messages.append({
                    'role': 'user',
                    'content': prompt
                })
                
                # Step 4: Stream response from Claude
                status_placeholder.success(f"✓ Found {len(retrieved_docs)} memories • Generating...")
                
                full_response = ""
                claude_client = get_claude_client()
                
                for chunk in claude_client.chat_stream(
                    messages=recent_messages,
                    system_prompt=system_prompt
                ):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                
                # Final response (remove cursor)
                message_placeholder.markdown(full_response)
                status_placeholder.empty()
                
                # Step 5: Voice output if enabled
                # Render audio player (required for macOS + mobile)
                if (
                    st.session_state.voice_output_enabled
                    and st.session_state.tts_audio
                    ):
                    if st.button("▶️ Play Voice Response", key=f"play_{st.session_state.turn_number}"):

                        b64_audio = base64.b64encode(
                            st.session_state.tts_audio
                        ).decode("utf-8")

                        audio_html = f"""
                        <audio controls>
                            <source src="data:audio/wav;base64,{b64_audio}" type="audio/wav">
                        Your browser does not support the audio element.
                        </audio>
                        """

                        st.markdown(audio_html, unsafe_allow_html=True)


                
                # Step 6: Calculate tokens and cost
                input_tokens = count_tokens_approx(prompt + retrieved_memories)
                output_tokens = count_tokens_approx(full_response)
                total_tokens = input_tokens + output_tokens
                cost = estimate_cost(input_tokens, output_tokens)
                
                # Update session totals
                st.session_state.total_tokens += total_tokens
                st.session_state.total_cost += cost
                
                # Step 7: Add assistant response to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
                
            except Exception as e:
                status_placeholder.error(f"Error: {str(e)}")
                logger.error(f"Error generating response: {e}", exc_info=True)
                st.error(
                    "Sorry, I encountered an error. Please try again. "
                    "Check Settings if the problem persists."
                )


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        logger.info("Starting Athena (Phase 2A Enhanced)...")
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        st.error(
            "Failed to start application. Please check:\n\n"
            "1. Streamlit secrets are configured\n"
            "2. Database connection is valid\n"
            "3. API keys are correct"
        )
