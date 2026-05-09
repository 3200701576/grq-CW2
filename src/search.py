"""
Search helpers for an inverted index: `print`-style postings and `find` (AND) retrieval.

Token rules match `indexer.html_to_tokens` via the same ``TOKEN_PATTERN``.
"""

from __future__ import annotations

import math

from src.indexer import TOKEN_PATTERN, InvertedIndex


# --- TF-IDF helpers -------------------------------------------------------

def compute_total_docs(index: InvertedIndex) -> int:
    """Return the number of unique documents across the entire index."""
    urls: set[str] = set()
    for postings in index.values():
        urls.update(postings)
    return len(urls)


def _tf(posting: dict[str, int]) -> float:
    """
    Log-normalised term frequency.

    tf(t,d) = 1 + log(freq) if freq > 0, else 0
    """
    freq = int(posting["frequency"])
    return 1.0 + math.log(freq) if freq > 0 else 0.0


def _idf(term: str, index: InvertedIndex, total_docs: int) -> float:
    """
    Inverse document frequency with smoothing to avoid division by zero.

    idf(t) = log((N + 1) / (df(t) + 1)) + 1
    """
    df = len(index.get(term, {}))
    return math.log((total_docs + 1) / (df + 1)) + 1


def tfidf(term: str, url: str, index: InvertedIndex, total_docs: int) -> float:
    """
    TF-IDF score for a single term in a single document.

    score = tf(t,d) × idf(t)
    """
    if term not in index or url not in index[term]:
        return 0.0
    return _tf(index[term][url]) * _idf(term, index, total_docs)


def rank_urls(
    urls: list[str],
    terms: list[str],
    index: InvertedIndex,
    total_docs: int,
) -> list[tuple[str, float]]:
    """
    Rank ``urls`` by the sum of their per-term TF-IDF scores for ``terms``.

    Returns a sorted list of (url, score) pairs in descending score order.
    Ties are broken by URL for deterministic output.
    """
    scored: list[tuple[str, float]] = []
    for url in urls:
        score = sum(tfidf(term, url, index, total_docs) for term in terms)
        scored.append((url, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


# --- Query parsing --------------------------------------------------------

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
    Return URLs containing **all** query terms (Boolean AND), ranked by TF-IDF score.

    Documents are scored by the sum of their per-term TF-IDF values and returned
    in descending score order. Empty query → empty list.
    If any term is absent from the index → empty list.

    Complexity:
        Time  — O(W · U) where W = number of query terms, U = average URLs per term
                (set construction from dict keys is O(U); set intersection is O(min_set)).
                TF-IDF scoring adds O(W · |intersection|) time.
        Space — O(U) for the intermediate URL sets plus O(|intersection|) for scored results.
    """
    terms = terms_from_cli_args(query_args)
    if not terms:
        return []

    total_docs = compute_total_docs(index)
    sets: list[set[str]] = []
    for term in terms:
        if term not in index:
            return []
        sets.append(set(index[term].keys()))

    intersection = set.intersection(*sets)
    ranked = rank_urls(sorted(intersection), terms, index, total_docs)
    return [url for url, _ in ranked]
