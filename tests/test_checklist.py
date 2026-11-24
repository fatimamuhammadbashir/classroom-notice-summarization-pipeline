"""Tests for the accuracy checklist and missing-detail suggestions."""

from __future__ import annotations

import tempfile
import unittest

from src.checklist import build_checklist
from src.editing import apply_edits
from tests.helpers import make_service, process_notice


class ChecklistTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = make_service(self.temp_dir.name)
        self.complete, _, _ = process_notice(self.service, "year7_museum_visit.txt")
        self.incomplete, _, _ = process_notice(self.service, "incomplete_notice.txt")
        self.relative, _, _ = process_notice(self.service, "relative_date_notice.txt")

    def test_complete_notice_passes(self) -> None:
        checklist = self.complete["checklist"]
        self.assertTrue(checklist["passed"])
        self.assertEqual(checklist["quality_status"], "pass")
        self.assertEqual(checklist["missing_details"], [])
        self.assertTrue(all(check["passed"] for check in checklist["checks"]))

    def test_incomplete_notice_fails_core_checks(self) -> None:
        checklist = self.incomplete["checklist"]
        self.assertFalse(checklist["passed"])
        failed = {check["id"] for check in checklist["checks"] if not check["passed"]}
        self.assertIn("audience", failed)
        self.assertIn("date", failed)
        self.assertIn("action", failed)
        self.assertIn("next_step", failed)

    def test_incomplete_has_suggestions(self) -> None:
        suggestions = " ".join(self.incomplete["checklist"]["missing_details"])
        self.assertIn("audience", suggestions.lower())
        self.assertIn("date", suggestions.lower())
        self.assertIn("action", suggestions.lower())
        self.assertIn("next step", suggestions.lower())

    def test_relative_date_fails_specificity(self) -> None:
        checklist = self.relative["checklist"]
        self.assertFalse(checklist["passed"])
        failed = {check["id"] for check in checklist["checks"] if not check["passed"]}
        self.assertEqual(failed, {"specific_dates"})
        self.assertIn("tomorrow", " ".join(checklist["missing_details"]))

    def test_editing_out_dates_fails_date_check(self) -> None:
        summary = self.complete["summary"]
        edited_summary = dict(summary)
        edited_summary["key_dates"] = []
        edited_summary["sentences"] = [
            {"sentence_id": None, "text": "A short manual summary.", "score": None, "manual": True}
        ]
        edited_summary["rendered"] = "A short manual summary.\n"
        checklist = build_checklist(
            self.complete["input"]["text"],
            self.complete["analysis"],
            edited_summary,
        )
        self.assertFalse(checklist["passed"])
        failed = {check["id"] for check in checklist["checks"] if not check["passed"]}
        self.assertIn("date", failed)
        self.assertIn("critical_instructions", failed)

    def test_editing_out_critical_instruction_fails(self) -> None:
        summary = dict(self.complete["summary"])
        summary["critical_instructions"] = []
        summary["rendered"] = summary["headline"] + "\n\nSummary:\n- Nothing critical.\n"
        checklist = build_checklist(
            self.complete["input"]["text"],
            self.complete["analysis"],
            summary,
        )
        failed = {check["id"] for check in checklist["checks"] if not check["passed"]}
        self.assertIn("critical_instructions", failed)

    def test_manual_text_marks_extractive_warning(self) -> None:
        result = apply_edits(
            self.complete,
            {"sentences": ["This wording is not in the original notice."]},
            actor="Teacher",
        )
        extractive = next(
            check for check in result["checklist"]["checks"] if check["id"] == "extractive"
        )
        self.assertFalse(extractive["passed"])
        self.assertFalse(extractive["required"])
        self.assertIn("new text", " ".join(result["checklist"]["missing_details"]).lower())

    def test_length_check_uses_baseline_words(self) -> None:
        length = next(
            check for check in self.complete["checklist"]["checks"] if check["id"] == "length"
        )
        self.assertTrue(length["passed"])
        self.assertIn(str(self.complete["summary"]["word_count"]), length["detail"])


if __name__ == "__main__":
    unittest.main()
