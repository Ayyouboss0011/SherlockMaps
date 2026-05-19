"""FastAPI server for the Google Maps Crawler REST API.

This module creates a persistent REST API server that:
1. Initializes the browser on startup
2. Accepts crawl jobs via HTTP requests
3. Processes jobs sequentially (one at a time)
4. Remains running for additional requests
5. Preserves the Chrome profile between jobs
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
    BrowserInfoResponse,
    CancelResponse,
    ClearResponse,
    ConfigResponse,
    CrawlRequest,
    CrawlResponse,
    ExportRequest,
    HealthResponse,
    HistoryEntry,
    HistoryResponse,
    JobResultResponse,
    JobStatus,
    OutputFormat,
    StatsResponse,
    StatusResponse,
)
from core.api.queue_manager import QueueManager
from core.browser import BrowserManager
from core.extractors import MapsExtractor
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
) -> list[dict[str, Any]]:
    """Run a crawl in a worker process.

    This function performs the actual crawl operation using synchronous Playwright code
    in a separate process to avoid asyncio loop conflicts.

    Args:
        prompt: Search prompt for Google Maps.
        output_format: Output format.
        headless: Run in headless mode.
        locale: Browser locale.

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
        raw_results = extractor.extract_all()

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


def _create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Google Maps Crawler API",
        description="REST API for crawling Google Maps company data. "
                    "This API allows you to submit crawl jobs, monitor their "
                    "progress, and retrieve results.",
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
            active_jobs=queue_manager.active_jobs,
            queue_length=queue_manager.queue_length,
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
        """
        job = await queue_manager.add_job(
            prompt=request.prompt,
            output_format=request.output_format.value,
            headless=request.headless,
            locale=request.locale,
            max_results=request.max_results,
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

        entries = [
            HistoryEntry(
                job_id=j.job_id,
                status=j.status,
                prompt=j.prompt,
                created_at=j.created_at,
                completed_at=j.completed_at,
                results_count=len(j.results) if j.results else 0,
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
        job = await queue_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return JobResultResponse(
            job_id=job.job_id,
            status=job.status,
            prompt=job.prompt,
            created_at=job.created_at,
            completed_at=job.completed_at,
            results=job.results,
            error=job.error,
        )

    @app.get("/crawl/{job_id}/results", response_model=JobResultResponse, tags="Crawler")
    async def get_job_results(job_id: str) -> JobResultResponse:
        """Get the results of a completed crawl job."""
        job = await queue_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )

        return JobResultResponse(
            job_id=job.job_id,
            status=job.status,
            prompt=job.prompt,
            created_at=job.created_at,
            completed_at=job.completed_at,
            results=job.results,
            error=job.error,
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
    """
    # Get the next job from queue - this transitions status from PENDING to RUNNING
    job = await queue_manager.get_next_job()
    if not job:
        logger.warning("Job %s not found in queue or already processed", job_id[:8])
        return

    logger.info("Processing job %s for prompt: %s", job_id[:8], job.prompt)

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
        )

        await queue_manager.complete_job(job_id, results)

    except Exception as e:
        logger.exception("Job %s failed: %s", job_id[:8], e)
        await queue_manager.fail_job(job_id, str(e))


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