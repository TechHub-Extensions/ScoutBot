BOT_NAME = "ScoutBot"

SPIDER_MODULES = ["scoutbot.spiders"]
NEWSPIDER_MODULE = "scoutbot.spiders"

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
    # Reddit requires a descriptive User-Agent or it returns 429/403.
    # Format: <platform>:<app ID>:<version> (by /u/<dev>)
    "User-Agent": (
        "python:scoutbot.opportunities-aggregator:v1.0 (by /u/scoutbot_ng)"
    ),
}

ITEM_PIPELINES = {
    "scoutbot.pipelines.DedupePipeline": 100,
    "scoutbot.pipelines.SheetsPipeline": 200,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 8
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
