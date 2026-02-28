from web_scraper.utils.hashing import content_hash


class TestContentHash:
    def test_deterministic(self):
        text = "Hello, world!"
        assert content_hash(text) == content_hash(text)

    def test_different_content_different_hash(self):
        assert content_hash("foo") != content_hash("bar")

    def test_sha256_length(self):
        result = content_hash("test")
        assert len(result) == 64  # SHA256 hex digest length

    def test_empty_string(self):
        result = content_hash("")
        assert len(result) == 64
