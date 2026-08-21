"""Company data model for the GoogleMapsCrawler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ReviewData:
    """Represents a single Google Maps review.

    Attributes:
        author_name: The name of the review author.
        author_image: URL to the author's profile image.
        author_local_guide: Whether the author is a Local Guide.
        author_review_count: Total number of reviews by this author.
        rating: The review rating (1.0 to 5.0).
        review_text: The main text content of the review.
        time_relative: Relative time string (e.g., "vor 6 Monaten").
        review_id: Unique Google review ID.
        likes: Number of "likes" on the review.
        photos: List of photo URLs included in the review.
        owner_response: The owner's response to the review (if any).
    """

    author_name: str = "N/A"
    author_image: str = "N/A"
    author_local_guide: bool = False
    author_review_count: int = 0
    rating: float = 0.0
    review_text: str = "N/A"
    time_relative: str = "N/A"
    review_id: str = "N/A"
    likes: int = 0
    photos: List[str] = field(default_factory=list)
    owner_response: str = "N/A"

    def to_dict(self) -> dict:
        """Convert the review data to a dictionary.

        Returns:
            A dictionary representation of the review.
        """
        return {
            "author_name": self.author_name,
            "author_image": self.author_image,
            "author_local_guide": self.author_local_guide,
            "author_review_count": self.author_review_count,
            "rating": self.rating,
            "review_text": self.review_text,
            "time_relative": self.time_relative,
            "review_id": self.review_id,
            "likes": self.likes,
            "photos": self.photos,
            "owner_response": self.owner_response,
        }


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
        reviews: List of review objects for this company.
        email_status: Status of the email crawling for this company.
            Values: "not_started", "pending", "completed", "failed", "no_website"
        emails: List of email addresses found for this company.
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
    reviews: List[ReviewData] = field(default_factory=lambda: [])
    email_status: str = "not_started"
    emails: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | List[str] | List[dict]]:
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
            "reviews": [r.to_dict() for r in self.reviews],
            "email_status": self.email_status,
            "emails": self.emails,
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
        if self.reviews is None:
            object.__setattr__(self, "reviews", [])
        if self.emails is None:
            object.__setattr__(self, "emails", [])
