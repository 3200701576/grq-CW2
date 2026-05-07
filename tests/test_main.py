import tempfile
import unittest
from pathlib import Path

from src.main import (
    SearchShell,
    build_index_from_pages,
    dispatch,
    run_find_cmd,
    run_load,
    run_print_cmd,
)


class MainTests(unittest.TestCase):
    def test_build_index_from_pages_persists_and_loads(self) -> None:
        pages = {
            "https://example.com/a": "<html><body>alpha beta alpha</body></html>",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            shell = SearchShell(index_path=path)
            msg = build_index_from_pages(shell, pages)
            self.assertTrue(path.is_file())
            self.assertIsNotNone(shell.index)
            self.assertIn("Built index", msg)

            fresh = SearchShell(index_path=path)
            load_msg = run_load(fresh)
            self.assertIn("Loaded index", load_msg)
            self.assertIsNotNone(fresh.index)
            self.assertIn("alpha", fresh.index)

    def test_load_missing_file_message(self) -> None:
        shell = SearchShell(index_path=Path("/nonexistent/path/index.json"))
        msg = run_load(shell)
        self.assertIn("No index file", msg)

    def test_print_requires_loaded_index(self) -> None:
        shell = SearchShell(index_path=Path("x.json"))
        msg = run_print_cmd(shell, ["alpha"])
        self.assertIn("No index in memory", msg)

    def test_find_conjunctive_after_build(self) -> None:
        pages = {
            "https://example.com/a": "<html><body>good friends</body></html>",
            "https://example.com/b": "<html><body>good only</body></html>",
        }
        with tempfile.TemporaryDirectory() as tmp:
            shell = SearchShell(index_path=Path(tmp) / "idx.json")
            build_index_from_pages(shell, pages)
            out = run_find_cmd(shell, ["good", "friends"])
            self.assertIn("https://example.com/a", out)
            self.assertNotIn("https://example.com/b", out)

    def test_dispatch_unknown_command(self) -> None:
        shell = SearchShell(index_path=Path("i.json"))
        out = dispatch("nope", shell)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertIn("Unknown command", out)

    def test_dispatch_blank_line(self) -> None:
        shell = SearchShell(index_path=Path("i.json"))
        self.assertIsNone(dispatch("   ", shell))


if __name__ == "__main__":
    unittest.main()
