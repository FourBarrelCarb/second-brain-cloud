"""
Voice Handler - Whisper Transcription and Text-to-Speech
Handles voice input and output for Athena
"""

import streamlit as st
import openai
import logging
from typing import Optional
import base64
import io

logger = logging.getLogger(__name__)


class VoiceHandler:
    """
    Manages voice input (Whisper) and voice output (browser TTS).
    """
    
    def __init__(self):
        """Initialize OpenAI client for Whisper."""
        try:
            self.client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            logger.info("✓ Voice handler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize voice handler: {e}")
            raise
    
    def transcribe_audio(self, audio_bytes: bytes, audio_format: str = "webm") -> Optional[str]:
        """
        Transcribe audio using Whisper API.
        
        Args:
            audio_bytes: Raw audio data
            audio_format: Audio format (webm, mp3, wav, etc.)
            
        Returns:
            Transcribed text or None on error
        """
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"audio.{audio_format}"
            
            # Call Whisper API
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"  # Can be removed for auto-detection
            )
            
            transcribed_text = transcript.text
            logger.info(f"✓ Transcribed {len(audio_bytes)} bytes: {transcribed_text[:50]}...")
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def get_audio_duration_estimate(self, audio_bytes: bytes) -> float:
        """
        Estimate audio duration for cost calculation.
        Very rough estimate: ~16KB per second for webm.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            Estimated duration in seconds
        """
        # Rough estimate: webm is ~16KB/second
        kb_size = len(audio_bytes) / 1024
        estimated_seconds = kb_size / 16
        return estimated_seconds
    
    def estimate_transcription_cost(self, audio_bytes: bytes) -> float:
        """
        Estimate Whisper API cost.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            Estimated cost in USD
        """
        duration_seconds = self.get_audio_duration_estimate(audio_bytes)
        duration_minutes = duration_seconds / 60
        
        # Whisper pricing: $0.006 per minute
        cost = duration_minutes * 0.006
        
        return cost


# Cached instance
@st.cache_resource
def get_voice_handler():
    """
    Get or create the global voice handler instance.
    Cached by Streamlit for performance.
    """
    return VoiceHandler()


def create_tts_audio(text: str) -> str:
    """
    Create text-to-speech audio using browser's built-in capabilities.
    Returns JavaScript code to execute speech synthesis.
    
    Args:
        text: Text to speak
        
    Returns:
        JavaScript code for speech synthesis
    """
    # Escape quotes in text
    safe_text = text.replace('"', '\\"').replace("'", "\\'")
    
    js_code = f"""
    <script>
    function speak() {{
        const utterance = new SpeechSynthesisUtterance("{safe_text}");
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        window.speechSynthesis.speak(utterance);
    }}
    speak();
    </script>
    """
    
    return js_code
