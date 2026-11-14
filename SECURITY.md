# Security policy

## Supported versions

Security fixes are applied to the latest release on the `main` branch. Older
releases may not receive patches.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's private vulnerability reporting:

<https://github.com/Ayyouboss0011/SherlockMaps/security/advisories/new>

Include:

- a description of the issue and its impact;
- steps to reproduce;
- affected version/commit;
- relevant logs or proof of concept;
- any suggested mitigation.

You will receive a best-effort response. Please allow time for a fix before
disclosing the issue publicly.

## Sensitive data

Never commit:

- `core/Chrome_Profile/` or any Chrome user-data directory;
- `.env` files or SMTP credentials;
- cookies, login data, session storage or API tokens;
- real lead lists, email addresses or send history.

The browser profile is a local runtime artifact and is ignored by Git. If you
believe a credential was exposed, rotate it immediately (SMTP password, API
token, Google session) and report the exposure.

## API exposure

The API has no authentication by default. Do not expose it directly to the
internet. Use a reverse proxy with authentication, network restrictions and
rate limiting.
