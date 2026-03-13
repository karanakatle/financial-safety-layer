from unidecode import unidecode
import re


def normalize_text(text: str) -> str:
    """
    Normalize speech output into a lowercase Latin-friendly form.

    Current behavior:
    - Convert Unicode text to a closest Latin approximation via ``unidecode``.
    - Remove punctuation while keeping word characters and spaces.
    """

    # convert unicode → closest latin representation
    text = unidecode(text)

    # remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    return text.lower().strip()
