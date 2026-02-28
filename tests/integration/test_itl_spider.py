"""Integration test: ITL spider with mocked HTTP responses."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from scrapy.http import HtmlResponse, Request

from web_scraper.spiders.itl_spider import ITLSpider


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _make_response(url: str, html: str) -> HtmlResponse:
    return HtmlResponse(
        url=url,
        body=html.encode("utf-8"),
        request=Request(url),
        encoding="utf-8",
    )


class TestITLSpider:
    def setup_method(self):
        self.spider = ITLSpider(site="itl")

    def test_spider_name(self):
        assert self.spider.name == "itl"
        assert self.spider.brand == "itl"

    def test_start_requests(self):
        requests = list(self.spider.start_requests())
        assert len(requests) > 0
        urls = [r.url for r in requests]
        assert any("ai-machine-learning" in u for u in urls)

    def test_parse_listing_first_page(self):
        html = FIXTURES_DIR.joinpath("itl_listing_page.html").read_text(encoding="utf-8")
        response = _make_response(
            "https://www.insurancethoughtleadership.com/ai-machine-learning",
            html,
        )
        results = list(self.spider.parse_listing_first_page(response, category="AI"))
        # Should yield article requests + pagination requests
        assert len(results) > 0
        # Check we found article links
        article_urls = [r.url for r in results if "page=" not in r.url]
        assert len(article_urls) == 3
        # Check pagination
        page_urls = [r.url for r in results if "page=" in r.url]
        assert len(page_urls) == 5  # pages 1-5

    def test_parse_article(self):
        html = FIXTURES_DIR.joinpath("itl_article_page.html").read_text(encoding="utf-8")
        url = "https://www.insurancethoughtleadership.com/ai-machine-learning/how-ai-transforming-insurance-underwriting"
        response = _make_response(url, html)

        items = list(self.spider.parse_article(response, listing_category="AI"))
        assert len(items) == 1
        item = items[0]

        assert item["title"] == "How AI Is Transforming Insurance Underwriting"
        assert item["author"] == "Jane Smith"
        assert item["brand"] == "itl"
        assert item["content_type"] == "article"
        assert "body" in item
        assert "revolutionizing" in item["body"]
        assert item["source_url"] == url

    def test_parse_article_images(self):
        html = FIXTURES_DIR.joinpath("itl_article_page.html").read_text(encoding="utf-8")
        url = "https://www.insurancethoughtleadership.com/ai-machine-learning/test"
        response = _make_response(url, html)

        items = list(self.spider.parse_article(response))
        item = items[0]
        assert len(item["images"]) == 1
        assert item["images"][0]["alt"] == "AI Underwriting Process"

    def test_dry_run_mode(self):
        spider = ITLSpider(site="itl", dry_run="true")
        html = FIXTURES_DIR.joinpath("itl_listing_page.html").read_text(encoding="utf-8")
        response = _make_response(
            "https://www.insurancethoughtleadership.com/ai-machine-learning",
            html,
        )
        results = list(spider.parse_listing_first_page(response, category="AI"))
        # Dry run should still yield pagination requests but NOT article requests
        article_requests = [r for r in results if "page=" not in r.url]
        assert len(article_requests) == 0

    def test_url_filtering(self):
        assert self.spider.url_allowed(
            "https://www.insurancethoughtleadership.com/ai-machine-learning/test"
        )
        assert not self.spider.url_allowed(
            "https://www.insurancethoughtleadership.com/user/login"
        )
        assert not self.spider.url_allowed("https://other-site.com/article")
