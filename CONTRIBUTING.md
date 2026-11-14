# Contributing to Sherlock Maps

Thanks for helping improve Sherlock Maps. This guide covers the local setup,
the pull-request checklist and the parts of the project that are easy to work
on.

## Code of conduct

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- Report bugs with logs and reproduction steps.
- Improve documentation or screenshots.
- Add tests for extractors, processors or API models.
- Add integrations (n8n, Google Sheets, CRM webhooks).
- Improve browser reliability or add locales.
- Triage issues and answer questions in Discussions.

Look for [`good first issue`](https://github.com/Ayyouboss0011/SherlockMaps/labels/good%20first%20issue)
and [`help wanted`](https://github.com/Ayyouboss0011/SherlockMaps/labels/help%20wanted).

## Development setup

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

- Dashboard: <http://localhost:3008>
- API: <http://localhost:6970>
- Swagger: <http://localhost:6970/docs>

### Local

Backend:

```bash
cd core
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python api_main.py
```

Frontend:

```bash
cd LeadGenUI
npm install
NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:8000 \
CRAWLER_API_URL=http://localhost:8000 \
npm run dev
```

See [docs/quickstart.md](docs/quickstart.md) for details.

## Branch and commit style

Use short, descriptive branches:

```text
feat/email-enrichment
fix/profile-lock
docs/quickstart
```

Prefer Conventional Commits:

```text
feat: add persistent profile option to crawl API
fix: truncate long website URLs in results table
docs: document Docker profile setup
```

Keep unrelated changes in separate pull requests.

## Pull request checklist

- [ ] The change is scoped and described in the PR.
- [ ] Python compiles (`python -m compileall -q core`).
- [ ] The UI builds (`cd LeadGenUI && npm run build`).
- [ ] Documentation is updated when behaviour or configuration changes.
- [ ] No `.env`, Chrome profile, cookies, SMTP credentials or real lead data
      are included.
- [ ] Screenshots are regenerated when the UI changes.
- [ ] New third-party assets include their license and attribution.

## Screenshots

The README screenshots are generated from fixture data, not a live crawl:

```bash
cd LeadGenUI
NEXT_PUBLIC_CRAWLER_API_URL=/api npm run build
npm start
```

In another terminal:

```bash
python scripts/capture_screenshots.py
```

Output goes to `docs/assets/screenshots/`. Update the README if a new screenshot
is added. The script requires Playwright:

```bash
pip install playwright
playwright install chromium
```

## Browser profile and extensions

- Never commit `core/Chrome_Profile/` or a real Chrome profile.
- The bundled cookie extension lives in `core/extensions/`.
- If you add an extension, include its license and add a notice to
  `THIRD_PARTY_NOTICES.md`.
- Use `CHROME_PROFILE_PATH` for personal browser state.

See [docs/browser-profile.md](docs/browser-profile.md) and
[docs/extensions.md](docs/extensions.md).

## Tests

Run the current unit tests:

```bash
python -m pytest -q
```

Useful contributions include:

- more `CrawlerConfig` and URL-validation tests;
- API tests with a mocked queue manager;
- extraction fixtures for Google Maps HTML snapshots;
- UI tests for the results table and campaign form.

Place Python tests in `tests/` and keep them independent of a real browser or
Google Maps whenever possible. Before opening a PR, also run
`python -m compileall -q core`, `ruff check core --select E9,F63,F7,F82` and the
UI production build.

## Reporting bugs

Include:

- Sherlock Maps version/commit;
- Docker or local setup;
- browser mode (`headless` or headed);
- search term and job ID;
- relevant crawler/API logs;
- expected vs. actual behaviour.

Do not paste cookies, SMTP passwords or personal data. Redact logs.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
