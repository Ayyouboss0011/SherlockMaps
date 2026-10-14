"""Import email addresses from spreadsheet files (xlsx/csv) into the blacklist.

Scans every cell of every sheet (or every CSV field) and extracts all
email-like tokens, so the user does not need a dedicated "Email" column -
the parser finds the addresses wherever they are in the table.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

# Matches typical email addresses: local@domain.tld (one or more dots in domain)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


def extract_emails_from_file(data: bytes, filename: str) -> tuple[list[str], dict[str, Any]]:
    """Extract unique email addresses from an .xlsx or .csv file.

    Args:
        data: Raw file bytes.
        filename: Original file name (decides the parser).

    Returns:
        (emails, info): sorted unique lowercase email addresses and scan info
        with 'sheets_scanned' and 'cells_scanned' keys.

    Raises:
        ValueError: If the file type is not supported.
    """
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        return _extract_xlsx(data)
    if name.endswith(".csv"):
        return _extract_csv(data)
    raise ValueError(
        "Unsupported file type: please upload .xlsx or .csv "
        "(for .xls please save it as .xlsx first)"
    )


def _extract_xlsx(data: bytes) -> tuple[list[str], dict[str, Any]]:
    from openpyxl import load_workbook  # imported here to keep module import light

    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    emails: set[str] = set()
    sheets_scanned = 0
    cells_scanned = 0
    try:
        for sheet in workbook.worksheets:
            sheets_scanned += 1
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is None:
                        continue
                    cells_scanned += 1
                    for match in EMAIL_RE.findall(str(cell.value)):
                        emails.add(match.lower())
    finally:
        workbook.close()
    return sorted(emails), {
        "sheets_scanned": sheets_scanned,
        "cells_scanned": cells_scanned,
    }


def _extract_csv(data: bytes) -> tuple[list[str], dict[str, Any]]:
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = data.decode("utf-8", errors="replace")

    emails: set[str] = set()
    cells_scanned = 0
    for row in csv.reader(io.StringIO(text)):
        for field in row:
            if not field:
                continue
            cells_scanned += 1
            for match in EMAIL_RE.findall(field):
                emails.add(match.lower())
    return sorted(emails), {
        "sheets_scanned": 1,
        "cells_scanned": cells_scanned,
    }
