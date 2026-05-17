"""URL validator for the GoogleMapsCrawler."""

from __future__ import annotations

import re


class URLValidator:
    """Validates HTTP(S) URLs.

    This class provides static methods for checking if a given string
    is a valid HTTP or HTTPS URL.

    Usage:
        URLValidator.is_valid("https://example.com")  # True
        URLValidator.is_valid("not a url")  # False
    """

    # Compiled regex pattern for URL validation
    _URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"  # domain name
        r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # TLD
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP address
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    @classmethod
    def is_valid(cls, url: str | None) -> bool:
        """Check if a given string is a valid HTTP(S) URL.

        Args:
            url: The URL string to validate.

        Returns:
            True if the URL is valid, False otherwise.
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip()
        if not url:
            return False

        return cls._URL_PATTERN.match(url) is not None