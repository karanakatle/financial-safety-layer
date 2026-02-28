from .provider_base import VoiceProvider

class BhashiniProvider(VoiceProvider):

    def speech_to_text(self, audio_base64):
        # call bhashini ASR
        pass

    def text_to_speech(self, text, language):
        # call bhashini TTS
        pass