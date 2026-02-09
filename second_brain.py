"""
Second Brain "Athena" - Phase 2B+C Enhanced
Cloud-Native Application with Grok Integration & Proactive Insights
Complete AI assistant with perfect memory, voice, real-time data, and weekly insights
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
    
    # Voice mode settings
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False
    
    if "voice_cost" not in st.session_state:
        st.session_state.voice_cost = 0.0
    
    # Grok cost tracking
    if "grok_cost" not in st.session_state:
        st.session_state.grok_cost = 0.0
    
    # Insights state
    if "digest_viewed" not in st.session_state:
        st.session_state.digest_viewed = False

     # 🔊 Voice output
    if "voice_output_enabled" not in st.session_state:
        st.session_state.voice_output_enabled = False


    @st.cache_resource
    def warm_grok():
        try:
            from execution.grok_handler import hybrid_query
            hybrid_query("ping")
        except Exception:
            pass

    warm_grok()


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
    st.subheader("🎤 Voice Input")
    
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
                    st.success(f"✓ Transcribed: {transcribed_text}")
                    st.caption(f"Voice cost: ${voice_cost:.4f}")
                    return transcribed_text
                else:
                    st.error("Failed to transcribe audio")
                    return ""
                    
        except Exception as e:
            logger.error(f"Voice input error: {e}", exc_info=True)
            st.error(f"Voice processing error: {e}")
            return ""
    
    return ""


def display_weekly_digest():
    """Display weekly digest if available and not viewed."""
    insights = get_insights_engine()
    
    # Check if we should show digest
    if st.session_state.digest_viewed:
        return
    
    digest = insights.get_latest_digest()
    
    if not digest:
        return
    
    # Show digest in expandable section
    with st.expander("📊 Weekly Digest Available - Click to View", expanded=True):
        st.markdown(f"**Week of {digest['week_start']} to {digest['week_end']}**")
        st.markdown(digest['digest_content'])
        
        if st.button("Mark as Read"):
            st.session_state.digest_viewed = True
            st.rerun()


def display_alerts():
    """Display any pending contradiction alerts."""
    insights = get_insights_engine()
    alerts = insights.get_pending_alerts()
    
    if not alerts:
        return
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚠️ Insights Alerts")
    
    for alert in alerts:
        with st.sidebar.expander(f"⚠️ {alert['title']}", expanded=False):
            st.markdown(alert['content'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Dismiss", key=f"dismiss_{alert['id']}"):
                    insights.dismiss_alert(alert['id'])
                    st.rerun()
            with col2:
                if alert.get('related_conversation_ids'):
                    st.caption(f"Related: {len(alert['related_conversation_ids'])} conversations")


def check_and_generate_digest():
    """Check if weekly digest should be generated."""
    insights = get_insights_engine()
    
    if insights.should_generate_weekly_digest():
        logger.info("Generating weekly digest...")
        digest_id = insights.generate_weekly_digest()
        if digest_id:
            st.session_state.digest_viewed = False
            logger.info(f"✓ Weekly digest generated: {digest_id}")

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main Streamlit application."""
    
    init_session_state()
    
    # Check for weekly digest generation
    check_and_generate_digest()
    
    # Title
    st.title("🧠 Athena - Your Second Brain")
    st.caption("Perfect memory • Voice enabled • Real-time data • Weekly insights")
    
    # Display weekly digest if available
    display_weekly_digest()
    
    # =========================================================================
    # SIDEBAR
    # =========================================================================

    
    with st.sidebar:
        st.header("📊 Session Info")
        
        # Metrics
        st.metric("Conversation", st.session_state.conversation_id[:8] + "...")
        st.metric("Turns", st.session_state.turn_number)
        st.metric("Tokens", f"{st.session_state.total_tokens:,}")
        
        # Cost breakdown
        claude_cost = st.session_state.total_cost
        voice_cost = st.session_state.voice_cost
        grok_cost = st.session_state.grok_cost
        total_cost = claude_cost + voice_cost + grok_cost
        
        st.metric("Claude Cost", f"${claude_cost:.4f}")
        st.metric("Voice Cost", f"${voice_cost:.4f}")
        st.metric("Grok Cost", f"${grok_cost:.4f}")
        st.metric("Total Cost", f"${total_cost:.4f}")
        
        st.divider()
        
        # Voice Input Toggle
        voice_input = st.toggle(
        if voice_enabled:
            "Enable Voice Input", 
            st.success("✓ Voice mode active")
            value=st.session_state.voice_input_enabled,
            help="Use microphone to speak your questions"
        )
        else:
        st.session_state.voice_input_enabled = voice_input
            st.info("Voice mode off")
        
        
        # Voice Output Toggle
        voice_output = st.toggle(
            "Enable Voice Output",
            value=st.session_state.voice_output_enabled,
            help="Athena will speak responses using OpenAI TTS"
        )
        st.divider()
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
        
        # Display alerts
        # Status indicators
        display_alerts()
        if voice_input:
            st.success("✓ Voice input active")
        if voice_output:
            st.success("✓ Voice output active")
        if not voice_input and not voice_output:
            st.info("Voice features disabled")

        st.divider()
        
        # Display alerts
     #   display_alerts()
        
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
                # Keep voice_cost and grok_cost running total
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
            st.caption("**Model:** Claude Sonnet 4 + Grok")
            st.caption("**Voice:** Whisper + Browser TTS")
            st.caption(f"**Retrieval:** Top {st.secrets.get('RETRIEVAL_TOP_K', 6)}")
            st.caption(f"**Context:** Last {st.secrets.get('SESSION_HISTORY_LIMIT', 10)} turns")
            st.caption(f"**Recency:** {st.secrets.get('RECENCY_BOOST_DAYS', 7)} days")
            st.caption("**Insights:** Weekly digests enabled")
        
        st.divider()
        
        # Tips
        st.caption("💡 **Tips:**")
        st.caption("• Toggle voice mode above")
        st.caption("• Grok handles real-time data")
        st.caption("• Weekly digests on Sundays")
        st.caption("• All conversations auto-saved")
    
    # =========================================================================
    # CHAT INTERFACE
    # =========================================================================
    
    # Display message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Voice Input Mode
    if st.session_state.voice_mode:
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
                # Step 1: Check if we should use Grok
                grok_result = hybrid_query(prompt)
                
                if grok_result["use_grok"]:
                    status_placeholder.info("🔍 Fetching real-time data from Grok...")
                    grok_data = grok_result["grok_data"]
                    st.session_state.grok_cost += grok_result["cost"]
                else:
                    grok_data = None
                
                # Step 2: Retrieve relevant past conversations
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
                
                # Step 3: Build system prompt with context
                system_prompt = f"""You are Athena, a helpful AI assistant with perfect memory of all past conversations.

{retrieved_memories}"""
                
                if grok_data:
                    system_prompt += f"""

=== REAL-TIME DATA (from Grok) ===
{grok_data}

Use this current data to provide up-to-date information, combined with historical context from memories."""
                
                system_prompt += """

Use the above information naturally when relevant. Don't mention the retrieval system or data sources.
Be helpful, concise, and build on our conversation history."""
                
                # Step 4: Prepare recent messages for Claude
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
                
                # Step 5: Stream response from Claude
                memories_count = len(retrieved_docs)
                status_msg = f"✓ Found {memories_count} memories"
                if grok_data:
                    status_msg += " • Real-time data retrieved"
                status_msg += " • Generating..."
                
                status_placeholder.success(status_msg)
                
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
                
                # Step 6: Voice output if enabled
                if st.session_state.voice_mode:
                    st.components.v1.html(
                        create_tts_audio(full_response),
                        height=0
                    )
                
                # Step 7: Calculate tokens and cost
                input_tokens = count_tokens_approx(prompt + retrieved_memories)
                if grok_data:
                    input_tokens += count_tokens_approx(grok_data)
                output_tokens = count_tokens_approx(full_response)
                total_tokens = input_tokens + output_tokens
                cost = estimate_cost(input_tokens, output_tokens)
                
                # Update session totals
                st.session_state.total_tokens += total_tokens
                st.session_state.total_cost += cost
                
                # Step 8: Add assistant response to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
                
                # Step 9: Check for contradictions (async, doesn't block)
                try:
                    insights = get_insights_engine()
                    insights.check_for_contradictions(
                        prompt,
                        st.session_state.conversation_id
                    )
                except Exception as e:
                    logger.warning(f"Contradiction check failed: {e}")
                
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
        logger.info("Starting Athena (Phase 2B+C)...")
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        st.error(
            "Failed to start application. Please check:\n\n"
            "1. Streamlit secrets are configured\n"
            "2. Database connection is valid\n"
            "3. API keys are correct"
        )
