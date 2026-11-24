"""Extractive baseline and structured summary generation."""

from __future__ import annotations

import math
import re

from .analysis import unique_texts
from .text_processing import title_from_sentences, word_count

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "is",
    "it",
    "may",
    "of",
    "on",
    "or",
    "our",
    "please",
    "should",
    "students",
    "the",
    "their",
    "this",
    "to",
    "will",
    "with",
    "you",
    "your",
}


def content_tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9£$%]+", text.casefold())
    return [word for word in words if word not in STOPWORDS and len(word) > 1]


def extract_baseline(
    sentences: list[dict],
    analysis: dict,
    *,
    max_sentences: int = 5,
    max_words: int = 180,
) -> dict:
    """Select source sentences using deterministic rules; never paraphrase."""

    frequencies: dict[str, int] = {}
    for sentence in sentences:
        for token in content_tokens(sentence["text"]):
            frequencies[token] = frequencies.get(token, 0) + 1

    date_sentence_ids = {
        item["sentence_id"] for item in analysis["dates"] + analysis["times"]
    }
    critical_sentence_ids = {
        item["sentence_id"] for item in analysis["critical_instructions"]
    }
    action_sentence_ids = {item["sentence_id"] for item in analysis["actions"]}
    audience_sentence_ids = {item["sentence_id"] for item in analysis["audience"]}
    next_step_id = analysis["next_step"]["sentence_id"] if analysis["next_step"] else None

    scored: list[dict] = []
    for index, sentence in enumerate(sentences):
        if sentence.get("is_heading"):
            continue
        tokens = content_tokens(sentence["text"])
        keyword_score = sum(frequencies.get(token, 0) for token in tokens) / math.sqrt(
            max(1, len(tokens))
        )
        position_score = 2.0 if index == 0 else 1.0 if index == 1 else 0.5 if index == len(sentences) - 1 else 0.0
        temporal_score = 2.5 if sentence["sentence_id"] in date_sentence_ids else 0.0
        critical_score = 3.0 if sentence["sentence_id"] in critical_sentence_ids else 0.0
        action_score = 1.5 if sentence["sentence_id"] in action_sentence_ids else 0.0
        audience_score = 1.0 if sentence["sentence_id"] in audience_sentence_ids else 0.0
        length_score = _length_score(sentence["word_count"])
        mandatory = (
            sentence["sentence_id"] in date_sentence_ids
            or sentence["sentence_id"] in critical_sentence_ids
            or sentence["sentence_id"] == next_step_id
        )
        score = round(
            keyword_score
            + position_score
            + temporal_score
            + critical_score
            + action_score
            + audience_score
            + length_score,
            4,
        )
        scored.append(
            {
                "sentence_id": sentence["sentence_id"],
                "text": sentence["text"],
                "word_count": sentence["word_count"],
                "score": score,
                "mandatory": mandatory,
                "breakdown": {
                    "keyword": round(keyword_score, 4),
                    "position": position_score,
                    "temporal": temporal_score,
                    "critical": critical_score,
                    "action": action_score,
                    "audience": audience_score,
                    "length": length_score,
                },
            }
        )

    mandatory_items = [item for item in scored if item["mandatory"]]
    optional_items = sorted(
        (item for item in scored if not item["mandatory"]),
        key=lambda item: (-item["score"], item["sentence_id"]),
    )

    selected = list(mandatory_items)
    selected_word_count = sum(item["word_count"] for item in selected)
    for item in optional_items:
        if len(selected) >= max_sentences:
            break
        if selected_word_count + item["word_count"] > max_words:
            continue
        selected.append(item)
        selected_word_count += item["word_count"]

    selected.sort(key=lambda item: item["sentence_id"])
    selected_word_count = sum(item["word_count"] for item in selected)
    limit_exceeded = len(selected) > max_sentences or selected_word_count > max_words

    return {
        "method": "rule-based-extractive-v1",
        "max_sentences": max_sentences,
        "max_words": max_words,
        "selected_count": len(selected),
        "mandatory_count": len(mandatory_items),
        "word_count": selected_word_count,
        "limit_exceeded": limit_exceeded,
        "sentences": selected,
        "candidate_scores": sorted(scored, key=lambda item: (-item["score"], item["sentence_id"])),
    }


def generate_summary(sentences: list[dict], analysis: dict, baseline: dict) -> dict:
    """Format the extractive baseline into a structured, editable draft."""

    temporal = sorted(
        analysis["temporal_mentions"],
        key=lambda item: (item["sentence_id"], item.get("position", 0)),
    )
    key_dates = _unique_texts([item["text"] for item in temporal])
    critical = unique_texts(analysis["critical_instructions"])
    actions = unique_texts(analysis["actions"])
    audience = unique_texts(analysis["audience"])
    next_steps = [analysis["next_step"]["text"]] if analysis["next_step"] else []
    summary_sentences = [
        {
            "sentence_id": item["sentence_id"],
            "text": item["text"],
            "score": item["score"],
            "mandatory": item["mandatory"],
            "manual": False,
        }
        for item in baseline["sentences"]
    ]
    summary = {
        "headline": title_from_sentences(sentences),
        "audience": audience,
        "sentences": summary_sentences,
        "key_dates": key_dates,
        "critical_instructions": critical,
        "actions": actions,
        "next_steps": next_steps,
        "word_count": baseline["word_count"],
        "generator": "rule-based-extractive-v1",
    }
    summary["rendered"] = render_summary(summary)
    return summary


def render_summary(summary: dict) -> str:
    lines: list[str] = [summary.get("headline") or "Classroom notice", ""]
    audience = summary.get("audience") or []
    lines.append("Audience: " + (", ".join(audience) if audience else "Not specified."))
    lines.append("")

    sentences = summary.get("sentences") or []
    if sentences:
        lines.append("Summary:")
        for item in sentences:
            text = item["text"] if isinstance(item, dict) else str(item)
            lines.append(f"- {text}")
        lines.append("")

    key_dates = summary.get("key_dates") or []
    if key_dates:
        lines.append("Key dates and times:")
        for item in key_dates:
            lines.append(f"- {item}")
        lines.append("")

    critical = summary.get("critical_instructions") or []
    if critical:
        lines.append("Critical instructions:")
        for item in critical:
            lines.append(f"- {item}")
        lines.append("")

    actions = summary.get("actions") or []
    if actions:
        lines.append("Actions:")
        for item in actions:
            lines.append(f"- {item}")
        lines.append("")

    next_steps = summary.get("next_steps") or []
    if next_steps:
        lines.append("Next step:")
        for item in next_steps:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def summary_sentences_as_text(summary: dict) -> list[str]:
    result: list[str] = []
    for item in summary.get("sentences", []):
        text = item["text"] if isinstance(item, dict) else str(item)
        if text.strip():
            result.append(text.strip())
    return result


def _length_score(word_count_value: int) -> float:
    if 8 <= word_count_value <= 30:
        return 1.0
    if 5 <= word_count_value <= 45:
        return 0.4
    if word_count_value < 5:
        return -2.0
    return -1.0


def _unique_texts(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = re.sub(r"\s+", " ", item).strip().casefold()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result
