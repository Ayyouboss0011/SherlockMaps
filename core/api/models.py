"""Pydantic models for the Google Maps Crawler REST API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class OutputFormat(str, Enum):
    """Supported output formats."""
    JSON = "json"
    CSV = "csv"
    PRETTY = "pretty"
    FILE = "file"
    PRINT = "print"


class JobStatus(str, Enum):
    """Status of a crawl job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlRequest(BaseModel):
    """Request model for starting a new crawl."""
    prompt: str = Field(..., min_length=1, description="Search term for Google Maps")
    output_format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format")
    headless: bool = Field(default=False, description="Run in headless mode")
    locale: str = Field(default="de-DE", description="Browser locale")
    max_results: Optional[int] = Field(default=None, ge=1, description="Maximum number of results")


class CrawlResponse(BaseModel):
    """Response model for a crawl job."""
    job_id: str
    status: JobStatus
    prompt: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results_count: Optional[int] = None
    error: Optional[str] = None


class JobResultResponse(BaseModel):
    """Response model for job results."""
    job_id: str
    status: JobStatus
    prompt: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[List[dict[str, Any]]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class StatusResponse(BaseModel):
    """Crawler status response."""
    status: str
    active_jobs: int
    queue_length: int
    total_completed: int
    total_failed: int
    timestamp: datetime


class StatsResponse(BaseModel):
    """Statistics response."""
    total_crawls: int = 0
    total_companies_found: int = 0
    total_pending: int = 0
    total_running: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    timestamp: datetime


class ConfigResponse(BaseModel):
    """Configuration response."""
    chrome_profile_path: str
    page_timeout: int
    selector_timeout: int
    scroll_timeout: int
    max_scroll_attempts: int
    max_retries: int
    request_timeout: int
    viewport_width: int
    viewport_height: int


class BrowserInfoResponse(BaseModel):
    """Browser information response."""
    is_initialized: bool
    is_running: bool
    profile_path: str
    headless: bool
    locale: str


class HistoryEntry(BaseModel):
    """History entry for completed jobs."""
    job_id: str
    status: JobStatus
    prompt: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results_count: Optional[int] = None


class HistoryResponse(BaseModel):
    """History response."""
    jobs: List[HistoryEntry]
    total: int
    limit: int
    offset: int


class ExportRequest(BaseModel):
    """Export request model."""
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Export format")


class ClearResponse(BaseModel):
    """Clear response."""
    message: str
    cleared_count: int


class CancelResponse(BaseModel):
    """Cancel response."""
    message: str
    job_id: str
    status: JobStatus