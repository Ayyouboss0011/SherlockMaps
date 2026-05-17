"""CLI entry point for the GoogleMapsCrawler.

This module provides the command-line interface for running the crawler.
It handles argument parsing, environment variable reading, and logging setup.

Usage:
    export PROMPT="restaurants berlin"
    python core/main.py

    python core/main.py "restaurants berlin"

    OUTPUT_FORMAT=csv python core/main.py "hotels münchen"
"""

from __future__ import annotations

import logging
import os
import sys

# Add the parent directory to sys.path so that `from core.*` imports work
# This allows running from both the root directory and from within the core directory
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.crawler import run_crawler


def parse_args() -> tuple[str, str, bool]:
    """Parse command-line arguments and environment variables.

    Returns:
        A tuple of (prompt, output_format, headless).
    """
    # Get search prompt from environment variable or command line
    prompt = os.getenv("PROMPT", "")
    if not prompt:
        if len(sys.argv) > 1:
            prompt = " ".join(sys.argv[1:])
        else:
            print("Error: No search prompt provided.")
            print()
            print("Usage:")
            print("  export PROMPT='restaurants berlin' && python core/main.py")
            print("  python core/main.py 'restaurants berlin'")
            print()
            print("Options:")
            print("  PROMPT         Search term for Google Maps (required)")
            print("  OUTPUT_FORMAT  Output format: json, csv, pretty, file, print (default: json)")
            print("  HEADLESS       Run in headless mode: true, false (default: false)")
            sys.exit(1)

    # Get output format from environment variable
    output_format = os.getenv("OUTPUT_FORMAT", "json")
    valid_formats = ("json", "csv", "pretty", "file", "print")
    if output_format not in valid_formats:
        print(f"Warning: Invalid output format '{output_format}'. Using 'json'.")
        output_format = "json"

    # Get headless mode from environment variable
    headless = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

    return prompt, output_format, headless


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application.

    Args:
        level: The logging level.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """Main CLI entry point."""
    # Parse arguments
    prompt, output_format, headless = parse_args()

    # Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting Google Maps Crawler")
    logger.info("Prompt: %s", prompt)
    logger.info("Output format: %s", output_format)
    logger.info("Headless mode: %s", headless)

    # Run the crawler
    try:
        results = run_crawler(
            prompt=prompt,
            headless=headless,
            output_format=output_format,
        )
        logger.info("Crawler completed successfully. Found %d companies.", len(results))

    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Crawler failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()