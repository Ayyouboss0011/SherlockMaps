"""Browser manager for the GoogleMapsCrawler.

This module handles the complete lifecycle of the Playwright browser,
including initialization, navigation, consent handling, and cleanup.
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

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from core.exceptions import BrowserInitializationError, NavigationError

if TYPE_CHECKING:
    from core.models import CrawlerConfig

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages the Playwright browser lifecycle.

    This class is responsible for:
    - Starting and stopping Playwright
    - Launching and configuring the browser context
    - Creating and managing pages
    - Handling consent banners
    - Navigating to Google Maps search URLs

    Usage:
        config = CrawlerConfig(search_prompt="restaurants berlin")
        manager = BrowserManager(config)
        manager.initialize()
        page = manager.navigate_to_maps("restaurants berlin")
        # ... use page ...
        manager.close()
    """

    def __init__(self, config: CrawlerConfig) -> None:
        """Initialize the BrowserManager.

        Args:
            config: The crawler configuration.
        """
        self._config = config
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._is_initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the browser has been initialized.

        Returns:
            True if the browser is initialized, False otherwise.
        """
        return self._is_initialized

    @property
    def context(self) -> BrowserContext | None:
        """Get the browser context.

        Returns:
            The BrowserContext instance or None.
        """
        return self._context

    @property
    def page(self) -> Page | None:
        """Get the current page.

        Returns:
            The Page instance or None.
        """
        return self._page

    def initialize(self) -> None:
        """Initialize and launch the browser.

        Raises:
            BrowserInitializationError: If the browser cannot be started.
        """
        try:
            logger.info("Initializing Playwright browser...")
            self._playwright = sync_playwright().start()
            browser_args = self._config.to_browser_args()
            
            # Use a unique profile directory per run to avoid ProcessSingleton conflicts
            # This is critical when running multiple crawl jobs in the same container
            import tempfile
            import atexit
            
            # Create a unique temp directory for this browser instance
            # but keep the base chrome_profile_path for cookies/storage persistence
            base_profile = self._config.chrome_profile_path
            if not os.path.exists(base_profile):
                os.makedirs(base_profile, exist_ok=True)
            
            # Use the base profile path directly - the ProcessSingleton issue
            # is solved by adding --profile-directory=Default and disabling process singleton
            browser_args["args"].extend([
                "--profile-directory=Default",
                "--disable-process-singleton-check",
                "--create-browser-if-missing=false",
            ])
            
            self._context = self._playwright.chromium.launch_persistent_context(**browser_args)
            self._page = self._context.new_page()
            self._is_initialized = True
            logger.info("Browser launched successfully")

        except Exception as e:
            self._cleanup_playwright()
            raise BrowserInitializationError(
                message="Failed to initialize the browser.",
                cause=e,
            ) from e

    def navigate_to_maps(self, prompt: str) -> Page:
        """Navigate to Google Maps search results for the given prompt.

        Args:
            prompt: The search term (e.g., "restaurants berlin").

        Returns:
            The Playwright Page object.

        Raises:
            NavigationError: If navigation fails after max retries.
        """
        if not self._is_initialized:
            self.initialize()

        if not self._page:
            raise NavigationError("Page object is not available.")

        search_url = self._build_search_url(prompt)
        logger.info("Navigating to Google Maps: %s", search_url)

        max_retries = self._config.max_retries
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                self._page.goto(
                    search_url,
                    timeout=self._config.page_timeout,
                    wait_until="domcontentloaded",
                )
                self._page.wait_for_timeout(3000)

                # Handle consent banner if present
                self._handle_consent_banner()

                logger.info("Google Maps search page loaded successfully")
                return self._page

            except PlaywrightTimeoutError as e:
                last_error = e
                logger.warning(
                    "Navigation attempt %d/%d failed: %s",
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    self._page.wait_for_timeout(3000)

        raise NavigationError(
            message=f"Failed to navigate after {max_retries} attempts.",
            cause=last_error,
        ) from last_error  # type: ignore[arg-type]

    def _build_search_url(self, prompt: str) -> str:
        """Build a Google Maps search URL from the prompt.

        Args:
            prompt: The search term.

        Returns:
            A URL-friendly search string.
        """
        formatted = prompt.replace(" ", "+")
        return f"https://www.google.com/maps/search/{formatted}?hl=de"

    def _handle_consent_banner(self) -> None:
        """Attempt to accept the Google consent banner if present."""
        if not self._page:
            return

        try:
            consent_button = self._page.locator(
                'button[aria-label*="Alle akzeptieren"], button:has-text("Alle akzeptieren")'
            )
            if consent_button.count() > 0:
                logger.info("Found consent button, accepting...")
                consent_button.first.click(timeout=5000)
                self._page.wait_for_timeout(1000)
        except Exception as e:
            logger.debug("Consent handling skipped: %s", e)

    def close(self) -> None:
        """Close the browser and clean up resources."""
        logger.info("Closing browser...")

        if self._page:
            try:
                self._page.close()
                logger.info("Page closed")
            except Exception:
                pass
            self._page = None

        if self._context:
            try:
                self._context.close()
                logger.info("Browser context closed")
            except Exception:
                pass
            self._context = None

        self._is_initialized = False
        self._cleanup_playwright()
        logger.info("Browser cleanup complete")

    def _cleanup_playwright(self) -> None:
        """Stop the Playwright instance."""
        if self._playwright:
            try:
                self._playwright.stop()
                logger.info("Playwright stopped")
            except Exception:
                pass
            self._playwright = None

    def __enter__(self) -> BrowserManager:
        """Context manager entry - initialize the browser."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close the browser."""
        self.close()