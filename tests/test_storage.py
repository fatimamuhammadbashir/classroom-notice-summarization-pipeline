"""Tests for result storage, exports and failure logging."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.errors import StorageError
from src.storage import ResultStore
from tests.helpers import make_service, process_notice


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.store = ResultStore(self.root)
        self.service = make_service(self.root)
        self.result, self.json_path, self.markdown_path = process_notice(
            self.service, "year7_museum_visit.txt"
        )

    def test_save_and_load_roundtrip(self) -> None:
        loaded = self.store.load_result(self.json_path)
        self.assertEqual(loaded["notice_id"], self.result["notice_id"])
        self.assertEqual(loaded["summary"]["headline"], "Year 7 Science Museum Visit")

    def test_markdown_is_written(self) -> None:
        text = Path(self.markdown_path).read_text(encoding="utf-8")
        self.assertIn("# Year 7 Science Museum Visit", text)
        self.assertIn("Quality: **pass**", text)

    def test_failure_log_records_failed_checks(self) -> None:
        incomplete, _, _ = process_notice(self.service, "incomplete_notice.txt")
        records = self.store.read_failures()
        self.assertTrue(any(record["notice_id"] == incomplete["notice_id"] for record in records))
        record = next(item for item in records if item["notice_id"] == incomplete["notice_id"])
        self.assertEqual(record["event"], "generated")
        self.assertIn("audience", record["failed_checks"])
        self.assertNotIn("text", record)
        self.assertNotIn("Library Update", json.dumps(record))

    def test_failure_log_limit(self) -> None:
        process_notice(self.service, "incomplete_notice.txt")
        process_notice(self.service, "relative_date_notice.txt")
        records = self.store.read_failures(limit=1)
        self.assertEqual(len(records), 1)

    def test_missing_failure_log_returns_empty(self) -> None:
        empty = ResultStore(self.root / "empty")
        self.assertEqual(empty.read_failures(), [])

    def test_missing_result_is_reported(self) -> None:
        with self.assertRaises(StorageError):
            self.store.load_result(self.root / "missing.json")

    def test_corrupt_result_is_reported(self) -> None:
        path = self.root / "bad.json"
        path.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.store.load_result(path)

    def test_invalid_notice_id_is_rejected(self) -> None:
        bad = dict(self.result)
        bad["notice_id"] = "../escape"
        with self.assertRaises(StorageError):
            self.store.save_result(bad)

    def test_invalid_limit_is_rejected(self) -> None:
        for value in (0, -1, True, "5"):
            with self.subTest(value=value):
                with self.assertRaises(StorageError):
                    self.store.read_failures(limit=value)

    def test_save_does_not_leave_temporary_files(self) -> None:
        self.service.edit_result(self.json_path, {"headline": "Updated title"})
        self.assertEqual(list(self.root.rglob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
