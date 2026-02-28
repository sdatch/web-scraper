import re
from urllib.parse import urlparse


def url_to_slug(url: str, max_length: int = 80) -> str:
    """Convert a URL path into a filesystem-safe slug."""
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if "/" in path else path
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug)
    slug = slug.strip("-").lower()
    return slug[:max_length] if slug else "index"
