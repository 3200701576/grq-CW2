import unittest

from src.search import (
    find_pages,
    format_print_word,
    normalise_print_term,
    terms_from_cli_args,
)


def _tiny_index() -> dict:
    return {
        "good": {
            "https://a.example/page": {"frequency": 1, "positions": [0]},
            "https://b.example/page": {"frequency": 2, "positions": [3, 9]},
        },
        "friends": {
            "https://a.example/page": {"frequency": 1, "positions": [1]},
        },
    }


class SearchTests(unittest.TestCase):
    def test_terms_from_cli_args_multiword(self) -> None:
        self.assertEqual(terms_from_cli_args(["good", "friends"]), ["good", "friends"])

    def test_terms_case_insensitive(self) -> None:
        self.assertEqual(terms_from_cli_args(["Good"]), ["good"])

    def test_terms_skips_empty_segments(self) -> None:
        self.assertEqual(terms_from_cli_args(["", "  ", "ok"]), ["ok"])

    def test_find_single_term_sorted(self) -> None:
        idx = _tiny_index()
        urls = find_pages(idx, ["good"])
        self.assertEqual(
            urls,
            ["https://a.example/page", "https://b.example/page"],
        )

    def test_find_conjunctive_and(self) -> None:
        idx = _tiny_index()
        self.assertEqual(find_pages(idx, ["good", "friends"]), ["https://a.example/page"])

    def test_find_missing_term_empty(self) -> None:
        idx = _tiny_index()
        self.assertEqual(find_pages(idx, ["good", "nope"]), [])

    def test_find_empty_query(self) -> None:
        self.assertEqual(find_pages(_tiny_index(), []), [])

    def test_print_unknown_term(self) -> None:
        text = format_print_word(_tiny_index(), "nope")
        self.assertIn("No postings", text)

    def test_print_invalid_term(self) -> None:
        text = format_print_word(_tiny_index(), "@@@")
        self.assertIn("No valid term", text)

    def test_print_contains_stats(self) -> None:
        text = format_print_word(_tiny_index(), "good")
        self.assertIn("term: good", text)
        self.assertIn("https://b.example/page", text)
        self.assertIn("frequency: 2", text)
        self.assertIn("positions: [3, 9]", text)

    def test_normalise_print_term(self) -> None:
        self.assertEqual(normalise_print_term("Good"), "good")
        self.assertIsNone(normalise_print_term("@@@"))


if __name__ == "__main__":
    unittest.main()
