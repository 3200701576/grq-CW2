"""
Inverted index construction and persistence for crawled HTML pages.

Each token stores per-document statistics required by the coursework brief:
term frequency and token positions within the document (0-based).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, TypedDict

from bs4 import BeautifulSoup

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class Posting(TypedDict):
    frequency: int
    positions: list[int]


InvertedIndex = dict[str, dict[str, Posting]]


def html_to_tokens(html: str) -> list[str]:
    """Extract visible text from HTML and split into lowercase alphanumeric tokens."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return TOKEN_PATTERN.findall(text.lower())


def build_inverted_index(pages: dict[str, str]) -> InvertedIndex:
    """
    Build an inverted index mapping term -> URL -> posting stats.

    Search is case-insensitive at indexing time by normalising tokens to lowercase.
    Positions refer to indices in the document token sequence after html_to_tokens().
    """
    inverted: InvertedIndex = {}

    for url, html in pages.items():
        tokens = html_to_tokens(html)
        for position, term in enumerate(tokens):
            by_url = inverted.setdefault(term, {})
            posting = by_url.setdefault(url, {"frequency": 0, "positions": []})
            posting["frequency"] += 1
            posting["positions"].append(position)

    return inverted


def save_index(index: InvertedIndex, path: str | Path) -> None:
    """Serialise the inverted index as UTF-8 JSON (single file)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def load_index(path: str | Path) -> InvertedIndex:
    """Load an inverted index previously written by save_index."""
    raw: Any
    with Path(path).open(encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise ValueError("Index file root must be a JSON object.")

    restored: InvertedIndex = {}
    for term, urls in raw.items():
        if not isinstance(term, str) or not isinstance(urls, dict):
            raise ValueError("Malformed index: expected term -> url map.")
        restored_urls: dict[str, Posting] = {}
        for url, posting in urls.items():
            if (
                not isinstance(url, str)
                or not isinstance(posting, dict)
                or posting.get("frequency") is None
                or posting.get("positions") is None
            ):
                raise ValueError(f"Malformed posting for term {term!r}, url {url!r}.")
            restored_urls[url] = {
                "frequency": int(posting["frequency"]),
                "positions": [int(p) for p in posting["positions"]],
            }
        restored[term] = restored_urls

    return restored
