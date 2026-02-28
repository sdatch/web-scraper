import logging
import re

from bs4 import BeautifulSoup, Comment
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

STRIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"}


def clean_html(html: str) -> str:
    """Remove scripts, styles, ads, and nav elements from HTML body content."""
    soup = BeautifulSoup(html, "lxml")

    # Remove unwanted tags
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return str(soup)


def extract_body(response: HtmlResponse, selector: str) -> str | None:
    """Extract and clean body content from a DOM selector."""
    element = response.css(selector).get()
    if not element:
        return None
    return clean_html(element)


def extract_text(response: HtmlResponse, selector: str) -> str | None:
    """Extract text content from a CSS selector."""
    text = response.css(f"{selector}::text").get()
    if text:
        return text.strip()
    # Try getting all text within the element
    element = response.css(selector).get()
    if element:
        soup = BeautifulSoup(element, "lxml")
        return soup.get_text(strip=True)
    return None


def extract_date_from_time(response: HtmlResponse, selector: str) -> str | None:
    """Extract datetime attribute from <time> elements."""
    return response.css(f"{selector}::attr(datetime)").get()


def extract_categories(response: HtmlResponse, selector: str) -> list[str]:
    """Extract category names from breadcrumb or similar navigation."""
    links = response.css(f"{selector}::text").getall()
    # Filter out generic crumbs like "Home"
    return [c.strip() for c in links if c.strip().lower() not in ("home", "")]


def extract_dom(response: HtmlResponse, selectors: dict) -> dict:
    """
    Extract article data using DOM selectors as fallback.

    Args:
        response: Scrapy HtmlResponse
        selectors: Dict of field names to CSS selectors

    Returns:
        Dict of extracted fields.
    """
    result = {}

    if "body" in selectors:
        body = extract_body(response, selectors["body"])
        if body:
            result["body"] = body

    if "title" in selectors:
        title = extract_text(response, selectors["title"])
        if title:
            result["title"] = title

    if "date" in selectors:
        date = extract_date_from_time(response, selectors["date"])
        if date:
            result["date_published"] = date

    if "category" in selectors:
        categories = extract_categories(response, selectors["category"])
        if categories:
            result["categories"] = categories
            result["category"] = categories[-1] if categories else None

    if "author" in selectors:
        author = extract_text(response, selectors["author"])
        if author:
            result["author"] = author

    return result
