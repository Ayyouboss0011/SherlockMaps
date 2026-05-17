"""Company data model for the GoogleMapsCrawler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CompanyData:
    """Represents a company extracted from Google Maps.

    Attributes:
        name: The name of the company.
        category: The category or type of business.
        address: The physical street address.
        phone: The contact phone number.
        website: The official website URL.
        rating: The average rating (e.g., "4.5").
        reviews_count: The total number of reviews.
        plus_code: The Google Plus Code for location reference.
        opening_hours: The operating hours information.
        attributes: Additional attributes (e.g., wheelchair accessibility).
    """

    name: str = "N/A"
    category: str = "N/A"
    address: str = "N/A"
    phone: str = "N/A"
    website: str = "N/A"
    rating: str = "N/A"
    reviews_count: str = "N/A"
    plus_code: str = "N/A"
    opening_hours: str = "N/A"
    attributes: List[str] = field(default_factory=lambda: ["N/A"])

    def to_dict(self) -> dict[str, str | List[str]]:
        """Convert the company data to a dictionary.

        Returns:
            A dictionary representation of the company.
        """
        return {
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "plus_code": self.plus_code,
            "opening_hours": self.opening_hours,
            "attributes": self.attributes,
        }

    def has_valid_website(self) -> bool:
        """Check if the company has a valid website URL.

        Returns:
            True if the website is a valid HTTP(S) URL, False otherwise.
        """
        from processors.url_validator import URLValidator

        return URLValidator.is_valid(self.website)

    def __post_init__(self) -> None:
        """Normalize attributes after dataclass initialization."""
        if self.attributes is None:
            object.__setattr__(self, "attributes", ["N/A"])