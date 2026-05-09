"""
Web crawler for https://quotes.toscrape.com/

Respects a minimum delay between successive HTTP requests (politeness window).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_BASE_URL = "https://quotes.toscrape.com/"
DEFAULT_POLITENESS_SECONDS = 6.0
DEFAULT_TIMEOUT = 30


class PolitenessSession:
    """HTTP GET with enforced minimum interval between requests."""

    def __init__(
        self,
        politeness_seconds: float = DEFAULT_POLITENESS_SECONDS,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str | None = None,
    ) -> None:
        self._politeness = politeness_seconds
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (compatible; XJCO3011-Coursework2/1.0; "
                    "+student coursework crawler)"
                ),
            }
        )
        self._last_fetch_monotonic: float | None = None

    def get_text(self, url: str) -> str:
        if self._last_fetch_monotonic is not None:
            elapsed = time.monotonic() - self._last_fetch_monotonic
            wait = self._politeness - elapsed
            if wait > 0:
                time.sleep(wait)

        response = self._session.get(url, timeout=self._timeout)
        self._last_fetch_monotonic = time.monotonic()
        response.raise_for_status()
        return response.text


def _site_host(base_url: str) -> str:
    host = urlparse(base_url).netloc.lower()
    if not host:
        raise ValueError(f"Invalid base URL (missing host): {base_url!r}")
    return host


def _normalize_url(url: str, site_host: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", ""):
        return None

    netloc = parsed.netloc.lower()
    if netloc and netloc != site_host:
        return None

    if not netloc:
        path = parsed.path or "/"
        url = f"https://{site_host}{path}"
        if parsed.query:
            url = f"{url}?{parsed.query}"
        parsed = urlparse(url)

    scheme = "https"
    path = parsed.path or "/"
    norm = f"{scheme}://{site_host}{path}"
    if parsed.query:
        norm = f"{norm}?{parsed.query}"
    return norm


def _extract_same_site_links(html: str, page_url: str, site_host: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    for base_tag in soup.find_all("base"):
        base_tag.decompose()
    found: set[str] = set()
    for tag in soup.find_all("a", href=True):
        raw_href = tag["href"].strip()
        if not raw_href or raw_href.startswith("#"):
            continue
        absolute = urljoin(page_url, raw_href)
        normalized = _normalize_url(absolute, site_host)
        if normalized:
            found.add(normalized)
    return found


def crawl_quotes_site(
    base_url: str = DEFAULT_BASE_URL,
    *,
    politeness_seconds: float = DEFAULT_POLITENESS_SECONDS,
    timeout: float = DEFAULT_TIMEOUT,
    session: PolitenessSession | None = None,
    fetch_url: Callable[[str], str] | None = None,
) -> dict[str, str]:
    """
    Crawl all HTML pages reachable via same-site links starting from base_url.

    Returns a mapping of canonical URL -> response body (HTML text).

    For tests or offline fixtures, pass ``fetch_url`` to supply HTML without
    making network calls. The default path uses ``PolitenessSession`` and
    enforces the coursework politeness window (>= 6 seconds between requests).

    Complexity:
        Time  — O(U + E) where U = number of unique pages discovered,
                E = total number of links extracted across all pages.
                Each page is fetched at most once; each link is processed once.
        Space — O(U) for the ``visited`` dict (stores raw HTML for every page)
                plus O(E) transient queue overhead during crawling.
    """
    base_url = base_url if urlparse(base_url).scheme else f"https://{base_url}"
    site_host = _site_host(base_url)
    start = _normalize_url(base_url, site_host)
    if not start:
        raise ValueError(f"Could not normalize base URL: {base_url!r}")

    fetch_fn: Callable[[str], str]
    if fetch_url is None:
        if politeness_seconds < DEFAULT_POLITENESS_SECONDS:
            raise ValueError(
                f"politeness_seconds must be >= {DEFAULT_POLITENESS_SECONDS} "
                f"for live crawling (got {politeness_seconds})."
            )

        http = session or PolitenessSession(
            politeness_seconds=politeness_seconds,
            timeout=timeout,
        )
        fetch_fn = http.get_text
    else:
        fetch_fn = fetch_url

    visited: dict[str, str] = {}
    queue: deque[str] = deque([start])

    while queue:
        url = queue.popleft()
        if url in visited:
            continue

        html = fetch_fn(url)
        visited[url] = html

        for link in _extract_same_site_links(html, url, site_host):
            if link not in visited:
                queue.append(link)

    return visited


def main() -> None:
    pages = crawl_quotes_site()
    print(f"Crawled {len(pages)} unique pages.")
    for u in sorted(pages.keys()):
        print(u)


if __name__ == "__main__":
    main()
