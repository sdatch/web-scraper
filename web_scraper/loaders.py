from itemloaders import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Identity

from web_scraper.items import ContentItem
from web_scraper.utils.date_utils import normalize_date


def strip_whitespace(value):
    if isinstance(value, str):
        return value.strip()
    return value


class ContentItemLoader(ItemLoader):
    default_item_class = ContentItem
    default_output_processor = TakeFirst()

    # Input processors
    title_in = MapCompose(strip_whitespace)
    author_in = MapCompose(strip_whitespace)
    description_in = MapCompose(strip_whitespace)
    date_published_in = MapCompose(strip_whitespace, normalize_date)
    category_in = MapCompose(strip_whitespace)
    publisher_in = MapCompose(strip_whitespace)

    # List fields use Identity (keep all values)
    categories_out = Identity()
    images_out = Identity()
    _missing_fields_out = Identity()
