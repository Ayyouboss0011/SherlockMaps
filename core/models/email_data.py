"""Email data model for the Email Crawler feature."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class EmailData:
    """Represents an email address found during website crawling.

    Attributes:
        email: The found email address (normalized to lowercase).
        source_url: The URL where the email was found.
        company_name: The associated company name.
        job_id: The original crawl job ID.
        domain: The domain of the source URL.
        additional_urls_crawled: Number of additional URLs crawled for this email.
        found_at: Timestamp when the email was found.
    """

    email: str = ""
    source_url: str = ""
    company_name: str = "N/A"
    job_id: str = ""
    domain: str = ""
    additional_urls_crawled: int = 0
    found_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert the email data to a dictionary.

        Returns:
            A dictionary representation of the email.
        """
        return {
            "email": self.email,
            "source_url": self.source_url,
            "company_name": self.company_name,
            "job_id": self.job_id,
            "domain": self.domain,
            "additional_urls_crawled": self.additional_urls_crawled,
            "found_at": self.found_at.isoformat(),
        }

    def normalize(self) -> None:
        """Normalize the email address to lowercase for deduplication."""
        self.email = self.email.strip().lower()