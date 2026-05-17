"""Deduplication processor for the GoogleMapsCrawler."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import CompanyData

logger = logging.getLogger(__name__)


class DeduplicationProcessor:
    """Removes duplicate companies from a list based on name and website.

    This processor uses a combination of company name and website URL
    as the unique identifier to detect duplicates.

    Usage:
        processor = DeduplicationProcessor()
        unique_companies = processor.process(companies)
    """

    def process(self, companies: list["CompanyData"]) -> list["CompanyData"]:
        """Remove duplicate companies from the list.

        Companies are considered duplicates if they have the same
        name AND website combination.

        Args:
            companies: A list of CompanyData objects.

        Returns:
            A list of unique CompanyData objects, preserving order.
        """
        if not companies:
            return []

        unique_companies: list[CompanyData] = []
        seen: set[tuple[str, str]] = set()

        for company in companies:
            key = (company.name.strip().lower(), company.website.strip().lower())

            if key not in seen:
                seen.add(key)
                unique_companies.append(company)

        removed = len(companies) - len(unique_companies)
        if removed > 0:
            logger.info(
                "Removed %d duplicate companies. Remaining: %d",
                removed,
                len(unique_companies),
            )

        return unique_companies