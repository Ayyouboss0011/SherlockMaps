#!/usr/bin/env python3
"""API entry point for the Google Maps Crawler REST API.

This module starts the FastAPI server that provides a REST API
for controlling the crawler.

Usage:
    python core/api_main.py

Environment Variables:
    API_HOST: The host to bind to (default: 0.0.0.0)
    API_PORT: The port to listen on (default: 8000)

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
import sys

# Add the parent directory to sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.api.server import start_server

logger = logging.getLogger(__name__)


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