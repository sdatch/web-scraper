import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import scrapy

from web_scraper.spiders.base_spider import BaseSpider
from web_scraper.loaders import ContentItemLoader

logger = logging.getLogger(__name__)


class CLMSpider(BaseSpider):
    """Spider for The CLM Magazine (theclm.org/Magazine).

    Two discovery paths:
      - Listing pages (/Magazine/ and /Magazine/topic/*) link directly
        to articles via a.article-link.
      - The /Magazine/Home/Archive page links to past Edition pages,
        each of which lists that issue's articles.
    No JSON-LD on this site; extraction is DOM-only. The publication
    date is plain text in <span class="artdate">.
    """

    name = "clm"

    def __init__(self, site="clm", dry_run="false", *args, **kwargs):
        super().__init__(site=site, *args, **kwargs)
        self.dry_run = dry_run.lower() in ("true", "1", "yes")
        self._seen_urls = set()
        self._seen_editions = set()

    def start_requests(self):
        for entry in self.config.get("entry_points", []):
            url = entry["url"]
            category = entry.get("category", "")
            if "/Home/Archive" in url:
                yield scrapy.Request(
                    url,
                    callback=self.parse_archive,
                    cb_kwargs={"category": category},
                )
            else:
                yield scrapy.Request(
                    url,
                    callback=self.parse_listing,
                    cb_kwargs={"category": category},
                )

    def parse_archive(self, response, category=""):
        """Archive index: each row links to an Edition page that lists articles."""
        edition_selector = self.config.get("listing", {}).get(
            "edition_selector", "a[href*='Editions/']"
        )
        hrefs = response.css(f"{edition_selector}::attr(href)").getall()
        for href in hrefs:
            url = urljoin(response.url, href)
            if url in self._seen_editions:
                continue
            self._seen_editions.add(url)
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                cb_kwargs={"category": category},
            )

    def parse_listing(self, response, category=""):
        """Listing or edition page: extract /Magazine/articles/ links."""
        link_selector = self.config.get("listing", {}).get(
            "link_selector", "a.article-link"
        )
        hrefs = response.css(f"{link_selector}::attr(href)").getall()

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
            category or "current",
            response.url,
            discovered,
            self.dry_run,
        )

    def parse_article(self, response, listing_category=""):
        dom_data = self.extract_dom_data(response)
        images = self.extract_image_data(response)

        date_text = response.css("span.artdate::text").get()
        date_published = date_text.strip() if date_text else None

        loader = ContentItemLoader(response=response)
        loader.add_value("title", dom_data.get("title"))
        loader.add_value("author", dom_data.get("author"))
        loader.add_value("date_published", date_published)
        loader.add_value("body", dom_data.get("body"))
        loader.add_value("canonical_url", response.url)
        loader.add_value("brand", self.brand)
        loader.add_value("content_type", "article")
        loader.add_value("category", listing_category)
        loader.add_value(
            "categories", [listing_category] if listing_category else []
        )
        loader.add_value("images", images)
        loader.add_value("publisher", "The CLM")
        loader.add_value("source_url", response.url)
        loader.add_value("_scraped_at", datetime.now(timezone.utc).isoformat())

        yield loader.load_item()
