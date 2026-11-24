"""Accuracy checklist and missing-detail suggestions."""

from __future__ import annotations

from .summarizer import summary_sentences_as_text
from .text_processing import contains_mention, normalize_for_match, word_count


def build_checklist(
    source_text: str,
    analysis: dict,
    summary: dict,
    *,
    max_words: int = 180,
) -> dict:
    rendered = summary.get("rendered") or ""
    source_dates = _unique_texts(
        [item["text"] for item in analysis.get("temporal_mentions", [])]
    )
    source_critical = _unique_texts(
        [item["text"] for item in analysis.get("critical_instructions", [])]
    )
    date_hits = [item for item in source_dates if contains_mention(rendered, item)]
    missing_dates = [item for item in source_dates if item not in date_hits]
    critical_hits = [item for item in source_critical if contains_mention(rendered, item)]
    missing_critical = [item for item in source_critical if item not in critical_hits]
    summary_sentences = summary_sentences_as_text(summary)
    source_normalized = normalize_for_match(source_text)
    extractive = all(
        normalize_for_match(sentence) in source_normalized for sentence in summary_sentences
    )
    relative_dates = [
        item["text"]
        for item in analysis.get("dates", [])
        if item.get("kind") == "relative"
    ]

    checks: list[dict] = []

    def add(
        check_id: str,
        label: str,
        passed: bool,
        detail: str,
        *,
        required: bool = True,
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "label": label,
                "passed": bool(passed),
                "required": required,
                "detail": detail,
            }
        )

    audience_present = bool(analysis.get("audience")) and bool(summary.get("audience"))
    add(
        "audience",
        "Audience is clear",
        audience_present,
        (
            "Audience: " + ", ".join(summary.get("audience", []))
            if audience_present
            else "The intended audience is missing from the notice or summary."
        ),
    )

    date_present = bool(source_dates) and not missing_dates
    add(
        "date",
        "All dates and times are preserved",
        date_present,
        (
            f"{len(date_hits)} of {len(source_dates)} temporal mentions preserved."
            if source_dates
            else "No date or time was found in the notice."
        )
        + (f" Missing: {', '.join(missing_dates)}." if missing_dates else ""),
    )

    action_present = bool(analysis.get("actions")) and bool(summary.get("actions"))
    add(
        "action",
        "Action is clear",
        action_present,
        (
            "At least one action is identified."
            if action_present
            else "No clear action from the reader was found."
        ),
    )

    next_step_present = bool(analysis.get("next_step")) and bool(summary.get("next_steps"))
    add(
        "next_step",
        "Next step is clear",
        next_step_present,
        (
            "A next step is included."
            if next_step_present
            else "Add a clear next step: who should do what, and by when."
        ),
    )

    critical_preserved = not missing_critical
    add(
        "critical_instructions",
        "Critical instructions are preserved",
        critical_preserved,
        (
            f"{len(critical_hits)} of {len(source_critical)} critical instructions preserved."
            if source_critical
            else "No critical instruction cues were detected."
        )
        + (f" Missing: {' | '.join(missing_critical)}" if missing_critical else ""),
    )

    date_specific = bool(analysis.get("dates")) and not relative_dates
    add(
        "specific_dates",
        "Dates are specific",
        date_specific,
        (
            "All date references are calendar dates."
            if date_specific
            else "Relative date(s) found: " + ", ".join(relative_dates)
            if relative_dates
            else "No specific date was found."
        ),
    )

    add(
        "extractive",
        "Baseline stays extractive",
        extractive,
        (
            "Summary sentences are copied from the notice."
            if extractive
            else "The summary contains manually edited text; verify it against the source."
        ),
        required=False,
    )

    target = summary.get("word_count")
    if not isinstance(target, int):
        target = word_count(summary.get("rendered") or "")
    add(
        "length",
        "Baseline length is controlled",
        target <= max_words,
        f"{target} summary words; limit {max_words}.",
        required=False,
    )

    missing_details: list[str] = []
    if not audience_present:
        missing_details.append("Add the intended audience, for example parents of Year 7.")
    if not source_dates:
        missing_details.append("Add at least one specific date or deadline.")
    if missing_dates:
        missing_details.append("Keep every source date in the summary: " + "; ".join(missing_dates))
    if relative_dates:
        missing_details.append(
            "Replace relative date(s) with calendar dates: " + ", ".join(relative_dates)
        )
    if not action_present:
        missing_details.append("Add the action required from the reader.")
    if not next_step_present:
        missing_details.append("Add a clear next step: who should do what, and by when.")
    if missing_critical:
        missing_details.append(
            "Keep the critical instruction(s): " + "; ".join(missing_critical)
        )
    if not extractive:
        missing_details.append(
            "The edited summary includes new text; check it against the original notice."
        )

    required_checks = [check for check in checks if check["required"]]
    passed = all(check["passed"] for check in required_checks)
    return {
        "passed": passed,
        "quality_status": "pass" if passed else "needs_attention",
        "checks": checks,
        "missing_details": missing_details,
        "summary_word_count": target,
    }


def _unique_texts(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = normalize_for_match(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result
