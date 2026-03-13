import base64
import os

from openai import OpenAI

from .provider_base import VoiceProvider


class OpenAIVoiceProvider(VoiceProvider):
    def __init__(self):
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenAI voice provider requires OPENAI_API_KEY to be set. "
                "Configure OPENAI_API_KEY or set VOICE_PROVIDER=bhashini."
            )

        self._client = OpenAI(api_key=api_key)
        return self._client

    def speech_to_text(self, audio_base64: str):
        audio_bytes = base64.b64decode(audio_base64)

        transcript = self._get_client().audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("speech.webm", audio_bytes),
        )
        # language may not be returned
        detected_language = getattr(transcript, "language", "unknown")

        return {"text": transcript.text, "language": detected_language}

    def text_to_speech(self, text: str, language: str):
        audio = self._get_client().audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )

        return base64.b64encode(audio.read()).decode("utf-8")
