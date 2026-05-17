"""Crawler configuration model for the GoogleMapsCrawler."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ViewPort:
    """Represents the browser viewport dimensions.

    Attributes:
        width: The viewport width in pixels.
        height: The viewport height in pixels.
    """

    width: int = 1920
    height: int = 1080

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for Playwright.

        Returns:
            A dictionary with width and height keys.
        """
        return {"width": self.width, "height": self.height}


@dataclass
class CrawlerConfig:
    """Configuration for the GoogleMapsCrawler.

    This class holds all configuration options needed to run the crawler.
    It is mutable to allow runtime adjustments (e.g., changing the prompt).

    Attributes:
        search_prompt: The search term for Google Maps (e.g., "restaurants berlin").
        headless: Whether to run the browser in headless mode.
        output_format: The output format - one of "json", "csv", "pretty", "file", "print".
        chrome_profile_path: Path to the Chrome user data directory.
        viewport: The browser viewport dimensions.
        locale: The browser locale (e.g., "de-DE").
        page_timeout: Maximum navigation timeout in milliseconds.
        selector_timeout: Maximum timeout for selector waits in milliseconds.
        scroll_timeout: Maximum time for scrolling through results in seconds.
        max_scroll_attempts: Number of consecutive equal-height scrolls before stopping.
        max_retries: Number of navigation retry attempts.
        request_timeout: Request timeout in milliseconds.
    """

    search_prompt: str = ""
    headless: bool = False
    output_format: Literal["json", "csv", "pretty", "file", "print"] = "json"
    chrome_profile_path: str = field(default="")
    viewport: ViewPort = field(default_factory=lambda: ViewPort())
    locale: str = "de-DE"
    page_timeout: int = 30000
    selector_timeout: int = 15000
    scroll_timeout: int = 45
    max_scroll_attempts: int = 5
    max_retries: int = 3
    request_timeout: int = 25000

    def __post_init__(self) -> None:
        """Resolve relative paths to absolute paths after initialization."""
        if not self.chrome_profile_path:
            # Default profile path relative to this file's directory
            script_dir = Path(__file__).resolve().parent.parent
            object.__setattr__(
                self,
                "chrome_profile_path",
                str(script_dir / "Chrome_Profile"),
            )

    def with_prompt(self, prompt: str) -> "CrawlerConfig":
        """Return a new config with the updated search prompt.

        Args:
            prompt: The new search term.

        Returns:
            A new CrawlerConfig instance with the updated prompt.
        """
        from copy import deepcopy

        new_config = deepcopy(self)
        object.__setattr__(new_config, "search_prompt", prompt)
        return new_config

    def to_browser_args(self) -> dict:
        """Convert config to Playwright launch_persistent_context arguments.

        Returns:
            A dictionary of browser launch arguments.
        """
        return {
            "user_data_dir": self.chrome_profile_path,
            "headless": self.headless,
            "args": [
                "--autoplay-policy=no-user-gesture-required",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            "locale": self.locale,
            "viewport": self.viewport.to_dict(),
        }