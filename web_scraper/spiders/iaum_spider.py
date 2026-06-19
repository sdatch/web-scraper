import logging
from datetime import datetime, timezone
from urllib.parse import urljoin
from xml.etree import ElementTree

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class IAUMSpider(BaseSpider):
    """Spider for Insurance Assets Under Management (insuranceaum.com).

    Uses the sitemap for content discovery since category listing pages
    are not reliably accessible. Extracts article data via JSON-LD
    (NewsArticle) with DOM fallback.
    """

    name = "iaum"

    def __init__(self, site="iaum", dry_run="false", *args, **kwargs):
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
            logger.error("No sitemap_url configured for IAUM spider")

    def parse_sitemap(self, response):
        """Parse sitemap XML and yield requests for each article URL."""
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

            yield scrapy.Request(url, callback=self.parse_article)

        logger.info(
            "Sitemap: discovered %d article URLs (dry_run=%s)",
            discovered,
            self.dry_run,
        )

    def parse_article(self, response):
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
        loader.add_value("publisher", merged.get("publisher"))
        loader.add_value("source_url", response.url)
        loader.add_value("images", images)
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        # Categories from JSON-LD "about" field (list of strings)
        categories = merged.get("categories", [])
        if isinstance(categories, list):
            loader.add_value("categories", categories)
            if categories:
                loader.add_value("category", categories[0])
        elif isinstance(categories, str):
            loader.add_value("category", categories)
            loader.add_value("categories", [categories])

        yield loader.load_item()
