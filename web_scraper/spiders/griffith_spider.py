import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class GriffithSpider(BaseSpider):
    """Spider for The Institutes Griffith Foundation (griffithfoundation.org).

    Uses listing pages for content discovery. Three entry points: News,
    Programming, and Thought Leadership. No pagination; all articles are
    rendered on a single listing page per section.
    """

    name = "griffith"

    def __init__(self, site="griffith", dry_run="false", *args, **kwargs):
        super().__init__(site=site, *args, **kwargs)
        self.dry_run = dry_run.lower() in ("true", "1", "yes")

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
        """Parse a listing page and yield requests for each article link.

        News and Thought Leadership pages use "Read More" links to point to
        full articles. Programming uses heading title links instead.
        """
        listing_config = self.config.get("listing", {})
        read_more_xpath = listing_config.get("read_more_xpath")
        link_selector = listing_config.get("link_selector", "h2 a[href]")

        # Try "Read More" links first, fall back to CSS title links
        links = []
        if read_more_xpath:
            links = response.xpath(read_more_xpath).getall()
        if not links:
            links = response.css(f"{link_selector}::attr(href)").getall()

        seen = set()
        discovered = 0
        for href in links:
            url = urljoin(response.url, href)
            if not self.url_allowed(url) or url in seen:
                continue
            seen.add(url)

            discovered += 1
            if self.dry_run:
                logger.info("[DRY RUN] Discovered: %s", url)
                continue

            yield scrapy.Request(
                url,
                callback=self.parse_article,
                cb_kwargs={"listing_category": category},
            )

        logger.info(
            "Listing %s: discovered %d article URLs (dry_run=%s)",
            category,
            discovered,
            self.dry_run,
        )

    def parse_article(self, response, listing_category=""):
        """Parse an article page using JSON-LD + DOM fallback."""
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
        loader.add_value("categories", merged.get("categories", [listing_category]))
        loader.add_value("images", images)
        loader.add_value("publisher", merged.get("publisher"))
        loader.add_value("source_url", response.url)
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        yield loader.load_item()
