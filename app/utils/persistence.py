"""
Persistence utilities for TraderDesk V2.

This module provides utilities for file operations, including seen signals
tracking and trade logging.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone


def load_seen_signals(filename: str) -> set[str]:
    """
    Load seen signals from file.

    Args:
        filename: Path to seen signals file

    Returns:
        Set of seen signal IDs
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data)
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse seen signals file: {e}")
        return set()
    except Exception as e:
        print(f"[WARN] Failed to load seen signals: {e}")
        return set()


def save_seen_signals(seen: set[str], filename: str) -> bool:
    """
    Save seen signals to file.

    Args:
        seen: Set of seen signal IDs
        filename: Path to seen signals file

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen)), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[WARN] Failed to save seen signals: {e}")
        return False


def create_event_id(symbol: str, as_of: str, signal: str) -> str:
    """
    Create unique event ID for a signal.

    Args:
        symbol: Trading symbol
        as_of: Timestamp of the bar
        signal: Signal type (LONG/SHORT)

    Returns:
        Unique event ID string
    """
    return f"{symbol}|{as_of}|{signal}"


def write_trade_log(entry: dict[str, Any], filename: str) -> bool:
    """
    Write a trade log entry to file.

    Args:
        entry: Dictionary containing trade information
        filename: Path to log file

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"[WARN] Failed to write trade log: {e}")
        return False


def read_trade_logs(filename: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
    """
    Read trade logs from file.

    Args:
        filename: Path to log file
        limit: Maximum number of entries to read (from end)

    Returns:
        List of trade log entries
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if limit is not None and limit > 0:
            lines = lines[-limit:]

        logs = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return logs
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"[WARN] Failed to read trade logs: {e}")
        return []


def ensure_directory_exists(filepath: str) -> bool:
    """
    Ensure the directory for a file path exists.

    Args:
        filepath: Path to file

    Returns:
        True if directory exists or was created, False on error
    """
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"[WARN] Failed to create directory: {e}")
        return False


def save_json(data: Any, filename: str, pretty: bool = True) -> bool:
    """
    Save data to JSON file.

    Args:
        data: Data to save (must be JSON-serializable)
        filename: Path to file
        pretty: Use pretty printing if True

    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_directory_exists(filename)

        with open(filename, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"[WARN] Failed to save JSON: {e}")
        return False


def load_json(filename: str, default: Optional[Any] = None) -> Any:
    """
    Load data from JSON file.

    Args:
        filename: Path to file
        default: Default value if file doesn't exist or is invalid

    Returns:
        Loaded data or default value
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse JSON file: {e}")
        return default
    except Exception as e:
        print(f"[WARN] Failed to load JSON: {e}")
        return default


def append_to_csv(data: dict[str, Any], filename: str,
                  headers: Optional[list[str]] = None) -> bool:
    """
    Append data row to CSV file.

    Args:
        data: Dictionary containing row data
        filename: Path to CSV file
        headers: Column headers (written if file doesn't exist)

    Returns:
        True if successful, False otherwise
    """
    try:
        import csv

        file_exists = Path(filename).exists()

        with open(filename, "a", newline="", encoding="utf-8") as f:
            if headers:
                writer = csv.DictWriter(f, fieldnames=headers)

                if not file_exists:
                    writer.writeheader()

                writer.writerow(data)
            else:
                # Write as comma-separated values
                writer = csv.writer(f)
                writer.writerow(data.values())

        return True
    except Exception as e:
        print(f"[WARN] Failed to append to CSV: {e}")
        return False


def create_trade_summary(symbol: str, signal: str, quantity: int,
                        fill_price: Optional[float], tp_price: Optional[float],
                        sl_price: Optional[float], account_id: int,
                        dry_run: bool = False) -> dict[str, Any]:
    """
    Create a structured trade summary dictionary.

    Args:
        symbol: Trading symbol
        signal: Signal type (LONG/SHORT)
        quantity: Order quantity
        fill_price: Fill price
        tp_price: Take profit price
        sl_price: Stop loss price
        account_id: Account ID
        dry_run: Whether this is a dry run

    Returns:
        Trade summary dictionary
    """
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "signal": signal,
        "quantity": quantity,
        "fill_price": fill_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "account_id": account_id,
        "dry_run": dry_run,
    }


def rotate_log_file(filename: str, max_size_mb: float = 10.0,
                    keep_backups: int = 5) -> bool:
    """
    Rotate log file if it exceeds max size.

    Args:
        filename: Path to log file
        max_size_mb: Maximum file size in MB
        keep_backups: Number of backup files to keep

    Returns:
        True if rotation occurred or wasn't needed, False on error
    """
    try:
        path = Path(filename)

        if not path.exists():
            return True

        # Check file size
        size_mb = path.stat().st_size / (1024 * 1024)

        if size_mb < max_size_mb:
            return True

        # Rotate backups
        for i in range(keep_backups - 1, 0, -1):
            old_backup = Path(f"{filename}.{i}")
            new_backup = Path(f"{filename}.{i + 1}")

            if old_backup.exists():
                if new_backup.exists():
                    new_backup.unlink()
                old_backup.rename(new_backup)

        # Move current file to .1
        backup = Path(f"{filename}.1")
        if backup.exists():
            backup.unlink()
        path.rename(backup)

        return True
    except Exception as e:
        print(f"[WARN] Failed to rotate log file: {e}")
        return False


def cleanup_old_signals(seen: set[str], max_age_days: int = 30) -> set[str]:
    """
    Remove old signals from the seen set.

    Signals are expected to be in format: "SYMBOL|TIMESTAMP|SIGNAL"

    Args:
        seen: Set of seen signal IDs
        max_age_days: Maximum age in days

    Returns:
        Cleaned set of signals
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    cleaned = set()

    for signal_id in seen:
        try:
            parts = signal_id.split("|")
            if len(parts) >= 2:
                timestamp_str = parts[1]
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                if timestamp >= cutoff:
                    cleaned.add(signal_id)
        except Exception:
            # Keep signal if we can't parse it
            cleaned.add(signal_id)

    return cleaned
