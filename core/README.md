# Sherlock Maps crawler

This directory contains the Python crawler, FastAPI server, extractors,
processors and bundled Chromium extensions.

## Layout

```text
core/
├── api/            FastAPI server, job queue and email campaign API
├── browser/        Playwright browser lifecycle
├── extractors/     Google Maps and email extractors
├── models/         CrawlerConfig, CompanyData and EmailData
├── output/         JSON, CSV and pretty output
├── processors/     Deduplication and URL validation
├── extensions/     Unpacked Chromium extensions
├── api_main.py     Start the REST API
├── main.py         CLI entry point
├── crawler.py      Crawler orchestration and Python API
└── requirements.txt
```

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# CLI
PROMPT="restaurants berlin" python main.py

# API
python api_main.py
```

See the [quick start](../docs/quickstart.md) and
[REST API](../docs/api.md) documentation for the full setup.
