# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## [1.0.0] - 2026-11-14

### Added

- Google Maps company extraction with ratings, reviews, opening hours and
  attributes.
- Email enrichment from company websites.
- FastAPI REST API with a persistent job queue.
- Next.js dashboard for crawls, results, exports, SMTP campaigns and settings.
- Email blacklist with CSV/XLSX import.
- Docker Compose deployment for crawler and UI.
- Bundled cookie-consent extension for reproducible browser behavior.
- Optional persistent Chrome profile via `CHROME_PROFILE_PATH` and
  `use_persistent_profile`.
- Repository documentation, screenshots, demo fixtures and screenshot tooling.
- GitHub issue/PR templates, CI workflow and third-party notices.

### Changed

- Standardized documentation around Docker ports `6970` (API) and `3008` (UI).
- Improved the results table truncation for long websites and emails.
- Improved the dashboard header, page hierarchy and error-state colors.
- Updated the README with a visual overview, quick start and use cases.

### Security

- Removed the local Chrome profile from Git history. Browser profiles can
  contain cookies, login data and session storage and must never be committed.
- Added `SECURITY.md` and a browser-profile security guide.

### Fixed

- Corrected clone and port instructions.
- Added the missing contributing guide referenced by the README.
- Prevented long URLs/emails from overlapping adjacent table columns.

## [Unreleased]

See the [roadmap](README.md#roadmap) for planned work.
