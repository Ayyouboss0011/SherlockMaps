# Configuration

## Ports

| Context | Service | URL / port |
|---|---|---|
| Docker Compose | Dashboard | <http://localhost:3008> |
| Docker Compose | Crawler API | <http://localhost:6970> |
| Docker Compose | Swagger UI | <http://localhost:6970/docs> |
| Local backend | Crawler API | <http://localhost:8000> |
| Local frontend | Dashboard | <http://localhost:3000> |

`API_PORT` and `UI_PORT` are the **host** ports used by Docker Compose. The
containers keep the internal ports `8000` (API) and `3000` (UI).

## Environment variables

### Docker Compose

| Variable | Default | Description |
|---|---|---|
| `API_PORT` | `6970` | Host port for the crawler API |
| `UI_PORT` | `3008` | Host port for the dashboard |
| `NEXT_PUBLIC_CRAWLER_API_URL` | `http://localhost:6970` | API URL used by the browser; inlined at build time |
| `CRAWLER_API_URL` | `http://crawler:8000` | API URL used by the UI server inside Docker |

After changing `NEXT_PUBLIC_CRAWLER_API_URL`, rebuild the UI:

```bash
docker compose up -d --build leadgenui
```

### Crawler

| Variable | Default | Description |
|---|---|---|
| `PROMPT` | — | Search term for CLI mode |
| `OUTPUT_FORMAT` | `json` | `json`, `csv`, `pretty`, `file` or `print` |
| `HEADLESS` | `false` | Run Chromium without a visible window |
| `TRACK_REVIEWS` | `true` | Extract reviews for each company |
| `CHROME_PROFILE_PATH` | `core/Chrome_Profile` | Persistent Chrome user-data directory |
| `JOBS_DATA_DIR` | `core/jobs_data` | Directory for persisted crawl jobs |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port inside the container/process |

### Frontend

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_CRAWLER_API_URL` | `http://localhost:8000` | API base URL used in the browser |
| `CRAWLER_API_URL` | `http://localhost:6970` | API base URL used by the Next.js server proxy |

Use `/api` as `NEXT_PUBLIC_CRAWLER_API_URL` when the app is served behind the
same domain and you want the built-in Next.js proxy to forward requests.

## Crawler configuration

`CrawlerConfig` can be used directly from Python:

```python
from core.models import CrawlerConfig

config = CrawlerConfig(
    search_prompt="restaurants berlin",
    headless=False,
    output_format="json",
    track_reviews=True,
    locale="de-DE",
    chrome_profile_path="",  # empty = CHROME_PROFILE_PATH or core/Chrome_Profile
    extensions_path="",      # empty = core/extensions
)
```

| Attribute | Type | Default | Description |
|---|---|---|---|
| `search_prompt` | `str` | `""` | Google Maps search term |
| `headless` | `bool` | `False` | Run without a visible browser |
| `output_format` | `str` | `"json"` | Output format |
| `chrome_profile_path` | `str` | `core/Chrome_Profile` | Persistent browser profile |
| `extensions_path` | `str` | `core/extensions` | Unpacked Chromium extensions |
| `viewport` | `ViewPort` | `1920x1080` | Browser viewport |
| `locale` | `str` | `"de-DE"` | Browser locale |
| `page_timeout` | `int` | `30000` | Navigation timeout in ms |
| `selector_timeout` | `int` | `15000` | Selector timeout in ms |
| `scroll_timeout` | `int` | `45` | Scroll timeout in seconds |
| `max_scroll_attempts` | `int` | `5` | Consecutive unchanged scrolls before stopping |
| `max_retries` | `int` | `3` | Navigation retries |
| `request_timeout` | `int` | `25000` | Request timeout in ms |
| `track_reviews` | `bool` | `True` | Extract review data |

## REST request options

`POST /crawl` accepts:

| Field | Type | Default | Description |
|---|---|---|---|
| `prompt` | `str` | required | Search term |
| `output_format` | `str` | `json` | Output format |
| `headless` | `bool` | `false` | Run browser headless |
| `locale` | `str` | `de-DE` | Browser locale |
| `max_results` | `int` | unlimited | Stop after N companies |
| `track_reviews` | `bool` | `true` | Extract reviews |
| `auto_email_crawl` | `bool` | `false` | Start email enrichment after the crawl |
| `use_persistent_profile` | `bool` | `false` | Reuse `CHROME_PROFILE_PATH` instead of a temporary profile |

`use_persistent_profile=true` is useful when you need your own cookies, logins
or profile-specific extensions. Run crawls one at a time in that mode. See
[Browser profile](browser-profile.md).

## Data directories

| Path | Docker volume | Contents |
|---|---|---|
| `core/jobs_data` | `jobs_data` | Crawl jobs, results, email jobs |
| `core/results` | `results` | Export files created by CLI runs |
| `core/smtp_data` | `smtp_data` | SMTP settings, templates, send history |
| `core/Chrome_Profile` | `chrome_profile` | Local Chrome profile (never commit) |

## Security

The API has no authentication by default. Do not expose it directly to the
public internet. Put it behind a reverse proxy with authentication, or bind it
to localhost/your private network.

See [Browser profile](browser-profile.md) for the recommended profile setup.
