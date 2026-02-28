from indic_transliteration.sanscript import transliterate, DEVANAGARI, ITRANS
from unidecode import unidecode
import re

from unidecode import unidecode
import re

def normalize_text(text: str) -> str:
    """
    Normalize multilingual speech output into Latin-friendly form.
    Handles:
    - Hindi (Devanagari)
    - Urdu (Arabic script)
    - Hinglish
    """

    # convert unicode → closest latin representation
    text = unidecode(text)

    # remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    return text.lower().strip()