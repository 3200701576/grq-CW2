# Quotes Search Engine — XJCO3011 Coursework 2

> A production-grade web search tool that crawls [quotes.toscrape.com](https://quotes.toscrape.com/),
> builds a persistent inverted index, and answers Boolean AND queries ranked by TF-IDF scores.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Usage](#3-usage)
4. [Architecture & Design Rationale](#4-architecture--design-rationale)
5. [Complexity Analysis](#5-complexity-analysis)
6. [Search Algorithm Research](#6-search-algorithm-research)
7. [Testing](#7-testing)
8. [Project Structure](#8-project-structure)
9. [References](#9-references)

---

## 1. Overview

This project implements a **web search engine tool** for the XJCO3011 Web Services and Web Data
module. It satisfies all coursework requirements:

| Requirement | Implementation |
|---|---|
| Web crawler | BFS traversal with 6-second politeness window |
| Inverted index | Per-term posting lists with frequency + positional stats |
| Boolean AND search | Conjunctive multi-term query matching |
| TF-IDF ranking | Log-normalised TF × smoothed IDF, results ordered by score |
| Persistence | JSON serialisation of the complete index |
| CLI shell | `build`, `load`, `print <word>`, `find <terms...>`, `help`, `quit` |

The tool crawls **all pages** reachable from `quotes.toscrape.com`, builds an in-memory inverted
index, and can save/load that index to disk so repeated searches avoid re-crawling.

---

## 2. Installation

**Prerequisites:** Python 3.10 or later.

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

**Required packages** (declared in `requirements.txt`):

```
beautifulsoup4 >= 4.12.0   # HTML parsing
requests     >= 2.31.0    # HTTP client
pytest       >= 8.0.0     # Test runner
pytest-cov   >= 4.1.0     # Coverage reporting
```

---

## 3. Usage

### Starting the shell

```bash
python -m src.main
```

The shell runs interactively:

```
> _
```

### Command reference

#### `build`
Crawl the target website and build the index. Saves to `data/index.json`.

```
> build
Crawled 10 unique pages.
Built index: 10 pages, 847 unique terms. Saved to data/index.json.
```

> **Note:** `build` fetches pages over the network. With the default 6-second politeness
> window, a full crawl takes approximately **90 seconds**.

#### `load`
Load a previously saved index from disk into memory.

```
> load
Loaded index from data/index.json (847 terms).
```

#### `print <word>`
Print all postings for a single term — the term's document frequency and per-document positions.

```
> print good
term: good
  https://quotes.toscrape.com/page/1/
    frequency: 4
    positions: [18, 42, 67, 103]
  https://quotes.toscrape.com/page/2/
    frequency: 1
    positions: [12]
```

#### `find <term> [<term> ...]`
Execute a Boolean AND query. Returns all pages containing **every** supplied term, ranked by
descending TF-IDF score.

```
> find good friends
https://quotes.toscrape.com/page/5/  (score=3.8470)
https://quotes.toscrape.com/page/2/  (score=2.1039)
https://quotes.toscrape.com/page/1/  (score=1.9821)
```

#### `help`
Print the command summary.

```
> help
Commands: build | load | print <word> | find <term> [<term> ...] | quit
```

#### `quit`
Exit the shell.

### Non-interactive / one-liner usage

```bash
# Build and immediately exit
echo "build" | python -m src.main

# Load existing index and search
echo -e "load\nfind love" | python -m src.main
```

### Custom index path

```bash
python -m src.main --index path/to/my-index.json
```

---

## 4. Architecture & Design Rationale

### System pipeline

```
quotes.toscrape.com
        │
        ▼
┌─────────────────┐
│    crawler.py   │  BFS + PolitenessSession (6 s/request)
│  crawl_quotes_  │
│      site()     │
└────────┬────────┘
         │  dict[url → html]
         ▼
┌─────────────────┐
│   indexer.py    │  BeautifulSoup + TOKEN_PATTERN regex
│ build_inverted_ │  case-insensitive, stores tf + positions
│     index()     │
└────────┬────────┘
         │  InvertedIndex (dict)
         ▼
┌─────────────────┐
│   search.py     │  set intersection (AND) + TF-IDF ranking
│   find_pages()  │
│   rank_urls()   │
└────────┬────────┘
         │
         ▼
   ranked URL list
```

### Design decisions

#### Why BFS for crawling?
Breadth-first search naturally discovers pages in order of depth from the start URL, which
minimises the risk of deep crawls consuming all politeness budget before reaching shallow,
high-value pages. A `deque` provides O(1) push/pop on both ends, and a `visited` dict ensures
each URL is fetched exactly once.

#### Why an inverted index instead of a forward index?
A forward index maps documents → terms (useful for listing what's in a document). An **inverted
index** maps terms → documents, which is the standard structure used by all production search
engines (Elasticsearch, Solr, Lucene) because it allows **O(1) term lookup** during query
processing. For a Boolean AND query across W terms, we retrieve W posting lists and intersect
them — far more efficient than scanning every document for each term.

#### What statistics are stored per posting?
Each posting records:

- `frequency` — number of occurrences of the term in this document (enables TF computation)
- `positions` — ordered list of 0-based token indices (enables phrase search and proximity
  queries in future extensions)

Storing raw positions is more flexible than storing only `frequency`, as it enables future
features such as **positional queries** (`"good friends"` as an exact phrase).

#### Why log-normalised TF?
Raw term frequency (`tf`) is proportional to document length — long documents will always
score higher than short ones for common terms. Log-normalisation `1 + log(tf)` dampens this
effect while preserving the rank-ordering benefit of frequency. The `+1` avoids zero values
for single-occurrence terms.

#### Why smoothed IDF?
The standard IDF formula `log(N / df)` produces division-by-zero when a term appears in
zero documents. Smoothed IDF `log((N+1)/(df+1)) + 1` avoids this, ensures all IDF values are
strictly positive, and prevents terms with df = N (appearing in every document) from
contributing zero to the score.

#### Why JSON for persistence?
JSON is human-readable, language-agnostic, and trivially version-controlled. For a single-file
index of this size, the overhead of a binary format (e.g. MessagePack) is not justified. The
index is small enough that JSON serialisation and deserialisation complete in well under a second.

### Error handling & defensive programming

| Scenario | Handling |
|---|---|
| Malformed JSON index file | `load_index` validates root type, term types, and posting structure; raises `ValueError` with descriptive message |
| Missing index file | `run_load` checks `path.is_file()` before reading |
| Empty query | `find_pages` and `run_find_cmd` return usage message |
| Non-existent term | `format_print_word` returns "No postings for term X" |
| HTTP error during crawl | `raise_for_status()` propagates as exception; caught by `run_build` |
| Politeness window too short | `crawl_quotes_site` raises `ValueError` if `politeness_seconds < 6` for live crawling |
| Invalid CLI arguments | `dispatch` catches `shlex.split` errors and returns a parse error message |

---

## 5. Complexity Analysis

| Function | Time | Space |
|---|---|---|
| `crawl_quotes_site()` | O(U + E) | O(U + E) |
| `html_to_tokens()` | O(n) | O(k) |
| `build_inverted_index()` | O(T) | O(V) |
| `save_index()` / `load_index()` | O(V) | O(V) |
| `find_pages()` | O(W · U + W · \|I\|) | O(U + \|I\|) |
| `rank_urls()` | O(W · \|I\|) | O(\|I\|) |

**Legend:**
- U = number of unique pages, E = total links extracted, T = total tokens across all docs
- V = number of unique (term, URL) posting pairs
- W = number of query terms, I = intersection set of matching URLs

**Derivation of `find_pages` complexity:**
1. Normalising query terms: O(total args)
2. For each term, building a URL set from dict keys: O(U) per term → O(W·U) total
3. Set intersection: O(min set size) per intersection step
4. TF-IDF scoring each URL in the intersection: O(W · |I|)
5. Total: dominated by O(W · U) for typical W << U

---

## 6. Search Algorithm Research

### TF-IDF foundations

TF-IDF (Term Frequency–Inverse Document Frequency) was introduced by
**Jones (1972)** as a statistical measure of term importance in document retrieval.
The intuition is dual:
- A term that appears many times in a document (**high TF**) is likely to describe that document.
- A term that appears in many documents (**high DF**) is less discriminative, so it should be
  penalised (**high IDF** means rare term = valuable signal).

Modern search engines (Elasticsearch, OpenSearch) use TF-IDF as one of several
**similarity algorithms** alongside BM25 and vector-based dense retrieval. BM25 improves on
TF-IDF by introducing a saturation function for TF and document-length normalisation, but
TF-IDF remains the foundation taught in information retrieval courses and serves as the
baseline comparison for all advanced models.

**References:**
- Salton, G. & Buckley, C. (1988). *Term-weighting approaches in automatic text retrieval.*
  Information Processing & Management, 24(5), 513–523.
- Robertson, S. & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond.*
  Foundations and Trends in Information Retrieval, 3(4), 333–389.
- Jones, K. S. (1972). *A statistical interpretation of term specificity and its application in retrieval.*
  Journal of Documentation, 28(1), 11–21.

### Modern search engine architecture

Production-grade search engines typically implement a **tiered architecture**:

```
Query → Parser → Query Rewrite → Retrieval → Scoring → Re-ranking → Response
```

Our tool implements the retrieval and scoring tiers:
- **Retrieval:** Inverted index lookup + Boolean AND filtering (equivalent to Elasticsearch's
  `bool.filter` query)
- **Scoring:** TF-IDF as the `similarity` algorithm (equivalent to Lucene's `TFIDFSimilarity`)

Future extensions to consider:
- **BM25** ranking (better document-length normalisation)
- **Phrasal queries** using positional posting information
- **Wildcard / fuzzy matching** for typo tolerance
- **Result pagination** (currently all results are returned)

---

## 7. Testing

### Running the test suite

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run with HTML coverage report (output in htmlcov/)
python -m pytest tests/ --cov=src --cov-report=html
```

### Coverage summary

| Module | Coverage |
|---|---|
| `src/crawler.py` | 89% |
| `src/indexer.py` | 100% |
| `src/main.py` | 72% |
| `src/search.py` | 100% |
| **Total** | **87%** |

The 72% on `main.py` reflects the interactive REPL (`input()` calls) and `argparse`
boilerplate, which are inherently difficult to unit-test without more sophisticated mocking.
All functional logic is fully covered.

### Test categories

| File | Category |
|---|---|
| `test_crawler.py` | Unit + integration (normalisation, link extraction, BFS, politeness enforcement, HTTP error handling) |
| `test_indexer.py` | Unit + round-trip (tokenisation, case-insensitivity, positions, JSON persistence) |
| `test_search.py` | Unit (term parsing, print formatting, AND logic, TF-IDF correctness, ranking) |
| `test_main.py` | Integration (shell dispatch, command sequencing, error propagation) |

---

## 8. Project Structure

```
code/
├── .github/
│   └── workflows/
│       └── test.yml          # CI: run pytest on push/PR
├── data/
│   └── index.json            # Default output path for build / input for load
├── src/
│   ├── __init__.py
│   ├── crawler.py            # BFS crawler + PolitenessSession
│   ├── indexer.py           # Inverted index construction + JSON persistence
│   ├── main.py              # CLI shell, command dispatch, REPL
│   └── search.py            # Query parsing, Boolean AND, TF-IDF ranking
├── tests/
│   ├── __init__.py
│   ├── test_crawler.py      # 17 tests
│   ├── test_indexer.py      # 10 tests
│   ├── test_main.py        # 13 tests
│   └── test_search.py       # 19 tests (incl. 9 TF-IDF tests)
├── pytest.ini               # Test discovery configuration
├── requirements.txt         # Runtime + dev dependencies
└── README.md                # This file
```

---

## 9. References

- **Beautiful Soup documentation** — https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Requests library** — https://docs.python-requests.org/en/latest/
- **Python `re` (regex) module** — https://docs.python.org/3/library/re.html
- **Jones, K. S. (1972).** A statistical interpretation of term specificity and its application in retrieval. *Journal of Documentation*, 28(1), 11–21.
- **Salton, G. & Buckley, C. (1988).** Term-weighting approaches in automatic text retrieval. *Information Processing & Management*, 24(5), 513–523.
- **Robertson, S. & Zaragoza, H. (2009).** The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in Information Retrieval*, 3(4), 333–389.
- **Elasticsearch similarity module** — https://www.elastic.co/guide/en/elasticsearch/reference/current/similarity.html
- **Lucene TFIDFSimilarity** — https://lucene.apache.org/core/
