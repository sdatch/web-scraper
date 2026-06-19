import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class IISSpider(BaseSpider):
    """Spider for International Insurance Society (internationalinsurance.org).

    Uses paginated listing pages for content discovery. Follows "next" page
    links to traverse all pages. Extracts article data via DOM selectors
    (no JSON-LD; site uses inline RDFa).
    """

    name = "iis"

    def __init__(self, site="iis", dry_run="false", *args, **kwargs):
        super().__init__(site=site, *args, **kwargs)
        self.dry_run = dry_run.lower() in ("true", "1", "yes")
        self._seen_urls = set()

    def start_requests(self):
        for entry in self.config.get("entry_points", []):
            url = entry["url"]
            category = entry.get("category", "")
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                cb_kwargs={"category": category},
            )

    def parse_listing(self, response, category=""):
        """Parse a listing page: extract article links and follow next page."""
        yield from self._extract_article_links(response, category)

        # Follow "next" pagination link
        next_selector = (
            self.config.get("pagination", {}).get("next_page_selector", "")
        )
        if next_selector:
            next_href = response.css(f"{next_selector}::attr(href)").get()
            if next_href:
                next_url = urljoin(response.url, next_href)
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_listing,
                    cb_kwargs={"category": category},
                )

    def _extract_article_links(self, response, category):
        """Extract article links from a listing page."""
        link_selector = self.config.get("listing", {}).get("link_selector", "a")
        links = response.css(f"{link_selector}::attr(href)").getall()

        for href in links:
            url = urljoin(response.url, href)
            if url in self._seen_urls or not self.url_allowed(url):
                continue
            self._seen_urls.add(url)

            if self.dry_run:
                logger.info("[DRY RUN] Discovered: %s", url)
                continue
            yield scrapy.Request(
                url,
                callback=self.parse_article,
                cb_kwargs={"listing_category": category},
            )

    def parse_article(self, response, listing_category=""):
        """Parse an article page using DOM extraction."""
        dom_data = self.extract_dom_data(response)
        images = self.extract_image_data(response)

        # Extract date from RDFa content attribute (not <time datetime>)
        date_published = response.css(
            'span[property="schema:dateCreated"]::attr(content)'
        ).get()

        # Extract tags as additional categories
        tags = response.css(
            "div.field--name-field-tags .field__item a::text"
        ).getall()
        tags = [t.strip() for t in tags if t.strip()]

        loader = ContentItemLoader(response=response)

        loader.add_value("title", dom_data.get("title"))
        loader.add_value("author", dom_data.get("author"))
        loader.add_value("date_published", date_published)
        loader.add_value("body", dom_data.get("body"))
        loader.add_value("canonical_url", response.url)
        loader.add_value("brand", self.brand)
        loader.add_value("content_type", "article")
        loader.add_value("source_url", response.url)
        loader.add_value("images", images)
        loader.add_value("publisher", "International Insurance Society")
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        # Categories from DOM topics + tags
        categories = dom_data.get("categories", [])
        if tags:
            categories = categories + [t for t in tags if t not in categories]
        if categories:
            loader.add_value("categories", categories)
            loader.add_value("category", categories[0])
        else:
            loader.add_value("category", listing_category)

        yield loader.load_item()
