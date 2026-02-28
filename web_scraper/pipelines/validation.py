import logging

from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["title", "body", "source_url"]


class ValidationPipeline:
    """Check required fields. Annotate missing fields but save partial items."""

    def process_item(self, item, spider):
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        if missing:
            item["_missing_fields"] = missing
            logger.warning(
                "Item from %s missing fields: %s",
                item.get("source_url", "unknown"),
                ", ".join(missing),
            )
        return item
