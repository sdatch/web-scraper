from pathlib import Path

from web_scraper.utils.config_loader import load_defaults

# Load defaults from YAML
_defaults = load_defaults()
_crawl = _defaults.get("crawl", {})
_output = _defaults.get("output", {})
_state = _defaults.get("state", {})
_logging = _defaults.get("logging", {})

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOT_NAME = "web_scraper"
SPIDER_MODULES = ["web_scraper.spiders"]
NEWSPIDER_MODULE = "web_scraper.spiders"

# Crawl settings from config
DOWNLOAD_DELAY = _crawl.get("download_delay", 8)
CONCURRENT_REQUESTS = _crawl.get("concurrent_requests", 3)
DOWNLOAD_TIMEOUT = _crawl.get("request_timeout", 30)
RETRY_TIMES = _crawl.get("max_retries", 3)
ROBOTSTXT_OBEY = _crawl.get("obey_robots_txt", False)
USER_AGENT = _crawl.get("user_agent", "Scrapy")

# Output settings
OUTPUT_DIR = str(PROJECT_ROOT / _output.get("directory", "output"))
OUTPUT_INDENT = _output.get("indent", 2)

# State settings
STATE_DIR = str(PROJECT_ROOT / _state.get("directory", "state"))

# Logging
LOG_DIR = str(PROJECT_ROOT / _logging.get("directory", "logs"))
LOG_LEVEL = _logging.get("level", "INFO")

# Pipeline order: validation → dedup → json output
ITEM_PIPELINES = {
    "web_scraper.pipelines.validation.ValidationPipeline": 100,
    "web_scraper.pipelines.dedup.DedupPipeline": 200,
    "web_scraper.pipelines.json_output.JsonOutputPipeline": 300,
}

# Downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    "web_scraper.middlewares.captcha_middleware.CaptchaDetectionMiddleware": 543,
    "web_scraper.middlewares.retry_middleware.ExponentialBackoffRetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,  # Disable default
}

# Misc
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
