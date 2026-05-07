import unittest

from src.crawler import _normalize_url, crawl_quotes_site


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


if __name__ == "__main__":
    unittest.main()
