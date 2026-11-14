# Bundled Chromium extensions

Sherlock Maps loads every direct child directory in this folder that contains a
`manifest.json` as an unpacked Chromium extension. This keeps browser behaviour
reproducible without committing a full Chrome profile (cookies, logins, session
storage).

## Included extensions

### I still don't care about cookies

- **Version:** 1.1.4
- **Purpose:** Automatically handles cookie-consent banners on most websites.
- **Upstream:** <https://github.com/OhMyGuus/I-Still-Dont-Care-About-Cookies>
- **License:** GPL-3.0 (see `i-still-dont-care-about-cookies/LICENSE`)

## Adding your own extension

1. Download or unpack the extension into `core/extensions/<your-extension>/`.
2. Make sure the directory contains a `manifest.json`.
3. Restart the crawler.

The extension is loaded automatically for CLI and API crawls. For best results,
run the browser in headed mode (the Docker image starts Xvfb automatically).

> Do not put personal Chrome profiles or extensions containing credentials in
> this directory. Use `CHROME_PROFILE_PATH` for a local profile instead.
