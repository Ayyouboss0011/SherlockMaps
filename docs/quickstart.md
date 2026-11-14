# Quick start

Sherlock Maps has two services:

| Service | Default URL | Description |
|---|---|---|
| LeadGenUI | <http://localhost:3008> | Next.js dashboard for crawls, results and email campaigns |
| Crawler API | <http://localhost:6970> | FastAPI crawler, job queue and Swagger docs |
| API docs | <http://localhost:6970/docs> | Interactive OpenAPI documentation |

The ports above are the Docker Compose defaults. Local development uses the
backend on `8000` and the UI on `3000` unless you configure otherwise.

## Docker Compose (recommended)

### Requirements

- Docker Desktop or Docker Engine with Compose v2
- ~4 GB free disk space for the Playwright/Chromium image

### Start the stack

```bash
git clone https://github.com/Ayyouboss0011/SherlockMaps.git
cd SherlockMaps
cp .env.example .env
docker compose up -d --build
```

The first build downloads the Playwright Python image and Chromium, so it can
take a few minutes. When it is ready:

- Open the dashboard at <http://localhost:3008>
- Open the API docs at <http://localhost:6970/docs>
- Check the API health at <http://localhost:6970/health>

### Start a crawl

From the dashboard, enter a search term such as `restaurants berlin` and press
**Start Crawl**. To start one from the command line:

```bash
curl -X POST http://localhost:6970/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "restaurants berlin",
    "auto_email_crawl": true,
    "max_results": 50
  }'
```

Check the job:

```bash
curl http://localhost:6970/status
curl http://localhost:6970/crawl/history
```

Export all results:

```bash
curl "http://localhost:6970/results?format=csv" -o leads.csv
curl "http://localhost:6970/results?format=json" -o leads.json
```

### Useful Docker commands

```bash
docker compose logs -f crawler
docker compose logs -f leadgenui
docker compose restart
docker compose down
```

Data is stored in named volumes, so `docker compose down` does **not** delete
your jobs, results or SMTP settings. To remove everything, including volumes:

```bash
docker compose down -v
```

### Change the ports

Edit `.env`:

```dotenv
API_PORT=6970
UI_PORT=3008
```

If you change `API_PORT`, also update `NEXT_PUBLIC_CRAWLER_API_URL` and rebuild
the UI, because public Next.js variables are inlined at build time:

```bash
docker compose up -d --build
```

## Local development

### Requirements

- Python 3.9+
- Node.js 18+
- Git
- A display for headed Chromium, or `HEADLESS=true`

### Backend

```bash
cd core
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python api_main.py
```

The API is now available at <http://localhost:8000> and the Swagger UI at
<http://localhost:8000/docs>.

### Frontend

In a second terminal:

```bash
cd LeadGenUI
npm install
```

Create `LeadGenUI/.env.local`:

```dotenv
NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:8000
CRAWLER_API_URL=http://localhost:8000
```

Start the dashboard:

```bash
npm run dev
```

Open <http://localhost:3000>.

### CLI mode

The crawler can run without the API:

```bash
cd core
source .venv/bin/activate

PROMPT="restaurants berlin" python main.py
PROMPT="restaurants berlin" OUTPUT_FORMAT=csv python main.py
PROMPT="restaurants berlin" OUTPUT_FORMAT=file python main.py
PROMPT="restaurants berlin" HEADLESS=true python main.py
```

See [Configuration](configuration.md) for all output formats and environment
variables.

## Next steps

- [Use your own Chrome profile](browser-profile.md)
- [Learn about the bundled cookie extension](extensions.md)
- [Explore the REST API](api.md)
- [Troubleshoot common issues](troubleshooting.md)
