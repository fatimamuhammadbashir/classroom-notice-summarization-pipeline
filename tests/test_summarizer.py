"""Tests for extractive baseline and structured summary generation."""

from __future__ import annotations

import unittest

from src.analysis import analyze
from src.summarizer import extract_baseline, generate_summary, render_summary
from src.text_processing import split_sentences, word_count
from tests.helpers import NOTICES_DIR


class SummarizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (NOTICES_DIR / "year7_museum_visit.txt").read_text(encoding="utf-8")
        self.sentences = split_sentences(self.text)
        self.analysis = analyze(self.text, self.sentences)
        self.baseline = extract_baseline(
            self.sentences,
            self.analysis,
            max_sentences=8,
            max_words=220,
        )
        self.summary = generate_summary(self.sentences, self.analysis, self.baseline)

    def test_selected_sentences_are_verbatim(self) -> None:
        source = " ".join(item["text"] for item in self.sentences)
        for item in self.baseline["sentences"]:
            self.assertIn(item["text"], source)

    def test_heading_is_not_in_baseline(self) -> None:
        texts = [item["text"] for item in self.baseline["sentences"]]
        self.assertNotIn("Year 7 Science Museum Visit", texts)

    def test_all_dates_and_critical_instructions_are_mandatory(self) -> None:
        selected_ids = {item["sentence_id"] for item in self.baseline["sentences"]}
        date_ids = {item["sentence_id"] for item in self.analysis["dates"] + self.analysis["times"]}
        critical_ids = {
            item["sentence_id"] for item in self.analysis["critical_instructions"]
        }
        self.assertTrue(date_ids.issubset(selected_ids))
        self.assertTrue(critical_ids.issubset(selected_ids))

    def test_baseline_preserves_source_order(self) -> None:
        ids = [item["sentence_id"] for item in self.baseline["sentences"]]
        self.assertEqual(ids, sorted(ids))

    def test_baseline_respects_limits_when_possible(self) -> None:
        baseline = extract_baseline(
            self.sentences,
            self.analysis,
            max_sentences=2,
            max_words=50,
        )
        self.assertEqual(baseline["mandatory_count"], len(baseline["sentences"]))
        self.assertTrue(baseline["limit_exceeded"])

    def test_summary_contains_required_sections(self) -> None:
        for key in (
            "headline",
            "audience",
            "sentences",
            "key_dates",
            "critical_instructions",
            "actions",
            "next_steps",
            "rendered",
        ):
            self.assertIn(key, self.summary)
        self.assertEqual(self.summary["headline"], "Year 7 Science Museum Visit")
        self.assertIn("Friday 5 March 2027", self.summary["rendered"])
        self.assertIn("permission slip", self.summary["rendered"])

    def test_rendered_summary_contains_all_lists(self) -> None:
        rendered = render_summary(self.summary)
        for item in self.summary["key_dates"]:
            self.assertIn(item, rendered)
        for item in self.summary["critical_instructions"]:
            self.assertIn(item, rendered)
        for item in self.summary["next_steps"]:
            self.assertIn(item, rendered)

    def test_summary_word_count_matches_selected_sentences(self) -> None:
        expected = sum(
            word_count(item["text"] if isinstance(item, dict) else item)
            for item in self.summary["sentences"]
        )
        self.assertEqual(self.summary["word_count"], expected)

    def test_incomplete_notice_generates_small_summary(self) -> None:
        text = (NOTICES_DIR / "incomplete_notice.txt").read_text(encoding="utf-8")
        sentences = split_sentences(text)
        analysis = analyze(text, sentences)
        baseline = extract_baseline(sentences, analysis, max_sentences=8, max_words=220)
        summary = generate_summary(sentences, analysis, baseline)
        self.assertEqual(summary["audience"], [])
        self.assertEqual(summary["key_dates"], [])
        self.assertEqual(summary["next_steps"], [])
        self.assertTrue(summary["rendered"])


if __name__ == "__main__":
    unittest.main()
