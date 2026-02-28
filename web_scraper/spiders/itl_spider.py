import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class ITLSpider(BaseSpider):
    name = "itl"

    def __init__(self, site="itl", dry_run="false", *args, **kwargs):
        super().__init__(site=site, *args, **kwargs)
        self.dry_run = dry_run.lower() in ("true", "1", "yes")

    def start_requests(self):
        for entry in self.config.get("entry_points", []):
            url = entry["url"]
            category = entry.get("category", "")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_first_page,
                cb_kwargs={"category": category},
            )

    def parse_listing_first_page(self, response, category=""):
        """Parse first listing page: discover total pages and extract article links."""
        # Extract article links from this page
        yield from self._extract_article_links(response, category)

        # Discover total pages from "Last" pager link
        pagination = self.config.get("pagination", {})
        last_selector = pagination.get("last_page_selector", "")
        last_link = response.css(f"{last_selector}::attr(href)").get()

        if last_link:
            last_url = urljoin(response.url, last_link)
            parsed = urlparse(last_url)
            params = parse_qs(parsed.query)
            page_param = pagination.get("page_param", "page")
            try:
                last_page = int(params.get(page_param, [0])[0])
            except (ValueError, IndexError):
                last_page = 0

            # Request pages 1 through last_page (0-indexed, page 0 already parsed)
            for page_num in range(1, last_page + 1):
                page_url = self._build_page_url(response.url, page_param, page_num)
                yield scrapy.Request(
                    page_url,
                    callback=self.parse_listing_page,
                    cb_kwargs={"category": category},
                )

    def parse_listing_page(self, response, category=""):
        """Parse subsequent listing pages for article links."""
        yield from self._extract_article_links(response, category)

    def _extract_article_links(self, response, category):
        """Extract article links from a listing page."""
        link_selector = self.config.get("listing", {}).get("link_selector", "h5 a")
        links = response.css(f"{link_selector}::attr(href)").getall()

        for href in links:
            url = urljoin(response.url, href)
            if not self.url_allowed(url):
                continue
            if self.dry_run:
                logger.info("[DRY RUN] Discovered: %s", url)
                continue
            yield scrapy.Request(
                url,
                callback=self.parse_article,
                cb_kwargs={"listing_category": category},
            )

    def parse_article(self, response, listing_category=""):
        """Parse an article page: JSON-LD + DOM fallback + images."""
        jsonld_data = self.extract_jsonld_data(response)
        dom_data = self.extract_dom_data(response)
        merged = self.merge_extraction(jsonld_data, dom_data)
        images = self.extract_image_data(response)

        loader = ContentItemLoader(response=response)

        loader.add_value("title", merged.get("title"))
        loader.add_value("author", merged.get("author"))
        loader.add_value("date_published", merged.get("date_published"))
        loader.add_value("description", merged.get("description"))
        loader.add_value("body", merged.get("body"))
        loader.add_value("canonical_url", merged.get("canonical_url", response.url))
        loader.add_value("brand", self.brand)
        loader.add_value("content_type", "article")
        loader.add_value("category", merged.get("category") or listing_category)
        loader.add_value("categories", merged.get("categories", []))
        loader.add_value("images", images)
        loader.add_value("publisher", merged.get("publisher"))
        loader.add_value("source_url", response.url)
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        yield loader.load_item()

    def _build_page_url(self, base_url: str, page_param: str, page_num: int) -> str:
        """Build a paginated URL."""
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)
        params[page_param] = [str(page_num)]
        query = urlencode(params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}"
