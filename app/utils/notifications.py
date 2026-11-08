"""
Notification utilities for TraderDesk V2.

This module provides utilities for sending notifications via Telegram and Email.
"""
from __future__ import annotations
import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Optional, Any
import requests


def send_telegram_message(token: str, chat_id: str, text: str,
                         timeout: int = 10) -> bool:
    """
    Send a message via Telegram.

    Args:
        token: Telegram bot token
        chat_id: Telegram chat ID
        text: Message text
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    if not token or not chat_id:
        return False

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        }

        response = requests.post(url, json=payload, timeout=timeout)
        return response.ok
    except Exception as e:
        print(f"[TELEGRAM][WARN] Failed to send message: {e}")
        return False


def send_email(subject: str, body: str, smtp_host: str, smtp_port: int,
              smtp_user: str, smtp_pass: str, email_from: str, email_to: str,
              timeout: int = 15) -> bool:
    """
    Send an email via SMTP.

    Args:
        subject: Email subject
        body: Email body
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_user: SMTP username
        smtp_pass: SMTP password
        email_from: From email address
        email_to: To email address(es) (comma-separated)
        timeout: Connection timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    if not all([smtp_host, smtp_port, smtp_user, smtp_pass, email_from, email_to]):
        return False

    try:
        # Create message
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = email_to

        # Parse recipients
        recipients = [addr.strip() for addr in email_to.split(",") if addr.strip()]

        if not recipients:
            return False

        # Send email
        if smtp_port == 465:
            # SSL connection
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(email_from, recipients, msg.as_string())
        else:
            # STARTTLS connection
            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(email_from, recipients, msg.as_string())

        return True
    except Exception as e:
        print(f"[EMAIL][WARN] Failed to send email: {e}")
        return False


def format_trade_notification(trade_data: dict[str, Any], dry_run: bool = False) -> str:
    """
    Format trade data as a notification message.

    Args:
        trade_data: Dictionary containing trade information
        dry_run: Whether this is a dry run

    Returns:
        Formatted notification message
    """
    symbol = trade_data.get("symbol", "UNKNOWN")
    signal = trade_data.get("signal", "UNKNOWN")
    quantity = trade_data.get("qty", trade_data.get("quantity", 0))
    fill_price = trade_data.get("fill_price")
    tp_price = trade_data.get("tp_price")
    sl_price = trade_data.get("sl_price")
    as_of = trade_data.get("as_of", "")
    account_id = trade_data.get("account_id", "")
    tag = trade_data.get("tag", "")

    # Build message
    lines = []

    # Header
    if dry_run:
        lines.append(f"[DRY RUN] Trade Signal: {symbol} {signal}")
    else:
        lines.append(f"Trade Executed: {symbol} {signal}")

    lines.append("=" * 40)

    # Trade details
    lines.append(f"Symbol: {symbol}")
    lines.append(f"Signal: {signal}")
    lines.append(f"Quantity: {quantity}")

    if fill_price:
        lines.append(f"Fill Price: {fill_price:.2f}")

    if tp_price:
        lines.append(f"Take Profit: {tp_price:.2f}")

    if sl_price:
        lines.append(f"Stop Loss: {sl_price:.2f}")

    # Additional info
    if as_of:
        lines.append(f"Bar Time: {as_of}")

    if account_id:
        lines.append(f"Account: {account_id}")

    if tag:
        lines.append(f"Tag: {tag}")

    return "\n".join(lines)


def format_error_notification(error_data: dict[str, Any]) -> str:
    """
    Format error data as a notification message.

    Args:
        error_data: Dictionary containing error information

    Returns:
        Formatted error notification
    """
    symbol = error_data.get("symbol", "UNKNOWN")
    error_msg = error_data.get("error", "Unknown error")
    event = error_data.get("event", "ERROR")

    lines = [
        f"Trading Error: {symbol}",
        "=" * 40,
        f"Event: {event}",
        f"Error: {error_msg}",
    ]

    # Add additional details if present
    for key, value in error_data.items():
        if key not in ("symbol", "error", "event", "ts", "timestamp"):
            lines.append(f"{key}: {value}")

    return "\n".join(lines)


