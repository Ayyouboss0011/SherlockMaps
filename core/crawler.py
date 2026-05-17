"""Main crawler orchestrator for the GoogleMapsCrawler.

This module provides the main GoogleMapsCrawler class that orchestrates
the entire crawling process: browser management, data extraction,
processing, and output.

Usage:
    from core.models import CrawlerConfig
    from core.crawler import GoogleMapsCrawler

    config = CrawlerConfig(search_prompt="restaurants berlin")

    with GoogleMapsCrawler(config) as crawler:
        results = crawler.crawl()
"""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

# Add the parent directory to sys.path so that `from core.*` imports work
# This allows running from both the root directory and from within the core directory
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.browser import BrowserManager
from core.extractors import MapsExtractor
from core.exceptions import CrawlerBaseException
from core.models import CompanyData, CrawlerConfig
from core.output import OutputHandler
from core.processors import DeduplicationProcessor, URLValidator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GoogleMapsCrawler:
    """Main crawler class that orchestrates the entire scraping process.

    This class coordinates all the components:
    1. BrowserManager - Manages the Playwright browser
    2. MapsExtractor - Extracts company data from Google Maps
    3. DeduplicationProcessor - Removes duplicate companies
    4. URLValidator - Validates website URLs
    5. OutputHandler - Formats and outputs results

    Usage:
        config = CrawlerConfig(search_prompt="restaurants berlin")
        crawler = GoogleMapsCrawler(config)
        crawler.start()
        results = crawler.get_results()
        crawler.close()

    Or with context manager:
        with GoogleMapsCrawler(config) as crawler:
            results = crawler.crawl()
    """

    def __init__(self, config: CrawlerConfig) -> None:
        """Initialize the GoogleMapsCrawler.

        Args:
            config: The crawler configuration.
        """
        self._config = config
        self._browser_manager: BrowserManager | None = None
        self._results: list[CompanyData] = []
        self._is_started = False

    @property
    def config(self) -> CrawlerConfig:
        """Get the crawler configuration.

        Returns:
            The CrawlerConfig instance.
        """
        return self._config

    @property
    def results(self) -> list[CompanyData]:
        """Get the crawl results.

        Returns:
            A list of CompanyData objects.
        """
        return self._results

    @property
    def is_started(self) -> bool:
        """Check if the crawler has been started.

        Returns:
            True if started, False otherwise.
        """
        return self._is_started

    def start(self) -> "GoogleMapsCrawler":
        """Start the crawler and initialize all components.

        Returns:
            self for method chaining.

        Raises:
            CrawlerBaseException: If initialization fails.
        """
        logger.info("Starting GoogleMapsCrawler for prompt: %s", self._config.search_prompt)

        # Initialize browser manager
        self._browser_manager = BrowserManager(self._config)
        self._browser_manager.initialize()
        self._is_started = True

        return self

    def crawl(self, prompt: str | None = None) -> list[CompanyData]:
        """Run the complete crawl process.

        This method:
        1. Navigates to Google Maps search results
        2. Extracts company data
        3. Removes duplicates
        4. Filters invalid websites
        5. Outputs results

        Args:
            prompt: Optional search prompt override. Uses config if not provided.

        Returns:
            A list of CompanyData objects.
        """
        search_prompt = prompt or self._config.search_prompt

        if not search_prompt:
            logger.error("No search prompt provided")
            return []

        if not self._is_started:
            self.start()

        if not self._browser_manager:
            logger.error("Browser manager not initialized")
            return []

        try:
            # Step 1: Navigate to Google Maps
            page = self._browser_manager.navigate_to_maps(search_prompt)

            # Step 2: Extract company data
            extractor = MapsExtractor(page, self._config.selector_timeout)
            raw_results = extractor.extract_all()

            if not raw_results:
                logger.warning("No companies found for prompt: %s", search_prompt)
                self._results = []
                return []

            logger.info("Extracted %d raw companies", len(raw_results))

            # Step 3: Remove duplicates
            deduplicator = DeduplicationProcessor()
            unique_results = deduplicator.process(raw_results)

            # Step 4: Filter valid websites
            valid_results = [c for c in unique_results if URLValidator.is_valid(c.website)]

            self._results = valid_results
            logger.info(
                "Crawl complete. Found %d companies with valid websites",
                len(valid_results),
            )

            # Step 5: Output results
            output_handler = OutputHandler()
            output_handler.output(valid_results, search_prompt, self._config.output_format)

            return valid_results

        except CrawlerBaseException as e:
            logger.error("Crawler error: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error during crawl: %s", e)
            raise
        # Don't close browser here - let the user control the lifecycle

    def get_results(self) -> list[CompanyData]:
        """Get the results from the last crawl.

        Returns:
            A list of CompanyData objects.
        """
        return self._results

    def close(self) -> None:
        """Close the crawler and clean up resources."""
        logger.info("Closing GoogleMapsCrawler...")

        if self._browser_manager:
            self._browser_manager.close()

        self._is_started = False
        logger.info("GoogleMapsCrawler closed")

    def __enter__(self) -> "GoogleMapsCrawler":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


def run_crawler(
    prompt: str,
    headless: bool = False,
    output_format: str = "json",
) -> list[CompanyData]:
    """Convenience function to run a crawl with default settings.

    Args:
        prompt: The search term (e.g., "restaurants berlin").
        headless: Whether to run the browser in headless mode.
        output_format: The output format.

    Returns:
        A list of CompanyData objects.
    """
    config = CrawlerConfig(
        search_prompt=prompt,
        headless=headless,
        output_format=output_format,
    )

    with GoogleMapsCrawler(config) as crawler:
        return crawler.crawl()
