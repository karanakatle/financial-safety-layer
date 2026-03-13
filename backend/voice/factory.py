import os

def get_voice_provider():
    provider = os.getenv("VOICE_PROVIDER", "openai")

    if provider == "bhashini":
        from .bhashini_provider import BhashiniProvider

        return BhashiniProvider()

    from .openai_provider import OpenAIVoiceProvider

    return OpenAIVoiceProvider()
