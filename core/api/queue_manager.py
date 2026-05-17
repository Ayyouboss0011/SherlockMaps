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
                 locale: str = "de-DE", max_results: Optional[int] = None) -> None:
        self.job_id: str = str(uuid.uuid4())
        self.prompt: str = prompt
        self.output_format: str = output_format
        self.headless: bool = headless
        self.locale: str = locale
        self.max_results: Optional[int] = max_results
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
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results_count": len(self.results) if self.results else 0,
            "error": self.error,
        }


class QueueManager:
    """Manages crawl job queue and execution."""

    def __init__(self) -> None:
        self._jobs: Dict[str, CrawlJob] = {}
        self._queue: list[str] = []
        self._active_job: Optional[str] = None
        self._lock = asyncio.Lock()
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._total_companies: int = 0

    @property
    def queue_length(self) -> int:
        """Get the current queue length."""
        return len(self._queue)

    @property
    def active_jobs(self) -> int:
        """Get the number of active jobs."""
        return 1 if self._active_job else 0

    @property
    def is_busy(self) -> bool:
        """Check if the crawler is currently busy."""
        return self._active_job is not None

    @property
    def active_job_id(self) -> Optional[str]:
        """Get the active job ID."""
        return self._active_job

    async def add_job(self, prompt: str, output_format: str = "json", headless: bool = False,
                      locale: str = "de-DE", max_results: Optional[int] = None) -> CrawlJob:
        """Add a new crawl job to the queue."""
        async with self._lock:
            job = CrawlJob(
                prompt=prompt,
                output_format=output_format,
                headless=headless,
                locale=locale,
                max_results=max_results,
            )
            self._jobs[job.job_id] = job
            self._queue.append(job.job_id)
            logger.info("Added new crawl job: %s for prompt: %s", job.job_id[:8], prompt)
            return job

    async def get_next_job(self) -> Optional[CrawlJob]:
        """Get the next job from the queue."""
        async with self._lock:
            if not self._queue:
                return None
            job_id = self._queue.pop(0)
            job = self._jobs.get(job_id)
            if job:
                self._active_job = job_id
                job.status = JobStatus.RUNNING
                logger.info("Started processing job: %s", job_id[:8])
            return job

    async def complete_job(self, job_id: str, results: list[dict[str, Any]]) -> None:
        """Mark a job as completed."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.complete(results)
                self._active_job = None
                self._total_completed += 1
                self._total_companies += len(results)
                logger.info("Completed job: %s with %d results", job_id[:8], len(results))

    async def fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.fail(error)
                self._active_job = None
                self._total_failed += 1
                logger.info("Failed job: %s - %s", job_id[:8], error)

    async def cancel_job(self, job_id: str) -> Optional[CrawlJob]:
        """Cancel a specific job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                if job.status == JobStatus.RUNNING:
                    self._active_job = None
                elif job.status == JobStatus.PENDING and job_id in self._queue:
                    self._queue.remove(job_id)
                job.cancel()
                logger.info("Cancelled job: %s", job_id[:8])
                return job
            return None

    async def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def get_all_jobs(self, limit: int = 50, offset: int = 0) -> list[CrawlJob]:
        """Get all jobs with pagination."""
        async with self._lock:
            jobs = list(self._jobs.values())
            # Sort by created_at descending (newest first)
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs[offset:offset + limit]

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about all jobs."""
        async with self._lock:
            pending = sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING)
            running = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)
            completed = sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED)
            failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)
            cancelled = sum(1 for j in self._jobs.values() if j.status == JobStatus.CANCELLED)

            return {
                "total_crawls": len(self._jobs),
                "total_companies_found": self._total_companies,
                "total_pending": pending,
                "total_running": running,
                "total_completed": completed,
                "total_failed": failed,
                "total_cancelled": cancelled,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def clear_results(self) -> int:
        """Clear all completed job results."""
        async with self._lock:
            count = 0
            for job in self._jobs.values():
                if job.status == JobStatus.COMPLETED:
                    job.results = None
                    count += 1
            logger.info("Cleared results from %d completed jobs", count)
            return count

    async def get_all_results(self) -> list[dict[str, Any]]:
        """Get results from all completed jobs."""
        async with self._lock:
            results = []
            for job in self._jobs.values():
                if job.results:
                    results.extend(job.results)
            return results