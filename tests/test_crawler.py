import unittest

from src.crawler import _extract_same_site_links, _normalize_url, crawl_quotes_site


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


if __name__ == "__main__":
    unittest.main()
