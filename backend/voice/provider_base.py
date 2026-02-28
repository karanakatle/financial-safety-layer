from abc import ABC, abstractmethod

class VoiceProvider(ABC):

    @abstractmethod
    def speech_to_text(self, audio_base64: str) -> dict:
        """
        Returns:
        {
          "text": "...",
          "language": "hi"
        }
        """
        pass

    @abstractmethod
    def text_to_speech(self, text: str, language: str) -> str:
        """
        Returns base64 encoded audio
        """
        pass