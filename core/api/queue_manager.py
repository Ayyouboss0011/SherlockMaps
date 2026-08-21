"""Queue manager for handling crawl jobs in the Google Maps Crawler REST API."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.api.models import JobStatus

logger = logging.getLogger(__name__)


class CrawlJob:
    """Represents a single crawl job."""

    def __init__(self, prompt: str, output_format: str = "json", headless: bool = False,
                 locale: str = "de-DE", max_results: Optional[int] = None,
                 track_reviews: bool = True, auto_email_crawl: bool = False) -> None:
        self.job_id: str = str(uuid.uuid4())
        self.prompt: str = prompt
        self.output_format: str = output_format
        self.headless: bool = headless
        self.locale: str = locale
        self.max_results: Optional[int] = max_results
        self.track_reviews: bool = track_reviews
        self.auto_email_crawl: bool = auto_email_crawl
        self.status: JobStatus = JobStatus.PENDING
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.results: Optional[list[dict[str, Any]]] = None
        self.error: Optional[str] = None
        self._cancel_event: asyncio.Event = asyncio.Event()

    def cancel(self) -> None:
        """Mark this job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
        self._cancel_event.set()

    def fail(self, error: str) -> None:
        """Mark this job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def complete(self, results: list[dict[str, Any]]) -> None:
        """Mark this job as completed with results."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.results = results

    def should_cancel(self) -> bool:
        """Check if this job has been cancelled."""
        return self.status == JobStatus.CANCELLED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "prompt": self.prompt,
            "output_format": self.output_format,
            "headless": self.headless,
            "locale": self.locale,
            "max_results": self.max_results,
            "track_reviews": self.track_reviews,
            "auto_email_crawl": self.auto_email_crawl,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results_count": len(self.results) if self.results else 0,
            "error": self.error,
        }


class EmailCrawlJob:
    """Represents a single email crawl job."""

    def __init__(self, parent_job_id: str, websites: list[dict],
                 headless: bool = True, chrome_profile_path: str = "") -> None:
        self.job_id: str = str(uuid.uuid4())
        self.parent_job_id: str = parent_job_id
        self.websites: list[dict] = websites
        self.headless: bool = headless
        self.chrome_profile_path: str = chrome_profile_path
        self.status: JobStatus = JobStatus.PENDING
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.results: Optional[list[dict[str, Any]]] = None
        self.error: Optional[str] = None

    def complete(self, results: list[dict[str, Any]]) -> None:
        """Mark this job as completed with results."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.results = results

    def fail(self, error: str) -> None:
        """Mark this job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "parent_job_id": self.parent_job_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "emails_found": len(self.results) if self.results else 0,
            "error": self.error,
        }


