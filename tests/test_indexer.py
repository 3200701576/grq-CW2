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

    def test_html_to_tokens_empty(self) -> None:
        self.assertEqual(html_to_tokens(""), [])

    def test_html_to_tokens_non_alphanumeric(self) -> None:
        self.assertEqual(html_to_tokens("hello @#$ world 123"), ["hello", "world", "123"])

    def test_html_to_tokens_script_style_tags(self) -> None:
        html = "<script>secret</script><p>visible</p>"
        self.assertEqual(html_to_tokens(html), ["visible"])

    def test_load_index_malformed_root_not_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('"not a dict"')
            with self.assertRaises(ValueError) as ctx:
                load_index(path)
            self.assertIn("JSON object", str(ctx.exception))

    def test_load_index_malformed_term_not_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"good": {"http://x": {"frequency": 1, "positions": [0]}}, "bad": 123}')
            with self.assertRaises(ValueError) as ctx:
                load_index(path)
            self.assertIn("Malformed index", str(ctx.exception))

    def test_load_index_missing_frequency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"good": {"http://x": {"positions": [0]}}}')
            with self.assertRaises(ValueError) as ctx:
                load_index(path)
            self.assertIn("Malformed posting", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
