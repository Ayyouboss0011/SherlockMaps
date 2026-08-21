"""Email extractor module for crawling websites and extracting email addresses.

This module uses Playwright headless browser to visit websites,
extract email addresses from HTML content, and follow internal links
to discover more emails on sub-pages.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, BrowserContext, Page

from core.models import EmailData

logger = logging.getLogger(__name__)

# Regex pattern for extracting email addresses
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Keywords that indicate important pages for email discovery
IMPORTANT_PAGE_KEYWORDS = [
    "kontakt", "contact", "impressum", "about", "ueber", "about-us",
    "team", "about-us", "about-us/", "uber-uns", "uber uns", "support",
    "help", "faq", "erreichbar", "email", "write", "message",
]


@dataclass
class CrawlStats:
    """Statistics for the email crawling process."""
    urls_crawled: int = 0
    emails_found: int = 0
    unique_emails: int = 0
    pages_with_emails: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_time(self) -> float:
        """Get the elapsed time in seconds."""
        return time.time() - self.start_time

    def summary(self) -> str:
        """Get a summary of the crawl statistics."""
        return (
            f"Crawl Statistics:\n"
            f"  URLs crawled:      {self.urls_crawled}\n"
            f"  Emails found:      {self.emails_found}\n"
            f"  Unique emails:     {self.unique_emails}\n"
            f"  Pages with emails: {self.pages_with_emails}\n"
            f"  Errors:            {self.errors}\n"
            f"  Time elapsed:      {self.elapsed_time:.1f}s"
        )


@dataclass
class EmailCrawlerConfig:
    """Configuration for the email crawler."""
    headless: bool = True
    chrome_profile_path: str = ""
    page_timeout: int = 15000
    crawl_delay: float = 1.5
    max_pages_per_domain: int = 20
    max_total_pages: int = 200
    timeout_per_website: int = 300
    extract_from_homepage_only: bool = False


class EmailExtractor:
    """Extracts email addresses from websites using Playwright headless browser.

    This crawler:
    1. Visits the homepage of each website
    2. Extracts email addresses from the HTML
    3. Follows internal links to find more emails
    4. Deduplicates emails
    5. Respects rate limiting
    """

    def __init__(self, config: Optional[EmailCrawlerConfig] = None) -> None:
        """Initialize the email crawler.

        Args:
            config: Configuration for the crawler.
        """
        self.config = config or EmailCrawlerConfig()
        self.stats = CrawlStats()
        self._emails: dict[str, EmailData] = {}  # email -> EmailData (deduplication)
        self._visited_urls: Set[str] = set()
        self._pending_links: list[str] = []
        self._browser_context: Optional[BrowserContext] = None

    async def __aenter__(self) -> "EmailExtractor":
        """Async context manager entry."""
        await self._initialize_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _initialize_browser(self) -> None:
        """Initialize the Playwright browser with Chrome profile."""
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()

        # Launch browser with existing Chrome profile
        if self.config.chrome_profile_path:
            self._browser_context = await playwright.chromium.launch_persistent_context(
                user_data_dir=self.config.chrome_profile_path,
                headless=self.config.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                bypass_csp=True,
            )
        else:
            browser = await playwright.chromium.launch(
                headless=self.config.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            self._browser_context = await browser.new_context()

        logger.info("Browser initialized (headless=%s, profile=%s)",
                     self.config.headless, self.config.chrome_profile_path)

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        if self._browser_context:
            await self._browser_context.close()
            self._browser_context = None
        logger.info("Browser closed")

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL for consistent tracking.

        Args:
            url: The URL to normalize.

        Returns:
            The normalized URL.
        """
        try:
            parsed = urlparse(url)
            # Remove fragment
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            # Remove trailing slash (except for root)
            if normalized.endswith("/") and len(parsed.path) > 1:
                normalized = normalized.rstrip("/")
            return normalized.lower()
        except Exception:
            return url.lower()

    def _is_internal_link(self, url: str, base_domain: str) -> bool:
        """Check if a link is internal (same domain).

        Args:
            url: The URL to check.
            base_domain: The base domain to compare against.

        Returns:
            True if the link is internal, False otherwise.
        """
        try:
            parsed = urlparse(url)
            link_domain = parsed.netloc.lower()
            # Remove port if present
            if ":" in link_domain:
                link_domain = link_domain.split(":")[0]
            return link_domain == base_domain or link_domain.endswith(f".{base_domain}")
        except Exception:
            return False

    def _is_important_page(self, url: str) -> bool:
        """Check if a URL points to an important page for email discovery.

        Args:
            url: The URL to check.

        Returns:
            True if the page is considered important.
        """
        url_lower = url.lower()
        return any(keyword in url_lower for keyword in IMPORTANT_PAGE_KEYWORDS)

    def _extract_emails_from_html(self, html: str) -> list[str]:
        """Extract email addresses from HTML content.

        Args:
            html: The HTML content to parse.

        Returns:
            List of found email addresses.
        """
        found_emails = EMAIL_PATTERN.findall(html)
        # Normalize emails
        return [email.strip().lower() for email in found_emails if "@" in email and "." in email.split("@")[-1]]

    async def _crawl_page(self, page: Page, url: str, company_name: str,
                          job_id: str, source_domain: str) -> list[str]:
        """Crawl a single page for email addresses.

        Args:
            page: The Playwright page object.
            url: The URL to crawl.
            company_name: The associated company name.
            job_id: The original crawl job ID.
            source_domain: The source domain for internal link tracking.

        Returns:
            List of email addresses found on this page.
        """
        try:
            await page.goto(url, timeout=self.config.page_timeout, wait_until="domcontentloaded")
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(2000)

            # Get the page content
            html = await page.content()
            found_emails = self._extract_emails_from_html(html)

            self.stats.urls_crawled += 1

            if found_emails:
                self.stats.pages_with_emails += 1

                for email in found_emails:
                    if email not in self._emails:
                        email_data = EmailData(
                            email=email,
                            source_url=url,
                            company_name=company_name,
                            job_id=job_id,
                            domain=source_domain,
                            found_at=datetime.now(timezone.utc),
                        )
                        email_data.normalize()
                        self._emails[email] = email_data
                        self.stats.unique_emails += 1
                        self.stats.emails_found += 1
                        logger.info("Found email '%s' on %s", email, url)

            # Extract internal links for further crawling
            if not self.config.extract_from_homepage_only:
                links = await page.query_selector_all("a[href]")
                for link_elem in links:
                    href = await link_elem.get_attribute("href")
                    if href:
                        full_url = urljoin(url, href)
                        # Only follow internal links that haven't been visited
                        normalized = self._normalize_url(full_url)
                        if (self._is_internal_link(full_url, source_domain)
                                and normalized not in self._visited_urls
                                and normalized not in self._pending_links):
                            self._pending_links.append(normalized)

            # Rate limiting
            await page.wait_for_timeout(int(self.config.crawl_delay * 1000))

            return found_emails

        except Exception as e:
            self.stats.errors += 1
            logger.warning("Error crawling %s: %s", url, e)
            return []

    async def crawl_website(self, website_url: str, company_name: str,
                            job_id: str) -> list[EmailData]:
        """Crawl a single website for email addresses.

        This method:
        1. Normalizes the URL to the homepage
        2. Crawls the homepage
        3. Follows internal links to find more emails
        4. Returns all unique emails found

        Args:
            website_url: The website URL to crawl.
            company_name: The name of the company.
            job_id: The original crawl job ID.

        Returns:
            List of unique EmailData objects found.
        """
        self.stats = CrawlStats()  # Reset stats for this crawl
        self._emails = {}
        self._visited_urls = set()
        self._pending_links = []

        # Normalize the URL
        normalized_url = self._normalize_url(website_url)
        parsed = urlparse(normalized_url)

        # Ensure we have a protocol
        if not parsed.scheme:
            normalized_url = "https://" + normalized_url

        # Get the base domain
        base_domain = parsed.netloc.lower()
        if ":" in base_domain:
            base_domain = base_domain.split(":")[0]

        # Ensure https protocol for the base URL
        if parsed.scheme in ("http", "https"):
            homepage = normalized_url
        else:
            homepage = f"https://{normalized_url}"

        # Extract domain for tracking
        homepage = self._normalize_url(homepage)
        self._visited_urls.add(homepage)

        logger.info("Starting email crawl for: %s (company: %s, domain: %s)",
                     homepage, company_name, base_domain)

        # Create a new page for this crawl
        page = await self._browser_context.new_page() if self._browser_context else None

        if not page:
            logger.error("Failed to create browser page for %s", homepage)
            return list(self._emails.values())

        try:
            # Crawl the homepage
            await self._crawl_page(page, homepage, company_name, job_id, base_domain)

            # Crawl internal links (up to max_pages_per_domain)
            pages_crawled = 1

            # Prioritize important pages
            important_links = []
            normal_links = []
            for link in self._pending_links:
                if self._is_important_page(link):
                    important_links.append(link)
                else:
                    normal_links.append(link)

            prioritized_links = important_links + normal_links

            for link in prioritized_links:
                if pages_crawled >= self.config.max_pages_per_domain:
                    break

                link_normalized = self._normalize_url(link)
                if link_normalized in self._visited_urls:
                    continue

                self._visited_urls.add(link_normalized)
                pages_crawled += 1

                await self._crawl_page(page, link_normalized, company_name, job_id, base_domain)

            logger.info("Email crawl completed for %s: %d unique emails found",
                        homepage, len(self._emails))
            logger.info(self.stats.summary())

        except Exception as e:
            logger.error("Error during email crawl of %s: %s", homepage, e)
        finally:
            await page.close()

        return list(self._emails.values())

    async def crawl_websites(self, websites: list[dict], job_id: str) -> list[EmailData]:
        """Crawl multiple websites for email addresses.

        Args:
            websites: List of company dictionaries with 'website', 'name' keys.
            job_id: The original crawl job ID.

        Returns:
            List of all unique EmailData objects found across all websites.
        """
        all_emails: dict[str, EmailData] = {}

        for i, company in enumerate(websites):
            website = company.get("website", "")
            company_name = company.get("name", "N/A")

            if not website or website == "N/A" or website == "":
                logger.debug("Skipping company '%s' - no valid website", company_name)
                continue

            logger.info("Crawling website %d/%d: %s", i + 1, len(websites), website)

            try:
                emails = await self.crawl_website(website, company_name, job_id)
                for email in emails:
                    all_emails[email.email] = email
            except Exception as e:
                logger.error("Failed to crawl %s: %s", website, e)

            # Rate limiting between websites
            if i < len(websites) - 1:
                await asyncio.sleep(self.config.crawl_delay)

        logger.info("Email crawling completed: %d unique emails from %d websites",
                     len(all_emails), len(websites))
        return list(all_emails.values())


async def extract_emails_from_websites(
    websites: list[dict],
    job_id: str,
    config: Optional[EmailCrawlerConfig] = None,
) -> list[dict]:
    """Convenience function to extract emails from a list of websites.

    Args:
        websites: List of company dictionaries with 'website', 'name' keys.
        job_id: The original crawl job ID.
        config: Optional crawler configuration.

    Returns:
        List of email dictionaries.
    """
    async with EmailExtractor(config) as crawler:
        emails = await crawler.crawl_websites(websites, job_id)
        return [email.to_dict() for email in emails]