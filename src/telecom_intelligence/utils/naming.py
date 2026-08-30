"""Consistent naming helpers for source schemas."""

import re
import unicodedata


def to_snake_case(value: str) -> str:
    """Convert a source label to stable ASCII snake_case."""
    normalized = unicodedata.normalize("NFKD", value.strip())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    words = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_")
    return re.sub(r"_+", "_", words).lower()
