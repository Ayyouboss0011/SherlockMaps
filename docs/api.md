# REST API

The crawler exposes a FastAPI service with an asynchronous job queue.

- Docker Compose: <http://localhost:6970>
- Local backend: <http://localhost:8000>
- Swagger UI: `/docs`
- OpenAPI schema: `/openapi.json`

The API has **no authentication by default**. Keep it on localhost or a trusted
private network, or put it behind an authenticated reverse proxy.

## Quick example

```bash
API=http://localhost:6970

curl -X POST "$API/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "restaurants berlin",
    "auto_email_crawl": true,
    "max_results": 50
  }'
```

Response:

```json
{
  "job_id": "8f3c1a2e-0b7d-4a8f-9d2e-1c6b5a4f3e21",
  "status": "pending",
  "prompt": "restaurants berlin",
  "created_at": "2026-11-14T14:00:00Z",
  "results_count": null,
  "error": null
}
```

## Endpoints

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/status` | Idle/busy status, active jobs and queue length |
| `GET` | `/stats` | Aggregated crawl, company and email statistics |

### Crawler

| Method | Path | Description |
|---|---|---|
| `POST` | `/crawl` | Start a crawl job |
| `GET` | `/crawl/history` | List jobs with pagination |
| `GET` | `/crawl/{job_id}` | Get job status |
| `GET` | `/crawl/{job_id}/results` | Get job results |
| `DELETE` | `/crawl/{job_id}` | Cancel a pending/running job |

### Results

| Method | Path | Description |
|---|---|---|
| `GET` | `/results?format=json` | All results as JSON |
| `GET` | `/results?format=csv` | All results as CSV download |
| `GET` | `/results?format=pretty` | Pretty-printed JSON |
| `POST` | `/results/export` | Export with `{"format": "csv"}` |
| `DELETE` | `/results/clear` | Delete all stored results |

### Configuration

| Method | Path | Description |
|---|---|---|
| `GET` | `/config` | Current crawler configuration |
| `PUT` | `/config` | Update crawler configuration |
| `GET` | `/browser/info` | Browser/profile information |
| `POST` | `/browser/restart` | Restart endpoint (process-based mode) |

### Email crawling

| Method | Path | Description |
|---|---|---|
| `POST` | `/email-crawl` | Start email enrichment for a completed job |
| `GET` | `/email-crawl/{job_id}` | Get email crawl status |
| `GET` | `/email-crawl/parent/{parent_job_id}` | Find the email job for a crawl job |
| `GET` | `/emails` | All found emails with pagination |
| `DELETE` | `/emails` | Clear stored emails |

### Email campaigns

| Method | Path | Description |
|---|---|---|
| `GET` | `/smtp/settings` | Read SMTP settings |
| `PUT` | `/smtp/settings` | Update SMTP settings |
| `POST` | `/smtp/test` | Send a test email |
| `GET` | `/templates` | List email templates |
| `POST` | `/templates` | Create a template |
| `PUT` | `/templates/{template_id}` | Update a template |
| `DELETE` | `/templates/{template_id}` | Delete a template |
| `GET` | `/emails/recipients/{job_id}` | Recipients for a completed job |
| `POST` | `/emails/send` | Start a campaign |
| `GET` | `/emails/send/history` | Campaign send history |
| `POST` | `/emails/send/{history_id}/cancel` | Cancel a campaign |
| `DELETE` | `/emails/send/history` | Clear send history |

### Email blacklist

| Method | Path | Description |
|---|---|---|
| `GET` | `/email-blacklist` | List blacklisted addresses |
| `POST` | `/email-blacklist` | Add addresses |
| `POST` | `/email-blacklist/check` | Check addresses |
| `DELETE` | `/email-blacklist/{email}` | Remove one address |
| `DELETE` | `/email-blacklist` | Clear the blacklist |
| `POST` | `/email-blacklist/import-file` | Import `.xlsx`/`.csv` emails |

## Crawl request

```json
{
  "prompt": "restaurants berlin",
  "output_format": "json",
  "headless": false,
  "locale": "de-DE",
  "max_results": 100,
  "track_reviews": true,
  "auto_email_crawl": true,
  "use_persistent_profile": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `prompt` | string | required | Search term |
| `output_format` | string | `json` | `json`, `csv`, `pretty`, `file`, `print` |
| `headless` | boolean | `false` | Run browser without a window |
| `locale` | string | `de-DE` | Browser locale |
| `max_results` | integer | unlimited | Maximum companies |
| `track_reviews` | boolean | `true` | Extract review data |
| `auto_email_crawl` | boolean | `false` | Start email enrichment automatically |
| `use_persistent_profile` | boolean | `false` | Reuse `CHROME_PROFILE_PATH` |

## Job lifecycle

```text
pending -> running -> completed
                   -> failed
                   -> cancelled
```

Poll a job:

```bash
curl "$API/crawl/$JOB_ID"
curl "$API/crawl/$JOB_ID/results"
```

`GET /crawl/{job_id}` returns status metadata. `GET /crawl/{job_id}/results`
returns the company array once the job is completed.

## Email enrichment

Auto-triggered:

```bash
curl -X POST "$API/crawl" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "restaurants berlin", "auto_email_crawl": true}'
```

Manual trigger after a completed crawl:

```bash
curl -X POST "$API/email-crawl" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "YOUR_JOB_ID"}'
```

Read emails:

```bash
curl "$API/emails?limit=20&offset=0"
```

## Email campaigns

```bash
curl -X POST "$API/emails/send" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "YOUR_JOB_ID",
    "template_id": "tpl-local-seo",
    "delay_seconds": 2,
    "test": false
  }'
```

Use `"test": true` to send every message to the configured test recipient
instead of the real leads.

## Python client

```python
from core.crawler import run_crawler

results = run_crawler(
    prompt="restaurants berlin",
    headless=False,
    output_format="json",
    track_reviews=True,
)

for company in results:
    print(company.name, company.website)
```

For full control:

```python
from core.crawler import GoogleMapsCrawler
from core.models import CrawlerConfig

config = CrawlerConfig(
    search_prompt="cafes berlin",
    headless=False,
    output_format="pretty",
)

with GoogleMapsCrawler(config) as crawler:
    results = crawler.crawl()
```

## Data model

A company result contains:

| Field | Example |
|---|---|
| `name` | `Café Morgenrot` |
| `category` | `Café` |
| `address` | `Torstraße 12, 10119 Berlin` |
| `phone` | `+49 30 1234 5678` |
| `website` | `https://cafemorgenrot.example` |
| `rating` | `4.8` |
| `reviews_count` | `214` |
| `plus_code` | `GVMF+8H Berlin` |
| `opening_hours` | `Mon: 12:00-22:00, ...` |
| `attributes` | `["Wheelchair accessible entrance"]` |
| `emails` | `["hello@cafemorgenrot.example"]` |
| `email_status` | `completed` |

## Errors

The API uses standard HTTP status codes:

- `400` — invalid request or job state
- `404` — job/template/resource not found
- `422` — validation error
- `500` — crawler or server failure

Error responses include a `detail` field:

```json
{"detail": "Parent job is not completed. Current status: running"}
```
