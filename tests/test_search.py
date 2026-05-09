import math
import unittest

from src.search import (
    _idf,
    _tf,
    compute_total_docs,
    find_pages,
    format_print_word,
    normalise_print_term,
    rank_urls,
    terms_from_cli_args,
    tfidf,
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

    def test_find_single_term_sorted_by_tfidf(self) -> None:
        idx = _tiny_index()
        urls = find_pages(idx, ["good"])
        # Results are now ranked by TF-IDF descending; tie-break by URL
        self.assertEqual(
            urls,
            ["https://b.example/page", "https://a.example/page"],
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


class TFIDFTests(unittest.TestCase):
    def test_tf_positive_freq(self) -> None:
        self.assertAlmostEqual(_tf({"frequency": 1, "positions": [0]}), 1.0)
        self.assertAlmostEqual(_tf({"frequency": 10, "positions": list(range(10))}), 1.0 + math.log(10))
        self.assertAlmostEqual(_tf({"frequency": 0, "positions": []}), 0.0)

    def test_idf_decreases_with_document_frequency(self) -> None:
        idx: dict = {
            "common": {
                "http://a": {"frequency": 1, "positions": [0]},
                "http://b": {"frequency": 1, "positions": [0]},
                "http://c": {"frequency": 1, "positions": [0]},
            },
            "rare": {"http://a": {"frequency": 1, "positions": [0]}},
        }
        idf_common = _idf("common", idx, total_docs=3)
        idf_rare = _idf("rare", idx, total_docs=3)
        self.assertGreater(idf_rare, idf_common)

    def test_tfidf_zero_for_missing_term(self) -> None:
        idx: dict = {"term": {"http://a": {"frequency": 1, "positions": [0]}}}
        self.assertEqual(tfidf("nope", "http://a", idx, 1), 0.0)
        self.assertEqual(tfidf("term", "http://missing", idx, 1), 0.0)

    def test_rank_urls_sorted_descending(self) -> None:
        urls = ["http://a", "http://b", "http://c"]
        idx: dict = {
            "term": {
                "http://a": {"frequency": 1, "positions": [0]},
                "http://b": {"frequency": 5, "positions": list(range(5))},
                "http://c": {"frequency": 10, "positions": list(range(10))},
            },
        }
        ranked = rank_urls(urls, ["term"], idx, 3)
        self.assertEqual([u for u, _ in ranked], ["http://c", "http://b", "http://a"])

    def test_compute_total_docs(self) -> None:
        idx: dict = {
            "t1": {"http://a": {"frequency": 1, "positions": [0]}},
            "t2": {"http://a": {"frequency": 1, "positions": [0]}, "http://b": {"frequency": 1, "positions": [0]}},
        }
        self.assertEqual(compute_total_docs(idx), 2)

    def test_find_pages_returns_tfidf_ranked_order(self) -> None:
        idx: dict = {
            "hello": {
                "http://low": {"frequency": 1, "positions": [0]},
                "http://high": {"frequency": 5, "positions": list(range(5))},
            },
        }
        result = find_pages(idx, ["hello"])
        self.assertEqual(result, ["http://high", "http://low"])

    def test_find_pages_empty_query_returns_empty(self) -> None:
        self.assertEqual(find_pages(_tiny_index(), []), [])

    def test_find_pages_missing_term_returns_empty(self) -> None:
        self.assertEqual(find_pages(_tiny_index(), ["missing"]), [])

    def test_find_pages_multi_term_ranking(self) -> None:
        idx: dict = {
            "a": {
                "http://p1": {"frequency": 3, "positions": [0, 1, 2]},
                "http://p2": {"frequency": 1, "positions": [0]},
            },
            "b": {
                "http://p1": {"frequency": 1, "positions": [5]},
                "http://p2": {"frequency": 3, "positions": [1, 2, 3]},
            },
        }
        result = find_pages(idx, ["a", "b"])
        # p1: tf=1+log3 + idf; p2: tf=1+log3 + idf; equal tf, order by URL
        self.assertEqual(set(result), {"http://p1", "http://p2"})


if __name__ == "__main__":
    unittest.main()
