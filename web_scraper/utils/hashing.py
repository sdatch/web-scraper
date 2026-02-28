import hashlib


def content_hash(text: str) -> str:
    """Compute SHA256 hash of content text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
