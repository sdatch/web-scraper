"""Integration test: IAUM spider with mocked HTTP responses."""
from pathlib import Path

from scrapy.http import HtmlResponse, XmlResponse, Request

from web_scraper.spiders.iaum_spider import IAUMSpider


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _make_html_response(url: str, html: str) -> HtmlResponse:
    return HtmlResponse(
        url=url,
        body=html.encode("utf-8"),
        request=Request(url),
        encoding="utf-8",
    )


def _make_xml_response(url: str, xml: str) -> XmlResponse:
    return XmlResponse(
        url=url,
        body=xml.encode("utf-8"),
        request=Request(url),
        encoding="utf-8",
    )


class TestIAUMSpider:
    def setup_method(self):
        self.spider = IAUMSpider(site="iaum")

    def test_spider_name(self):
        assert self.spider.name == "iaum"
        assert self.spider.brand == "iaum"

    def test_start_requests(self):
        requests = list(self.spider.start_requests())
        assert len(requests) == 1
        assert "sitemap.xml" in requests[0].url

    def test_parse_sitemap(self):
        xml = FIXTURES_DIR.joinpath("iaum_sitemap.xml").read_text(encoding="utf-8")
        response = _make_xml_response("https://insuranceaum.com/sitemap.xml", xml)
        results = list(self.spider.parse_sitemap(response))
        # Should yield article requests, filtering out /category/, /events, /user/
        urls = [r.url for r in results]
        assert len(urls) == 3
        assert "https://insuranceaum.com/implementing-ai-for-limited-partners" in urls
        assert "https://insuranceaum.com/going-beyond-core-how-allocators-are-tapping-new-cre-debt-opportunities" in urls
        assert "https://insuranceaum.com/unlocking-the-potential-of-solvency-ii-long-term-equity-portfolios-ltei-0" in urls
        # Filtered URLs should not appear
        assert not any("/category/" in u for u in urls)
        assert not any("/events" in u for u in urls)
        assert not any("/user/" in u for u in urls)

    def test_parse_sitemap_dry_run(self):
        spider = IAUMSpider(site="iaum", dry_run="true")
        xml = FIXTURES_DIR.joinpath("iaum_sitemap.xml").read_text(encoding="utf-8")
        response = _make_xml_response("https://insuranceaum.com/sitemap.xml", xml)
        results = list(spider.parse_sitemap(response))
        # Dry run yields no requests
        assert len(results) == 0

    def test_parse_article(self):
        html = FIXTURES_DIR.joinpath("iaum_article_page.html").read_text(encoding="utf-8")
        url = "https://insuranceaum.com/implementing-ai-for-limited-partners"
        response = _make_html_response(url, html)

        items = list(self.spider.parse_article(response))
        assert len(items) == 1
        item = items[0]

        assert item["title"] == "Implementing AI for Limited Partners"
        assert item["brand"] == "iaum"
        assert item["content_type"] == "article"
        assert item["source_url"] == url
        assert "body" in item
        assert "transforming how limited partners" in item["body"]
        assert item["date_published"] == "2026-03-19"
        assert item["description"] == "How limited partners can leverage AI to enhance portfolio management and due diligence."

    def test_parse_article_categories(self):
        html = FIXTURES_DIR.joinpath("iaum_article_page.html").read_text(encoding="utf-8")
        url = "https://insuranceaum.com/implementing-ai-for-limited-partners"
        response = _make_html_response(url, html)

        items = list(self.spider.parse_article(response))
        item = items[0]
        assert "Alternatives" in item["categories"]
        assert "Data and Technology" in item["categories"]
        assert item["category"] == "Alternatives"

    def test_parse_article_images(self):
        html = FIXTURES_DIR.joinpath("iaum_article_page.html").read_text(encoding="utf-8")
        url = "https://insuranceaum.com/implementing-ai-for-limited-partners"
        response = _make_html_response(url, html)

        items = list(self.spider.parse_article(response))
        item = items[0]
        assert len(item["images"]) == 1
        assert item["images"][0]["alt"] == "AI Workflow Diagram"
        assert item["images"][0]["caption"] == "AI-powered LP workflow"

    def test_url_filtering(self):
        assert self.spider.url_allowed(
            "https://insuranceaum.com/implementing-ai-for-limited-partners"
        )
        assert not self.spider.url_allowed(
            "https://insuranceaum.com/user/login"
        )
        assert not self.spider.url_allowed(
            "https://insuranceaum.com/category/topics/private-credit"
        )
        assert not self.spider.url_allowed(
            "https://insuranceaum.com/events"
        )
        assert not self.spider.url_allowed(
            "https://other-site.com/article"
        )
