import os
from .openai_provider import OpenAIVoiceProvider
from .bhashini_provider import BhashiniProvider

def get_voice_provider():
    provider = os.getenv("VOICE_PROVIDER", "openai")

    if provider == "bhashini":
        return BhashiniProvider()

    return OpenAIVoiceProvider()