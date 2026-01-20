"""
Audio Recorder Component - Simplified
Uses Streamlit's built-in audio recording capabilities
"""

import streamlit as st
from io import BytesIO


def audio_recorder_component(key: str = "audio_recorder"):
    """
    Display an audio recorder using Streamlit's native audio input.
    
    Args:
        key: Unique key for this component instance
        
    Returns:
        Audio bytes when recording is complete, None otherwise
    """
    
    st.markdown("""
    <style>
    .stAudioInput {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Use Streamlit's built-in audio input
    audio_value = st.audio_input(
        "🎤 Click to record your voice",
        key=key,
        help="Click the microphone to start recording. Click again to stop."
    )
    
    if audio_value:
        # Read the audio bytes
        audio_bytes = audio_value.getvalue()
        return audio_bytes
    
    return None
