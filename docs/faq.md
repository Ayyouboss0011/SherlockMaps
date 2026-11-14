# FAQ

## Is Sherlock Maps free?

Yes. The project is MIT-licensed and self-hosted. There are no per-result fees.
You pay only for your own infrastructure and any email/SMTP provider you use.

## Does it use the Google Maps API?

No. It automates a Chromium browser with Playwright. This means it can break
when Google changes the Maps UI, and you should respect Google's Terms of
Service and local law.

## Do I need a Google API key?

No. A `GOOGLE_API_KEY` is not required for the crawler.

## Can I use my own Chrome profile?

Yes. Keep `core/Chrome_Profile/` locally (it is ignored by Git) or point
`CHROME_PROFILE_PATH` at a profile. For API crawls, set
`use_persistent_profile=true`. See [Browser profile](browser-profile.md).

## Do other users need my profile?

No. The repository bundles the cookie-consent extension, so everyone gets the
same cookie-banner handling automatically. Personal cookies and logins should
stay local. Users can create their own profiles if they need them.

## Does it work headless?

The crawler supports `HEADLESS=true`. Extensions are most reliable in headed
mode; Docker uses Xvfb so the container can run headed without a display.

## Where is data stored?

- Jobs and results: `core/jobs_data`
- CLI exports: `core/results`
- SMTP/templates/history: `core/smtp_data`
- Browser profile: `core/Chrome_Profile`

In Docker these are named volumes, so they survive container restarts.

## Can I run multiple crawls in parallel?

The API queue is designed to process jobs sequentially. If you use a persistent
profile, run one crawl at a time to avoid Chromium profile locks.

## Can I use this for cold email?

The project includes SMTP sending and a do-not-contact blacklist, but you are
responsible for compliance with anti-spam and privacy laws (for example GDPR,
CAN-SPAM and local rules). Only contact businesses where you have a lawful
basis, honor opt-outs, and use the blacklist.

## How do I update?

```bash
git pull
docker compose up -d --build
```

If dependencies or the UI changed, rebuild both services.

## Why are there no reviews?

Review extraction can be disabled with `track_reviews=false` or
`TRACK_REVIEWS=false`. If enabled, Google's UI changes may require selector
updates.

## Is the API authenticated?

No. Do not expose it publicly without a reverse proxy, authentication and rate
limiting.

## How do I contribute?

Read [CONTRIBUTING.md](../CONTRIBUTING.md), open an issue, or pick a
`good first issue`. Bug reports with logs and reproduction steps are especially
useful.
