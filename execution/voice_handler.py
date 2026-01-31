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

    # -------------------------
    # Voice Input (Whisper)
    # -------------------------
    def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: str = "wav"
    ) -> Optional[str]:
        """
        Transcribe audio using Whisper API.
        """
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"audio.{audio_format}"

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            logger.info("✓ Whisper transcription successful")
            return transcript.text

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return None

    # -------------------------
    # Voice Output (TTS)
    # -------------------------
    def generate_speech(
        self,
        text: str,
        voice: str = "onyx",
        model: str = "tts-1"
    ) -> Optional[bytes]:
        """
        Generate speech from text using OpenAI TTS.
        Returns MP3 bytes (browser-safe).
        """
        try:
            if not text:
                return None

            if len(text) > 4096:
                logger.warning(
                    f"Text too long ({len(text)} chars), truncating to 4096"
                )
                text = text[:4096]

            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                format="mp3"  # 🔑 critical for macOS playback
            )

            audio_bytes = response.read()

            if not audio_bytes:
                raise ValueError("Empty audio returned from TTS")

            logger.info(
                f"✓ TTS generated ({len(text)} chars → {len(audio_bytes)} bytes)"
            )

            return audio_bytes

        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            return None

    # -------------------------
    # Cost Estimation Helpers
    # -------------------------
    def get_audio_duration_estimate(self, audio_bytes: bytes) -> float:
        """
        Rough duration estimate: ~16KB per second
        """
        kb_size = len(audio_bytes) / 1024
        return kb_size / 16

    def estimate_transcription_cost(self, audio_bytes: bytes) -> float:
        """
        Whisper cost estimate: $0.006 per minute
        """
        seconds = self.get_audio_duration_estimate(audio_bytes)
        return (seconds / 60) * 0.006

    def estimate_tts_cost(self, text: str, model: str = "tts-1") -> float:
        """
        TTS cost estimate based on character count
        """
        chars = len(text)

        if model == "tts-1-hd":
            return (chars / 1_000_000) * 30.0
        else:
            return (chars / 1_000_000) * 15.0


# -------------------------
# Cached Singleton
# -------------------------
@st.cache_resource
def get_voice_handler() -> VoiceHandler:
    """
    Global cached VoiceHandler instance.
    """
    return VoiceHandler()
