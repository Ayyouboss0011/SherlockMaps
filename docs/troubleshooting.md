# Troubleshooting

## The dashboard shows "Offline"

The UI cannot reach the crawler API.

1. Check the API directly:

   ```bash
   curl http://localhost:6970/health
   curl http://localhost:8000/health
   ```

2. Check the UI environment:

   ```bash
   # Docker Compose
   NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:6970

   # Local development
   NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:8000
   ```

3. Rebuild the UI after changing `NEXT_PUBLIC_*` values:

   ```bash
   docker compose up -d --build leadgenui
   ```

## Port already in use

Change the host ports in `.env`:

```dotenv
API_PORT=6971
UI_PORT=3009
```

Then rebuild the UI so the public API URL matches.

## `docker compose up` takes forever

The first build downloads the Playwright Python image, Chromium and system
dependencies. It is a one-time cost. Subsequent builds reuse the Docker layer
cache.

## The crawler finds no results

- Google may show a CAPTCHA or a consent page.
- Google Maps DOM selectors change regularly; check the latest logs.
- Try a smaller `max_results`, a headed browser, or a local Chrome profile.
- Increase `page_timeout`/`selector_timeout` if the network is slow.

## Browser profile is locked

Chromium allows only one process per profile. Close other Chromium/Chrome
instances using the same profile, or run one crawl at a time. API crawls use a
temporary profile by default; `use_persistent_profile=true` requires
serialization.

## Extensions are not loading

- Use headed mode; extensions are most reliable there.
- Confirm `core/extensions/<name>/manifest.json` exists.
- Docker uses Xvfb, so `HEADLESS=false` is supported in the container.
- Check the browser version compatibility of the extension.

## No emails found

- Some websites hide addresses behind JavaScript or forms.
- Check the company website manually.
- Increase the email crawler timeout or check logs for blocked pages.
- Email enrichment only runs for companies with a valid website URL.

## SMTP test fails

- Verify host, port and encryption (STARTTLS vs SSL/TLS).
- Many providers require an app password instead of your account password.
- Check whether the provider blocks the container's network/IP.
- Use the **Test Connection** section in Settings.

## Reset everything

This deletes jobs, results, SMTP settings and the browser profile:

```bash
docker compose down -v
```

Local:

```bash
rm -rf core/jobs_data core/results core/smtp_data core/Chrome_Profile
```

## Collect logs

```bash
docker compose logs -f crawler
docker compose logs -f leadgenui
```

For the API, open <http://localhost:6970/docs> and test endpoints directly. If
you report a bug, include the job ID, search term, browser mode (headless or
headed), Docker/local setup and relevant logs.
