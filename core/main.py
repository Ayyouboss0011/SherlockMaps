#!/usr/bin/env python3
"""
Google Maps Crawler - Professional Open Source Webcrawler

Extract company information from Google Maps with ease.
Supports JSON, CSV, and pretty-printed output formats.

Usage:
    # Using environment variables:
    export PROMPT="restaurants berlin"
    export OUTPUT_FORMAT="json"  # json, csv, pretty, file, print
    export HEADLESS="false"
    python core/main.py

    # Using command line arguments:
    python core/main.py "restaurants berlin"

    # Using Python API:
    from core.models import CrawlerConfig
    from core.crawler import GoogleMapsCrawler

    config = CrawlerConfig(search_prompt="restaurants berlin")
    with GoogleMapsCrawler(config) as crawler:
        results = crawler.crawl()
"""

import os
import sys

# Add the parent directory to sys.path so that `from core.main_cli import main` works
# This allows running from both the root directory and from within the core directory
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.main_cli import main

if __name__ == "__main__":
    main()
