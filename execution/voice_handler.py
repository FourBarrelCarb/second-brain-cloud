"""
Voice Handler - Phase 2A Enhanced
Whisper Transcription + OpenAI TTS (instead of browser TTS)
Handles voice input and output for Athena
"""

import streamlit as st
import openai
import logging
from typing import Optional
import io

logger = logging.getLogger(__name__)


class VoiceHandler:
    """
    Manages voice input (Whisper) and voice output (OpenAI TTS).
    Phase 2A enhancement: Replaced browser TTS with OpenAI TTS for natural voice.
    """

    def __init__(self):
        """Initialize OpenAI client for Whisper and TTS."""
        try:
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            self.client = openai
            logger.info("✓ Voice handler initialized (Whisper + OpenAI TTS)")
        except Exception as e:
            logger.error(f"Failed to initialize voice handler: {e}")
            raise

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: str = "wav"
    ) -> Optional[str]:
        """
        Transcribe audio using Whisper API.

        Args:
            audio_bytes: Raw audio data
            audio_format: Audio format (wav, webm, mp3, etc.)

        Returns:
            Transcribed text or None on error
        """
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"audio.{audio_format}"

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            transcribed_text = transcript.text
            logger.info(f"✓ Transcribed audio ({len(audio_bytes)} bytes)")

            return transcribed_text

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return None

    def generate_speech(
        self,
        text: str,
        voice: str = "onyx",
        model: str = "gpt-4o-mini-tts"
    ) -> Optional[bytes]:
    """
    Generate speech using the NEW OpenAI SDK (2024+).
    """

    try:
        if len(text) > 4096:
            text = text[:4096]

        with self.client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text
        ) as response:
            audio_bytes = response.read()

        logger.info(f"✓ Generated speech ({len(audio_bytes)} bytes)")
        return audio_bytes

    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        return None


    def get_audio_duration_estimate(self, audio_bytes: bytes) -> float:
        """
        Estimate audio duration for cost calculation.
        Rough estimate: ~16KB per second for webm-like audio.
        """
        kb_size = len(audio_bytes) / 1024
        estimated_seconds = kb_size / 16
        return estimated_seconds

    def estimate_transcription_cost(self, audio_bytes: bytes) -> float:
        """
        Estimate Whisper API cost.
        """
        duration_seconds = self.get_audio_duration_estimate(audio_bytes)
        duration_minutes = duration_seconds / 60
        return duration_minutes * 0.006

    def estimate_tts_cost(self, text: str, model: str = "tts-1") -> float:
        """
        Estimate OpenAI TTS cost.
        """
        char_count = len(text)

        if model == "tts-1-hd":
            return (char_count / 1_000_000) * 30.00
        else:
            return (char_count / 1_000_000) * 15.00


@st.cache_resource
def get_voice_handler() -> VoiceHandler:
    """
    Get or create the global voice handler instance.
    Cached by Streamlit for performance.
    """
    return VoiceHandler()

def create_tts_audio(text: str) -> str:
    """
    Browser-safe fallback TTS using SpeechSynthesis.
    Used by Phase 2B UI to avoid audio file handling issues.
    """

    if not text:
        return ""

    # Escape text for JS safety
    escaped = (
        text.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace("\n", " ")
    )

    return f"""
    <script>
        try {{
            const msg = new SpeechSynthesisUtterance('{escaped}');
            msg.rate = 1;
            msg.pitch = 1;
            msg.lang = 'en-US';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(msg);
        }} catch (e) {{
            console.error('TTS failed', e);
        }}
    </script>
    """
