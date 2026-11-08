# Security Policy

## Supported version

Security fixes are applied to the latest commit on `main`.

## Reporting a vulnerability

Do not publish credentials, account identifiers, broker responses, or exploitable details in a public issue. Use GitHub private vulnerability reporting when it is enabled for the repository, or contact the maintainer privately.

Include only sanitized logs and reproduction steps. Remove API keys, Telegram tokens, chat IDs, account IDs, order IDs, and personal information.

## Credential handling

- Store credentials only in the local `.env` file.
- Keep `accounts.json` local because it can contain account metadata.
- Never attach `trades.log`, `debug.log`, or `seen_signals.json` to a public issue without reviewing them.
- Revoke and replace any credential that appears in Git history, terminal output, screenshots, logs, or test failures.
- Use separate practice credentials for development and integration testing.

## Trading safety

Security also includes preventing unintended orders. New installations must remain in `DRY_RUN=true` with all accounts disabled until configuration and broker responses have been verified.
