import logging
import time

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)


class ExponentialBackoffRetryMiddleware(RetryMiddleware):
    """Retry middleware with exponential backoff for 429 responses."""

    def __init__(self, settings):
        super().__init__(settings)
        self.base_delay = settings.getfloat("RETRY_BASE_DELAY", 2.0)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        if response.status == 429:
            retries = request.meta.get("retry_times", 0)
            delay = self.base_delay * (2 ** retries)
            logger.warning(
                "Rate limited (429) on %s — backing off %.1fs (retry %d)",
                request.url, delay, retries + 1,
            )
            # Set download delay for this request's retry
            request.meta["download_slot_delay"] = delay
            return self._retry(request, response_status_message(response.status), spider) or response

        return super().process_response(request, response, spider)
