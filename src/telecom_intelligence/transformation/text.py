"""Controlled text normalization for display and matching fields."""

import re
import unicodedata


def normalize_display_text(value: str) -> str:
    """Normalize Unicode and whitespace while preserving accents and letter case."""
    normalized = unicodedata.normalize("NFC", value)
    without_invisible = "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in {"Cf", "Cc"} or character in "\t\n\r"
    )
    return re.sub(r"\s+", " ", without_invisible).strip()


def matching_key(value: str) -> str:
    """Create a deterministic ASCII key without changing the display value."""
    display = normalize_display_text(value).casefold()
    decomposed = unicodedata.normalize("NFKD", display)
    ascii_value = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", ascii_value)).strip("_")
