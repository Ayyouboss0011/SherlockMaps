"""Data models for the GoogleMapsCrawler."""

from .company import CompanyData, ReviewData
from .crawler_config import CrawlerConfig, ViewPort
from .email_data import EmailData

__all__ = [
    "CompanyData",
    "CrawlerConfig",
    "EmailData",
    "ReviewData",
    "ViewPort",
]
