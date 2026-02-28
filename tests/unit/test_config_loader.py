import pytest
from pathlib import Path

from web_scraper.utils.config_loader import deep_merge, load_merged_config, list_sites, load_site_config


CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"crawl": {"delay": 5, "timeout": 30}}
        override = {"crawl": {"delay": 10}}
        result = deep_merge(base, override)
        assert result["crawl"]["delay"] == 10
        assert result["crawl"]["timeout"] == 30

    def test_override_wins_for_non_dict(self):
        base = {"key": [1, 2]}
        override = {"key": [3, 4]}
        result = deep_merge(base, override)
        assert result["key"] == [3, 4]

    def test_does_not_mutate_inputs(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        deep_merge(base, override)
        assert "c" not in base["a"]


class TestLoadConfig:
    def test_load_merged_itl(self):
        config = load_merged_config("itl", config_dir=CONFIG_DIR)
        assert config["brand"] == "itl"
        assert config["crawl"]["download_delay"] == 8
        assert len(config["entry_points"]) > 0

    def test_missing_site_raises(self):
        with pytest.raises(FileNotFoundError):
            load_site_config("nonexistent", config_dir=CONFIG_DIR)

    def test_list_sites(self):
        sites = list_sites(config_dir=CONFIG_DIR)
        assert "itl" in sites
