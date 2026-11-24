"""Tests for dates, audience, actions and critical instructions."""

from __future__ import annotations

import unittest

from src.analysis import (
    analyze,
    find_actions,
    find_audience,
    find_critical_instructions,
    find_dates,
    find_next_step,
    find_times,
    normalize_date,
)
from src.text_processing import split_sentences
from tests.helpers import NOTICES_DIR


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (NOTICES_DIR / "year7_museum_visit.txt").read_text(encoding="utf-8")
        self.sentences = split_sentences(self.text)

    def test_weekday_date_normalizes_to_iso(self) -> None:
        self.assertEqual(normalize_date("Friday 5 March 2027"), "2027-03-05")
        self.assertEqual(normalize_date("5 March 2027"), "2027-03-05")
        self.assertEqual(normalize_date("March 5, 2027"), "2027-03-05")

    def test_numeric_and_iso_dates(self) -> None:
        self.assertEqual(normalize_date("5/3/2027"), "2027-03-05")
        self.assertEqual(normalize_date("2027-03-05"), "2027-03-05")
        self.assertIsNone(normalize_date("tomorrow"))

    def test_museum_dates_and_times_are_found(self) -> None:
        dates = find_dates(self.sentences)
        times = find_times(self.sentences)
        date_texts = [item["text"] for item in dates]
        time_texts = [item["text"] for item in times]
        self.assertIn("Friday 5 March 2027", date_texts)
        self.assertIn("Wednesday 3 March 2027", date_texts)
        self.assertIn("Monday 1 March 2027", date_texts)
        self.assertIn("7:45 am", time_texts)
        self.assertIn("8:00 am", time_texts)
        self.assertIn("4:30 pm", time_texts)
        self.assertTrue(all(item["normalized"] for item in dates))

    def test_relative_date_is_detected_but_not_specific(self) -> None:
        sentences = split_sentences("Year 7 Homework Club\n\nStudents meet tomorrow.")
        dates = find_dates(sentences)
        self.assertEqual(dates[0]["kind"], "relative")
        self.assertFalse(dates[0]["specific"])

    def test_audience_is_detected(self) -> None:
        audience = find_audience(self.sentences)
        texts = [item["text"] for item in audience]
        self.assertIn("parents", texts)
        self.assertIn("guardians", texts)
        self.assertIn("Year 7", texts)

    def test_actions_do_not_include_heading(self) -> None:
        actions = find_actions(self.sentences)
        self.assertTrue(any("permission slip" in item["text"] for item in actions))
        self.assertFalse(any(item["text"] == "Year 7 Science Museum Visit" for item in actions))

    def test_critical_instructions_are_detected(self) -> None:
        dates = find_dates(self.sentences)
        times = find_times(self.sentences)
        critical = find_critical_instructions(self.sentences, dates, times)
        texts = [item["text"] for item in critical]
        self.assertTrue(any("must arrive" in text for text in texts))
        self.assertTrue(any("Do not include nuts" in text for text in texts))
        self.assertTrue(any("must wear" in text for text in texts))
        self.assertFalse(any("Students should bring" in text for text in texts))

    def test_next_step_prefers_permission_slip_deadline(self) -> None:
        dates = find_dates(self.sentences)
        times = find_times(self.sentences)
        actions = find_actions(self.sentences)
        next_step = find_next_step(actions, dates, times)
        self.assertIsNotNone(next_step)
        self.assertIn("permission slip", next_step["text"])

    def test_analyze_returns_complete_structure(self) -> None:
        analysis = analyze(self.text, self.sentences)
        for key in (
            "audience",
            "dates",
            "times",
            "temporal_mentions",
            "actions",
            "critical_instructions",
            "next_step",
            "has_relative_dates",
        ):
            self.assertIn(key, analysis)
        self.assertGreaterEqual(len(analysis["dates"]), 3)
        self.assertGreaterEqual(len(analysis["times"]), 3)

    def test_incomplete_notice_has_no_audience_or_dates(self) -> None:
        text = (NOTICES_DIR / "incomplete_notice.txt").read_text(encoding="utf-8")
        analysis = analyze(text, split_sentences(text))
        self.assertEqual(analysis["audience"], [])
        self.assertEqual(analysis["dates"], [])
        self.assertEqual(analysis["actions"], [])
        self.assertIsNone(analysis["next_step"])


if __name__ == "__main__":
    unittest.main()
