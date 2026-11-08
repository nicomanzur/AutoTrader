# TraderDesk V2

TraderDesk V2 is an experimental Python trading assistant for monitoring EMA-based signals and submitting bracket orders through the ProjectX/TopstepX API. It includes a Windows desktop interface, a command-line mode, multi-account configuration, notifications, and local trade logs.

> [!WARNING]
> This project can submit real futures orders. It is not financial advice and is not production-ready by default. Keep `DRY_RUN=true`, use a practice account, and audit the strategy, account selection, exposure checks, contract rollover, and broker behavior before enabling live execution.

## Safety defaults

- Simulation mode is enabled in `.env.example`.
- The example account is disabled and has `account_id: 0`.
- Local credentials, account configuration, logs, virtual environments, and signal state are ignored by Git.
- CI runs unit tests without broker or Telegram credentials.
- No API key or bot token is required to inspect or test the code.

## Requirements

- Python 3.11 or 3.12
- A ProjectX/TopstepX account for broker-connected features
- Windows 10/11 for the PySide6 desktop interface

## Quick start on Windows

```powershell
git clone <your-public-repository-url>
cd traderdesk_v2
.\setup.ps1
```

The setup script creates `.venv-v2`, installs the GUI dependencies, and copies the safe example configuration when local files do not exist.

Then edit `.env` and `accounts.json`. Keep these values during initial testing:

```dotenv
DRY_RUN=true
ONLY_PRACTICE_ACCOUNT=true
```

Run the desktop interface:

```powershell
.\run.ps1
```

Run the command-line interface:

```powershell
.\run.ps1 --cli
```

## Headless setup

For a headless machine, create a local environment and install the core dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
cp accounts.json.example accounts.json
python unified_trader.py
```

The headless workflow does not install PySide6. Review service management and operating-system hardening separately before running continuously.

## Configuration

`.env.example` documents the supported environment variables. `accounts.json.example` contains the account structure. Create local copies rather than editing the examples:

```powershell
Copy-Item .env.example .env
Copy-Item accounts.json.example accounts.json
```

Never commit `.env`, `accounts.json`, logs, or state files. Contract identifiers expire; verify the active contract before every live session.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

The automated suite intentionally excludes scripts that contact external services. Broker and notification integration checks must use dedicated test credentials and should not run during test discovery.

## Project structure

```text
app/brokers/          ProjectX API client
app/services/         Market data and signal calculation
app/trading/          Order and force-close helpers
app/utils/            Timing, persistence, logging, and notifications
tests/                Offline unit tests
unified_trader.py     Main trading loop
main.py               GUI/CLI entry point
```

## Known limitations

- Multi-account and exposure behavior must be reviewed before live use.
- Contract rollover is configured manually.
- The codebase still contains legacy logic in `unified_trader.py` that overlaps with modules under `app/`.
- Unit coverage currently focuses on calculation helpers, not end-to-end order execution.

## Security

Read [SECURITY.md](SECURITY.md) before reporting a vulnerability. If a credential is ever printed, committed, or included in a traceback, revoke it immediately and create a new one.

## License

Released under the [MIT License](LICENSE).
