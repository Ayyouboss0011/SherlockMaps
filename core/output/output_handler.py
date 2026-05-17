"""Output handler for the GoogleMapsCrawler.

This module handles formatting and outputting the scraped company data
in various formats (JSON, CSV, pretty-printed, file).
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import CompanyData

logger = logging.getLogger(__name__)


class OutputHandler:
    """Handles outputting company data in various formats.

    Supported formats:
        - json: Print as formatted JSON to stdout
        - csv: Save to a CSV file
        - file: Save to a JSON file
        - pretty: Print formatted company details to stdout
        - print: Print raw company dicts to stdout

    Usage:
        handler = OutputHandler()
        handler.output(companies, prompt, "json")
    """

    # Output directory for file-based outputs
    OUTPUT_DIR = Path("output")

    def output(
        self,
        companies: list[CompanyData],
        prompt: str,
        output_format: str = "json",
    ) -> None:
        """Output the results in the specified format.

        Args:
            companies: A list of CompanyData objects.
            prompt: The original search prompt.
            output_format: The output format - "json", "csv", "pretty", "file", "print".
        """
        logger.info("Outputting %d results in format: %s", len(companies), output_format)

        # Print summary header
        print("\n" + "=" * 60)
        print(f"  Google Maps Crawler - Results")
        print("=" * 60)
        print(f"  Search term:       {prompt}")
        print(f"  Companies found:   {len(companies)}")
        print("=" * 60 + "\n")

        # Route to the appropriate output method
        dispatch = {
            "json": self._output_json,
            "csv": self._output_csv,
            "file": self._output_file,
            "pretty": self._output_pretty,
            "print": self._output_print,
        }

        method = dispatch.get(output_format)
        if method:
            method(companies)
        else:
            logger.warning("Unknown output format: %s. Using 'json' as default.", output_format)
            self._output_json(companies)

    def _output_json(self, companies: list[CompanyData]) -> None:
        """Output companies as formatted JSON.

        Args:
            companies: A list of CompanyData objects.
        """
        data = [company.to_dict() for company in companies]
        print(json.dumps(data, ensure_ascii=False, indent=2))

    def _output_csv(self, companies: list[CompanyData]) -> None:
        """Save companies to a CSV file.

        Args:
            companies: A list of CompanyData objects.
        """
        if not companies:
            print("No companies to export.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.OUTPUT_DIR / f"results_{timestamp}.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Flatten attributes for CSV
        fieldnames = ["name", "category", "address", "phone", "website", "rating", "reviews_count", "plus_code", "opening_hours", "attributes"]
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for company in companies:
                row = company.to_dict()
                # Convert attributes list to string
                if isinstance(row.get("attributes"), list):
                    row["attributes"] = "; ".join(row["attributes"])
                writer.writerow(row)

        print(f"📄 Results saved to: {output_file}")
        print()

    def _output_file(self, companies: list[CompanyData]) -> None:
        """Save companies to a JSON file.

        Args:
            companies: A list of CompanyData objects.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.OUTPUT_DIR / f"results_{timestamp}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = [company.to_dict() for company in companies]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"📄 Results saved to: {output_file}")
        print()

    def _output_pretty(self, companies: list[CompanyData]) -> None:
        """Output formatted company details.

        Args:
            companies: A list of CompanyData objects.
        """
        for i, company in enumerate(companies, 1):
            data = company.to_dict()
            print(f"\n{'─' * 60}")
            print(f"  {i}. {data.get('name', 'N/A')}")
            print(f"{'─' * 60}")
            for key, value in data.items():
                if value and value != "" and value != "N/A":
                    # Format attributes list
                    if isinstance(value, list):
                        value = ", ".join(value)
                    print(f"  {key:20s}: {value}")
        print(f"\n{'═' * 60}")

    def _output_print(self, companies: list[CompanyData]) -> None:
        """Output raw company dictionaries.

        Args:
            companies: A list of CompanyData objects.
        """
        for i, company in enumerate(companies, 1):
            data = company.to_dict()
            print(f"\n--- Company {i}/{len(companies)} ---")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            print("-" * 60)
        print()