import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class RIHSpider(BaseSpider):
    """Spider for Risk & Insurance (riskandinsurance.com).

    Crawls each configured /category/ page, follows pagination via the
    rel="next" link, and extracts articles. Article pages have a Yoast
    JSON-LD graph (type WebPage) which provides datePublished cleanly;
    title, body, author and topic tags come from the DOM.
    """

    name = "rih"

    def __init__(self, site="rih", dry_run="false", *args, **kwargs):
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
        yield from self._extract_article_links(response, category)

        next_selector = self.config.get("pagination", {}).get(
            "next_page_selector", ""
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
        listing_config = self.config.get("listing", {})
        link_xpath = listing_config.get("link_xpath")
        link_selector = listing_config.get("link_selector")

        if link_xpath:
            hrefs = response.xpath(link_xpath).getall()
        elif link_selector:
            hrefs = response.css(f"{link_selector}::attr(href)").getall()
        else:
            hrefs = []

        discovered = 0
        for href in hrefs:
            url = urljoin(response.url, href)
            if url in self._seen_urls or not self.url_allowed(url):
                continue
            self._seen_urls.add(url)

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
            "Listing %s (%s): discovered %d article URLs (dry_run=%s)",
            category,
            response.url,
            discovered,
            self.dry_run,
        )

    def parse_article(self, response, listing_category=""):
        jsonld_data = self.extract_jsonld_data(response)
        dom_data = self.extract_dom_data(response)
        merged = self.merge_extraction(jsonld_data, dom_data)
        images = self.extract_image_data(response)

        loader = ContentItemLoader(response=response)
        loader.add_value("title", merged.get("title"))
        loader.add_value("author", merged.get("author"))
        loader.add_value("date_published", merged.get("date_published"))
        loader.add_value("body", merged.get("body"))
        loader.add_value(
            "canonical_url", merged.get("canonical_url", response.url)
        )
        loader.add_value("brand", self.brand)
        loader.add_value("content_type", "article")
        loader.add_value("source_url", response.url)
        loader.add_value("images", images)
        loader.add_value("publisher", "Risk & Insurance")
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        categories = merged.get("categories", [])
        if categories:
            loader.add_value("categories", categories)
            loader.add_value("category", categories[0])
        else:
            loader.add_value("category", listing_category)
            loader.add_value(
                "categories", [listing_category] if listing_category else []
            )

        yield loader.load_item()
