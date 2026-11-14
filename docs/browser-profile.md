# Browser profile

Sherlock Maps can use a persistent Chromium profile for cookies, logins,
extensions and other browser state. The profile is a **local runtime artifact**
and is never committed to Git.

## Why the profile is not in the repository

A Chrome user-data directory contains:

- `Cookies`
- `Login Data`
- `Session Storage`
- extension state and cached data

It can be hundreds of megabytes and may contain sensitive sessions. Committing
it would expose credentials, bloat every clone and make the app depend on one
developer's machine. The repository instead ships a reproducible browser setup:

- a bundled cookie-consent extension
- code-level browser flags, locale and viewport
- an optional local profile for your own cookies/logins

## Local profile

By default the crawler uses:

```text
core/Chrome_Profile/
```

The directory is created on first use and ignored by Git. To use a different
location:

```bash
export CHROME_PROFILE_PATH="$HOME/.config/sherlock-maps/chrome-profile"
```

`CrawlerConfig(chrome_profile_path=...)` takes precedence over the environment
variable.

### CLI and Python

CLI crawls use the persistent profile by default:

```bash
cd core
PROMPT="restaurants berlin" python main.py
```

### REST API

API crawls use a temporary profile by default. To reuse the persistent profile:

```bash
curl -X POST http://localhost:6970/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "restaurants berlin",
    "use_persistent_profile": true
  }'
```

Run one crawl at a time when using the persistent profile, otherwise Chromium
may report a profile lock.

Email enrichment runs in a separate headless browser context and does not use
the persistent Chrome profile by default. It visits public company websites and
does not need your Google login. The bundled cookie extension is loaded by the
main crawler.

## Docker

The Compose stack persists the profile in the named volume `chrome_profile`.
A fresh clone starts with an empty profile. There are two ways to use your own:

### Option A — bind mount your local profile

Add this to `docker-compose.yml`:

```yaml
services:
  crawler:
    volumes:
      - ./core/Chrome_Profile:/app/core/Chrome_Profile
```

Then start the stack:

```bash
docker compose up -d
```

This is convenient for local use. On macOS, bind mounts can be slower than a
named volume; if crawls feel slow, use Option B.

### Option B — copy your profile into the volume

```bash
docker cp core/Chrome_Profile/. google-maps-crawler:/app/core/Chrome_Profile/
```

Or copy from the host into the volume with a temporary container:

```bash
docker run --rm \
  -v google-maps-crawler_chrome_profile:/target \
  -v "$PWD/core/Chrome_Profile:/source" \
  alpine sh -c "cp -a /source/. /target/"
```

The volume persists across `docker compose down` and container rebuilds.

## Extensions

The repository bundles **I still don't care about cookies** in
`core/extensions/i-still-dont-care-about-cookies/`. Every crawler launch loads
it automatically, so other users get the same cookie-banner handling without
your profile.

To add another unpacked extension:

```text
core/extensions/my-extension/
├── manifest.json
└── ...
```

Restart the crawler. Directories containing a `manifest.json` are loaded
automatically. See [Extensions](extensions.md) for details and licensing.

## Headed vs. headless

Chromium extensions are most reliable in headed mode. Docker starts Xvfb
automatically, so the container can run headed without a physical display.
For local headless runs, the bundled extension may not load; use a headed
browser if cookie banners are a problem.

## Team setups

Do **not** share a profile containing personal cookies or logins. Instead:

- give everyone the repository with the bundled extension;
- let each person create their own local profile if they need logins;
- use a secrets manager or a private artifact for any shared credentials.

This keeps browser state out of the public repository while keeping crawler
behaviour consistent.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ProcessSingleton` / profile lock | Close other Chromium instances or run one crawl at a time |
| Extensions not loading | Use headed mode; check `core/extensions/*/manifest.json` |
| Profile missing in Docker | Bind-mount it or copy it into the `chrome_profile` volume |
| Cookies/login missing | Set `CHROME_PROFILE_PATH` or enable `use_persistent_profile` |
| Profile too large | Delete caches inside the profile; never commit it |
