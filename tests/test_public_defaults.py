from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def _env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def test_example_environment_uses_safe_defaults() -> None:
    values = _env_values()
    assert values["DRY_RUN"].lower() == "true"
    assert values["ONLY_PRACTICE_ACCOUNT"].lower() == "true"
    assert values["PROJECTX_API_KEY"] == ""
    assert values["TELEGRAM_BOT_TOKEN"] == ""
    assert values["TRADING_START_TIME"] == "09:30"


def test_example_accounts_are_disabled() -> None:
    data = json.loads((ROOT / "accounts.json.example").read_text(encoding="utf-8"))
    accounts = data.get("trading_accounts", [])
    assert accounts
    assert all(account.get("enabled") is False for account in accounts)
    assert all(int(account.get("account_id", 0)) == 0 for account in accounts)
