"""Data processors for the GoogleMapsCrawler."""

from .url_validator import URLValidator
from .deduplication_processor import DeduplicationProcessor

__all__ = [
    "URLValidator",
    "DeduplicationProcessor",
]