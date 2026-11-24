"""Tests for the command-line interface and demo."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.cli import main
from tests.helpers import NOTICES_DIR


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--store", str(self.root), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_summarize_text_output(self) -> None:
        code, stdout, stderr = self.run_cli(
            "summarize",
            str(NOTICES_DIR / "year7_museum_visit.txt"),
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("Year 7 Science Museum Visit", stdout)
        self.assertIn("Quality: pass", stdout)
        self.assertIn("Result JSON:", stdout)

    def test_summarize_json_output(self) -> None:
        code, stdout, stderr = self.run_cli(
            "summarize",
            str(NOTICES_DIR / "year7_museum_visit.txt"),
            "--json",
        )
        self.assertEqual(code, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["quality_status"], "pass")
        self.assertIn("summary", result)

    def test_summarize_from_text(self) -> None:
        text = "Year 7 Notice\n\nStudents must bring a form by Friday 5 March 2027."
        code, stdout, stderr = self.run_cli("summarize", "--text", text)
        self.assertEqual(code, 0, stderr)
        self.assertIn("Year 7 Notice", stdout)

    def test_strict_incomplete_exits_one(self) -> None:
        code, stdout, stderr = self.run_cli(
            "summarize",
            str(NOTICES_DIR / "incomplete_notice.txt"),
            "--strict",
        )
        self.assertEqual(code, 1)
        self.assertIn("needs_attention", stdout)
        self.assertIn("SUGGEST", stdout)

    def test_validate(self) -> None:
        code, stdout, stderr = self.run_cli("validate", str(NOTICES_DIR / "year7_museum_visit.txt"))
        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertTrue(payload["valid"])
        self.assertGreater(payload["characters"], 100)

    def test_invalid_notice_returns_safe_error(self) -> None:
        code, stdout, stderr = self.run_cli("summarize", str(self.root / "missing.txt"))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["type"], "validation_error")

    def test_edit_result(self) -> None:
        code, stdout, stderr = self.run_cli(
            "summarize",
            str(NOTICES_DIR / "year7_museum_visit.txt"),
            "--json",
        )
        self.assertEqual(code, 0, stderr)
        result = json.loads(stdout)
        result_path = self.root / "results" / f"{result['notice_id']}.json"
        edits_path = self.root / "edits.json"
        edits_path.write_text(
            json.dumps({"headline": "Updated museum notice"}),
            encoding="utf-8",
        )
        code, stdout, stderr = self.run_cli(
            "edit",
            str(result_path),
            "--edits",
            str(edits_path),
            "--actor",
            "Ms. Rivera",
            "--json",
        )
        self.assertEqual(code, 0, stderr)
        edited = json.loads(stdout)
        self.assertEqual(edited["summary"]["headline"], "Updated museum notice")
        self.assertEqual(edited["edits"][0]["actor"], "Ms. Rivera")

    def test_checklist_command(self) -> None:
        code, stdout, stderr = self.run_cli(
            "summarize",
            str(NOTICES_DIR / "incomplete_notice.txt"),
            "--json",
        )
        result = json.loads(stdout)
        result_path = self.root / "results" / f"{result['notice_id']}.json"
        code, stdout, stderr = self.run_cli("checklist", str(result_path))
        self.assertEqual(code, 1)
        checklist = json.loads(stdout)
        self.assertFalse(checklist["passed"])

    def test_failures_command(self) -> None:
        self.run_cli("summarize", str(NOTICES_DIR / "incomplete_notice.txt"))
        code, stdout, stderr = self.run_cli("failures", "--json")
        self.assertEqual(code, 0, stderr)
        records = json.loads(stdout)
        self.assertTrue(records)
        self.assertIn("failed_checks", records[0])

    def test_batch_command(self) -> None:
        batch_dir = self.root / "batch"
        batch_dir.mkdir()
        for name in ("year7_museum_visit.txt", "incomplete_notice.txt"):
            (batch_dir / name).write_bytes((NOTICES_DIR / name).read_bytes())
        code, stdout, stderr = self.run_cli("batch", str(batch_dir))
        self.assertEqual(code, 0, stderr)
        self.assertIn("year7_museum_visit.txt", stdout)
        self.assertIn("incomplete_notice.txt", stdout)

    def test_demo_command(self) -> None:
        code, stdout, stderr = self.run_cli("demo")
        self.assertEqual(code, 0, stderr)
        self.assertIn("CLASSROOM NOTICE SUMMARIZATION - DEMO", stdout)
        self.assertIn("COMPLETE NOTICE", stdout)
        self.assertIn("INCOMPLETE NOTICE", stdout)
        self.assertIn("TEACHER EDIT", stdout)
        self.assertIn("OVERRIDE THAT REMOVES A DATE", stdout)
        self.assertIn("DEMO COMPLETE", stdout)


if __name__ == "__main__":
    unittest.main()
