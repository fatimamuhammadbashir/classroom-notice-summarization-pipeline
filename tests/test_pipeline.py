"""Tests for the end-to-end pipeline and notice validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.errors import ValidationError
from src.pipeline import NoticePipeline
from tests.helpers import NOTICES_DIR, config, make_service, process_notice


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = make_service(self.temp_dir.name)
        self.pipeline = self.service.pipeline

    def test_complete_notice_result_structure(self) -> None:
        result, json_path, markdown_path = process_notice(
            self.service, "year7_museum_visit.txt"
        )
        for key in (
            "notice_id",
            "source",
            "input",
            "sentences",
            "analysis",
            "baseline",
            "summary",
            "checklist",
            "quality_status",
        ):
            self.assertIn(key, result)
        self.assertTrue(Path(json_path).exists())
        self.assertTrue(Path(markdown_path).exists())
        self.assertEqual(result["quality_status"], "pass")

    def test_all_source_dates_appear_in_summary(self) -> None:
        result, _, _ = process_notice(self.service, "year7_museum_visit.txt")
        rendered = result["summary"]["rendered"]
        for item in result["analysis"]["temporal_mentions"]:
            self.assertIn(item["text"], rendered)

    def test_critical_instructions_appear_in_summary(self) -> None:
        result, _, _ = process_notice(self.service, "year7_museum_visit.txt")
        rendered = result["summary"]["rendered"]
        for item in result["analysis"]["critical_instructions"]:
            self.assertIn(item["text"], rendered)

    def test_incomplete_notice_needs_attention(self) -> None:
        result, _, _ = process_notice(self.service, "incomplete_notice.txt")
        self.assertEqual(result["quality_status"], "needs_attention")
        self.assertTrue(result["checklist"]["missing_details"])

    def test_relative_date_notice_needs_attention(self) -> None:
        result, _, _ = process_notice(self.service, "relative_date_notice.txt")
        self.assertEqual(result["quality_status"], "needs_attention")
        failed = {check["id"] for check in result["checklist"]["checks"] if not check["passed"]}
        self.assertIn("specific_dates", failed)

    def test_process_text(self) -> None:
        result = self.pipeline.process_text(
            "Year 7 Notice\n\nStudents must bring a form by Friday 5 March 2027."
        )
        self.assertEqual(result["source"], "pasted-text")
        self.assertEqual(result["quality_status"], "pass")

    def test_notice_id_pattern(self) -> None:
        result = self.pipeline.process_text(
            "Year 7 Notice\n\nStudents must bring a form by Friday 5 March 2027."
        )
        self.assertRegex(result["notice_id"], r"^NTC-\d{8}-\d{6}-[A-F0-9]{6}$")

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.summarize_file(NOTICES_DIR / "missing.txt")

    def test_wrong_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.pdf"
            path.write_text("Year 7 notice with enough characters to pass validation.", encoding="utf-8")
            with self.assertRaises(ValidationError):
                self.service.summarize_file(path)

    def test_empty_notice_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.txt"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ValidationError):
                self.service.summarize_file(path)

    def test_too_long_notice_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "long.txt"
            path.write_text("A" * 20001, encoding="utf-8")
            with self.assertRaises(ValidationError):
                self.service.summarize_file(path)

    def test_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            path.write_bytes(b"\xff\xfe\x00bad")
            with self.assertRaises(ValidationError):
                self.service.summarize_file(path)

    def test_validation_config_limits(self) -> None:
        active = config()
        with self.assertRaises(ValidationError):
            NoticePipeline(active).process_text("short")
        with self.assertRaises(ValidationError):
            NoticePipeline(active).process_text("x" * 20001)


if __name__ == "__main__":
    unittest.main()
