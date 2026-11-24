"""Tests for normalization and sentence splitting."""

from __future__ import annotations

import unittest

from src.text_processing import (
    contains_mention,
    normalize_for_match,
    normalize_text,
    split_sentences,
    title_from_sentences,
    truncate_words,
    word_count,
)


class TextProcessingTests(unittest.TestCase):
    def test_normalize_handles_bom_and_line_endings(self) -> None:
        raw = "\ufeffTitle\r\n\r\nBody   text\r\n"
        self.assertEqual(normalize_text(raw), "Title\n\nBody   text")

    def test_normalize_collapses_excess_blank_lines(self) -> None:
        raw = "Title\n\n\n\nBody"
        self.assertEqual(normalize_text(raw), "Title\n\nBody")

    def test_split_paragraphs_and_sentences(self) -> None:
        text = "Title\n\nFirst sentence. Second sentence?\n\nFinal sentence!"
        sentences = split_sentences(text)
        self.assertEqual(
            [item["text"] for item in sentences],
            ["Title", "First sentence.", "Second sentence?", "Final sentence!"],
        )
        self.assertEqual(sentences[0]["is_heading"], True)
        self.assertEqual(sentences[1]["sentence_id"], 2)

    def test_abbreviations_do_not_split_sentences(self) -> None:
        text = "Please ask Mr. Smith for help. Bring the form."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 2)
        self.assertIn("Mr. Smith", sentences[0]["text"])

    def test_heading_is_only_first_sentence(self) -> None:
        sentences = split_sentences("Year 7 Visit\n\nBring a packed lunch.")
        self.assertTrue(sentences[0]["is_heading"])
        self.assertFalse(sentences[1]["is_heading"])

    def test_word_count(self) -> None:
        self.assertEqual(word_count("Bring a water bottle, please."), 5)
        self.assertEqual(word_count("£8 payment"), 2)

    def test_normalize_for_match(self) -> None:
        self.assertEqual(normalize_for_match("  Friday   5 March  "), "friday 5 march")

    def test_contains_mention_is_case_and_space_insensitive(self) -> None:
        self.assertTrue(contains_mention("Deadline: Friday 5 March 2027.", "friday 5   march 2027"))
        self.assertFalse(contains_mention("Friday 5 March 2027", "Monday 1 March 2027"))

    def test_truncate_words(self) -> None:
        self.assertEqual(truncate_words("one two three four", 3), "one two three…")
        self.assertEqual(truncate_words("one two", 3), "one two")

    def test_title_from_sentences(self) -> None:
        sentences = split_sentences("Year 7 Museum Visit\n\nBring a lunch.")
        self.assertEqual(title_from_sentences(sentences), "Year 7 Museum Visit")


if __name__ == "__main__":
    unittest.main()
