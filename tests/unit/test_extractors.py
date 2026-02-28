import json
from pathlib import Path

import pytest
from scrapy.http import HtmlResponse, Request

from web_scraper.extractors.jsonld import extract_jsonld, _resolve_dot_path
from web_scraper.extractors.dom_fallback import extract_dom, clean_html
from web_scraper.extractors.image_extractor import extract_images


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _make_response(html: str, url: str = "https://example.com/test") -> HtmlResponse:
    return HtmlResponse(
        url=url,
        body=html.encode("utf-8"),
        request=Request(url),
        encoding="utf-8",
    )


class TestJsonLD:
    def test_extract_article_fields(self, itl_article_html):
        response = _make_response(itl_article_html)
        field_map = {
            "title": "headline",
            "author": "author.name",
            "date_published": "datePublished",
            "description": "description",
            "canonical_url": "url",
            "publisher": "publisher.name",
        }
        result = extract_jsonld(response, field_map, type_filter="Article")

        assert result["title"] == "How AI Is Transforming Insurance Underwriting"
        assert result["author"] == "Jane Smith"
        assert result["date_published"] == "2024-11-15T10:00:00-05:00"
        assert "revolutionizing" in result["description"]
        assert result["publisher"] == "Insurance Thought Leadership"

    def test_type_filter_no_match(self, itl_article_html):
        response = _make_response(itl_article_html)
        result = extract_jsonld(response, {"title": "headline"}, type_filter="BlogPosting")
        assert result == {}

    def test_empty_jsonld(self):
        html = "<html><body>No JSON-LD here</body></html>"
        response = _make_response(html)
        result = extract_jsonld(response, {"title": "headline"})
        assert result == {}

    def test_resolve_dot_path(self):
        data = {"author": {"name": "Alice"}, "title": "Test"}
        assert _resolve_dot_path(data, "author.name") == "Alice"
        assert _resolve_dot_path(data, "title") == "Test"
        assert _resolve_dot_path(data, "missing.field") is None


class TestDomFallback:
    def test_extract_body(self, itl_article_html):
        response = _make_response(itl_article_html)
        selectors = {"body": "div.article__body"}
        result = extract_dom(response, selectors)
        assert "body" in result
        assert "revolutionizing" in result["body"]
        # Script tags should be cleaned
        assert "tracking" not in result["body"]

    def test_extract_title(self, itl_article_html):
        response = _make_response(itl_article_html)
        selectors = {"title": "h1.page-title"}
        result = extract_dom(response, selectors)
        assert result["title"] == "How AI Is Transforming Insurance Underwriting"

    def test_extract_date(self, itl_article_html):
        response = _make_response(itl_article_html)
        selectors = {"date": "time[datetime]"}
        result = extract_dom(response, selectors)
        assert result["date_published"] == "2024-11-15T10:00:00-05:00"

    def test_extract_categories(self, itl_article_html):
        response = _make_response(itl_article_html)
        selectors = {"category": "nav.breadcrumb ol li a"}
        result = extract_dom(response, selectors)
        assert "AI & Machine Learning" in result["categories"]
        assert "Home" not in result["categories"]

    def test_clean_html_removes_scripts(self):
        html = '<div><p>Content</p><script>evil()</script></div>'
        cleaned = clean_html(html)
        assert "evil" not in cleaned
        assert "Content" in cleaned


class TestImageExtractor:
    def test_extract_images(self, itl_article_html):
        response = _make_response(
            itl_article_html,
            url="https://www.insurancethoughtleadership.com/article/test",
        )
        images = extract_images(
            response,
            container_selector="div.article__body",
            base_url="https://www.insurancethoughtleadership.com",
        )
        assert len(images) == 1
        assert images[0]["alt"] == "AI Underwriting Process"
        assert images[0]["caption"] == "An illustration of AI-powered underwriting"
        assert "ai-underwriting.jpg" in images[0]["url"]

    def test_no_images(self):
        html = '<div class="body"><p>No images</p></div>'
        response = _make_response(html)
        images = extract_images(response, "div.body")
        assert images == []
