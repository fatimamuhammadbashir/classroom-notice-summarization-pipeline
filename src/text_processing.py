"""Text normalization, sentence splitting and matching helpers."""

from __future__ import annotations

import re

_ABBREVIATIONS = ("Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "No.", "e.g.", "i.e.")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def normalize_text(raw: str) -> str:
    if not isinstance(raw, str):
        raise TypeError("Notice text must be a string.")
    text = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[dict]:
    """Split paragraphs into sentence records without paraphrasing."""

    sentences: list[dict] = []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    for paragraph_index, paragraph in enumerate(paragraphs):
        joined = " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
        protected = joined
        placeholders: dict[str, str] = {}
        for index, abbreviation in enumerate(_ABBREVIATIONS):
            marker = f"__ABBR{index}__"
            placeholders[marker] = abbreviation
            protected = protected.replace(abbreviation, marker)
        parts = _SENTENCE_SPLIT.split(protected)
        for part in parts:
            for marker, abbreviation in placeholders.items():
                part = part.replace(marker, abbreviation)
            cleaned = re.sub(r"\s+", " ", part).strip()
            if not cleaned:
                continue
            sentences.append(
                {
                    "sentence_id": len(sentences) + 1,
                    "paragraph": paragraph_index + 1,
                    "text": cleaned,
                    "word_count": word_count(cleaned),
                    "is_heading": (
                        len(sentences) == 0
                        and not cleaned.endswith((".", "!", "?"))
                        and word_count(cleaned) <= 14
                    ),
                }
            )
    return sentences


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9£$%]+(?:['’-][A-Za-z0-9]+)*", text))


def normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def contains_mention(haystack: str, needle: str) -> bool:
    return normalize_for_match(needle) in normalize_for_match(haystack)


def truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(".,;:") + "…"


def title_from_sentences(sentences: list[dict]) -> str:
    if not sentences:
        return "Classroom notice"
    first = sentences[0]["text"]
    if first.endswith((".", "!", "?")) or len(first) > 110:
        return truncate_words(first, 12)
    return first
