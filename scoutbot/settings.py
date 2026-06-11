BOT_NAME = "ScoutBot"

SPIDER_MODULES = ["scoutbot.spiders"]
NEWSPIDER_MODULE = "scoutbot.spiders"

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

ITEM_PIPELINES = {
    "scoutbot.pipelines.DedupePipeline": 100,
    # "scoutbot.pipelines.GeminiPipeline": 150,  # Gemini AI scoring — see gemini_scoring.py
    #   Removed from active pipeline: free-tier quota (1,500 req/day) was exhausted by test runs,
    #   extending run times from ~2 min to 6–8 min due to 60s retry waits on HTTP 429.
    #   Score distribution clustered 6–8 for nearly all items that passed keyword filters,
    #   providing little additional signal. Code preserved in gemini_scoring.py for future use
    #   if a paid tier or improved quota becomes available.
    "scoutbot.pipelines.SheetsPipeline": 200,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 8
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
