import json
import logging
from datetime import datetime
from pathlib import Path

from web_scraper.utils.slug import url_to_slug

logger = logging.getLogger(__name__)


class JsonOutputPipeline:
    """Write each item as a JSON file with structured filename."""

    def __init__(self, output_dir, indent):
        self.output_dir = Path(output_dir)
        self.indent = indent

    @classmethod
    def from_crawler(cls, crawler):
        output_dir = crawler.settings.get("OUTPUT_DIR", "output")
        indent = crawler.settings.getint("OUTPUT_INDENT", 2)
        return cls(output_dir, indent)

    def open_spider(self, spider):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_item(self, item, spider):
        brand = item.get("brand", "unknown")
        content_type = item.get("content_type", "content")
        date = item.get("date_published", "")
        date_str = date.replace("-", "") if date else datetime.now().strftime("%Y%m%d")
        slug = url_to_slug(item.get("source_url", "") or item.get("canonical_url", ""))

        filename = f"{brand}_{content_type}_{date_str}_{slug}.json"
        filepath = self.output_dir / filename

        # Handle collisions
        counter = 1
        while filepath.exists():
            filename = f"{brand}_{content_type}_{date_str}_{slug}_{counter}.json"
            filepath = self.output_dir / filename
            counter += 1

        # Convert item to serializable dict
        data = dict(item)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=self.indent, ensure_ascii=False, default=str)

        logger.info("Saved: %s", filepath)
        return item
