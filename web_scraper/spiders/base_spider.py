import re
import logging

import scrapy

from web_scraper.utils.config_loader import load_merged_config
from web_scraper.extractors.jsonld import extract_jsonld
from web_scraper.extractors.dom_fallback import extract_dom
from web_scraper.extractors.image_extractor import extract_images

logger = logging.getLogger(__name__)


class BaseSpider(scrapy.Spider):
    """Base spider that loads config and provides extraction helpers."""

    def __init__(self, site: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not site:
            raise ValueError("Must provide 'site' argument")
        self.site = site
        self.config = load_merged_config(site)
        self.brand = self.config.get("brand", site)

        # Compile URL filters
        include = self.config.get("url_filters", {}).get("include", [])
        exclude = self.config.get("url_filters", {}).get("exclude", [])
        self._include_patterns = [re.compile(p) for p in include]
        self._exclude_patterns = [re.compile(p) for p in exclude]

    def url_allowed(self, url: str) -> bool:
        """Check URL against include/exclude filters."""
        if self._include_patterns:
            if not any(p.search(url) for p in self._include_patterns):
                return False
        if any(p.search(url) for p in self._exclude_patterns):
            return False
        return True

    def extract_jsonld_data(self, response):
        """Extract data from JSON-LD using site config."""
        extraction = self.config.get("extraction", {})
        jsonld_config = extraction.get("jsonld", {})
        if not jsonld_config.get("enabled", False):
            return {}
        return extract_jsonld(
            response,
            field_map=jsonld_config.get("field_map", {}),
            type_filter=jsonld_config.get("type_filter"),
        )

    def extract_dom_data(self, response):
        """Extract data from DOM using site config selectors."""
        extraction = self.config.get("extraction", {})
        dom_config = extraction.get("dom_fallback", {})
        if not dom_config.get("enabled", False):
            return {}
        return extract_dom(response, selectors=dom_config.get("selectors", {}))

    def extract_image_data(self, response):
        """Extract images using site config."""
        extraction = self.config.get("extraction", {})
        img_config = extraction.get("images", {})
        container = img_config.get("container")
        if not container:
            return []
        return extract_images(
            response,
            container_selector=container,
            base_url=img_config.get("base_url"),
        )

    def merge_extraction(self, jsonld_data: dict, dom_data: dict) -> dict:
        """Merge extractions. JSON-LD wins, DOM fills gaps."""
        merged = dict(dom_data)
        merged.update({k: v for k, v in jsonld_data.items() if v is not None})
        return merged
