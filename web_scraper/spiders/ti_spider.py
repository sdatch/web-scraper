import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)

# Map URL path prefixes to content categories
PATH_CATEGORIES = {
    "/designations/": "Designations",
    "/ceu/": "CEU",
    "/agents-and-brokers/": "Agents & Brokers",
}


class TISpider(BaseSpider):
    """Spider for The Institutes (web.theinstitutes.org).

    Uses the sitemap for content discovery, filtering to designations,
    CEU, and agents-and-brokers paths. Extracts page data via JSON-LD
    (EducationalOccupationalProgram) with DOM fallback.
    """

    name = "ti"

    def __init__(self, site="ti", dry_run="false", *args, **kwargs):
        super().__init__(site=site, *args, **kwargs)
        self.dry_run = dry_run.lower() in ("true", "1", "yes")

    def start_requests(self):
        sitemap_url = self.config.get("sitemap_url")
        if sitemap_url:
            yield scrapy.Request(
                sitemap_url,
                callback=self.parse_sitemap,
                headers={"Accept": "application/xml, text/xml"},
            )
        else:
            logger.error("No sitemap_url configured for TI spider")

    def parse_sitemap(self, response):
        """Parse sitemap XML and yield requests for each matching URL."""
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError:
            logger.error("Failed to parse sitemap XML from %s", response.url)
            return

        # Handle standard sitemap namespace
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = root.findall(".//sm:url/sm:loc", ns)

        # Fallback: try without namespace
        if not urls:
            urls = root.findall(".//url/loc")

        discovered = 0
        for loc in urls:
            url = loc.text.strip() if loc.text else ""
            if not url or not self.url_allowed(url):
                continue

            discovered += 1
            if self.dry_run:
                logger.info("[DRY RUN] Discovered: %s", url)
                continue

            category = self._category_from_url(url)
            yield scrapy.Request(
                url,
                callback=self.parse_page,
                cb_kwargs={"sitemap_category": category},
            )

        logger.info(
            "Sitemap: discovered %d URLs (dry_run=%s)",
            discovered,
            self.dry_run,
        )

    def parse_page(self, response, sitemap_category=""):
        """Parse a content page: JSON-LD + DOM fallback + images."""
        jsonld_data = self.extract_jsonld_data(response)
        dom_data = self.extract_dom_data(response)
        merged = self.merge_extraction(jsonld_data, dom_data)
        images = self.extract_image_data(response)

        loader = ContentItemLoader(response=response)

        loader.add_value("title", merged.get("title"))
        loader.add_value("description", merged.get("description"))
        loader.add_value("body", merged.get("body"))
        loader.add_value("canonical_url", merged.get("canonical_url", response.url))
        loader.add_value("brand", self.brand)
        loader.add_value("content_type", "article")
        loader.add_value("category", sitemap_category)
        loader.add_value("publisher", "The Institutes")
        loader.add_value("source_url", response.url)
        loader.add_value("images", images)
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        yield loader.load_item()

    @staticmethod
    def _category_from_url(url: str) -> str:
        """Derive a content category from the URL path."""
        path = urlparse(url).path
        for prefix, category in PATH_CATEGORIES.items():
            if path.startswith(prefix):
                return category
        return ""
