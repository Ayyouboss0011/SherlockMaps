# Browser extensions

Sherlock Maps loads unpacked Chromium extensions from `core/extensions/`. This
keeps browser behaviour reproducible without committing a full Chrome profile.

## Bundled extension

### I still don't care about cookies

- **Version:** 1.1.4
- **Purpose:** automatically dismisses cookie-consent banners on most websites
- **Upstream:** <https://github.com/OhMyGuus/I-Still-Dont-Care-About-Cookies>
- **License:** GPL-3.0
- **Location:** `core/extensions/i-still-dont-care-about-cookies/`

The extension is loaded automatically for CLI and API crawls. You do not need
to install it manually or copy a Chrome profile.

## How loading works

`CrawlerConfig.get_extension_paths()` scans direct child directories of
`extensions_path`. Every directory with a `manifest.json` is passed to Chromium:

```text
--disable-extensions-except=/app/core/extensions/i-still-dont-care-about-cookies
--load-extension=/app/core/extensions/i-still-dont-care-about-cookies
```

Multiple extensions are joined with commas. The default path is
`core/extensions`; override it with `CrawlerConfig(extensions_path=...)`.

## Add an extension

1. Download or unpack the extension.
2. Put it in a new directory:

   ```text
   core/extensions/my-extension/
   ├── manifest.json
   ├── ...
   └── LICENSE
   ```

3. Restart the crawler.

The next browser launch will include it.

## Remove an extension

Delete its directory from `core/extensions/` and restart. Do not remove the
bundled cookie extension unless you have another consent strategy.

## Licensing

The bundled cookie extension is GPL-3.0. Its license and attribution are in:

- `core/extensions/i-still-dont-care-about-cookies/LICENSE`
- `THIRD_PARTY_NOTICES.md`

The rest of Sherlock Maps remains MIT-licensed. If you add third-party
extensions, check their licenses and add the appropriate notice.

## Security

Extensions can read and modify pages. Only add extensions you trust, and never
put an extension containing credentials or a personal profile in the public
repository. Use `CHROME_PROFILE_PATH` for personal browser state instead.
