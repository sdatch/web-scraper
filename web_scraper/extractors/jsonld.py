import json
import logging
from typing import Any

from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)


def _resolve_dot_path(data: dict, path: str) -> Any | None:
    """Navigate a nested dict using dot-separated keys (e.g., 'author.name')."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and current:
            current = current[0].get(part) if isinstance(current[0], dict) else None
        else:
            return None
        if current is None:
            return None
    return current


def extract_jsonld(response: HtmlResponse, field_map: dict,
                   type_filter: str | None = None) -> dict:
    """
    Extract structured data from JSON-LD script blocks.

    Args:
        response: Scrapy HtmlResponse
        field_map: Mapping of output field names to JSON-LD dot paths
        type_filter: If set, only process JSON-LD blocks matching this @type

    Returns:
        Dict of extracted fields.
    """
    scripts = response.css('script[type="application/ld+json"]::text').getall()
    result = {}

    for script_text in scripts:
        try:
            data = json.loads(script_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON-LD block on %s", response.url)
            continue

        # Handle @graph arrays
        items = data if isinstance(data, list) else data.get("@graph", [data])

        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            # Normalize type to string for comparison
            if isinstance(item_type, list):
                item_type = item_type[0] if item_type else ""

            if type_filter and item_type != type_filter:
                continue

            for output_field, json_path in field_map.items():
                if output_field not in result:
                    value = _resolve_dot_path(item, json_path)
                    if value is not None:
                        result[output_field] = value

    return result
