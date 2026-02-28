import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from web_scraper.items import ContentItem
from web_scraper.pipelines.validation import ValidationPipeline
from web_scraper.pipelines.dedup import DedupPipeline
from web_scraper.pipelines.json_output import JsonOutputPipeline


def _make_item(**kwargs):
    item = ContentItem()
    defaults = {
        "title": "Test Article",
        "body": "<p>Article body content</p>",
        "source_url": "https://example.com/article/test",
        "brand": "test",
        "content_type": "article",
        "date_published": "2024-11-15",
        "canonical_url": "https://example.com/article/test",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        item[k] = v
    return item


class TestValidationPipeline:
    def setup_method(self):
        self.pipeline = ValidationPipeline()
        self.spider = MagicMock()

    def test_valid_item_passes(self):
        item = _make_item()
        result = self.pipeline.process_item(item, self.spider)
        assert "_missing_fields" not in result or result["_missing_fields"] == []

    def test_missing_title_annotated(self):
        item = _make_item(title=None)
        result = self.pipeline.process_item(item, self.spider)
        assert "title" in result["_missing_fields"]

    def test_missing_body_annotated(self):
        item = _make_item(body=None)
        result = self.pipeline.process_item(item, self.spider)
        assert "body" in result["_missing_fields"]

    def test_partial_item_not_dropped(self):
        item = _make_item(title=None, body=None)
        result = self.pipeline.process_item(item, self.spider)
        assert result is not None  # Should not raise DropItem


class TestDedupPipeline:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pipeline = DedupPipeline(self.tmpdir)
        self.spider = MagicMock()
        self.spider.brand = "test"
        self.pipeline.open_spider(self.spider)

    def teardown_method(self):
        self.pipeline.close_spider(self.spider)

    def test_new_item_passes(self):
        item = _make_item()
        result = self.pipeline.process_item(item, self.spider)
        assert result is not None
        assert "_content_hash" in result

    def test_duplicate_item_dropped(self):
        from scrapy.exceptions import DropItem
        item = _make_item()
        self.pipeline.process_item(item, self.spider)
        with pytest.raises(DropItem):
            self.pipeline.process_item(_make_item(), self.spider)

    def test_updated_item_passes(self):
        item1 = _make_item()
        self.pipeline.process_item(item1, self.spider)
        item2 = _make_item(body="<p>Updated content</p>")
        result = self.pipeline.process_item(item2, self.spider)
        assert result is not None


class TestJsonOutputPipeline:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pipeline = JsonOutputPipeline(self.tmpdir, indent=2)
        self.spider = MagicMock()
        self.pipeline.open_spider(self.spider)

    def test_writes_json_file(self):
        item = _make_item()
        self.pipeline.process_item(item, self.spider)
        files = list(Path(self.tmpdir).glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["title"] == "Test Article"

    def test_filename_format(self):
        item = _make_item()
        self.pipeline.process_item(item, self.spider)
        files = list(Path(self.tmpdir).glob("*.json"))
        name = files[0].name
        assert name.startswith("test_article_20241115_")
        assert name.endswith(".json")

    def test_collision_handling(self):
        item = _make_item()
        self.pipeline.process_item(item, self.spider)
        # Write same item again — should get suffixed filename
        item2 = _make_item()
        self.pipeline.process_item(item2, self.spider)
        files = list(Path(self.tmpdir).glob("*.json"))
        assert len(files) == 2
