import tempfile
import unittest
from pathlib import Path

from src.indexer import (
    build_inverted_index,
    html_to_tokens,
    load_index,
    save_index,
)


class IndexerTests(unittest.TestCase):
    def test_html_to_tokens_strips_tags_and_lowercases(self) -> None:
        html = "<html><body><p>Good</p> <span>Friends!</span></body></html>"
        self.assertEqual(html_to_tokens(html), ["good", "friends"])

    def test_case_insensitive_counts_merge(self) -> None:
        html = "<body>Good good GOOD</body>"
        pages = {"https://quotes.toscrape.com/": html}
        idx = build_inverted_index(pages)
        posting = idx["good"]["https://quotes.toscrape.com/"]
        self.assertEqual(posting["frequency"], 3)
        self.assertEqual(posting["positions"], [0, 1, 2])

    def test_positions_follow_token_order(self) -> None:
        html = "<div>hello world</div><p>world hello</p>"
        pages = {"https://example.com/a": html}
        idx = build_inverted_index(pages)
        hello = idx["hello"]["https://example.com/a"]
        world = idx["world"]["https://example.com/a"]
        self.assertEqual(hello["positions"], [0, 3])
        self.assertEqual(world["positions"], [1, 2])

    def test_save_load_roundtrip(self) -> None:
        pages = {"https://example.com/p": "<html><body>alpha beta alpha</body></html>"}
        idx = build_inverted_index(pages)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            save_index(idx, path)
            loaded = load_index(path)
        self.assertEqual(loaded, idx)


if __name__ == "__main__":
    unittest.main()
