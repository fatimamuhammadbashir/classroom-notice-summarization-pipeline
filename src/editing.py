"""Teacher overrides and edits for generated summaries."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from .checklist import build_checklist
from .errors import EditError
from .summarizer import render_summary
from .text_processing import word_count

EDITABLE_FIELDS = (
    "headline",
    "audience",
    "sentences",
    "key_dates",
    "critical_instructions",
    "actions",
    "next_steps",
)


def utc_now_iso(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def apply_edits(
    result: dict,
    edits: dict,
    *,
    actor: str = "Teacher",
    now: datetime | None = None,
    max_words: int = 180,
) -> dict:
    if not isinstance(result, dict) or not isinstance(result.get("summary"), dict):
        raise EditError("This result does not contain a generated summary.")
    if not isinstance(edits, dict):
        raise EditError("Edits must be a JSON object.")

    allowed = set(EDITABLE_FIELDS) | {"note"}
    unknown = sorted(set(edits) - allowed)
    if unknown:
        raise EditError(
            f"Unknown edit field: {unknown[0]}",
            field=unknown[0],
            details={"allowed_fields": sorted(allowed)},
        )
    changed_fields = [field for field in EDITABLE_FIELDS if field in edits]
    if not changed_fields:
        raise EditError(
            "Provide at least one summary field to edit.",
            field="$",
            details={"allowed_fields": list(EDITABLE_FIELDS)},
        )

    actor = _text(actor, "actor", 100)
    note = _optional_text(edits.get("note", ""), "note", 500)
    updated = copy.deepcopy(result)
    summary = updated["summary"]

    if "headline" in edits:
        summary["headline"] = _text(edits["headline"], "headline", 240)
    if "audience" in edits:
        summary["audience"] = _text_list(edits["audience"], "audience", 10, allow_empty=True)
    if "sentences" in edits:
        values = _text_list(edits["sentences"], "sentences", 20, allow_empty=False)
        summary["sentences"] = [
            {
                "sentence_id": None,
                "text": value,
                "score": None,
                "mandatory": False,
                "manual": True,
            }
            for value in values
        ]
    for field in ("key_dates", "critical_instructions", "actions", "next_steps"):
        if field in edits:
            summary[field] = _text_list(edits[field], field, 30, allow_empty=True)

    summary["word_count"] = sum(
        word_count(item["text"] if isinstance(item, dict) else str(item))
        for item in summary.get("sentences", [])
    )
    summary["rendered"] = render_summary(summary)

    timestamp = utc_now_iso(now)
    updated["updated_at"] = timestamp
    updated["manual_override"] = True
    updated.setdefault("edits", []).append(
        {
            "timestamp_utc": timestamp,
            "actor": actor,
            "note": note,
            "fields": changed_fields,
        }
    )

    checklist = build_checklist(
        updated.get("input", {}).get("text", ""),
        updated.get("analysis", {}),
        summary,
        max_words=max_words,
    )
    updated["checklist"] = checklist
    updated["quality_status"] = checklist["quality_status"]
    return updated


def _text(value: object, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EditError(f"{field} must be a non-empty string.", field=field)
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise EditError(f"{field} must be {max_length} characters or fewer.", field=field)
    return cleaned


def _optional_text(value: object, field: str, max_length: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise EditError(f"{field} must be a string.", field=field)
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise EditError(f"{field} must be {max_length} characters or fewer.", field=field)
    return cleaned


def _text_list(
    value: object,
    field: str,
    max_items: int,
    *,
    allow_empty: bool,
) -> list[str]:
    if not isinstance(value, list):
        raise EditError(f"{field} must be a list of strings.", field=field)
    if not value and not allow_empty:
        raise EditError(f"{field} must not be empty.", field=field)
    if len(value) > max_items:
        raise EditError(f"{field} must contain at most {max_items} items.", field=field)
    cleaned: list[str] = []
    for index, item in enumerate(value):
        text = _text(item, f"{field}[{index}]", 800)
        if text not in cleaned:
            cleaned.append(text)
    return cleaned
