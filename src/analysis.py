"""Rule-based extraction of audience, dates, actions and instructions."""

from __future__ import annotations

import re
from datetime import date
from typing import Iterable

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
WEEKDAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
MONTH_PATTERN = "|".join(MONTHS)
DATE_PATTERN = "|".join(
    [
        rf"\b(?:{WEEKDAYS})\s+\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTH_PATTERN})\s+\d{{4}}\b",
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTH_PATTERN})\s+\d{{4}}\b",
        rf"\b(?:{MONTH_PATTERN})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    ]
)
RELATIVE_DATE_PATTERN = rf"\b(?:today|tomorrow|tonight|(?:this|next)\s+(?:{WEEKDAYS}|week|month|morning|afternoon|evening))\b"
TIME_PATTERN = r"\b(?:\d{1,2}(?::\d{2})?\s?(?:am|pm)|noon|midday|midnight)\b"

DATE_RE = re.compile(DATE_PATTERN, re.IGNORECASE)
RELATIVE_DATE_RE = re.compile(RELATIVE_DATE_PATTERN, re.IGNORECASE)
TIME_RE = re.compile(TIME_PATTERN, re.IGNORECASE)

AUDIENCE_PATTERNS = [
    r"\bparents?\b",
    r"\bguardians?\b",
    r"\bcarers?\b",
    r"\bfamilies\b",
    r"\bstudents?\b",
    r"\bpupils?\b",
    r"\bteachers?\b",
    r"\bstaff\b",
    r"\bYear\s+\d+\b",
    r"\bclass\s+[A-Z0-9]+\b",
]

CRITICAL_CUES = [
    "must not",
    "must",
    "required",
    "need to",
    "needs to",
    "ensure",
    "do not",
    "no later than",
    "deadline",
    "urgent",
    "important",
    "only",
    "not allowed",
    "permission",
]

ACTION_CUES = [
    "bring",
    "return",
    "submit",
    "sign",
    "pay",
    "complete",
    "arrive",
    "collect",
    "register",
    "book",
    "download",
    "wear",
    "pack",
    "label",
    "contact",
    "inform",
    "reply",
    "attend",
    "meet",
    "check",
    "send",
    "buy",
    "sign in",
    "pick up",
    "drop off",
]


def find_dates(sentences: list[dict]) -> list[dict]:
    mentions: list[dict] = []
    for sentence in sentences:
        candidates: list[tuple[int, int, str, str]] = []
        for match in DATE_RE.finditer(sentence["text"]):
            candidates.append((match.start(), match.end(), match.group(0), "date"))
        for match in RELATIVE_DATE_RE.finditer(sentence["text"]):
            candidates.append((match.start(), match.end(), match.group(0), "relative"))
        candidates.sort(key=lambda item: (-(item[1] - item[0]), item[0]))
        chosen: list[tuple[int, int, str, str]] = []
        for candidate in candidates:
            start, end, _, _ = candidate
            if any(start < existing[1] and end > existing[0] for existing in chosen):
                continue
            chosen.append(candidate)
        for start, end, text, kind in sorted(chosen, key=lambda item: item[0]):
            normalized = normalize_date(text) if kind == "date" else None
            mentions.append(
                {
                    "text": text,
                    "kind": kind,
                    "sentence_id": sentence["sentence_id"],
                    "position": start,
                    "sentence": sentence["text"],
                    "normalized": normalized,
                    "specific": normalized is not None,
                }
            )
    return mentions


def find_times(sentences: list[dict]) -> list[dict]:
    mentions: list[dict] = []
    for sentence in sentences:
        for match in TIME_RE.finditer(sentence["text"]):
            mentions.append(
                {
                    "text": match.group(0),
                    "kind": "time",
                    "sentence_id": sentence["sentence_id"],
                    "position": match.start(),
                    "sentence": sentence["text"],
                    "normalized": None,
                    "specific": True,
                }
            )
    return mentions


