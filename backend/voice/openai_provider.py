import base64
from openai import OpenAI
from .provider_base import VoiceProvider

client = OpenAI()

class OpenAIVoiceProvider(VoiceProvider):

    def speech_to_text(self, audio_base64: str):
        audio_bytes = base64.b64decode(audio_base64)

        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("speech.webm", audio_bytes)
        )
        # language may not be returned
        detected_language = getattr(transcript, "language", "unknown")

        return {
            "text": transcript.text,
            "language": detected_language
        }

    def text_to_speech(self, text: str, language: str):
        audio = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text
        )

        return base64.b64encode(audio.read()).decode("utf-8")