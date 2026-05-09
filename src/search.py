"""
Search helpers for an inverted index: `print`-style postings and `find` (AND) retrieval.

Token rules match `indexer.html_to_tokens` via the same ``TOKEN_PATTERN``.
"""

from __future__ import annotations

from src.indexer import TOKEN_PATTERN, InvertedIndex


def terms_from_cli_args(args: list[str]) -> list[str]:
    """
    Normalise CLI arguments to index terms (lowercase, alphanumeric runs).

    Examples matching the coursework brief:
    ``find good friends`` → ``["good", "friends"]`` (conjunctive AND).
    """
    terms: list[str] = []
    for raw in args:
        if not raw.strip():
            continue
        terms.extend(TOKEN_PATTERN.findall(raw.lower()))
    return terms


def normalise_print_term(word: str) -> str | None:
    """Pick the indexing token for `print <word>` (single-token queries)."""
    chunks = TOKEN_PATTERN.findall(word.lower())
    if not chunks:
        return None
    return chunks[0]


def format_print_word(index: InvertedIndex, word: str) -> str:
    """
    Pretty-print postings for one term (output for the ``print`` command).

    Unknown or invalid terms return a short explanatory message for demos.
    """
    term = normalise_print_term(word)
    if term is None:
        return "No valid term (empty or non-alphanumeric)."

    if term not in index:
        return f"No postings for term {term!r}."

    lines: list[str] = [f"term: {term}"]
    for url in sorted(index[term].keys()):
        posting = index[term][url]
        lines.append(f"  {url}")
        lines.append(f"    frequency: {posting['frequency']}")
        lines.append(f"    positions: {posting['positions']}")
    return "\n".join(lines)


def find_pages(index: InvertedIndex, query_args: list[str]) -> list[str]:
    """
    Return URLs containing **all** query terms (Boolean AND), sorted.

    Empty query → empty list. If any term is absent from the index → empty list.

    Complexity:
        Time  — O(W · U) where W = number of query terms, U = average URLs per term
                (set construction from dict keys is O(U); set intersection is O(min_set)).
        Space — O(U) for the intermediate URL sets built during intersection.
    """
    terms = terms_from_cli_args(query_args)
    if not terms:
        return []

    sets: list[set[str]] = []
    for term in terms:
        if term not in index:
            return []
        sets.append(set(index[term].keys()))

    intersection = set.intersection(*sets)
    return sorted(intersection)
