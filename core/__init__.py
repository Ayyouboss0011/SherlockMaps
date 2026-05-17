"""GoogleMapsCrawler - Professional Open Source Google Maps Webcrawler.

Extract company information from Google Maps with ease.
Supports JSON, CSV, and pretty-printed output formats.

Packages:
    - models: Data models (CompanyData, CrawlerConfig)
    - exceptions: Custom exceptions
    - browser: Browser management
    - extractors: Data extraction
    - processors: Data processing (validation, deduplication)
    - output: Output handling

Usage:
    from core.models import CrawlerConfig
    from core.crawler import GoogleMapsCrawler

    config = CrawlerConfig(search_prompt="restaurants berlin")
    with GoogleMapsCrawler(config) as crawler:
        results = crawler.crawl()
"""

__version__ = "2.0.0"
__author__ = "GoogleMapsCrawler Contributors"

from core.crawler import GoogleMapsCrawler, run_crawler
from core.models import CompanyData, CrawlerConfig, ViewPort
from core.exceptions import (
    CrawlerBaseException,
    BrowserInitializationError,
    ExtractionError,
    NavigationError,
)

__all__ = [
    # Version
    "__version__",
    # Classes
    "GoogleMapsCrawler",
    "CompanyData",
    "CrawlerConfig",
    "ViewPort",
    # Functions
    "run_crawler",
    # Exceptions
    "CrawlerBaseException",
    "BrowserInitializationError",
    "ExtractionError",
    "NavigationError",
]