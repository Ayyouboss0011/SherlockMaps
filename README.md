<div align="center">
  <img src="public/SherlockMaps.png" alt="SherlockMaps Icon" width="200">
</div>

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Playwright](https://img.shields.io/badge/browser--automation-playwright-green.svg)](https://playwright.dev/)

A professional, object-oriented open-source Google Maps web crawler that extracts company information from Google Maps. Built with [Playwright](https://playwright.dev/) for browser automation.

<div align="center">
  <h2>Sherlock Maps</h2>
  <p>Open-Source Google Maps Webcrawler</p>
</div>

## Features

- **Object-Oriented** - Cleanly structured with classes, dataclasses, and design patterns
- **Search** - Search Google Maps with any search term
- **Detailed Company Information** extraction:
  - Company name
  - Category / Industry
  - Address
  - Phone number
  - Website URL
  - Rating (stars)
  - Number of reviews
  - Plus Code
  - Opening hours
  - Attributes (wheelchair accessibility, etc.)
- **Deduplication** based on company name + website
- **URL Validation** (filters out invalid websites)
- **Multiple Output Formats**: JSON, CSV, Pretty-Print, File, Print
- **REST API** - Asynchronous job queue server with full-featured endpoints
- **Docker Support** - Containerized deployment
- **Chrome Profile Persistence** - Session data persists between runs

---

## Get Started

Choose the path that fits your workflow:

| | Description | Install |
|---|---|---|
| **[CLI Mode](#cli-mode)** | Direct command-line usage | `pip install -r requirements.txt` |
| **[Python Library](#python-library)** | Programmatic usage in your scripts | `from core.crawler import run_crawler` |
| **[REST API](#rest-api)** | Persistent API server for integrations | `docker run -p 8000:8000 sherlock-maps` |
| **[Docker](#docker)** | Containerized deployment | `docker build -t sherlock-maps .` |

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd GoogleMapsCrawler
```

### 2. Install dependencies

```bash
cd core
pip install -r requirements.txt
playwright install chromium
```

### 3. Run the crawler

```bash
# CLI Mode
export PROMPT="restaurants berlin"
python main.py
```

---

## CLI Mode

The crawler can be used directly from the command line. All results are output to stdout as JSON by default.

### Output Formats

```bash
# JSON to stdout (default)
export PROMPT="restaurants berlin"
python main.py

# Save as JSON file
export PROMPT="restaurants berlin"
export OUTPUT_FORMAT="file"
python main.py

# Save as CSV file
export PROMPT="restaurants berlin"
export OUTPUT_FORMAT="csv"
python main.py

# Formatted output (one company per block)
export PROMPT="restaurants berlin"
export OUTPUT_FORMAT="print"
python main.py

# Human-readable output
export PROMPT="restaurants berlin"
export OUTPUT_FORMAT="pretty"
python main.py

# Headless mode (for production/servers)
export PROMPT="restaurants berlin"
export HEADLESS="true"
python main.py
```

### Output Formats Overview

| Format | Description |
|---|---|
| `json` | JSON array to stdout (default) |
| `file` | Saves results as `sherlock-maps_YYYYMMDD_HHMMSS.json` |
| `csv` | Saves results as `sherlock-maps_YYYYMMDD_HHMMSS.csv` |
| `print` | Each company individually with separator |
| `pretty` | Human-readable format with aligned fields |

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `PROMPT` | Search term for Google Maps | Required |
| `OUTPUT_FORMAT` | Output format: `json`, `print`, `file`, `csv`, `pretty` | `json` |
| `HEADLESS` | Run browser in headless mode | `false` |
| `GOOGLE_API_KEY` | Optional Google API key | (empty) |

---

## Python Library

### Simple (Convenience Function)

```python
from core.crawler import run_crawler

results = run_crawler(
    prompt="restaurants berlin",
    headless=False,
    output_format="json"
)

for company in results:
    print(f"{company.name} - {company.website}")
```

### Complete (With Configuration)

```python
from core.models import CrawlerConfig, CompanyData
from core.crawler import GoogleMapsCrawler

# Create configuration
config = CrawlerConfig(
    search_prompt="restaurants berlin",
    headless=False,
    output_format="pretty",
)

# Use crawler with context manager
with GoogleMapsCrawler(config) as crawler:
    results = crawler.crawl()

# Process results
for company in results:
    if isinstance(company, CompanyData):
        print(f"{company.name}: {company.rating} stars ({company.reviews_count} reviews)")
```

### Custom Search at Runtime

```python
from core.models import CrawlerConfig
from core.crawler import GoogleMapsCrawler

config = CrawlerConfig(
    search_prompt="cafes berlin",
    output_format="json",
)

with GoogleMapsCrawler(config) as crawler:
    # First search
    results1 = crawler.crawl()

    # Second search with different term
    results2 = crawler.crawl(prompt="restaurants munich")
```

---

## REST API

The crawler can run as a persistent service with REST API. The container starts as an API server and can process multiple crawl jobs sequentially.

### Start the API

```bash
# Build the image
cd core
docker build -t sherlock-maps .

# Start API server (port 8000)
docker run -p 8000:8000 sherlock-maps

# With custom port
docker run -p 8080:8080 -e API_PORT=8080 sherlock-maps
```

### API Endpoints

#### Health & Status

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check (for Docker orchestrators) |
| GET | `/status` | Current status (idle/busy), active jobs, queue length |
| GET | `/stats` | Detailed statistics |

#### Crawler Control

| Method | Path | Description |
|---|---|---|
| POST | `/crawl` | Start a new crawl job |
| GET | `/crawl/{job_id}` | Get job status |
| GET | `/crawl/{job_id}/results` | Get job results |
| DELETE | `/crawl/{job_id}` | Cancel a running job |
| GET | `/crawl/history` | List all jobs with pagination |

#### Data Management

| Method | Path | Description |
|---|---|---|
| GET | `/results` | Get all results |
| POST | `/results/export` | Export results |
| DELETE | `/results/clear` | Clear all results |

#### Configuration

| Method | Path | Description |
|---|---|---|
| GET | `/config` | Get current configuration |
| PUT | `/config` | Update configuration |

#### Browser

| Method | Path | Description |
|---|---|---|
| GET | `/browser/info` | Browser information |
| POST | `/browser/restart` | Restart browser |

### API Examples

```bash
# Start a new crawl job
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"prompt": "restaurants berlin", "output_format": "json"}'

# Get job status
curl http://localhost:8000/crawl/<job_id>

# Get results
curl http://localhost:8000/crawl/<job_id>/results

# Get all results as CSV
curl "http://localhost:8000/results?format=csv"

# Get status
curl http://localhost:8000/status

# Health check
curl http://localhost:8000/health

# Cancel job
curl -X DELETE http://localhost:8000/crawl/<job_id>

# Job history
curl "http://localhost:8000/crawl/history?limit=10&offset=0"
```

### Request Example

```json
{
  "prompt": "restaurants berlin",
  "output_format": "json",
  "headless": false,
  "locale": "de-DE",
  "max_results": 100
}
```

### Response Example (Job Status)

```json
{
  "job_id": "abc-123-def",
  "status": "completed",
  "prompt": "restaurants berlin",
  "created_at": "2026-01-15T10:30:00Z",
  "completed_at": "2026-01-15T10:31:30Z",
  "results_count": 42,
  "error": null
}
```

### Job Status

| Status | Description |
|---|---|
| `pending` | In the queue |
| `running` | Currently running |
| `completed` | Successfully completed |
| `failed` | Failed |
| `cancelled` | Cancelled |

### Interactive API Documentation

When the API server is running, interactive Swagger documentation is available:

```
http://localhost:8000/docs
```

---

## Docker

### Build & Run

```bash
# Build the image
cd core
docker build -t sherlock-maps .

# Run as API server
docker run -p 8000:8000 sherlock-maps

# Run in CLI mode
docker run -e PROMPT="restaurants berlin" sherlock-maps python /app/core/main_cli.py

# Headless mode
docker run -e PROMPT="restaurants berlin" -e HEADLESS="true" sherlock-maps python /app/core/main_cli.py
```

### How It Works

1. **Search** - Navigates to Google Maps with the search term
2. **Scroll** - Loads all search results by scrolling
3. **Extract** - Navigates to each result's detail page and extracts:
   - Company name, category, address, phone, website
   - Rating and number of reviews
   - Opening hours
   - Attributes
4. **Filter** - Removes duplicates and validates website URLs
5. **Output** - Outputs results in the desired format

---

## Architecture

```
Sherlock Maps/
├── .gitignore
├── docker-compose.yml
├── README.md
├── public/
│   └── SherlockMaps.png
└── core/
    ├── __init__.py                   # Package exports
    ├── main.py                       # CLI entry point
    ├── main_cli.py                   # CLI logic
    ├── crawler.py                    # Main crawler class
    ├── requirements.txt              # Python dependencies
    ├── api/
    │   ├── __init__.py
    │   ├── models.py                 # API data models
    │   ├── queue_manager.py          # Job queue management
    │   └── server.py                 # FastAPI server
    ├── browser/
    │   ├── __init__.py
    │   └── browser_manager.py        # Browser lifecycle management
    ├── exceptions/
    │   ├── __init__.py
    │   └── crawler_exceptions.py     # Custom exceptions
    ├── extractors/
    │   ├── __init__.py
    │   └── maps_extractor.py         # Google Maps data extraction
    ├── models/
    │   ├── __init__.py
    │   ├── company.py                # CompanyData model
    │   └── crawler_config.py         # CrawlerConfig model
    ├── output/
    │   ├── __init__.py
    │   └── output_handler.py         # Output formats
    └── processors/
        ├── __init__.py
        ├── url_validator.py          # URL validation
        └── deduplication_processor.py # Deduplication
```

### Class Overview

| Class | Module | Description |
|---|---|---|
| `Sherlock Maps` | | Open-Source Google Maps Webcrawler |
| `GoogleMapsCrawler` | `crawler.py` | Main class, orchestrates the entire crawling process |
| `BrowserManager` | `browser/browser_manager.py` | Manages Playwright browser lifecycle |
| `MapsExtractor` | `extractors/maps_extractor.py` | Extracts company data from Google Maps |
| `CompanyData` | `models/company.py` | Data model for a company |
| `CrawlerConfig` | `models/crawler_config.py` | Crawler configuration |
| `URLValidator` | `processors/url_validator.py` | Validates HTTP(S) URLs |
| `DeduplicationProcessor` | `processors/deduplication_processor.py` | Removes duplicates |
| `OutputHandler` | `output/output_handler.py` | Formats and outputs results |
| `CrawlerBaseException` | `exceptions/crawler_exceptions.py` | Base exception class |

---

## Configuration

### CrawlerConfig Attributes

| Attribute | Type | Default | Description |
|---|---|---|---|
| `search_prompt` | `str` | `""` | The search term for Google Maps |
| `headless` | `bool` | `False` | Run browser in headless mode |
| `output_format` | `Literal` | `"json"` | Output format |
| `chrome_profile_path` | `str` | `"Chrome_Profile"` | Path to Chrome user data directory |
| `viewport` | `ViewPort` | `1920x1080` | Browser viewport dimensions |
| `locale` | `str` | `"de-DE"` | Browser localization |
| `page_timeout` | `int` | `30000` | Maximum navigation timeout in ms |
| `selector_timeout` | `int` | `15000` | Maximum timeout for selectors in ms |
| `scroll_timeout` | `int` | `45` | Maximum time for scrolling in seconds |
| `max_scroll_attempts` | `int` | `5` | Number of scroll attempts before stop |
| `max_retries` | `int` | `3` | Number of navigation retry attempts |
| `request_timeout` | `int` | `25000` | Request timeout in ms |

---

## Example Output

```json
[
  {
    "name": "Restaurant Name",
    "category": "Restaurant",
    "address": "Musterstrasse 1, 10115 Berlin",
    "phone": "+49 30 12345678",
    "website": "https://www.restaurant-example.de",
    "rating": "4.5",
    "reviews_count": "234",
    "plus_code": "GVMF+8H Berlin",
    "opening_hours": "Mon: 12:00-22:00, Tue: 12:00-22:00, ...",
    "attributes": ["Wheelchair accessible entrance"]
  }
]
```

---

## Limitations

- Google Maps UI changes may break selectors (CSS classes like `h1.DUwDvf` are Google-specific)
- Rate limiting: Google may show CAPTCHAs for fast requests
- German localization is hardcoded (`hl=de`), for other languages `browser_manager.py` must be modified
- Requires a display or headless mode for Chromium

---

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Contribution Guide](CONTRIBUTING.md)
- [MIT License](LICENSE)

---

## License

MIT License