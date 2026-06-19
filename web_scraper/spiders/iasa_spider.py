import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class IASASpider(BaseSpider):
    """Spider for Insurance Accounting & Systems Association (iasa.org).

    Uses listing pages for content discovery. Two entry points under
    the Insights tab: Insurance Insights and IASA News. No pagination;
    all articles are rendered on a single listing page per section.
    """

    name = "iasa"

    def __init__(self, site="iasa", dry_run="false", *args, **kwargs):
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
        """Parse a listing page and yield requests for each article link."""
        link_selector = self.config.get("listing", {}).get(
            "link_selector", "#mainContentWrapper a[href*='.aspx']"
        )
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
        """Parse an article page using DOM extraction."""
        dom_data = self.extract_dom_data(response)
        images = self.extract_image_data(response)

        loader = ContentItemLoader(response=response)

        loader.add_value("title", dom_data.get("title"))
        loader.add_value("body", dom_data.get("body"))
        loader.add_value("canonical_url", response.url)
        loader.add_value("brand", self.brand)
        loader.add_value("content_type", "article")
        loader.add_value("category", listing_category)
        loader.add_value("categories", [listing_category] if listing_category else [])
        loader.add_value("images", images)
        loader.add_value("source_url", response.url)
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        yield loader.load_item()