class QueueManager:
    """Manages crawl job queue and execution."""

    def __init__(self) -> None:
        self._crawl_jobs: Dict[str, CrawlJob] = {}
        self._email_jobs: Dict[str, EmailCrawlJob] = {}
        self._crawl_queue: list[str] = []
        self._email_queue: list[str] = []
        self._active_crawl_job: Optional[str] = None
        self._active_email_job: Optional[str] = None
        self._lock = asyncio.Lock()
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._total_companies: int = 0
        self._total_emails: int = 0

    @property
    def crawl_queue_length(self) -> int:
        """Get the current crawl queue length."""
        return len(self._crawl_queue)

    @property
    def email_queue_length(self) -> int:
        """Get the current email queue length."""
        return len(self._email_queue)

    @property
    def active_crawl_jobs(self) -> int:
        """Get the number of active crawl jobs."""
        return 1 if self._active_crawl_job else 0

    @property
    def active_email_jobs(self) -> int:
        """Get the number of active email jobs."""
        return 1 if self._active_email_job else 0

    @property
    def is_busy(self) -> bool:
        """Check if the crawler is currently busy."""
        return self._active_crawl_job is not None

    @property
    def is_email_busy(self) -> bool:
        """Check if the email crawler is currently busy."""
        return self._active_email_job is not None

    @property
    def active_crawl_job_id(self) -> Optional[str]:
        """Get the active crawl job ID."""
        return self._active_crawl_job

    @property
    def active_email_job_id(self) -> Optional[str]:
        """Get the active email job ID."""
        return self._active_email_job

    async def add_job(self, prompt: str, output_format: str = "json", headless: bool = False,
                      locale: str = "de-DE", max_results: Optional[int] = None,
                      track_reviews: bool = True, auto_email_crawl: bool = False) -> CrawlJob:
        """Add a new crawl job to the queue."""
        async with self._lock:
            job = CrawlJob(
                prompt=prompt,
                output_format=output_format,
                headless=headless,
                locale=locale,
                max_results=max_results,
                track_reviews=track_reviews,
                auto_email_crawl=auto_email_crawl,
            )
            self._crawl_jobs[job.job_id] = job
            self._crawl_queue.append(job.job_id)
            logger.info("Added new crawl job: %s for prompt: %s (auto_email_crawl=%s)",
                        job.job_id[:8], prompt, auto_email_crawl)
            return job

    async def add_email_job(self, parent_job_id: str, websites: list[dict],
                            headless: bool = True, chrome_profile_path: str = "") -> EmailCrawlJob:
        """Add a new email crawl job to the queue."""
        async with self._lock:
            job = EmailCrawlJob(
                parent_job_id=parent_job_id,
                websites=websites,
                headless=headless,
                chrome_profile_path=chrome_profile_path,
            )
            self._email_jobs[job.job_id] = job
            self._email_queue.append(job.job_id)
            logger.info("Added new email crawl job: %s for parent job: %s (websites: %d)",
                        job.job_id[:8], parent_job_id[:8], len(websites))
            return job

    async def get_next_job(self) -> Optional[CrawlJob]:
        """Get the next crawl job from the queue."""
        async with self._lock:
            if not self._crawl_queue:
                return None
            job_id = self._crawl_queue.pop(0)
            job = self._crawl_jobs.get(job_id)
            if job:
                self._active_crawl_job = job_id
                job.status = JobStatus.RUNNING
                logger.info("Started processing crawl job: %s", job_id[:8])
            return job

    async def get_next_email_job(self) -> Optional[EmailCrawlJob]:
        """Get the next email crawl job from the queue."""
        async with self._lock:
            if not self._email_queue:
                return None
            job_id = self._email_queue.pop(0)
            job = self._email_jobs.get(job_id)
            if job:
                self._active_email_job = job_id
                job.status = JobStatus.RUNNING
                logger.info("Started processing email crawl job: %s", job_id[:8])
            return job

    async def complete_job(self, job_id: str, results: list[dict[str, Any]]) -> None:
        """Mark a crawl job as completed."""
        async with self._lock:
            job = self._crawl_jobs.get(job_id)
            if job:
                job.complete(results)
                self._active_crawl_job = None
                self._total_completed += 1
                self._total_companies += len(results)
                logger.info("Completed crawl job: %s with %d results", job_id[:8], len(results))

    async def start_email_crawl_for_parent(self, parent_job_id: str) -> None:
        """Set email_status to 'pending' for all companies in the parent job."""
        async with self._lock:
            parent_job = self._crawl_jobs.get(parent_job_id)
            if parent_job and parent_job.results:
                for company in parent_job.results:
                    company["email_status"] = "pending"

    async def set_failed_email_status_for_parent(self, parent_job_id: str) -> None:
        """Set email_status to 'failed' for all companies in the parent job."""
        async with self._lock:
            parent_job = self._crawl_jobs.get(parent_job_id)
            if parent_job and parent_job.results:
                for company in parent_job.results:
                    company["email_status"] = "failed"

    async def complete_email_job(self, job_id: str, results: list[dict[str, Any]]) -> None:
        """Mark an email crawl job as completed.
        
        This method merges the email results into the parent crawl job results
        and updates the email_status for each company.
        """
        async with self._lock:
            job = self._email_jobs.get(job_id)
            if job:
                job.complete(results)
                self._active_email_job = None
                self._total_emails += len(results)
                logger.info("Completed email crawl job: %s with %d emails", job_id[:8], len(results))

                # Merge emails into parent crawl job results
                parent_job = self._crawl_jobs.get(job.parent_job_id)
                if parent_job and parent_job.results:
                    from urllib.parse import urlparse

                    # Group emails by company name (lowercased)
                    email_map = {}
                    for email_data in results:
                        comp_name = email_data.get("company_name", "").strip().lower()
                        email = email_data.get("email", "")
                        if comp_name and email:
                            if comp_name not in email_map:
                                email_map[comp_name] = []
                            if email not in email_map[comp_name]:
                                email_map[comp_name].append(email)

                    # Group emails by domain (lowercased)
                    domain_map = {}
                    for email_data in results:
                        domain = email_data.get("domain", "").strip().lower()
                        email = email_data.get("email", "")
                        if domain and email:
                            if domain not in domain_map:
                                domain_map[domain] = []
                            if email not in domain_map[domain]:
                                domain_map[domain].append(email)

                    # Update parent job company results
                    for company in parent_job.results:
                        c_name = company.get("name", company.get("company_name", "")).strip().lower()
                        website = company.get("website", "")
                        c_domain = ""
                        if website and website != "N/A":
                            try:
                                parsed = urlparse(website)
                                c_domain = parsed.netloc.replace("www.", "").strip().lower()
                            except Exception:
                                pass

                        matched_emails = set()
                        if c_name in email_map:
                            matched_emails.update(email_map[c_name])
                        if c_domain in domain_map:
                            matched_emails.update(domain_map[c_domain])

                        # Update email status and emails for this company
                        company["email_status"] = "completed"
                        if matched_emails:
                            existing_emails = company.get("emails", [])
                            if not isinstance(existing_emails, list):
                                existing_emails = []
                            updated_emails = set(existing_emails)
                            updated_emails.update(matched_emails)
                            company["emails"] = list(updated_emails)
                            company["email"] = ", ".join(updated_emails)
                        else:
                            # No emails found for this company
                            company["emails"] = []
                            company["email"] = ""

    async def fail_job(self, job_id: str, error: str) -> None:
        """Mark a crawl job as failed."""
        async with self._lock:
            job = self._crawl_jobs.get(job_id)
            if job:
                job.fail(error)
                self._active_crawl_job = None
                self._total_failed += 1
                logger.info("Failed crawl job: %s - %s", job_id[:8], error)

    async def fail_email_job(self, job_id: str, error: str) -> None:
        """Mark an email crawl job as failed."""
        async with self._lock:
            job = self._email_jobs.get(job_id)
            if job:
                job.fail(error)
                self._active_email_job = None
                self._total_failed += 1
                logger.info("Failed email crawl job: %s - %s", job_id[:8], error)

    async def cancel_job(self, job_id: str) -> Optional[CrawlJob]:
        """Cancel a specific crawl job."""
        async with self._lock:
            job = self._crawl_jobs.get(job_id)
            if job:
                if job.status == JobStatus.RUNNING:
                    self._active_crawl_job = None
                elif job.status == JobStatus.PENDING and job_id in self._crawl_queue:
                    self._crawl_queue.remove(job_id)
                job.cancel()
                logger.info("Cancelled crawl job: %s", job_id[:8])
                return job
            return None

    async def get_crawl_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get a crawl job by ID."""
        async with self._lock:
            return self._crawl_jobs.get(job_id)

    async def get_email_job(self, job_id: str) -> Optional[EmailCrawlJob]:
        """Get an email crawl job by ID."""
        async with self._lock:
            return self._email_jobs.get(job_id)

    async def get_all_jobs(self, limit: int = 50, offset: int = 0) -> list[CrawlJob]:
        """Get all crawl jobs with pagination."""
        async with self._lock:
            jobs = list(self._crawl_jobs.values())
            # Sort by created_at descending (newest first)
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs[offset:offset + limit]

    async def get_all_email_jobs(self, limit: int = 50, offset: int = 0) -> list[EmailCrawlJob]:
        """Get all email crawl jobs with pagination."""
        async with self._lock:
            jobs = list(self._email_jobs.values())
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs[offset:offset + limit]

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about all jobs."""
        async with self._lock:
            crawl_pending = sum(1 for j in self._crawl_jobs.values() if j.status == JobStatus.PENDING)
            crawl_running = sum(1 for j in self._crawl_jobs.values() if j.status == JobStatus.RUNNING)
            crawl_completed = sum(1 for j in self._crawl_jobs.values() if j.status == JobStatus.COMPLETED)
            crawl_failed = sum(1 for j in self._crawl_jobs.values() if j.status == JobStatus.FAILED)
            crawl_cancelled = sum(1 for j in self._crawl_jobs.values() if j.status == JobStatus.CANCELLED)

            email_pending = sum(1 for j in self._email_jobs.values() if j.status == JobStatus.PENDING)
            email_running = sum(1 for j in self._email_jobs.values() if j.status == JobStatus.RUNNING)
            email_completed = sum(1 for j in self._email_jobs.values() if j.status == JobStatus.COMPLETED)
            email_failed = sum(1 for j in self._email_jobs.values() if j.status == JobStatus.FAILED)

            return {
                "total_crawls": len(self._crawl_jobs),
                "total_email_crawls": len(self._email_jobs),
                "total_companies_found": self._total_companies,
                "total_emails_found": self._total_emails,
                "total_pending": crawl_pending,
                "total_running": crawl_running,
                "total_completed": crawl_completed,
                "total_failed": crawl_failed,
                "total_cancelled": crawl_cancelled,
                "email_pending": email_pending,
                "email_running": email_running,
                "email_completed": email_completed,
                "email_failed": email_failed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def clear_results(self) -> int:
        """Clear all completed job results."""
        async with self._lock:
            count = 0
            for job in self._crawl_jobs.values():
                if job.status == JobStatus.COMPLETED:
                    job.results = None
                    count += 1
            logger.info("Cleared results from %d completed jobs", count)
            return count

    async def clear_email_results(self) -> int:
        """Clear all completed email job results."""
        async with self._lock:
            count = 0
            for job in self._email_jobs.values():
                if job.status == JobStatus.COMPLETED:
                    job.results = None
                    count += 1
            logger.info("Cleared results from %d completed email jobs", count)
            return count

    async def get_all_results(self) -> list[dict[str, Any]]:
        """Get results from all completed crawl jobs."""
        async with self._lock:
            results = []
            for job in self._crawl_jobs.values():
                if job.results:
                    results.extend(job.results)
            return results

    async def get_all_email_results(self) -> list[dict[str, Any]]:
        """Get results from all completed email crawl jobs."""
        async with self._lock:
            results = []
            for job in self._email_jobs.values():
                if job.results:
                    results.extend(job.results)
            return results

    async def get_parent_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get the parent crawl job by ID."""
        async with self._lock:
            return self._crawl_jobs.get(job_id)