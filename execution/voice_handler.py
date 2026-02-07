"""
Voice Handler - Phase 2B Stable
Whisper Transcription + OpenAI TTS (primary) + Browser TTS (fallback)
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
    """

    def __init__(self):
        try:
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            self.client = openai
            logger.info("✓ Voice handler initialized (Whisper + OpenAI TTS)")
        except Exception as e:
            logger.error(f"Failed to initialize voice handler: {e}")
            raise

    # ==========================
    # VOICE INPUT (WHISPER)
    # ==========================
    def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: str = "wav"
    ) -> Optional[str]:
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"audio.{audio_format}"

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            return transcript.text

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return None

    # ==========================
    # VOICE OUTPUT (OPENAI TTS)
    # ==========================
    def generate_speech(
        self,
        text: str,
        voice: str = "onyx",
        model: str = "gpt-4o-mini-tts"
    ) -> Optional[bytes]:
        """
        Generate speech using the modern OpenAI TTS API.
        """
        try:
            if not text:
                return None

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

    # ==========================
    # COST ESTIMATION
    # ==========================
    def get_audio_duration_estimate(self, audio_bytes: bytes) -> float:
        kb_size = len(audio_bytes) / 1024
        return kb_size / 16  # ~16KB/sec estimate

    def estimate_transcription_cost(self, audio_bytes: bytes) -> float:
        minutes = (self.get_audio_duration_estimate(audio_bytes)) / 60
        return minutes * 0.006

    def estimate_tts_cost(self, text: str, model: str = "tts-1") -> float:
        chars = len(text)
        if model == "tts-1-hd":
            return (chars / 1_000_000) * 30.0
        return (chars / 1_000_000) * 15.0


# ==========================
# SINGLE CACHED INSTANCE
# ==========================
@st.cache_resource
def get_voice_handler() -> VoiceHandler:
    return VoiceHandler()


# ==========================
# BROWSER TTS FALLBACK
# ==========================
def create_tts_audio(text: str) -> str:
    """
    Browser SpeechSynthesis fallback (used only if OpenAI TTS fails).
    """
    if not text:
        return ""

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
            console.error("Browser TTS failed", e);
        }}
    </script>
    """
