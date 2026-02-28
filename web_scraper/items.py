import scrapy


class ContentItem(scrapy.Item):
    # Core fields
    title = scrapy.Field()
    author = scrapy.Field()
    date_published = scrapy.Field()
    description = scrapy.Field()
    body = scrapy.Field()
    canonical_url = scrapy.Field()

    # Classification
    brand = scrapy.Field()
    content_type = scrapy.Field()
    category = scrapy.Field()
    categories = scrapy.Field()

    # Media
    images = scrapy.Field()

    # Source metadata
    publisher = scrapy.Field()
    source_url = scrapy.Field()

    # Pipeline-populated
    _content_hash = scrapy.Field()
    _scraped_at = scrapy.Field()
    _missing_fields = scrapy.Field()

    # Metadata bag for extras
    metadata = scrapy.Field()
