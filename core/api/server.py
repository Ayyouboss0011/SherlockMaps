"""FastAPI server for the Google Maps Crawler REST API.

This module creates a persistent REST API server that:
1. Initializes the browser on startup
2. Accepts crawl jobs via HTTP requests
3. Processes jobs sequentially (one at a time)
4. Remains running for additional requests
5. Preserves the Chrome profile between jobs
6. Supports automatic/manual email crawling from crawled websites
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import sys
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from typing import Any, List, Optional

# Add the parent directory to sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from core.api.models import (
    AllReviewsResponse,
    BrowserInfoResponse,
    CancelResponse,
    ClearResponse,
    CompanyReviewsResponse,
    ConfigResponse,
    CrawlRequest,
    CrawlResponse,
    EmailCrawlRequest,
    EmailCrawlResponse,
    EmailDataResponse,
    EmailSendCancelResponse,
    EmailSendHistoryResponse,
    EmailSendRequest,
    EmailSendResponse,
    EmailTemplate,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailsResponse,
    ExportRequest,
    HealthResponse,
    HistoryEntry,
    HistoryResponse,
    JobEmailsResponse,
    JobReviewsResponse,
    JobResultResponse,
    JobStatus,
    OutputFormat,
    ReviewResponse,
    SmtpTestRequest,
    SmtpTestResponse,
    SmtpSettings,
    SmtpSettingsUpdate,
    StatsResponse,
    StatusResponse,
)
from core.api.email_sender import EmailSenderStore
from core.api.queue_manager import QueueManager
from core.browser import BrowserManager
from core.extractors import MapsExtractor
from core.extractors.email_extractor import EmailCrawlerConfig, EmailExtractor, extract_emails_from_websites
from core.models import CompanyData, CrawlerConfig
from core.processors import DeduplicationProcessor, URLValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
queue_manager = QueueManager()
email_sender_store = EmailSenderStore()
app_instance: Optional[FastAPI] = None


def init_browser(config_dict: dict) -> dict:
    """Initialize the browser in a worker process.

    This function runs in a separate process to avoid asyncio loop conflicts.

    Args:
        config_dict: Configuration as dictionary.

    Returns:
        Status dictionary.
    """
    # Reconstruct CrawlerConfig from dict
    config = CrawlerConfig(
        search_prompt=config_dict.get("search_prompt", ""),
        headless=config_dict.get("headless", False),
        output_format=config_dict.get("output_format", "json"),
        locale=config_dict.get("locale", "de-DE"),
        chrome_profile_path=config_dict.get("chrome_profile_path", ""),
        page_timeout=config_dict.get("page_timeout", 30000),
        selector_timeout=config_dict.get("selector_timeout", 15000),
        scroll_timeout=config_dict.get("scroll_timeout", 45),
        max_scroll_attempts=config_dict.get("max_scroll_attempts", 5),
        max_retries=config_dict.get("max_retries", 3),
        request_timeout=config_dict.get("request_timeout", 25000),
    )

    browser_mgr = BrowserManager(config)
    browser_mgr.initialize()

    return {
        "success": True,
        "profile_path": config.chrome_profile_path,
        "headless": config.headless,
        "locale": config.locale,
    }


def run_crawl_in_process(
    prompt: str,
    output_format: str = "json",
    headless: bool = False,
    locale: str = "de-DE",
    track_reviews: bool = True,
) -> list[dict[str, Any]]:
    """Run a crawl in a worker process.

    This function performs the actual crawl operation using synchronous Playwright code
    in a separate process to avoid asyncio loop conflicts.

    Args:
        prompt: Search prompt for Google Maps.
        output_format: Output format.
        headless: Run in headless mode.
        locale: Browser locale.
        track_reviews: Whether to extract reviews for each company.

    Returns:
        List of company dictionaries.
    """
    import tempfile

    # Create a unique temporary profile directory for this crawl
    # This avoids ProcessSingleton conflicts when running multiple crawls
    temp_profile_dir = tempfile.mkdtemp(prefix="chrome_profile_")

    # Import and initialize browser in this process with unique profile
    config = CrawlerConfig(
        search_prompt=prompt,
        headless=headless,
        output_format=output_format,
        locale=locale,
        chrome_profile_path=temp_profile_dir,
    )

    browser_mgr = BrowserManager(config)
    browser_mgr.initialize()

    try:
        # Navigate to Google Maps
        page = browser_mgr.navigate_to_maps(prompt)

        # Extract data
        extractor = MapsExtractor(page, config.selector_timeout)
        raw_results = extractor.extract_all(track_reviews=track_reviews)

        if not raw_results:
            logger.warning("No companies found for prompt: %s", prompt)
            return []

        logger.info("Extracted %d raw companies", len(raw_results))

        # Remove duplicates
        deduplicator = DeduplicationProcessor()
        unique_results = deduplicator.process(raw_results)

        # Filter valid websites
        valid_results = [c for c in unique_results if URLValidator.is_valid(c.website)]

        logger.info(
            "Crawl complete. Found %d companies with valid websites",
            len(valid_results),
        )

        # Convert to list of dicts
        return [company.to_dict() for company in valid_results]

    finally:
        browser_mgr.close()
        # Clean up temporary profile directory
        import shutil
        try:
            shutil.rmtree(temp_profile_dir, ignore_errors=True)
        except Exception:
            pass


def _collect_recipients_from_job(job) -> list[dict[str, Any]]:
    """Collect unique email recipients with company metadata from a crawl job.

    Args:
        job: A CrawlJob with results containing company emails.

    Returns:
        List of recipient dictionaries with 'email', 'company_name',
        'company_website' and 'company_address' keys.
    """
    recipients: dict[str, dict[str, Any]] = {}
    for company in (job.results or []):
        company_name = company.get("name") or company.get("company_name") or ""
        company_website = company.get("website") or ""
        company_address = company.get("address") or ""

        emails: list[str] = []
        raw_emails = company.get("emails")
        if isinstance(raw_emails, list):
            emails = [e for e in raw_emails if isinstance(e, str) and "@" in e]
        raw_email = company.get("email")
        if raw_email and isinstance(raw_email, str):
            for part in raw_email.split(","):
                part = part.strip()
                if "@" in part and part not in emails:
                    emails.append(part)

        for email in emails:
            email_lower = email.strip().lower()
            if email_lower not in recipients:
                recipients[email_lower] = {
                    "email": email_lower,
                    "company_name": company_name,
                    "company_website": company_website,
                    "company_address": company_address,
                }
    return list(recipients.values())


def _create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Google Maps Crawler API",
        description="REST API for crawling Google Maps company data. "
                    "This API allows you to submit crawl jobs, monitor their "
                    "progress, and retrieve results. It also supports crawling "
                    "company websites for email addresses.",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store app reference
    global app_instance
    app_instance = app

    # --- Health & Status Endpoints ---

    @app.get("/health", response_model=HealthResponse, tags="System")
    async def health_check() -> HealthResponse:
        """Health check endpoint for container orchestration."""
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
        )

    @app.get("/status", response_model=StatusResponse, tags="System")
    async def get_status() -> StatusResponse:
        """Get the current status of the crawler."""
        stats = await queue_manager.get_stats()
        return StatusResponse(
            status="idle" if not queue_manager.is_busy else "busy",
            active_jobs=queue_manager.active_crawl_jobs,
            queue_length=queue_manager.crawl_queue_length,
            total_completed=stats["total_completed"],
            total_failed=stats["total_failed"],
            timestamp=datetime.now(timezone.utc),
        )

    @app.get("/stats", response_model=StatsResponse, tags="System")
    async def get_stats() -> StatsResponse:
        """Get detailed statistics about all crawl jobs."""
        stats = await queue_manager.get_stats()
        return StatsResponse(
            total_crawls=stats["total_crawls"],
            total_companies_found=stats["total_companies_found"],
            total_pending=stats["total_pending"],
            total_running=stats["total_running"],
            total_completed=stats["total_completed"],
            total_failed=stats["total_failed"],
            total_cancelled=stats["total_cancelled"],
            total_email_crawls=stats.get("total_email_crawls", 0),
            total_emails_found=stats.get("total_emails_found", 0),
            timestamp=datetime.now(timezone.utc),
        )

    # --- Crawl Endpoints ---

    # IMPORTANT: Static routes MUST come before dynamic routes in FastAPI.
    # /crawl/history must be defined BEFORE /crawl/{job_id} or FastAPI will
    # interpret "history" as a job_id parameter value.

    @app.post("/crawl", response_model=CrawlResponse, status_code=202, tags="Crawler")
    async def start_crawl(request: CrawlRequest) -> CrawlResponse:
        """Start a new crawl job.

        The job is added to the queue and will be processed when the crawler is available.
        If the crawler is currently processing another job, this job will wait in the queue.

        Set auto_email_crawl=True to automatically start an email crawl after the map crawl completes.
        """
        job = await queue_manager.add_job(
            prompt=request.prompt,
            output_format=request.output_format.value,
            headless=request.headless,
            locale=request.locale,
            max_results=request.max_results,
            track_reviews=request.track_reviews,
            auto_email_crawl=request.auto_email_crawl,
        )

        # Start background processing
        asyncio.create_task(_process_job(job.job_id))

        return CrawlResponse(
            job_id=job.job_id,
            status=job.status,
            prompt=job.prompt,
            created_at=job.created_at,
        )

    @app.get("/crawl/history", response_model=HistoryResponse, tags="Crawler")
    async def get_crawl_history(
        limit: int = 50,
        offset: int = 0,
    ) -> HistoryResponse:
        """Get the history of crawl jobs with pagination."""
        jobs = await queue_manager.get_all_jobs(limit=limit, offset=offset)

        # Get all email jobs
        email_jobs_by_parent = {}
        for ej in queue_manager._email_jobs.values():
            parent_id = ej.parent_job_id
            if parent_id not in email_jobs_by_parent:
                email_jobs_by_parent[parent_id] = ej
            else:
                current_ej = email_jobs_by_parent[parent_id]
                if ej.created_at > current_ej.created_at:
                    email_jobs_by_parent[parent_id] = ej

        entries = [
            HistoryEntry(
                job_id=j.job_id,
                status=j.status,
                prompt=j.prompt,
                created_at=j.created_at,
                completed_at=j.completed_at,
                results_count=len(j.results) if j.results else 0,
                auto_email_crawl=j.auto_email_crawl,
                email_job_status=email_jobs_by_parent[j.job_id].status.value if j.job_id in email_jobs_by_parent else None,
                emails_found=len(email_jobs_by_parent[j.job_id].results) if (j.job_id in email_jobs_by_parent and email_jobs_by_parent[j.job_id].results) else (0 if j.job_id in email_jobs_by_parent else None),
            )
            for j in jobs
        ]

        all_jobs = await queue_manager.get_all_jobs(limit=10000, offset=0)
        return HistoryResponse(
            jobs=entries,
            total=len(all_jobs),
            limit=limit,
            offset=offset,
        )

    @app.get("/crawl/{job_id}", response_model=JobResultResponse, tags="Crawler")
    async def get_job_status(job_id: str) -> JobResultResponse:
        """Get the status of a specific crawl job."""
        job = await queue_manager.get_crawl_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Find associated email job
        email_job = None
        for ej in queue_manager._email_jobs.values():
            if ej.parent_job_id == job_id:
                if not email_job or ej.created_at > email_job.created_at:
                    email_job = ej

        return JobResultResponse(
            job_id=job.job_id,
            status=job.status,
            prompt=job.prompt,
            created_at=job.created_at,
            completed_at=job.completed_at,
            results=job.results,
            error=job.error,
            auto_email_crawl=job.auto_email_crawl,
            email_job_status=email_job.status.value if email_job else None,
            emails_found=len(email_job.results) if (email_job and email_job.results) else (0 if email_job else None),
        )

    @app.get("/crawl/{job_id}/results", response_model=JobResultResponse, tags="Crawler")
    async def get_job_results(job_id: str) -> JobResultResponse:
        """Get the results of a completed crawl job."""
        job = await queue_manager.get_crawl_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )

        # Find associated email job
        email_job = None
        for ej in queue_manager._email_jobs.values():
            if ej.parent_job_id == job_id:
                if not email_job or ej.created_at > email_job.created_at:
                    email_job = ej

        return JobResultResponse(
            job_id=job.job_id,
            status=job.status,
            prompt=job.prompt,
            created_at=job.created_at,
            completed_at=job.completed_at,
            results=job.results,
            error=job.error,
            auto_email_crawl=job.auto_email_crawl,
            email_job_status=email_job.status.value if email_job else None,
            emails_found=len(email_job.results) if (email_job and email_job.results) else (0 if email_job else None),
        )

    @app.delete("/crawl/{job_id}", response_model=CancelResponse, tags="Crawler")
    async def cancel_job(job_id: str) -> CancelResponse:
        """Cancel a pending or running crawl job."""
        job = await queue_manager.cancel_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return CancelResponse(
            message=f"Job {job_id} has been cancelled",
            job_id=job.job_id,
            status=job.status,
        )

    # --- Email Crawl Endpoints ---

    @app.post("/email-crawl", response_model=EmailCrawlResponse, status_code=202, tags="Email Crawler")
    async def start_email_crawl(request: EmailCrawlRequest) -> EmailCrawlResponse:
        """Start an email crawl for websites from a completed crawl job.

        This endpoint extracts all valid websites from the specified job's results
        and starts crawling them for email addresses.
        """
        # Get the parent job
        parent_job = await queue_manager.get_crawl_job(request.job_id)
        if not parent_job:
            raise HTTPException(status_code=404, detail=f"Parent job {request.job_id} not found")

        if parent_job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Parent job is not completed. Current status: {parent_job.status.value}",
            )

        if not parent_job.results:
            raise HTTPException(
                status_code=400,
                detail=f"No results found for job {request.job_id}",
            )

        # Extract valid websites from results
        websites = []
        for company in parent_job.results:
            website = company.get("website", "")
            if website and website != "N/A" and URLValidator.is_valid(website):
                websites.append({
                    "name": company.get("name", "N/A"),
                    "website": website,
                })

        if not websites:
            raise HTTPException(
                status_code=400,
                detail=f"No valid websites found in job {request.job_id}",
            )

        # Set email_status to "pending" for all companies in the parent job
        await queue_manager.start_email_crawl_for_parent(request.job_id)

        # Create email crawl job
        email_job = await queue_manager.add_email_job(
            parent_job_id=request.job_id,
            websites=websites,
            headless=True,
            chrome_profile_path="",  # Will use default Chrome profile
        )

        # Start background email processing
        asyncio.create_task(_process_email_job(email_job.job_id))

        return EmailCrawlResponse(
            job_id=email_job.job_id,
            parent_job_id=request.job_id,
            status=email_job.status,
            created_at=email_job.created_at,
        )

    @app.get("/email-crawl/parent/{parent_job_id}", response_model=Optional[EmailCrawlResponse], tags="Email Crawler")
    async def get_email_job_by_parent(parent_job_id: str) -> Optional[EmailCrawlResponse]:
        """Get the email crawl job status for a parent crawl job."""
        matching_jobs = [job for job in queue_manager._email_jobs.values() if job.parent_job_id == parent_job_id]
        if not matching_jobs:
            return None
        # Sort by created_at descending
        matching_jobs.sort(key=lambda j: j.created_at, reverse=True)
        job = matching_jobs[0]
        return EmailCrawlResponse(
            job_id=job.job_id,
            parent_job_id=job.parent_job_id,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
            emails_found=len(job.results) if job.results else 0,
            error=job.error,
        )

    @app.get("/email-crawl/{job_id}", response_model=JobEmailsResponse, tags="Email Crawler")
    async def get_email_job_status(job_id: str) -> JobEmailsResponse:
        """Get the status of a specific email crawl job."""
        job = await queue_manager.get_email_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Email crawl job {job_id} not found")

        return JobEmailsResponse(
            job_id=job.job_id,
            parent_job_id=job.parent_job_id,
            status=job.status,
            total_emails=len(job.results) if job.results else 0,
            emails=[EmailDataResponse(**e) for e in (job.results or [])],
            created_at=job.created_at,
            completed_at=job.completed_at,
            error=job.error,
        )

    @app.get("/emails", response_model=EmailsResponse, tags="Email Crawler")
    async def get_all_emails(
        limit: int = 50,
        offset: int = 0,
    ) -> EmailsResponse:
        """Get all emails from completed email crawl jobs with pagination."""
        all_emails = await queue_manager.get_all_email_results()

        if not all_emails:
            return EmailsResponse(
                total_emails=0,
                emails=[],
                total=0,
                limit=limit,
                offset=offset,
            )

        total = len(all_emails)
        paginated = [EmailDataResponse(**email) for email in all_emails[offset:offset + limit]]

        return EmailsResponse(
            total_emails=total,
            emails=paginated,
            total=total,
            limit=limit,
            offset=offset,
        )

    @app.delete("/emails", response_model=ClearResponse, tags="Email Crawler")
    async def clear_emails() -> ClearResponse:
        """Clear all stored email results from completed email crawl jobs."""
        count = await queue_manager.clear_email_results()
        return ClearResponse(
            message=f"Cleared emails from {count} completed email crawl jobs",
            cleared_count=count,
        )

    # --- Email Sender Endpoints ---

    @app.get("/smtp/settings", response_model=SmtpSettings, tags="Email Sender")
    async def get_smtp_settings() -> SmtpSettings:
        """Get the configured SMTP settings (password is masked)."""
        return SmtpSettings(**email_sender_store.get_smtp())

    @app.put("/smtp/settings", response_model=SmtpSettings, tags="Email Sender")
    async def update_smtp_settings(update: SmtpSettingsUpdate) -> SmtpSettings:
        """Update the SMTP settings."""
        return SmtpSettings(**email_sender_store.update_smtp(update))

    @app.post("/smtp/test", response_model=SmtpTestResponse, tags="Email Sender")
    async def test_smtp(request: SmtpTestRequest) -> SmtpTestResponse:
        """Send a test email to verify the SMTP configuration."""
        return email_sender_store.test_connection(request.to_email)

    @app.get("/templates", response_model=list[EmailTemplate], tags="Email Sender")
    async def list_templates() -> list[EmailTemplate]:
        """List all email templates."""
        return [EmailTemplate(**t) for t in email_sender_store.list_templates()]

    @app.post("/templates", response_model=EmailTemplate, status_code=201, tags="Email Sender")
    async def create_template(data: EmailTemplateCreate) -> EmailTemplate:
        """Create a new email template."""
        return email_sender_store.create_template(data)

    @app.put("/templates/{template_id}", response_model=EmailTemplate, tags="Email Sender")
    async def update_template(template_id: str, data: EmailTemplateUpdate) -> EmailTemplate:
        """Update an existing email template."""
        template = email_sender_store.update_template(template_id, data)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        return template

    @app.delete("/templates/{template_id}", response_model=ClearResponse, tags="Email Sender")
    async def delete_template(template_id: str) -> ClearResponse:
        """Delete an email template."""
        if not email_sender_store.delete_template(template_id):
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        return ClearResponse(
            message=f"Deleted template {template_id}",
            cleared_count=1,
        )

    @app.get("/emails/recipients/{job_id}", tags="Email Sender")
    async def get_job_recipients(job_id: str) -> list[dict[str, Any]]:
        """Get the deduplicated email recipients of a completed crawl job."""
        job = await queue_manager.get_crawl_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )
        return _collect_recipients_from_job(job)

    @app.post("/emails/send", response_model=EmailSendResponse, status_code=202, tags="Email Sender")
    async def send_emails(request: EmailSendRequest) -> EmailSendResponse:
        """Send emails to all crawled contacts of a completed job.

        Emails are sent in the background using the selected template.
        Use ``test=true`` for a test run where every personalized email is
        sent to the configured test recipient email instead of the real one.
        """
        job = await queue_manager.get_crawl_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )

        template = email_sender_store.get_template(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")

        if request.test:
            test_recipient = email_sender_store.get_smtp().get("test_recipient_email", "").strip()
            if not test_recipient:
                raise HTTPException(
                    status_code=400,
                    detail="Test run requires a configured test recipient email. "
                           "Set it in the SMTP settings.",
                )

        recipients = _collect_recipients_from_job(job)
        if not recipients:
            raise HTTPException(
                status_code=400,
                detail=f"No email addresses found in job {request.job_id}",
            )

        history_id = email_sender_store.create_send(
            job_id=request.job_id,
            template=template,
            recipients=recipients,
            test=request.test,
        )

        asyncio.create_task(
            email_sender_store.process_send(
                history_id=history_id,
                template=template,
                recipients=recipients,
                delay_seconds=request.delay_seconds,
                test=request.test,
            )
        )

        return EmailSendResponse(
            history_id=history_id,
            job_id=request.job_id,
            template_id=template.id,
            total_recipients=len(recipients),
            started_at=datetime.now(timezone.utc),
        )

    @app.get("/emails/send/history", response_model=EmailSendHistoryResponse, tags="Email Sender")
    async def get_send_history(
        limit: int = 50,
        offset: int = 0,
    ) -> EmailSendHistoryResponse:
        """Get the email send history with pagination."""
        entries, total = email_sender_store.get_history(limit=limit, offset=offset)
        return EmailSendHistoryResponse(
            history=entries,
            total=total,
            limit=limit,
            offset=offset,
        )

    @app.post("/emails/send/{history_id}/cancel", response_model=EmailSendCancelResponse, tags="Email Sender")
    async def cancel_email_send(history_id: str) -> EmailSendCancelResponse:
        """Cancel a running send batch.

        Stops sending further emails in the batch and marks all remaining
        pending entries as cancelled.
        """
        cancelled = email_sender_store.cancel_send(history_id)
        if not cancelled:
            raise HTTPException(
                status_code=404,
                detail=f"No active send batch {history_id} found",
            )
        return EmailSendCancelResponse(
            history_id=history_id,
            cancelled=True,
            message=f"Send batch {history_id} cancelled",
        )

    @app.delete("/emails/send/history", response_model=ClearResponse, tags="Email Sender")
    async def clear_send_history() -> ClearResponse:
        """Delete the entire email send history."""
        count = email_sender_store.clear_history()
        return ClearResponse(
            message=f"Cleared {count} send history entries",
            cleared_count=count,
        )

    # --- Results Endpoints ---

    @app.get("/results", tags="Results")
    async def get_all_results(format: Optional[str] = "json") -> Response:
        """Get all results from completed jobs.

        Optionally export in a specific format: json, csv, or pretty.
        """
        results = await queue_manager.get_all_results()

        if not results:
            return Response(content="No results available", media_type="text/plain")

        if format == "csv":
            if not results:
                return Response(content="", media_type="text/csv")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=results.csv"},
            )
        elif format == "pretty":
            formatted = json.dumps(results, indent=2, ensure_ascii=False)
            return Response(content=formatted, media_type="application/json")
        else:
            return Response(
                content=json.dumps(results, ensure_ascii=False, default=str),
                media_type="application/json",
            )

    @app.post("/results/export", tags="Results")
    async def export_results(request: ExportRequest) -> Response:
        """Export all results in the specified format."""
        results = await queue_manager.get_all_results()

        if not results:
            return Response(content="No results to export", media_type="text/plain")

        if request.format == OutputFormat.CSV:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=results.csv"},
            )
        elif request.format == OutputFormat.PRETTY:
            formatted = json.dumps(results, indent=2, ensure_ascii=False)
            return Response(content=formatted, media_type="application/json")
        else:
            return Response(
                content=json.dumps(results, ensure_ascii=False, default=str),
                media_type="application/json",
            )

    @app.delete("/results/clear", response_model=ClearResponse, tags="Results")
    async def clear_results() -> ClearResponse:
        """Clear all stored results from completed jobs."""
        count = await queue_manager.clear_results()
        return ClearResponse(
            message=f"Cleared results from {count} completed jobs",
            cleared_count=count,
        )

    # --- Configuration Endpoints ---

    @app.get("/config", response_model=ConfigResponse, tags="Configuration")
    async def get_config() -> ConfigResponse:
        """Get the current crawler configuration."""
        return ConfigResponse(
            chrome_profile_path="",
            page_timeout=30000,
            selector_timeout=15000,
            scroll_timeout=45,
            max_scroll_attempts=5,
            max_retries=3,
            request_timeout=25000,
            viewport_width=1920,
            viewport_height=1080,
        )

    @app.put("/config", response_model=ConfigResponse, tags="Configuration")
    async def update_config(config_update: dict[str, Any]) -> ConfigResponse:
        """Update the crawler configuration."""
        return ConfigResponse(
            chrome_profile_path=config_update.get("chrome_profile_path", ""),
            page_timeout=config_update.get("page_timeout", 30000),
            selector_timeout=config_update.get("selector_timeout", 15000),
            scroll_timeout=config_update.get("scroll_timeout", 45),
            max_scroll_attempts=config_update.get("max_scroll_attempts", 5),
            max_retries=config_update.get("max_retries", 3),
            request_timeout=config_update.get("request_timeout", 25000),
            viewport_width=config_update.get("viewport_width", 1920),
            viewport_height=config_update.get("viewport_height", 1080),
        )

    # --- Review Endpoints ---

    @app.get("/reviews", response_model=AllReviewsResponse, tags="Reviews")
    async def get_all_reviews(
        limit: int = 50,
        offset: int = 0,
    ) -> AllReviewsResponse:
        """Get all reviews from completed crawl jobs with pagination.

        This endpoint returns reviews from all completed jobs, flattened into a single list.
        """
        all_results = await queue_manager.get_all_results()

        if not all_results:
            return AllReviewsResponse(
                total_reviews=0,
                reviews=[],
                total=0,
                limit=limit,
                offset=offset,
            )

        # Extract all reviews from all companies
        all_reviews = []
        for company_data in all_results:
            reviews = company_data.get("reviews", [])
            if reviews and isinstance(reviews, list):
                for review in reviews:
                    all_reviews.append(ReviewResponse(**review))

        # Apply pagination
        total = len(all_reviews)
        paginated = all_reviews[offset:offset + limit]

        return AllReviewsResponse(
            total_reviews=total,
            reviews=list(paginated),
            total=total,
            limit=limit,
            offset=offset,
        )

    @app.get("/reviews/job/{job_id}", response_model=JobReviewsResponse, tags="Reviews")
    async def get_job_reviews(job_id: str) -> JobReviewsResponse:
        """Get all reviews from a specific crawl job.

        This endpoint returns all reviews grouped by company for a given job.
        """
        job = await queue_manager.get_crawl_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )

        if not job.results:
            return JobReviewsResponse(
                job_id=job.job_id,
                prompt=job.prompt,
                total_reviews=0,
                companies=[],
            )

        companies_reviews = []
        total_reviews = 0

        for company_data in job.results:
            reviews = company_data.get("reviews", [])
            if reviews and isinstance(reviews, list) and len(reviews) > 0:
                company_reviews = [ReviewResponse(**r) for r in reviews]
                companies_reviews.append(
                    CompanyReviewsResponse(
                        company_name=company_data.get("name", "N/A"),
                        company_rating=company_data.get("rating", "N/A"),
                        company_category=company_data.get("category", "N/A"),
                        reviews=company_reviews,
                    )
                )
                total_reviews += len(company_reviews)

        return JobReviewsResponse(
            job_id=job.job_id,
            prompt=job.prompt,
            total_reviews=total_reviews,
            companies=companies_reviews,
        )

    @app.get(
        "/reviews/company/{job_id}/{company_index}",
        response_model=CompanyReviewsResponse,
        tags="Reviews",
    )
    async def get_company_reviews(
        job_id: str,
        company_index: int,
    ) -> CompanyReviewsResponse:
        """Get reviews for a specific company from a completed crawl job.

        Args:
            job_id: The ID of the crawl job.
            company_index: The zero-based index of the company in the job results.
        """
        job = await queue_manager.get_crawl_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )

        if not job.results:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for job {job_id}",
            )

        if company_index < 0 or company_index >= len(job.results):
            raise HTTPException(
                status_code=404,
                detail=f"Company index {company_index} out of range. Job has {len(job.results)} companies.",
            )

        company_data = job.results[company_index]
        reviews = company_data.get("reviews", [])

        company_reviews = [ReviewResponse(**r) for r in reviews] if reviews else []

        return CompanyReviewsResponse(
            company_name=company_data.get("name", "N/A"),
            company_rating=company_data.get("rating", "N/A"),
            company_category=company_data.get("category", "N/A"),
            reviews=company_reviews,
        )

    # --- Browser Endpoints ---

    @app.get("/browser/info", response_model=BrowserInfoResponse, tags="Browser")
    async def get_browser_info() -> BrowserInfoResponse:
        """Get browser information and status."""
        return BrowserInfoResponse(
            is_initialized=True,
            is_running=True,
            profile_path="",
            headless=False,
            locale="de-DE",
        )

    @app.post("/browser/restart", tags="Browser")
    async def restart_browser() -> dict[str, str]:
        """Restart the browser (useful if browser state becomes corrupted)."""
        return {"message": "Browser restart not available in process-based mode"}

    return app


# Create the FastAPI app instance
app = _create_app()


async def _process_job(job_id: str) -> None:
    """Process a single crawl job in the background.

    This function runs the actual crawl operation in a separate process
    and updates the queue manager with the result.
    If auto_email_crawl is enabled, it also triggers an email crawl.
    """
    # Get the next job from queue - this transitions status from PENDING to RUNNING
    job = await queue_manager.get_next_job()
    if not job:
        logger.warning("Job %s not found in queue or already processed", job_id[:8])
        return

    logger.info(
        "Processing job %s for prompt: %s (track_reviews=%s, auto_email_crawl=%s)",
        job_id[:8],
        job.prompt,
        job.track_reviews,
        job.auto_email_crawl,
    )

    try:
        # Run the crawl in a separate process to avoid asyncio/Sync API conflicts
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,  # Uses default ProcessPoolExecutor
            run_crawl_in_process,
            job.prompt,
            job.output_format,
            job.headless,
            job.locale,
            job.track_reviews,
        )

        await queue_manager.complete_job(job_id, results)

        # Check if auto_email_crawl is enabled
        if job.auto_email_crawl and results:
            logger.info("Auto email crawl enabled for job %s, starting email crawl...", job_id[:8])

            # Extract valid websites from results
            websites = []
            for company in results:
                website = company.get("website", "")
                if website and website != "N/A" and URLValidator.is_valid(website):
                    websites.append({
                        "name": company.get("name", "N/A"),
                        "website": website,
                    })

            if websites:
                # Set email_status to "pending" for all companies in the parent job
                await queue_manager.start_email_crawl_for_parent(job_id)
                # Create and start email crawl job
                email_job = await queue_manager.add_email_job(
                    parent_job_id=job_id,
                    websites=websites,
                    headless=True,
                    chrome_profile_path="",
                )
                asyncio.create_task(_process_email_job(email_job.job_id))
            else:
                logger.warning("No valid websites found for email crawl in job %s", job_id[:8])

    except Exception as e:
        logger.exception("Job %s failed: %s", job_id[:8], e)
        await queue_manager.fail_job(job_id, str(e))


async def _process_email_job(job_id: str) -> None:
    """Process a single email crawl job in the background.

    This function crawls all websites from the parent job and extracts email addresses.
    """
    # Get the next email job from queue
    email_job = await queue_manager.get_next_email_job()
    if not email_job:
        logger.warning("Email job %s not found in queue or already processed", job_id[:8])
        return

    logger.info(
        "Processing email job %s for parent job %s (websites: %d)",
        job_id[:8],
        email_job.parent_job_id[:8],
        len(email_job.websites),
    )

    try:
        # Create email crawler config
        email_config = EmailCrawlerConfig(
            headless=True,
            chrome_profile_path=email_job.chrome_profile_path,
            page_timeout=15000,
            crawl_delay=1.5,
            max_pages_per_domain=20,
        )

        # Run the email crawl
        emails = await extract_emails_from_websites(
            websites=email_job.websites,
            job_id=email_job.parent_job_id,
            config=email_config,
        )

        await queue_manager.complete_email_job(job_id, emails)
        logger.info("Email job %s completed: %d emails found", job_id[:8], len(emails))

    except Exception as e:
        logger.exception("Email job %s failed: %s", job_id[:8], e)
        await queue_manager.fail_email_job(job_id, str(e))
        
        # Set email_status to "failed" for all companies in the parent job
        email_job_obj = queue_manager._email_jobs.get(job_id)
        if email_job_obj:
            await queue_manager.set_failed_email_status_for_parent(email_job_obj.parent_job_id)


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the FastAPI server.

    This is the main entry point for the API server.

    Args:
        host: The host to bind to.
        port: The port to listen on.
    """
    import uvicorn

    logger.info("Starting Google Maps Crawler API on %s:%d", host, port)
    uvicorn.run(
        "core.api.server:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    start_server()