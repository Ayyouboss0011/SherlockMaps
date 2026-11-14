# Sherlock Maps dashboard

The Next.js dashboard for Sherlock Maps. It provides:

- Live crawler status and KPIs
- Crawl form with review, email-enrichment and browser-profile options
- Job history with expandable company results
- Search and CSV/JSON export
- Email campaign composer, SMTP settings and templates
- Do-not-contact blacklist with CSV/XLSX import
- Send history

## Local development

Requirements: Node.js 18+ and a running crawler API.

```bash
npm install
```

Create `.env.local`:

```dotenv
NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:8000
CRAWLER_API_URL=http://localhost:8000
```

Start the dashboard:

```bash
npm run dev
```

Open <http://localhost:3000>.

## Docker

The dashboard is part of the root `docker-compose.yml`:

```bash
cd ..
docker compose up -d --build
```

Open <http://localhost:3008>. The API is available at
<http://localhost:6970> and its Swagger UI at
<http://localhost:6970/docs>.

## Environment

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_CRAWLER_API_URL` | API URL used by the browser; inlined at build time |
| `CRAWLER_API_URL` | API URL used by the Next.js server/proxy |

Changing `NEXT_PUBLIC_*` requires a rebuild.

## Scripts

```bash
npm run dev      # development server
npm run build    # production build
npm run start    # production server
npm run lint     # Next.js lint
```

For screenshots, run the build with `NEXT_PUBLIC_CRAWLER_API_URL=/api`, start
the app, then run `python ../scripts/capture_screenshots.py` from the repository
root.

## Documentation

- [Quick start](../docs/quickstart.md)
- [Configuration](../docs/configuration.md)
- [REST API](../docs/api.md)
- [Browser profile](../docs/browser-profile.md)
