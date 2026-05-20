"""Data models for the GoogleMapsCrawler."""

from .company import CompanyData, ReviewData
from .crawler_config import CrawlerConfig, ViewPort

__all__ = [
    "CompanyData",
    "CrawlerConfig",
    "ReviewData",
    "ViewPort",
]
