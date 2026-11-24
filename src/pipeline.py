"""End-to-end notice summarization pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .analysis import analyze
from .checklist import build_checklist
from .errors import ValidationError
from .summarizer import extract_baseline, generate_summary
from .text_processing import split_sentences, word_count
from .validation import load_notice_file, validate_notice_text


class NoticePipeline:
    def __init__(self, config: dict) -> None:
        self.config = config

    def process_file(
        self,
        path: str | Path,
        *,
        notice_id: str | None = None,
        now: datetime | None = None,
        max_sentences: int | None = None,
        max_words: int | None = None,
    ) -> dict:
        text, source = load_notice_file(path, self.config)
        return self.process_text(
            text,
            source=source,
            notice_id=notice_id,
            now=now,
            max_sentences=max_sentences,
            max_words=max_words,
        )

    def process_text(
        self,
        text: str,
        *,
        source: str = "pasted-text",
        notice_id: str | None = None,
        now: datetime | None = None,
        max_sentences: int | None = None,
        max_words: int | None = None,
    ) -> dict:
        normalized = validate_notice_text(text, self.config)
        sentences = split_sentences(normalized)
        if not sentences:
            # Validation normally catches this; keep the pipeline safe.
            raise ValidationError("Notice did not contain any sentences.", field="text")
        analysis = analyze(normalized, sentences)
        summary_config = self.config["summarization"]
        sentence_limit = max_sentences or summary_config["max_sentences"]
        word_limit = max_words or summary_config["max_words"]
        baseline = extract_baseline(
            sentences,
            analysis,
            max_sentences=sentence_limit,
            max_words=word_limit,
        )
        summary = generate_summary(sentences, analysis, baseline)
        checklist = build_checklist(
            normalized,
            analysis,
            summary,
            max_words=word_limit,
        )
        timestamp = _utc_now(now)
        result = {
            "schema_version": 1,
            "notice_id": notice_id or make_notice_id(now),
            "source": source,
            "created_at": timestamp,
            "updated_at": timestamp,
            "input": {
                "text": normalized,
                "character_count": len(normalized),
                "word_count": word_count(normalized),
            },
            "sentences": sentences,
            "analysis": analysis,
            "baseline": baseline,
            "summary": summary,
            "checklist": checklist,
            "quality_status": checklist["quality_status"],
            "manual_override": False,
            "edits": [],
        }
        return result


def make_notice_id(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    return f"NTC-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def _utc_now(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
