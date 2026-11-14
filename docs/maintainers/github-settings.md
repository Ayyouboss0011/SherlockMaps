# GitHub repository settings

Use these values to keep the public repository consistent with the README and
release assets.

## About

**Description**

> Self-hosted Google Maps scraper and lead-generation suite. Extract businesses, websites and emails, then export or enrich them. Python + Playwright, FastAPI, Next.js, Docker.

**Website**

Set this after publishing a docs site or demo video. Until then, point it at the
quick-start section:

```text
https://github.com/Ayyouboss0011/SherlockMaps#quick-start
```

**Topics**

```text
google-maps-scraper
google-maps-crawler
lead-generation
web-scraping
email-extraction
self-hosted
python
playwright
fastapi
nextjs
docker
rest-api
data-extraction
business-data
local-seo
open-source
```

Remove the old `scrapi` topic and any topic that does not describe the project.

**Social preview**

Upload `docs/assets/social-preview.png` (1280×640) under:

`Settings → General → Social preview`

## Features

- Enable **Discussions** for Q&A and use-case showcases.
- Keep **Issues** enabled.
- Add labels: `bug`, `enhancement`, `good first issue`, `help wanted`,
  `documentation`, `question`, `browser-profile`.
- Pin the repository on the owner profile.

## Releases

1. Update `CHANGELOG.md`.
2. Create a tag:

   ```bash
   git tag -a v1.0.0 -m "Sherlock Maps v1.0.0"
   git push origin v1.0.0
   ```

3. Create a GitHub release with:
   - the changelog section;
   - a short feature summary;
   - the dashboard/hero screenshot;
   - upgrade notes for Docker (`docker compose up -d --build`).

## README assets

| Asset | Path |
|---|---|
| Banner | `docs/assets/banner.webp` |
| Hero | `docs/assets/screenshots/hero.png` |
| Dashboard | `docs/assets/screenshots/dashboard.png` |
| Results | `docs/assets/screenshots/results.png` |
| Campaigns | `docs/assets/screenshots/email-campaign.png` |
| Settings | `docs/assets/screenshots/settings.png` |
| Social preview | `docs/assets/social-preview.png` |

Regenerate screenshots with:

```bash
cd LeadGenUI
NEXT_PUBLIC_CRAWLER_API_URL=/api npm run build
npm start
# in another terminal, from the repository root:
python scripts/capture_screenshots.py
```

The screenshot script uses fixture data and never calls Google Maps or a real
SMTP server.

## Before publishing a release

- [ ] `docker compose config` succeeds
- [ ] `docker compose up -d --build` works on a clean clone
- [ ] Dashboard and API URLs in README match `.env.example`
- [ ] Screenshots show no real personal data
- [ ] No Chrome profile, `.env`, cookies or logs are tracked
- [ ] `CONTRIBUTING.md`, `SECURITY.md` and `LICENSE` are linked
- [ ] CI is green
