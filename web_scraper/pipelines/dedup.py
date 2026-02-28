import logging
import sqlite3
from pathlib import Path

from scrapy.exceptions import DropItem

from web_scraper.utils.hashing import content_hash

logger = logging.getLogger(__name__)


class DedupPipeline:
    """SQLite-backed deduplication by URL and content hash."""

    def __init__(self, state_dir):
        self.state_dir = Path(state_dir)

    @classmethod
    def from_crawler(cls, crawler):
        state_dir = crawler.settings.get("STATE_DIR", "state")
        return cls(state_dir)

    def open_spider(self, spider):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        brand = getattr(spider, "brand", "default")
        db_path = self.state_dir / f"{brand}_dedup.db"
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS seen ("
            "  url TEXT PRIMARY KEY,"
            "  content_hash TEXT NOT NULL"
            ")"
        )
        self.conn.commit()

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        body = item.get("body", "")
        if body:
            item["_content_hash"] = content_hash(body)
        else:
            item["_content_hash"] = ""

        url = item.get("source_url") or item.get("canonical_url", "")
        if not url:
            return item

        cursor = self.conn.execute("SELECT content_hash FROM seen WHERE url = ?", (url,))
        row = cursor.fetchone()

        if row is None:
            # New URL — insert and pass
            self.conn.execute(
                "INSERT INTO seen (url, content_hash) VALUES (?, ?)",
                (url, item["_content_hash"]),
            )
            self.conn.commit()
            return item
        elif row[0] == item["_content_hash"]:
            # Same content — drop
            raise DropItem(f"Duplicate (unchanged): {url}")
        else:
            # Updated content — update and pass
            self.conn.execute(
                "UPDATE seen SET content_hash = ? WHERE url = ?",
                (item["_content_hash"], url),
            )
            self.conn.commit()
            logger.info("Content updated for %s", url)
            return item
