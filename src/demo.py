"""Scripted demonstration of the notice summarization pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .config import PROJECT_ROOT
from .service import NoticeService


def run_demo(
    service: NoticeService,
    *,
    data_dir: str | Path | None = None,
    output: Callable[[str], None] = print,
) -> int:
    data_path = Path(data_dir) if data_dir else PROJECT_ROOT / "data"
    notices = data_path / "notices"
    output("CLASSROOM NOTICE SUMMARIZATION - DEMO")
    output("=" * 56)
    output("Rule-based extractive summarization. No API keys are used.")
    output("")

    output("1. COMPLETE NOTICE: EXTRACTIVE SUMMARY + CHECKLIST")
    output("-" * 56)
    result, json_path, markdown_path = service.summarize_file(
        notices / "year7_museum_visit.txt"
    )
    output(f"Source: {result['source']}")
    output(f"Notice ID: {result['notice_id']}")
    output(f"Headline: {result['summary']['headline']}")
    output(f"Selected sentences: {result['baseline']['selected_count']} / {result['baseline']['max_sentences']}")
    output(f"Quality: {result['quality_status']}")
    output("")
    output(result["summary"]["rendered"])
    _print_checklist(result, output)
    output(f"Result JSON: {_display_path(json_path)}")
    output(f"Result Markdown: {_display_path(markdown_path)}")
    output("")

    output("2. INCOMPLETE NOTICE: CHECKLIST SUGGESTIONS")
    output("-" * 56)
    incomplete, _, _ = service.summarize_file(notices / "incomplete_notice.txt")
    output(f"Source: {incomplete['source']}")
    output(f"Quality: {incomplete['quality_status']}")
    _print_checklist(incomplete, output)
    output("")

    output("3. RELATIVE DATE: SPECIFICITY WARNING")
    output("-" * 56)
    relative, _, _ = service.summarize_file(notices / "relative_date_notice.txt")
    output(f"Source: {relative['source']}")
    output(f"Quality: {relative['quality_status']}")
    _print_checklist(relative, output)
    output("")

    output("4. TEACHER EDIT: OVERRIDE GENERATED OUTPUT")
    output("-" * 56)
    edits = json.loads((data_path / "sample_edits.json").read_text(encoding="utf-8"))
    edited, edited_json, _ = service.edit_result(
        json_path,
        edits,
        actor="Ms. Rivera",
    )
    output(f"Edited quality: {edited['quality_status']}")
    output(f"New headline: {edited['summary']['headline']}")
    output(f"Edit history: {len(edited.get('edits', []))} change(s)")
    output(f"Edited result: {_display_path(edited_json)}")
    output("")

    output("5. OVERRIDE THAT REMOVES A DATE: FAILURE IS LOGGED")
    output("-" * 56)
    override = json.loads(
        (data_path / "override_removing_date.json").read_text(encoding="utf-8")
    )
    overridden, _, _ = service.edit_result(
        edited_json,
        override,
        actor="Ms. Rivera",
    )
    output(f"Quality after override: {overridden['quality_status']}")
    _print_checklist(overridden, output)
    failures = service.failures(limit=3)
    output(f"Failure log entries available: {len(failures)}")
    output(f"Failure log: {_display_path(service.store.failure_log)}")
    output("")

    output("DEMO COMPLETE")
    output("The generated baseline is extractive; teacher edits are recorded separately.")
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _print_checklist(result: dict, output: Callable[[str], None]) -> None:
    checklist = result["checklist"]
    output("Checklist:")
    for check in checklist["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        output(f"  [{status}] {check['label']}: {check['detail']}")
    if checklist["missing_details"]:
        output("Suggested missing details:")
        for suggestion in checklist["missing_details"]:
            output(f"  - {suggestion}")
