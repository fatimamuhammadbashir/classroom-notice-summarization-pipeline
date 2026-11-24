"""Safe result storage, Markdown export and failure logging."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import PROJECT_ROOT
from .errors import StorageError

NOTICE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")


class ResultStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else PROJECT_ROOT / "var"
        self.results_dir = self.root / "results"
        self.failure_log = self.root / "logs" / "failures.jsonl"

    def save_result(self, result: dict, path: str | Path | None = None) -> Path:
        if not isinstance(result, dict):
            raise StorageError("Result must be an object.")
        notice_id = self._notice_id(result.get("notice_id"))
        target = Path(path) if path else self.results_dir / f"{notice_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            temporary.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, target)
        except OSError as exc:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass
            raise StorageError(
                f"Could not save result: {target.name}",
                details=str(exc),
            ) from None
        return target

    def save_markdown(self, result: dict, path: str | Path | None = None) -> Path:
        notice_id = self._notice_id(result.get("notice_id"))
        target = Path(path) if path else self.results_dir / f"{notice_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        summary = result.get("summary", {})
        header = (
            f"# {summary.get('headline', 'Classroom notice')}\n\n"
            f"- Notice ID: `{notice_id}`\n"
            f"- Source: `{result.get('source', 'unknown')}`\n"
            f"- Quality: **{result.get('quality_status', 'unknown')}**\n\n"
        )
        try:
            target.write_text(header + summary.get("rendered", ""), encoding="utf-8")
        except OSError as exc:
            raise StorageError(
                f"Could not save Markdown: {target.name}",
                details=str(exc),
            ) from None
        return target

    def load_result(self, path: str | Path) -> dict:
        result_path = Path(path)
        try:
            text = result_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise StorageError(
                f"Result file not found: {result_path.name}",
                field="result",
            ) from None
        except OSError as exc:
            raise StorageError(
                f"Could not read result: {result_path.name}",
                details=str(exc),
            ) from None
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"Result file is not valid JSON: {result_path.name}",
                details=f"line {exc.lineno}, column {exc.colno}",
            ) from None
        if not isinstance(result, dict):
            raise StorageError(f"Result file is not an object: {result_path.name}")
        return result

    def append_failure(self, result: dict, *, event: str, actor: str | None = None) -> None:
        checklist = result.get("checklist", {})
        record = {
            "timestamp_utc": _utc_now(),
            "notice_id": result.get("notice_id"),
            "source": result.get("source"),
            "event": event,
            "actor": actor,
            "quality_status": result.get("quality_status"),
            "failed_checks": [
                check["id"] for check in checklist.get("checks", []) if not check["passed"]
            ],
            "missing_details": checklist.get("missing_details", []),
        }
        self.failure_log.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.failure_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise StorageError(
                "Could not append to the failure log.",
                details=str(exc),
            ) from None

    def read_failures(self, limit: int = 20) -> list[dict]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise StorageError("Limit must be a positive whole number.", field="limit")
        if not self.failure_log.exists():
            return []
        records: list[dict] = []
        try:
            lines = self.failure_log.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise StorageError("Could not read the failure log.", details=str(exc)) from None
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
        return records[-limit:]

    @staticmethod
    def _notice_id(value: object) -> str:
        if not isinstance(value, str) or not NOTICE_ID_RE.match(value):
            raise StorageError(
                "Invalid notice_id. Use letters, numbers, hyphens and underscores only.",
                field="notice_id",
            )
        return value


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