def format_position_notification(position_data: dict[str, Any],
                                 close_reason: Optional[str] = None) -> str:
    """
    Format position data as a notification message.

    Args:
        position_data: Dictionary containing position information
        close_reason: Optional reason for closing position

    Returns:
        Formatted position notification
    """
    symbol = position_data.get("symbol", "UNKNOWN")
    order_id = position_data.get("order_id", position_data.get("position_id", ""))

    lines = []

    if close_reason:
        lines.append(f"Position Closed: {symbol}")
        lines.append("=" * 40)
        lines.append(f"Reason: {close_reason}")
    else:
        lines.append(f"Position Update: {symbol}")
        lines.append("=" * 40)

    if order_id:
        lines.append(f"Order ID: {order_id}")

    # Add other relevant fields
    for key, value in position_data.items():
        if key not in ("symbol", "order_id", "position_id"):
            lines.append(f"{key}: {value}")

    return "\n".join(lines)


class NotificationManager:
    """Manager for sending notifications via multiple channels."""

    def __init__(self, telegram_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None,
                 smtp_config: Optional[dict[str, Any]] = None,
                 dry_run_notifications: bool = False):
        """
        Initialize notification manager.

        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            smtp_config: SMTP configuration dictionary
            dry_run_notifications: Send notifications for dry runs
        """
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.smtp_config = smtp_config or {}
        self.dry_run_notifications = dry_run_notifications

        self.telegram_enabled = bool(telegram_token and telegram_chat_id)
        self.email_enabled = bool(
            smtp_config and
            smtp_config.get("host") and
            smtp_config.get("port") and
            smtp_config.get("user") and
            smtp_config.get("pass") and
            smtp_config.get("from") and
            smtp_config.get("to")
        )

    def send_trade_notification(self, trade_data: dict[str, Any],
                               dry_run: bool = False) -> bool:
        """
        Send trade notification via all enabled channels.

        Args:
            trade_data: Trade data dictionary
            dry_run: Whether this is a dry run

        Returns:
            True if at least one notification was sent successfully
        """
        if dry_run and not self.dry_run_notifications:
            return False

        message = format_trade_notification(trade_data, dry_run)
        success = False

        # Send Telegram
        if self.telegram_enabled:
            if send_telegram_message(self.telegram_token, self.telegram_chat_id, message):
                success = True

        # Send Email
        if self.email_enabled:
            symbol = trade_data.get("symbol", "UNKNOWN")
            signal = trade_data.get("signal", "UNKNOWN")
            subject = f"[{'DRY RUN' if dry_run else 'TRADE'}] {symbol} {signal}"

            if send_email(
                subject=subject,
                body=message,
                smtp_host=self.smtp_config["host"],
                smtp_port=self.smtp_config["port"],
                smtp_user=self.smtp_config["user"],
                smtp_pass=self.smtp_config["pass"],
                email_from=self.smtp_config["from"],
                email_to=self.smtp_config["to"]
            ):
                success = True

        return success

    def send_error_notification(self, error_data: dict[str, Any]) -> bool:
        """
        Send error notification via all enabled channels.

        Args:
            error_data: Error data dictionary

        Returns:
            True if at least one notification was sent successfully
        """
        message = format_error_notification(error_data)
        success = False

        # Send Telegram
        if self.telegram_enabled:
            if send_telegram_message(self.telegram_token, self.telegram_chat_id, message):
                success = True

        # Send Email
        if self.email_enabled:
            symbol = error_data.get("symbol", "UNKNOWN")
            subject = f"[ERROR] Trading Error - {symbol}"

            if send_email(
                subject=subject,
                body=message,
                smtp_host=self.smtp_config["host"],
                smtp_port=self.smtp_config["port"],
                smtp_user=self.smtp_config["user"],
                smtp_pass=self.smtp_config["pass"],
                email_from=self.smtp_config["from"],
                email_to=self.smtp_config["to"]
            ):
                success = True

        return success