def normalize_date(text: str) -> str | None:
    cleaned = re.sub(rf"\b(?:{WEEKDAYS})\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"(\d)(?:st|nd|rd|th)", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")

    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
            return date.fromisoformat(cleaned).isoformat()
    except ValueError:
        return None

    match = re.fullmatch(rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(\d{{4}})", cleaned, re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        return _safe_iso(int(year), MONTHS[month_name.lower()], int(day))

    match = re.fullmatch(
        rf"({MONTH_PATTERN})\s+(\d{{1,2}}),?\s+(\d{{4}})",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        month_name, day, year = match.groups()
        return _safe_iso(int(year), MONTHS[month_name.lower()], int(day))

    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", cleaned)
    if match:
        day, month, year = match.groups()
        year_number = int(year)
        if year_number < 100:
            year_number += 2000
        return _safe_iso(year_number, int(month), int(day))

    return None


def _safe_iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def find_audience(sentences: list[dict]) -> list[dict]:
    matches: list[dict] = []
    seen: set[str] = set()
    for sentence in sentences:
        for pattern in AUDIENCE_PATTERNS:
            for match in re.finditer(pattern, sentence["text"], re.IGNORECASE):
                text = match.group(0)
                key = text.casefold()
                if key in seen:
                    continue
                seen.add(key)
                matches.append(
                    {
                        "text": text,
                        "sentence_id": sentence["sentence_id"],
                    }
                )
    return matches


def find_actions(sentences: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for sentence in sentences:
        if sentence.get("is_heading"):
            continue
        lower = sentence["text"].casefold()
        cue = next((item for item in ACTION_CUES if re.search(rf"\b{re.escape(item)}\b", lower)), None)
        if cue:
            actions.append(
                {
                    "text": sentence["text"],
                    "sentence_id": sentence["sentence_id"],
                    "cue": cue,
                }
            )
    return actions


def find_critical_instructions(
    sentences: list[dict],
    dates: list[dict],
    times: list[dict],
) -> list[dict]:
    temporal_sentence_ids = {item["sentence_id"] for item in dates + times}
    instructions: list[dict] = []
    for sentence in sentences:
        if sentence.get("is_heading"):
            continue
        lower = sentence["text"].casefold()
        strong_cue = next(
            (cue for cue in CRITICAL_CUES if re.search(rf"\b{re.escape(cue)}\b", lower)),
            None,
        )
        action_cue = next(
            (cue for cue in ACTION_CUES if re.search(rf"\b{re.escape(cue)}\b", lower)),
            None,
        )
        deadline_cue = next(
            (
                cue
                for cue in ("by", "no later than", "deadline")
                if re.search(rf"\b{re.escape(cue)}\b", lower)
            ),
            None,
        )
        if strong_cue:
            instructions.append(
                {
                    "text": sentence["text"],
                    "sentence_id": sentence["sentence_id"],
                    "cue": strong_cue,
                    "reason": f"contains '{strong_cue}'",
                }
            )
        elif action_cue and (
            sentence["sentence_id"] in temporal_sentence_ids or deadline_cue is not None
        ):
            instructions.append(
                {
                    "text": sentence["text"],
                    "sentence_id": sentence["sentence_id"],
                    "cue": action_cue,
                    "reason": f"action '{action_cue}' with a date or deadline",
                }
            )
    return instructions


def find_next_step(actions: list[dict], dates: list[dict], times: list[dict]) -> dict | None:
    if not actions:
        return None
    temporal_ids = {item["sentence_id"] for item in dates + times}
    priority_cues = (
        "return the",
        "return your",
        "submit",
        "sign",
        "pay",
        "payment",
        "complete",
        "register",
        "book",
        "reply",
    )
    for cue in priority_cues:
        for action in actions:
            lower = action["text"].casefold()
            if cue in lower and (
                action["sentence_id"] in temporal_ids
                or re.search(r"\b(?:by|no later than|deadline)\b", lower)
            ):
                return action
    for action in actions:
        lower = action["text"].casefold()
        if re.search(r"\b(?:by|no later than|deadline)\b", lower):
            return action
    for action in actions:
        if action["sentence_id"] in temporal_ids:
            return action
    return actions[0]


def analyze(text: str, sentences: list[dict]) -> dict:
    dates = find_dates(sentences)
    times = find_times(sentences)
    audience = find_audience(sentences)
    actions = find_actions(sentences)
    critical = find_critical_instructions(sentences, dates, times)
    next_step = find_next_step(actions, dates, times)
    temporal_mentions = dates + times
    return {
        "audience": audience,
        "dates": dates,
        "times": times,
        "temporal_mentions": temporal_mentions,
        "actions": actions,
        "critical_instructions": critical,
        "next_step": next_step,
        "has_relative_dates": any(item["kind"] == "relative" for item in dates),
        "sentence_count": len(sentences),
    }


def unique_texts(items: Iterable[dict]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item["text"]
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result
