from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def itl_listing_html():
    return (FIXTURES_DIR / "itl_listing_page.html").read_text(encoding="utf-8")


@pytest.fixture
def itl_article_html():
    return (FIXTURES_DIR / "itl_article_page.html").read_text(encoding="utf-8")


@pytest.fixture
def itl_jsonld_sample():
    import json
    return json.loads((FIXTURES_DIR / "itl_jsonld_sample.json").read_text(encoding="utf-8"))
