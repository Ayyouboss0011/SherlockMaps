"""Maps extractor for the GoogleMapsCrawler.

This module handles extracting company data from Google Maps search results.
It navigates through result links and extracts detailed company information.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time

from playwright.sync_api import Page, TimeoutError

# Add the parent directory to sys.path so that `from core.*` imports work
# This allows running from both the root directory and from within the core directory
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.exceptions import ExtractionError
from core.models import CompanyData

logger = logging.getLogger(__name__)


class MapsExtractor:
    """Extracts company data from Google Maps search results.

    This class handles:
    - Scrolling through the results feed
    - Collecting result links
    - Navigating to individual company pages
    - Extracting detailed company information

    Usage:
        extractor = MapsExtractor(page, config)
        companies = extractor.extract_all()
    """

    # CSS Selectors
    FEED_SELECTOR = '[role="feed"]'
    LINK_SELECTOR = "a.hfpxzc"
    NAME_SELECTOR = "h1.DUwDvf"
    RATING_SELECTOR = "div.F7nice"
    CATEGORY_BUTTON_SELECTOR = 'button.DkEaL[jsaction*=".category"]'
    ADDRESS_CONTAINER_SELECTOR = 'button[data-item-id="address"] div.Io6YTe'
    WEBSITE_SELECTOR = 'a[data-item-id="authority"]'
    PHONE_CONTAINER_SELECTOR = 'button[data-item-id*="phone:tel:"] div.Io6YTe'
    PLUS_CODE_SELECTOR = 'button[data-item-id="oloc"] div.Io6YTe'

    def __init__(self, page: Page, selector_timeout: int = 15000) -> None:
        """Initialize the MapsExtractor.

        Args:
            page: The Playwright Page object.
            selector_timeout: Timeout for selector waits in milliseconds.
        """
        self._page = page
        self._selector_timeout = selector_timeout

    def extract_all(self) -> list[CompanyData]:
        """Extract all company data from the current Google Maps search results page.

        Returns:
            A list of CompanyData objects.

        Raises:
            ExtractionError: If the extraction process fails.
        """
        try:
            result_links = self._collect_result_links()
            if not result_links:
                logger.warning("No result links found on the page")
                return []

            logger.info("Found %d result links to process", len(result_links))
            companies = self._process_links(result_links)
            logger.info("Successfully extracted %d companies", len(companies))
            return companies

        except Exception as e:
            raise ExtractionError(
                message="Failed to extract data from Google Maps.",
                cause=e,
            ) from e

    def _collect_result_links(self) -> list[str]:
        """Collect all valid result links from the Google Maps feed.

        Returns:
            A list of unique Google Maps place URLs.
        """
        parent_element = self._wait_for_feed()
        if not parent_element:
            return []

        self._scroll_through_results()

        links = self._extract_links_from_feed(parent_element)
        return self._remove_duplicate_links(links)

    def _wait_for_feed(self):
        """Wait for the results feed to appear.

        Returns:
            The feed element or None if timeout.
        """
        try:
            return self._page.wait_for_selector(
                self.FEED_SELECTOR,
                timeout=25000,
            )
        except TimeoutError:
            logger.warning("Timeout waiting for feed selector")
            return None
        except Exception as e:
            logger.warning("Error waiting for feed: %s", e)
            return None

    def _scroll_through_results(self) -> None:
        """Scroll through the results feed to load all companies."""
        start_time = time.time()
        last_height = self._page.evaluate(
            '() => document.querySelector(\'[role="feed"]\').scrollHeight'
        )
        scroll_attempts = 0

        while time.time() - start_time < 45:
            self._page.evaluate(
                "document.querySelector('[role=\"feed\"]').scrollTop = "
                "document.querySelector('[role=\"feed\"]').scrollHeight"
            )
            self._page.wait_for_timeout(1500)

            new_height = self._page.evaluate(
                "() => document.querySelector('[role=\"feed\"]').scrollHeight"
            )

            if new_height == last_height:
                scroll_attempts += 1
                if scroll_attempts >= 5:
                    break
            else:
                scroll_attempts = 0
            last_height = new_height

    def _extract_links_from_feed(self, parent_element) -> list[str]:
        """Extract valid Google Maps place URLs from the feed.

        Args:
            parent_element: The feed container element.

        Returns:
            A list of valid place URLs.
        """
        link_elements = parent_element.query_selector_all(self.LINK_SELECTOR)
        links = []

        for link_element in link_elements:
            href = link_element.get_attribute("href")
            if href and href.startswith("https://www.google.com/maps/place/"):
                if len(href) > 40:
                    links.append(href)

        return links

    @staticmethod
    def _remove_duplicate_links(links: list[str]) -> list[str]:
        """Remove duplicate links while preserving order.

        Args:
            links: A list of URLs.

        Returns:
            A list of unique URLs.
        """
        return list(dict.fromkeys(links))

    def _process_links(self, links: list[str]) -> list[CompanyData]:
        """Process each link and extract company data.

        Args:
            links: A list of Google Maps place URLs.

        Returns:
            A list of CompanyData objects.
        """
        companies = []

        for i, url in enumerate(links):
            try:
                company = self._extract_company_details(url, i)
                if company:
                    companies.append(company)
                # Small delay between requests
                time.sleep(0.3 + (i % 5) * 0.1)

            except Exception as e:
                logger.warning("Failed to extract company from %s: %s", url, e)
                continue

        return companies

    def _extract_company_details(self, url: str, index: int) -> CompanyData | None:
        """Navigate to a company page and extract its details.

        Args:
            url: The Google Maps place URL.
            index: The index of this link in the results (for logging).

        Returns:
            A CompanyData object or None if extraction fails.
        """
        try:
            self._page.goto(url, timeout=25000, wait_until="domcontentloaded")

            # Wait for the company name to confirm the page loaded
            try:
                self._page.wait_for_selector(self.NAME_SELECTOR, timeout=15000)
            except TimeoutError:
                logger.debug("Company name selector not found, skipping this result")
                return None

            details = {
                "name": self._safe_text(self._page.locator(self.NAME_SELECTOR)),
                "rating": self._extract_rating(),
                "category": self._extract_category(),
                "address": self._safe_text(
                    self._page.locator(self.ADDRESS_CONTAINER_SELECTOR)
                ),
                "website": self._safe_attribute(
                    self._page.locator(self.WEBSITE_SELECTOR), "href"
                ),
                "phone": self._safe_text(
                    self._page.locator(self.PHONE_CONTAINER_SELECTOR)
                ),
                "plus_code": self._safe_text(
                    self._page.locator(self.PLUS_CODE_SELECTOR)
                ),
                "opening_hours": self._extract_opening_hours(),
                "attributes": self._extract_attributes(),
            }

            return CompanyData(**details)

        except Exception as e:
            logger.warning("Error extracting company details from %s: %s", url, e)
            return None

    def _extract_rating(self) -> str:
        """Extract the company rating and review count.

        Returns:
            The rating as a string (e.g., "4.5").
        """
        rating_text = self._safe_text(self._page.locator(self.RATING_SELECTOR))
        if not rating_text:
            return "N/A"

        rating_match = re.search(r"([\d,\.]+)", rating_text)
        return rating_match.group(1).replace(",", ".") if rating_match else "N/A"

    def _extract_category(self) -> str:
        """Extract the company category.

        Returns:
            The category as a string.
        """
        category_locator = self._page.locator(self.CATEGORY_BUTTON_SELECTOR)
        if category_locator.count() > 0:
            return self._safe_text(category_locator)

        # Fallback selector
        fallback = self._page.locator("div.fontBodyMedium span button.DkEaL")
        return self._safe_text(fallback, default="N/A")

    def _extract_opening_hours(self) -> str:
        """Extract the opening hours information.

        Returns:
            The opening hours as a formatted string.
        """
        hours_text = "N/A"

        # Try main hours container
        hours_container = self._page.locator(
            'div[aria-label*="Öffnungszeiten"], div.MkV9'
        )
        hours_button = self._page.locator('button[jsaction*="openhours"]')

        if hours_container.count() > 0:
            hours_text = self._safe_text(hours_container.first)
            if not hours_text or "Öffnungszeiten für die ganze Woche" in hours_text:
                if hours_button.count() > 0:
                    try:
                        hours_button.click(timeout=2000)
                        self._page.wait_for_timeout(500)
                        hours_text = self._safe_text(hours_container.first)
                    except Exception:
                        hours_text = self._safe_text(hours_container.first)

        # Fallback selectors
        if not hours_text or hours_text == "N/A":
            fallback_selectors = [
                'div.fontBodyMedium span[class*=""]:has-text("Öffnet")',
                'div.fontBodyMedium span[class*=""]:has-text("Geschlossen")',
                'div.fontBodyMedium span[class*=""]:has-text("Rund um die Uhr geöffnet")',
            ]
            for selector in fallback_selectors:
                extracted = self._safe_text(self._page.locator(selector).first)
                if extracted:
                    hours_text = extracted
                    break

        if hours_text and hours_text != "N/A":
            hours_text = hours_text.replace("\n", " ").strip()

        return hours_text

    def _extract_attributes(self) -> list[str]:
        """Extract company attributes (e.g., wheelchair accessibility).

        Returns:
            A list of attribute strings.
        """
        attributes = []

        # Wheelchair accessibility
        wc_locator = self._page.locator(
            'span.google-symbols[aria-label*="Rollstuhl"], span.google-symbols[data-tooltip*="Rollstuhl"]'
        )
        if wc_locator.count() > 0:
            wc_label = self._safe_attribute(wc_locator.first, "aria-label") or self._safe_attribute(
                wc_locator.first, "data-tooltip"
            )
            attributes.append(wc_label if wc_label else "Rollstuhlgerechter Eingang")

        # On-site services
        service_locator = self._page.locator(
            'div.Ahnjwc:has-text("Service/Leistungen vor Ort")'
        )
        if service_locator.count() > 0:
            attributes.append("Service/Leistungen vor Ort")

        return attributes if attributes else ["N/A"]

    def _safe_text(self, locator, default: str = "N/A", timeout: int = 2000) -> str:
        """Safely extract text from a locator.

        Args:
            locator: The Playwright locator.
            default: The default value if extraction fails.
            timeout: The timeout in milliseconds.

        Returns:
            The extracted text or the default value.
        """
        try:
            return locator.inner_text(timeout=timeout).strip() or default
        except TimeoutError:
            return default
        except Exception:
            return default

    def _safe_attribute(self, locator, attribute: str, default: str = "N/A", timeout: int = 2000) -> str:
        """Safely extract an attribute from a locator.

        Args:
            locator: The Playwright locator.
            attribute: The attribute name to extract.
            default: The default value if extraction fails.
            timeout: The timeout in milliseconds.

        Returns:
            The attribute value or the default value.
        """
        try:
            value = locator.get_attribute(attribute, timeout=timeout)
            return value if value else default
        except TimeoutError:
            return default
        except Exception:
            return default