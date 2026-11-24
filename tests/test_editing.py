"""Tests for teacher overrides and edit history."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.editing import apply_edits
from src.errors import EditError
from tests.helpers import make_service, process_notice


class EditingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = make_service(self.temp_dir.name)
        self.result, self.json_path, self.markdown_path = process_notice(
            self.service, "year7_museum_visit.txt"
        )

    def test_edit_headline_and_next_step(self) -> None:
        updated = apply_edits(
            self.result,
            {
                "headline": "Museum visit — key details",
                "next_steps": ["Return the signed permission slip."],
                "note": "Clarified the next step.",
            },
            actor="Ms. Rivera",
        )
        self.assertEqual(updated["summary"]["headline"], "Museum visit — key details")
        self.assertEqual(updated["summary"]["next_steps"], ["Return the signed permission slip."])
        self.assertEqual(updated["quality_status"], "pass")
        self.assertEqual(updated["edits"][0]["actor"], "Ms. Rivera")
        self.assertEqual(updated["edits"][0]["note"], "Clarified the next step.")
        self.assertIn("Return the signed permission slip.", updated["summary"]["rendered"])

    def test_edit_sentences_to_manual_text(self) -> None:
        updated = apply_edits(
            self.result,
            {"sentences": ["A shorter teacher-written summary."]},
        )
        self.assertEqual(updated["summary"]["sentences"][0]["text"], "A shorter teacher-written summary.")
        self.assertTrue(updated["summary"]["sentences"][0]["manual"])
        self.assertTrue(updated["manual_override"])
        extractive = next(
            check for check in updated["checklist"]["checks"] if check["id"] == "extractive"
        )
        self.assertFalse(extractive["passed"])

    def test_removing_dates_fails_checklist(self) -> None:
        updated = apply_edits(
            self.result,
            {
                "sentences": ["The trip will take place soon."],
                "key_dates": [],
                "critical_instructions": [],
                "next_steps": ["Return the slip."],
            },
        )
        self.assertEqual(updated["quality_status"], "needs_attention")
        failed = {check["id"] for check in updated["checklist"]["checks"] if not check["passed"]}
        self.assertIn("date", failed)
        self.assertIn("critical_instructions", failed)

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(EditError):
            apply_edits(self.result, {"title": "No"})

    def test_empty_edits_are_rejected(self) -> None:
        with self.assertRaises(EditError):
            apply_edits(self.result, {})

    def test_notes_only_is_rejected(self) -> None:
        with self.assertRaises(EditError):
            apply_edits(self.result, {"note": "No actual edit"})

    def test_invalid_list_type_is_rejected(self) -> None:
        with self.assertRaises(EditError):
            apply_edits(self.result, {"audience": "parents"})

    def test_empty_headline_is_rejected(self) -> None:
        with self.assertRaises(EditError):
            apply_edits(self.result, {"headline": "   "})

    def test_service_edit_saves_result_and_logs_failure(self) -> None:
        updated, edited_path, edited_markdown = self.service.edit_result(
            self.json_path,
            {"key_dates": [], "sentences": ["The trip will happen soon."]},
            actor="Ms. Rivera",
        )
        self.assertTrue(Path(edited_path).exists())
        self.assertTrue(Path(edited_markdown).exists())
        self.assertEqual(updated["quality_status"], "needs_attention")
        failures = self.service.failures(limit=10)
        self.assertTrue(any(item["event"] == "edited" for item in failures))

    def test_edit_history_accumulates(self) -> None:
        first = apply_edits(self.result, {"headline": "First title"})
        second = apply_edits(first, {"headline": "Second title"})
        self.assertEqual(len(second["edits"]), 2)
        self.assertEqual(second["summary"]["headline"], "Second title")


if __name__ == "__main__":
    unittest.main()
