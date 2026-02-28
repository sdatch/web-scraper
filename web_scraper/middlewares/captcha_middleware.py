import logging
import re

from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

CAPTCHA_INDICATORS = [
    re.compile(r"captcha", re.IGNORECASE),
    re.compile(r"challenge-form", re.IGNORECASE),
    re.compile(r"cf-turnstile", re.IGNORECASE),
    re.compile(r"recaptcha", re.IGNORECASE),
    re.compile(r"hcaptcha", re.IGNORECASE),
]


class CaptchaDetectionMiddleware:
    """Detect CAPTCHA responses and skip them."""

    def process_response(self, request, response, spider):
        if not isinstance(response, HtmlResponse):
            return response

        body_snippet = response.text[:5000] if response.text else ""

        for pattern in CAPTCHA_INDICATORS:
            if pattern.search(body_snippet):
                logger.warning(
                    "CAPTCHA detected on %s — skipping",
                    request.url,
                )
                request.meta["captcha_detected"] = True
                # Return response but flag it; spider can check meta
                return response

        return response
