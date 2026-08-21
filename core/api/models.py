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
    track_reviews: bool = Field(default=True, description="Whether to track and extract reviews for each company")
    auto_email_crawl: bool = Field(default=False, description="Automatically start email crawl after successful map crawl")


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
    auto_email_crawl: bool = False
    email_job_status: Optional[str] = None
    emails_found: Optional[int] = None


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
    total_email_crawls: int = 0
    total_emails_found: int = 0
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
    auto_email_crawl: bool = False
    email_job_status: Optional[str] = None
    emails_found: Optional[int] = None


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


# --- Review Models ---

class ReviewResponse(BaseModel):
    """Response model for a single review."""
    author_name: str
    author_image: str
    author_local_guide: bool
    author_review_count: int
    rating: float
    review_text: str
    time_relative: str
    review_id: str
    likes: int
    photos: List[str]
    owner_response: str


class CompanyReviewsResponse(BaseModel):
    """Response model for reviews of a specific company."""
    company_name: str
    company_rating: str
    company_category: str
    reviews: List[ReviewResponse]


class AllReviewsResponse(BaseModel):
    """Response model for all reviews across companies."""
    total_reviews: int
    reviews: List[ReviewResponse]
    total: int
    limit: int
    offset: int


class JobReviewsResponse(BaseModel):
    """Response model for all reviews from a specific crawl job."""
    job_id: str
    prompt: str
    total_reviews: int
    companies: List[CompanyReviewsResponse]


# --- Email Models ---

class EmailDataResponse(BaseModel):
    """Response model for a single email found during crawling."""
    email: str
    source_url: str
    company_name: str
    job_id: str
    domain: str
    additional_urls_crawled: int
    found_at: datetime


class EmailCrawlRequest(BaseModel):
    """Request model for starting an email crawl on existing job results."""
    job_id: str = Field(..., description="The job ID whose results should be crawled for emails")


class EmailCrawlResponse(BaseModel):
    """Response model for an email crawl job."""
    job_id: str
    parent_job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    emails_found: Optional[int] = None
    error: Optional[str] = None


class EmailsResponse(BaseModel):
    """Response model for all emails."""
    total_emails: int
    emails: List[EmailDataResponse]
    total: int
    limit: int
    offset: int


class JobEmailsResponse(BaseModel):
    """Response model for emails from a specific email crawl job."""
    job_id: str
    parent_job_id: str
    status: JobStatus
    total_emails: int
    emails: List[EmailDataResponse]
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# --- Email Sender Models ---

class SmtpEncryption(str, Enum):
    """Supported SMTP encryption modes."""
    NONE = "none"
    STARTTLS = "starttls"
    SSL = "ssl"


class SmtpSettings(BaseModel):
    """SMTP server configuration for sending emails."""
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    password_set: bool = False
    encryption: SmtpEncryption = SmtpEncryption.STARTTLS
    from_name: str = ""
    from_email: str = ""
    enabled: bool = False
    test_recipient_email: str = ""


class SmtpSettingsUpdate(BaseModel):
    """Update payload for SMTP settings."""
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    encryption: Optional[SmtpEncryption] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    enabled: Optional[bool] = None
    test_recipient_email: Optional[str] = None


class SmtpTestRequest(BaseModel):
    """Request to send a test email."""
    to_email: str = Field(..., description="Recipient email address for the test message")


class SmtpTestResponse(BaseModel):
    """Response for a SMTP test connection."""
    success: bool
    message: str
    error: Optional[str] = None


class EmailTemplate(BaseModel):
    """Email template used to send messages to crawled contacts."""
    id: str
    name: str
    subject: str
    body: str
    html: bool = False
    created_at: datetime
    updated_at: datetime


class EmailTemplateCreate(BaseModel):
    """Payload for creating a new email template."""
    name: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    html: bool = False


class EmailTemplateUpdate(BaseModel):
    """Payload for updating an existing email template."""
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    html: Optional[bool] = None


class EmailSendRequest(BaseModel):
    """Request to send emails to all contacts of a completed crawl job."""
    job_id: str = Field(..., description="Completed crawl job whose emails should be addressed")
    template_id: str = Field(..., description="Email template to use")
    delay_seconds: float = Field(default=2.0, ge=0.0, le=60.0, description="Delay between emails in seconds")
    test: bool = Field(default=False, description="Dry-run mode: no real emails are sent")


class EmailSendResponse(BaseModel):
    """Response after queuing an email send job."""
    history_id: str
    job_id: str
    template_id: str
    total_recipients: int
    started_at: datetime


class EmailSendHistoryEntry(BaseModel):
    """Single entry in the email send history."""
    id: str
    history_id: str
    job_id: str
    email: str
    company_name: str
    status: str
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


class EmailSendHistoryResponse(BaseModel):
    """Paginated email send history."""
    history: List[EmailSendHistoryEntry]
    total: int
    limit: int
    offset: int


class EmailSendCancelResponse(BaseModel):
    """Response for cancelling an active send batch."""
    history_id: str
    cancelled: bool
    message: str