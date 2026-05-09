"""
Interactive command shell for the coursework search engine.

Commands (as required by the brief): build, load, print <word>, find <terms...>.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from src.crawler import crawl_quotes_site
from src.indexer import InvertedIndex, build_inverted_index, load_index, save_index
from src.search import format_print_word, find_pages, rank_urls, terms_from_cli_args

DEFAULT_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "index.json"


@dataclass
class SearchShell:
    """In-memory index plus path used by ``build`` / ``load``."""

    index_path: Path
    index: InvertedIndex | None = None


def build_index_from_pages(shell: SearchShell, pages: dict[str, str]) -> str:
    idx = build_inverted_index(pages)
    save_index(idx, shell.index_path)
    shell.index = idx
    return (
        f"Built index: {len(pages)} pages, {len(idx)} unique terms. "
        f"Saved to {shell.index_path}."
    )


def run_build(shell: SearchShell) -> str:
    """
    Fetch all pages from quotes.toscrape.com and build the inverted index.

    Exits early with an error message if the crawl fails.
    """
    try:
        pages = crawl_quotes_site()
    except Exception as exc:
        return f"Crawl failed: {exc}"
    return build_index_from_pages(shell, pages)


def run_load(shell: SearchShell) -> str:
    """Load a previously saved index from disk into memory."""
    path = shell.index_path
    if not path.is_file():
        return f"No index file at {path}. Run build first."
    try:
        shell.index = load_index(path)
    except Exception as exc:
        return f"Load failed: {exc}"
    return f"Loaded index from {path} ({len(shell.index)} terms)."


def run_print_cmd(shell: SearchShell, args: list[str]) -> str:
    """
    Pretty-print postings for a single term.

    Returns usage message if no term is supplied.
    """
    if shell.index is None:
        return "No index in memory. Run build or load first."
    if not args:
        return "Usage: print <word>"
    word = " ".join(args)
    return format_print_word(shell.index, word)


def run_find_cmd(shell: SearchShell, args: list[str]) -> str:
    """
    Execute a Boolean AND query and return all matching URLs ranked by TF-IDF score.

    Returns usage message if no terms are supplied; returns "No matching pages."
    if no documents satisfy all query terms.
    """
    if shell.index is None:
        return "No index in memory. Run build or load first."
    if not args:
        return "Usage: find <term> [<term> ...]"

    terms = terms_from_cli_args(args)
    urls = find_pages(shell.index, args)
    if not urls:
        return "No matching pages."

    from src.search import compute_total_docs

    total_docs = compute_total_docs(shell.index)
    ranked = rank_urls(urls, terms, shell.index, total_docs)
    lines = [f"{url}  (score={score:.4f})" for url, score in ranked]
    return "\n".join(lines)


def dispatch(line: str, shell: SearchShell) -> str | None:
    """
    Parse and execute a single shell command line.

    Returns the command output string, ``"__QUIT__"`` for exit signals,
    or ``None`` for no-op (blank line).
    """
    stripped = line.strip()
    if not stripped:
        return None

    try:
        parts = shlex.split(stripped)
    except ValueError as exc:
        return f"Could not parse command: {exc}"

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in {"quit", "exit"}:
        return "__QUIT__"
    if cmd == "help":
        return (
            "Commands: build | load | print <word> | find <term> [<term> ...] | quit"
        )
    if cmd == "build":
        return "Usage: build (no arguments)" if args else run_build(shell)
    if cmd == "load":
        return "Usage: load (no arguments)" if args else run_load(shell)
    if cmd == "print":
        return run_print_cmd(shell, args)
    if cmd == "find":
        return run_find_cmd(shell, args)

    return f"Unknown command {cmd!r}. Type help."


def repl(shell: SearchShell) -> None:
    while True:
        try:
            line = input("> ")
        except EOFError:
            print()
            break
        result = dispatch(line, shell)
        if result == "__QUIT__":
            break
        if result is not None:
            print(result)


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Quotes.toscrape.com search tool shell.")
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_PATH,
        help="Path to the JSON inverted index file (default: ./data/index.json).",
    )
    ns = parser.parse_args(argv)
    shell = SearchShell(index_path=ns.index.resolve())
    repl(shell)


if __name__ == "__main__":
    main()
