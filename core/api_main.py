#!/usr/bin/env python3
"""API entry point for the Google Maps Crawler REST API.

This module starts the FastAPI server that provides a REST API
for controlling the crawler.

Usage:
    python core/api_main.py

Environment Variables:
    API_HOST: The host to bind to (default: 0.0.0.0)
    API_PORT: The port to listen on (default: 8000)
    DISPLAY: The X display to use (default: :99)

Example:
    # Start the API server
    python core/api_main.py

    # Custom host and port
    API_HOST=0.0.0.0 API_PORT=8080 python core/api_main.py

    # Using docker
    docker run -p 8000:8000 google-maps-crawler:latest
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys

# Add the parent directory to sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.api.server import start_server

logger = logging.getLogger(__name__)


def verify_display() -> bool:
    """Verify that the X display (Xvfb) is available and functional.

    Returns:
        True if the display is ready, False otherwise.
    """
    display = os.getenv("DISPLAY", ":99")
    logger.info("Checking X display: %s", display)

    try:
        result = subprocess.run(
            ["x11-info", "-display", display],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "Server reports" in result.stdout:
            logger.info("X display %s is functional", display)
            return True

        # Fallback: try xdpyinfo as alternative
        result = subprocess.run(
            ["xdpyinfo", "-display", display],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("xdpyinfo confirms X display %s is functional", display)
            return True

        logger.warning(
            "Display verification tools inconclusive. stdout: %s, stderr: %s",
            result.stdout[:200] if result.stdout else "(empty)",
            result.stderr[:200] if result.stderr else "(empty)",
        )
        # Do not block startup if verification tools are missing -
        # Playwright will fail with a clear error if DISPLAY is truly unavailable.
        return True

    except FileNotFoundError:
        # x11-info and xdpyinfo not available - skip verification
        logger.warning(
            "Display verification tools (x11-info, xdpyinfo) not found. "
            "Skipping DISPLAY check. Playwright will fail with a clear error "
            "if the display is truly unavailable."
        )
        return True
    except subprocess.TimeoutExpired:
        logger.warning("Display verification timed out. Proceeding anyway.")
        return True
    except Exception as e:
        logger.warning("Display verification failed: %s. Proceeding anyway.", e)
        return True


def main() -> None:
    """Start the API server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("=" * 50)
    logger.info("Google Maps Crawler - REST API Server")
    logger.info("=" * 50)

    # Verify X display is available before starting the server
    verify_display()

    # Get configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    logger.info("API Host: %s", host)
    logger.info("API Port: %d", port)
    logger.info("Starting server...")
    logger.info("")
    logger.info("API Documentation: http://%s:%d/docs", host, port)
    logger.info("Health Check: http://%s:%d/health", host, port)
    logger.info("")

    # Start the server
    start_server(host=host, port=port)


if __name__ == "__main__":
    main()