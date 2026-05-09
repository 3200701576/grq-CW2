import time
import unittest

from src.crawler import (
    PolitenessSession,
    _extract_same_site_links,
    _normalize_url,
    crawl_quotes_site,
)


class CrawlerTests(unittest.TestCase):
    def test_normalize_same_site(self) -> None:
        host = "quotes.toscrape.com"
        self.assertEqual(
            _normalize_url("https://quotes.toscrape.com/page/1/", host),
            "https://quotes.toscrape.com/page/1/",
        )
        self.assertEqual(
            _normalize_url("/page/2/", host),
            "https://quotes.toscrape.com/page/2/",
        )

    def test_normalize_rejects_other_hosts(self) -> None:
        host = "quotes.toscrape.com"
        self.assertIsNone(_normalize_url("https://example.com/", host))

    def test_bfs_with_stub_fetcher(self) -> None:
        html_home = (
            "<html><body>"
            '<a href="/page/2/">next</a>'
            '<a href="https://evil.example/">offsite</a>'
            "</body></html>"
        )
        html_page2 = "<html><body><p>end</p></body></html>"
        responses = {
            "https://quotes.toscrape.com/": html_home,
            "https://quotes.toscrape.com/page/2/": html_page2,
        }

        def fetch(url: str) -> str:
            return responses[url]

        pages = crawl_quotes_site("https://quotes.toscrape.com/", fetch_url=fetch)
        self.assertEqual(set(pages.keys()), set(responses.keys()))
        self.assertIn("next", pages["https://quotes.toscrape.com/"])

    def test_normalize_url_preserves_query_string(self) -> None:
        host = "quotes.toscrape.com"
        self.assertEqual(
            _normalize_url("https://quotes.toscrape.com/page?page=2", host),
            "https://quotes.toscrape.com/page?page=2",
        )

    def test_normalize_url_relative_with_query(self) -> None:
        host = "quotes.toscrape.com"
        self.assertEqual(
            _normalize_url("/search?tag=love", host),
            "https://quotes.toscrape.com/search?tag=love",
        )

    def test_normalize_url_http_to_https(self) -> None:
        host = "quotes.toscrape.com"
        self.assertEqual(
            _normalize_url("http://quotes.toscrape.com/page/", host),
            "https://quotes.toscrape.com/page/",
        )

    def test_normalize_url_unsupported_scheme(self) -> None:
        host = "quotes.toscrape.com"
        self.assertIsNone(_normalize_url("ftp://quotes.toscrape.com/", host))

    def test_extract_same_site_links_strips_base_tag(self) -> None:
        html = '<html><head><base href="http://evil.com/"></head><body><a href="/page">ok</a></body></html>'
        links = _extract_same_site_links(html, "https://quotes.toscrape.com/", "quotes.toscrape.com")
        self.assertIn("https://quotes.toscrape.com/page", links)

    def test_extract_same_site_links_skips_hash_only(self) -> None:
        html = '<html><body><a href="#top">skip</a><a href="/page">ok</a></body></html>'
        links = _extract_same_site_links(html, "https://quotes.toscrape.com/", "quotes.toscrape.com")
        self.assertEqual(links, {"https://quotes.toscrape.com/page"})

    def test_bfs_deduplicates_links_from_multiple_pages(self) -> None:
        html_a = '<html><body><a href="/b">b</a><a href="/c">c</a></body></html>'
        html_b = '<html><body><a href="/c">c again</a></body></html>'
        html_c = "<html><body>c only</body></html>"
        responses = {
            "https://quotes.toscrape.com/": html_a,
            "https://quotes.toscrape.com/b": html_b,
            "https://quotes.toscrape.com/c": html_c,
        }

        def fetch(url: str) -> str:
            return responses[url]

        pages = crawl_quotes_site("https://quotes.toscrape.com/", fetch_url=fetch)
        self.assertEqual(len(pages), 3)
        self.assertNotIn("https://evil.com/", pages)

    def test_crawl_fetch_url_raises_exception(self) -> None:
        def bad_fetch(url: str) -> str:
            raise RuntimeError("network error")

        with self.assertRaises(RuntimeError) as ctx:
            crawl_quotes_site("https://quotes.toscrape.com/", fetch_url=bad_fetch)
        self.assertIn("network error", str(ctx.exception))


class PolitenessSessionTests(unittest.TestCase):
    def test_get_text_returns_body(self) -> None:
        session = PolitenessSession(timeout=5)
        session._session.get = lambda url, **kw: _MockResponse("hello world")
        self.assertEqual(session.get_text("http://example.com/"), "hello world")

    def test_get_text_raises_on_http_error(self) -> None:
        session = PolitenessSession(timeout=5)
        session._session.get = lambda url, **kw: _MockResponse("", status_code=404)
        with self.assertRaises(Exception) as ctx:
            session.get_text("http://example.com/")
        self.assertIn("404", str(ctx.exception))

    def test_get_text_enforces_politeness_window(self) -> None:
        session = PolitenessSession(politeness_seconds=1.0, timeout=5)
        session._session.get = lambda url, **kw: _MockResponse("body")
        session._last_fetch_monotonic = time.monotonic() - 0.5
        before = time.monotonic()
        session.get_text("http://example.com/")
        elapsed = time.monotonic() - before
        self.assertGreaterEqual(elapsed, 0.5)

    def test_get_text_custom_user_agent(self) -> None:
        session = PolitenessSession(user_agent="TestBot/1.0")
        self.assertEqual(session._session.headers["User-Agent"], "TestBot/1.0")

    def test_get_text_default_user_agent_contains_coursework_id(self) -> None:
        session = PolitenessSession()
        ua = session._session.headers["User-Agent"]
        self.assertIn("XJCO3011", ua)


class _MockResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


if __name__ == "__main__":
    unittest.main()
