import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)


def extract_images(response: HtmlResponse, container_selector: str,
                   base_url: str | None = None) -> list[dict]:
    """
    Extract image information from a content container.

    Returns list of dicts with keys: url, alt, caption
    """
    base_url = base_url or response.url
    container_html = response.css(container_selector).get()
    if not container_html:
        return []

    soup = BeautifulSoup(container_html, "lxml")
    images = []

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue

        url = urljoin(base_url, src)
        alt = img.get("alt", "").strip()

        # Look for figcaption in parent figure element
        caption = ""
        figure = img.find_parent("figure")
        if figure:
            figcaption = figure.find("figcaption")
            if figcaption:
                caption = figcaption.get_text(strip=True)

        images.append({
            "url": url,
            "alt": alt,
            "caption": caption,
        })

    return images
