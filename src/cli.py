"""Command-line interface for the classroom notice pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import PROJECT_ROOT
from .demo import run_demo
from .errors import AppError
from .service import build_service
from .validation import load_notice_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="Rule-based classroom notice summarization pipeline.",
    )
    parser.add_argument(
        "--store",
        default=str(PROJECT_ROOT / "var"),
        help="Directory for results and the failure log (default: var).",
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "config.json"),
        help="Configuration file (default: config.json).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize = subparsers.add_parser("summarize", help="Summarize one uploaded notice.")
    summarize.add_argument("notice", nargs="?", help="Path to a .txt or .md notice, or '-' for stdin.")
    summarize.add_argument("--text", default=None, help="Summarize pasted notice text instead of a file.")
    summarize.add_argument("--out", default=None, help="Optional path for the result JSON.")
    summarize.add_argument("--json", action="store_true", help="Print the full result JSON.")
    summarize.add_argument("--max-sentences", type=int, default=None)
    summarize.add_argument("--max-words", type=int, default=None)
    summarize.add_argument("--strict", action="store_true", help="Exit 1 if the checklist needs attention.")

    batch = subparsers.add_parser("batch", help="Summarize every .txt/.md notice in a directory.")
    batch.add_argument("directory", help="Directory of notices.")
    batch.add_argument("--out-dir", default=None, help="Optional directory for result JSON files.")
    batch.add_argument("--json", action="store_true", help="Print a JSON report.")

    validate = subparsers.add_parser("validate", help="Validate a notice file without summarizing it.")
    validate.add_argument("notice")

    checklist = subparsers.add_parser("checklist", help="Show the checklist stored in a result.")
    checklist.add_argument("result")

    edit = subparsers.add_parser("edit", help="Apply teacher overrides to a generated result.")
    edit.add_argument("result")
    edit.add_argument("--edits", required=True, help="JSON file containing summary overrides.")
    edit.add_argument("--actor", default="Teacher", help="Name recorded in the edit history.")
    edit.add_argument("--json", action="store_true", help="Print the full edited result JSON.")
    edit.add_argument("--strict", action="store_true", help="Exit 1 if the edited checklist needs attention.")

    failures = subparsers.add_parser("failures", help="Show recent logged failures.")
    failures.add_argument("--limit", type=int, default=20)
    failures.add_argument("--json", action="store_true")

    subparsers.add_parser("demo", help="Run the scripted demonstration.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        service = build_service(store_root=args.store, config_path=args.config)

        if args.command == "summarize":
            if args.text is not None:
                result, json_path, markdown_path = service.summarize_text(
                    args.text,
                    output_path=args.out,
                    max_sentences=args.max_sentences,
                    max_words=args.max_words,
                )
            elif args.notice == "-":
                text = sys.stdin.read()
                result, json_path, markdown_path = service.summarize_text(
                    text,
                    source="stdin",
                    output_path=args.out,
                    max_sentences=args.max_sentences,
                    max_words=args.max_words,
                )
            elif args.notice:
                result, json_path, markdown_path = service.summarize_file(
                    args.notice,
                    output_path=args.out,
                    max_sentences=args.max_sentences,
                    max_words=args.max_words,
                )
            else:
                parser.error("Provide a notice path, '-' or --text.")
                return 2
            _print_summarize_result(result, json_path, markdown_path, as_json=args.json)
            return 1 if args.strict and result["quality_status"] != "pass" else 0

        if args.command == "batch":
            directory = Path(args.directory)
            if not directory.is_dir():
                raise AppError(f"Batch path is not a directory: {directory.name}", field="directory")
            files = sorted(
                path for path in directory.iterdir()
                if path.is_file() and path.suffix.casefold() in {".txt", ".md"}
            )
            if not files:
                raise AppError("No .txt or .md notices found in the batch directory.", field="directory")
            rows: list[dict] = []
            for path in files:
                output_path = Path(args.out_dir) / f"{path.stem}.json" if args.out_dir else None
                result, json_path, _ = service.summarize_file(path, output_path=output_path)
                rows.append(
                    {
                        "source": result["source"],
                        "notice_id": result["notice_id"],
                        "quality_status": result["quality_status"],
                        "headline": result["summary"]["headline"],
                        "selected_sentences": result["baseline"]["selected_count"],
                        "failed_checks": [
                            check["id"] for check in result["checklist"]["checks"] if not check["passed"]
                        ],
                        "result": str(json_path),
                    }
                )
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                for row in rows:
                    print(
                        f"{row['quality_status']:>15} | {row['source']} | "
                        f"{row['headline']} | {row['selected_sentences']} sentences"
                    )
            return 0

        if args.command == "validate":
            text, source = load_notice_file(args.notice, service.config)
            print(
                json.dumps(
                    {
                        "valid": True,
                        "source": source,
                        "characters": len(text),
                        "paragraphs": len([part for part in text.split("\n\n") if part.strip()]),
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "checklist":
            result = service.store.load_result(args.result)
            print(json.dumps(result.get("checklist", {}), indent=2))
            return 0 if result.get("checklist", {}).get("passed") else 1

        if args.command == "edit":
            edits = _load_json_object(Path(args.edits))
            updated, json_path, markdown_path = service.edit_result(
                args.result,
                edits,
                actor=args.actor,
            )
            if args.json:
                print(json.dumps(updated, indent=2, ensure_ascii=False))
            else:
                _print_summary(updated)
                print(f"\nEdited result: {json_path}")
                print(f"Edited Markdown: {markdown_path}")
            return 1 if args.strict and updated["quality_status"] != "pass" else 0

        if args.command == "failures":
            records = service.failures(limit=args.limit)
            if args.json:
                print(json.dumps(records, indent=2))
            elif not records:
                print("No failures logged.")
            else:
                for record in records:
                    print(
                        f"{record.get('timestamp_utc')} | {record.get('event')} | "
                        f"{record.get('notice_id')} | {record.get('quality_status')} | "
                        f"{', '.join(record.get('failed_checks', []))}"
                    )
            return 0

        if args.command == "demo":
            return run_demo(service)

        parser.error(f"Unknown command: {args.command}")
        return 2
    except AppError as exc:
        print(json.dumps(exc.to_dict(), indent=2), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"error": {"type": "io_error", "message": str(exc)}}, indent=2), file=sys.stderr)
        return 2


def _print_summarize_result(
    result: dict,
    json_path: Path,
    markdown_path: Path,
    *,
    as_json: bool,
) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    _print_summary(result)
    print(f"\nQuality: {result['quality_status']}")
    for check in result["checklist"]["checks"]:
        if not check["passed"]:
            print(f"  FAIL: {check['label']} — {check['detail']}")
    for suggestion in result["checklist"]["missing_details"]:
        print(f"  SUGGEST: {suggestion}")
    print(f"\nResult JSON: {json_path}")
    print(f"Result Markdown: {markdown_path}")


def _print_summary(result: dict) -> None:
    print(result["summary"]["rendered"])
    print(f"Baseline: {result['baseline']['selected_count']} extractive sentences "
          f"({result['baseline']['word_count']} words)")
    if result["baseline"]["limit_exceeded"]:
        print("Note: mandatory preservation exceeded the configured summary limits.")


def _load_json_object(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AppError(f"JSON file not found: {path.name}", field="edits") from None
    except OSError as exc:
        raise AppError(f"Could not read JSON file: {path.name}", details=str(exc)) from None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AppError(
            f"JSON file is not valid: {path.name}",
            details=f"line {exc.lineno}, column {exc.colno}",
        ) from None
    if not isinstance(payload, dict):
        raise AppError(f"JSON file must contain an object: {path.name}", field="edits")
    return payload
