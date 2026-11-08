# unified_trader.py
from __future__ import annotations
import sys
import os, time, json, smtplib, ssl

# Configurar UTF-8 para la consola en Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple
from zoneinfo import ZoneInfo
import requests
import concurrent.futures
import threading

from app.brokers.projectx_api import ProjectXClient
from app.services.market_monitor import MarketMonitor, REQUIRED_BARS
from app.trading.force_close_contracts import force_close_via_close_contract_api
from account_manager import AccountManager

# ===================== Configuración =====================
# Archivo para tracking de señales ya procesadas
SEEN_FILE = os.getenv("SEEN_SIGNALS_FILE", "seen_signals.json")

# Configuración de timing
BAR_MINUTES = int(os.getenv("BAR_MINUTES", "15"))
ALIGN_TZ_NAME = os.getenv("ALIGN_TIMEZONE", "UTC").strip() or "UTC"
CLOSE_LAG_SEC = float(os.getenv("CLOSE_LAG_SEC", "1.2"))
RETRY_COUNT = int(os.getenv("CLOSE_RETRY_COUNT", "15"))
RETRY_INTERVAL = float(os.getenv("CLOSE_RETRY_INTERVAL", "0.5"))
# Modo de timestamp de barra: 'open' (ej. 09:15 para la que cierra 09:30) o 'close'
BAR_TIMESTAMP_MODE = os.getenv("BAR_TIMESTAMP_MODE", "open").strip().lower()

# Configuración de trading
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
SIZE_MNQ = int(os.getenv("ORDER_SIZE_MNQ", os.getenv("ORDER_SIZE", "1")))
SIZE_ES = int(os.getenv("ORDER_SIZE_ES", os.getenv("ORDER_SIZE", "1")))
TP_MNQ = float(os.getenv("TP_POINTS_MNQ", "60"))
SL_MNQ = float(os.getenv("SL_POINTS_MNQ", "30"))
TP_ES = float(os.getenv("TP_POINTS_ES", "8"))
SL_ES = float(os.getenv("SL_POINTS_ES", "4"))
EXPLICIT_ACCT = os.getenv("PRACTICE_ACCOUNT_ID")
ONLY_PRACTICE_ACCOUNT = os.getenv("ONLY_PRACTICE_ACCOUNT", "true").lower() in ("1", "true", "yes")

# ============ CONFIGURACIÓN ESPECIAL ES POR DIRECCIÓN ============
# Cuando la señal ES es LONG: usar ES normal
ES_LONG_SIZE = int(os.getenv("ES_LONG_SIZE", "1"))
ES_LONG_TP_POINTS = float(os.getenv("ES_LONG_TP_POINTS", "8"))
ES_LONG_SL_POINTS = float(os.getenv("ES_LONG_SL_POINTS", "5"))

# Cuando la señal ES es SHORT: ejecutar SELL 6 contratos MES (Micro E-mini S&P), SL 7 pts (28 ticks), TP 10 pts (40 ticks)
ES_SHORT_USE_MES = os.getenv("ES_SHORT_USE_MES", "true").lower() in ("1", "true", "yes")
ES_SHORT_SIZE = int(os.getenv("ES_SHORT_SIZE", "6"))   # 6 contratos MES
ES_SHORT_TP_POINTS = float(os.getenv("ES_SHORT_TP_POINTS", "10"))  # 10 puntos = 40 ticks
ES_SHORT_SL_POINTS = float(os.getenv("ES_SHORT_SL_POINTS", "7"))   # 7 puntos = 28 ticks

# Configuración de monitoreo activo
ACTIVE_MONITOR_INTERVAL = int(os.getenv("ACTIVE_MONITOR_INTERVAL", "5"))  # segundos
MAX_ACTIVE_POSITIONS = int(os.getenv("MAX_ACTIVE_POSITIONS", "1"))
MAX_POSITIONS_PER_SYMBOL = int(os.getenv("MAX_POSITIONS_PER_SYMBOL", "1"))  # máximo por símbolo

# Configuración de monitoreo en tiempo real
SHOW_REALTIME_STATUS = os.getenv("SHOW_REALTIME_STATUS", "false").lower() in ("1", "true", "yes")
REALTIME_STATUS_INTERVAL = int(os.getenv("REALTIME_STATUS_INTERVAL", "60"))  # segundos

# Permitir seguir procesando señales aunque haya posiciones activas
PROCESS_SIGNALS_WHILE_ACTIVE = os.getenv("PROCESS_SIGNALS_WHILE_ACTIVE", "false").lower() in ("1", "true", "yes")

# Tipo de órdenes: "bracket" (una sola llamada con TP/SL) o "separate" (market + TP/SL por separado)
ORDER_PLACEMENT_MODE = os.getenv("ORDER_PLACEMENT_MODE", "bracket").strip().lower()  # "bracket" o "separate"

# Filtros de señales por símbolo y dirección
ALLOW_MNQ_LONG = os.getenv("ALLOW_MNQ_LONG", "true").lower() in ("1", "true", "yes")
ALLOW_MNQ_SHORT = os.getenv("ALLOW_MNQ_SHORT", "true").lower() in ("1", "true", "yes")
ALLOW_ES_LONG = os.getenv("ALLOW_ES_LONG", "true").lower() in ("1", "true", "yes")
ALLOW_ES_SHORT = os.getenv("ALLOW_ES_SHORT", "true").lower() in ("1", "true", "yes")

# Optimizaciones de velocidad
SKIP_PRECHECK_DUPLICATES = os.getenv("SKIP_PRECHECK_DUPLICATES", "false").lower() in ("1", "true", "yes")
ENABLE_PRELOAD = os.getenv("ENABLE_PRELOAD", "true").lower() in ("1", "true", "yes")
PRELOAD_SECONDS_BEFORE = int(os.getenv("PRELOAD_SECONDS_BEFORE", "5"))  # Segundos antes del cierre para preparar

# Configuración de horarios de trading
ENABLE_TRADING_HOURS = os.getenv("ENABLE_TRADING_HOURS", "false").lower() in ("1", "true", "yes")
TRADING_TIMEZONE = os.getenv("TRADING_TIMEZONE", "America/New_York").strip()
TRADING_START_TIME = os.getenv("TRADING_START_TIME", "09:30").strip()
TRADING_END_TIME = os.getenv("TRADING_END_TIME", "13:30").strip()  # Hora límite para abrir nuevas posiciones
FORCE_CLOSE_TIME = os.getenv("FORCE_CLOSE_TIME", "16:00").strip()  # Hora de cierre forzoso
AUTO_CLOSE_AT_END = os.getenv("AUTO_CLOSE_AT_END", "true").lower() in ("1", "true", "yes")
DAILY_READY_ALERT_TIME = os.getenv("DAILY_READY_ALERT_TIME", "09:15").strip()  # Alerta diaria de sistema listo

# Logging
TRADES_LOG = os.getenv("TRADES_LOG", "trades.log")

# Notificaciones
USE_TG = os.getenv("NOTIFY_TELEGRAM", "false").lower() in ("1", "true", "yes")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "").strip()
# Si está definido, /stop debe ir seguido del mismo texto: /stop tu_secreto
TELEGRAM_STOP_SECRET = os.getenv("TELEGRAM_STOP_SECRET", "").strip()

USE_MAIL = os.getenv("NOTIFY_EMAIL", "false").lower() in ("1", "true", "yes")
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
EMAIL_FROM = (os.getenv("EMAIL_FROM", "").strip() or SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO", "").strip()
NOTIFY_ON_DRY = os.getenv("NOTIFY_ON_DRY_RUN", "false").lower() in ("1", "true", "yes")
# Retraso (segundos) antes de enviar la notificación "precio entre EMAs" por Telegram (evitar picos de carga)
TELEGRAM_EMA_ALERT_DELAY_SEC = int(os.getenv("TELEGRAM_EMA_ALERT_DELAY_SEC", "300"))  # 5 min

DEBUG_TRADE = os.getenv("DEBUG_TRADE", "false").lower() in ("1", "true", "yes")
DEBUG_LOG = os.getenv("DEBUG_LOG", "debug.log").strip() or None  # Archivo para debug; vacío = solo consola

_dbg_lock = threading.Lock()

def _dbg(*a, **k):
    if not DEBUG_TRADE:
        return
    line = " ".join(str(x) for x in a)
    if k:
        line += " " + " ".join(f"{kk}={vv}" for kk, vv in k.items())
    msg = f"[DEBUG] {line}"
    print(msg)
    if DEBUG_LOG:
        try:
            with _dbg_lock:
                ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                with open(DEBUG_LOG, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] {msg}\n")
                    f.flush()
        except Exception as e:
            print(f"[DEBUG][WARN] No se pudo escribir en {DEBUG_LOG}: {e}")

# ===================== Utilidades =====================
def _load_seen() -> set[str]:
    """Carga las señales ya procesadas desde archivo"""
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def _save_seen(seen: set[str]) -> None:
    """Guarda las señales procesadas en archivo"""
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen)), f, ensure_ascii=False)
    except Exception as e:
        print("[SEEN][WARN]", e)

def _event_id(sym: str, as_of: str, signal: str) -> str:
    """Genera ID único para la señal"""
    return f"{sym}|{as_of}|{signal}"

def _get_align_tz() -> ZoneInfo:
    """Obtiene zona horaria para alineación"""
    try:
        return ZoneInfo(ALIGN_TZ_NAME)
    except Exception:
        return ZoneInfo("UTC")

def _next_quarter_close(now_tz: datetime) -> datetime:
    """Próximo cierre :00/:15/:30/:45 en el huso elegido"""
    m = now_tz.minute
    next_q = ((m // 15) + 1) * 15
    if next_q >= 60:
        return (now_tz.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    return now_tz.replace(minute=next_q, second=0, microsecond=0)

def _sleep_until(ts: datetime, shutdown_event: Optional[threading.Event] = None) -> bool:
    """Duerme hasta el timestamp especificado. Retorna False si shutdown_event se activa antes."""
    while True:
        if shutdown_event is not None and shutdown_event.is_set():
            return False
        now = datetime.now(ts.tzinfo)
        delta = (ts - now).total_seconds()
        if delta <= 0:
            break
        time.sleep(min(delta, 0.5))
    return True


def _sleep_interruptible(
    total_sec: float,
    shutdown_event: Optional[threading.Event],
    chunk_sec: float = 5.0,
) -> bool:
    """Duerme total_sec en trozos; retorna False si shutdown_event se activa."""
    if total_sec <= 0:
        return True
    if shutdown_event is None:
        time.sleep(total_sec)
        return True
    elapsed = 0.0
    while elapsed < total_sec:
        if shutdown_event.is_set():
            return False
        step = min(chunk_sec, total_sec - elapsed)
        time.sleep(step)
        elapsed += step
    return True

def _parse_time_string(time_str: str) -> Tuple[int, int]:
    """Parse time string HH:MM to (hour, minute)"""
    try:
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])
    except:
        raise ValueError(f"Invalid time format: {time_str}. Use HH:MM")

def _is_within_trading_hours(current_time: datetime, tz_name: str,
                             start_time: str, end_time: str) -> Tuple[bool, str]:
    """
    Check if current time is within trading hours (for opening new positions).
    Returns (is_within, status_message)
    """
    if not ENABLE_TRADING_HOURS:
        return True, "TRADING_HOURS_DISABLED"

    try:
        tz = ZoneInfo(tz_name)
        now_local = current_time.astimezone(tz)

        start_h, start_m = _parse_time_string(start_time)
        end_h, end_m = _parse_time_string(end_time)

        current_minutes = now_local.hour * 60 + now_local.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        is_within = start_minutes <= current_minutes < end_minutes

        if not is_within:
            if current_minutes < start_minutes:
                return False, "BEFORE_TRADING_HOURS"
            else:
                return False, "AFTER_TRADING_HOURS"

        return True, "WITHIN_TRADING_HOURS"
    except Exception as e:
        print(f"[TRADING_HOURS][ERROR] {e}")
        return True, "ERROR_CHECKING_HOURS"

def _should_close_positions_now(current_time: datetime, tz_name: str,
                                close_time: str, tolerance_minutes: int = 15) -> bool:
    """
    Check if we should close positions (at or near force close time).
    Uses tolerance to catch the close time even if we check slightly after.
    """
    if not ENABLE_TRADING_HOURS or not AUTO_CLOSE_AT_END:
        return False

    try:
        tz = ZoneInfo(tz_name)
        now_local = current_time.astimezone(tz)

        close_h, close_m = _parse_time_string(close_time)
        current_minutes = now_local.hour * 60 + now_local.minute
        close_minutes = close_h * 60 + close_m

        # Close if we're at or past close time (within tolerance)
        return current_minutes >= close_minutes and current_minutes < close_minutes + tolerance_minutes
    except Exception as e:
        print(f"[AUTO_CLOSE][ERROR] {e}")
        return False

def _round_to_tick(price: float, tick: float) -> float:
    """Redondea precio al tick más cercano"""
    return round(round(price / tick) * tick, 10)

def _pick_practice_account(px: ProjectXClient, explicit: Optional[int]) -> int:
    """Selecciona cuenta de práctica"""
    if explicit:
        return int(explicit)
    accts = px.search_accounts(only_active=True)
    for a in accts:
        if "PRACTICE" in str(a.get("name", "")).upper():
            return int(a["id"])
    for a in accts:
        if a.get("canTrade"):
            return int(a["id"])
    raise RuntimeError("No encontré una cuenta PRACTICE ni operable (canTrade).")

def _get_tick_size(px: ProjectXClient, contract_id: str, default: float = 0.25) -> float:
    """Obtiene tick size del contrato"""
    try:
        det = px.search_contracts_by_id(contract_id) or []
        if det and det[0].get("tickSize") is not None:
            return float(det[0]["tickSize"])
    except Exception as e:
        print(f"[WARN] tickSize fallback para {contract_id}: {e}")
    return default

def _poll_fill_price(px: ProjectXClient, account_id: int, contract_id: str, max_wait_sec: int = 30) -> Optional[float]:
    """Espera y obtiene precio de fill"""
    start_iso = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    waited = 0
    while waited < max_wait_sec:
        trades = px.search_trades(account_id, start_iso)
        for tr in reversed(trades):
            if tr.get("contractId") == contract_id:
                try:
                    return float(tr.get("price"))
                except Exception:
                    pass
        time.sleep(1)
        waited += 1
    return None

# ===================== Logging y Notificaciones =====================
def _write_log(entry: dict) -> None:
    """Escribe entrada en log de trades"""
    try:
        with open(TRADES_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print("[LOG][WARN]", e)

def _notify_telegram(text: str) -> None:
    """Envía notificación por Telegram"""
    if not (USE_TG and TG_TOKEN and TG_CHAT):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print("[TEL][WARN]", e)


def _telegram_commands_help_text() -> str:
    """Texto de referencia de comandos (mismo chat que TELEGRAM_CHAT_ID)."""
    stop_detail = (
        "  Si TELEGRAM_STOP_SECRET está en .env: /stop <secreto>"
        if TELEGRAM_STOP_SECRET
        else "  Sin secreto: basta /stop"
    )
    return "\n".join(
        [
            "📱 Comandos Telegram",
            "=" * 40,
            "/status — Modo, DRY_RUN, órdenes (activas/pausadas), posiciones, precios y señales.",
            "/log o /terminal — Mismo resumen detallado que en consola (último snapshot).",
            "/pause — Pausa solo nuevas órdenes (sigue monitoreo y /status).",
            "/resume o /unpause — Reanuda el envío de órdenes.",
            "/stop, /shutdown o /quit — Detiene por completo el trader.",
            stop_detail,
        ]
    )


def _telegram_send_reply(token: str, chat_id: str, text: str) -> None:
    """Envía un mensaje de respuesta a un chat de Telegram (para /status)."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print("[TEL][WARN] Reply failed:", e)


def _telegram_listener_loop(shared_state: dict, lock: threading.Lock, token: str, chat_id: str,
                            delayed_ema_alerts: list, delayed_ema_lock: threading.Lock,
                            delay_sec: int, shutdown_event: threading.Event) -> None:
    """Loop en segundo plano: /status, /log, /stop y alertas EMAs retrasadas."""
    last_update_id = 0
    while True:
        try:
            # Enviar alertas "precio entre EMAs" que ya cumplieron el retraso (ej. 5 min)
            now = time.time()
            to_send = []
            with delayed_ema_lock:
                remaining = []
                for item in delayed_ema_alerts:
                    if now - item["ts"] >= delay_sec:
                        to_send.append(item)
                    else:
                        remaining.append(item)
                delayed_ema_alerts.clear()
                delayed_ema_alerts.extend(remaining)
            for item in to_send:
                setup_type = item.get("setup_type", "unknown")
                bar_time = item.get("bar_time", "")

                if setup_type == "alcista":
                    emoji = "📈"
                    title = f"Setup Alcista ({item['sym']})"
                    description = (
                        f"EMA50 ({item['ema50']:.2f}) > EMA200 ({item['ema200']:.2f})\n"
                        f"Precio ({item['close']:.2f}) está por debajo de EMA50\n"
                        f"Posibilidad de Trade LONG"
                    )
                elif setup_type == "bajista":
                    emoji = "📉"
                    title = f"Setup Bajista ({item['sym']})"
                    description = (
                        f"EMA50 ({item['ema50']:.2f}) < EMA200 ({item['ema200']:.2f})\n"
                        f"Precio ({item['close']:.2f}) está por encima de EMA50\n"
                        f"Posibilidad de Trade SHORT"
                    )
                else:
                    # Fallback (no debería pasar)
                    emoji = "🔔"
                    title = f"Setup ({item['sym']})"
                    description = f"Cierre: {item['close']:.2f} | EMA50: {item['ema50']:.2f} | EMA200: {item['ema200']:.2f}"

                msg = (
                    f"{emoji} {title}\n"
                    f"{'='*40}\n"
                    f"{description}\n\n"
                    f"Bar: {item['as_of']} ({bar_time} NY)\n"
                )
                _notify_telegram(msg)

            r = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": last_update_id, "timeout": 30},
                timeout=35
            )
            data = r.json() if r.ok else {}
            if not data.get("ok"):
                time.sleep(5)
                continue
            for upd in data.get("result", []):
                last_update_id = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                if str(msg.get("chat", {}).get("id")) != str(chat_id):
                    continue
                text = (msg.get("text") or "").strip()
                with lock:
                    state = {
                        "mode": shared_state.get("mode", "?"),
                        "dry_run": shared_state.get("dry_run", True),
                        "snapshots": dict(shared_state.get("snapshots", {})),
                        "active_positions_count": shared_state.get("active_positions_count", 0),
                        "orders_paused": bool(shared_state.get("orders_paused", False)),
                    }

                if text == "/status":
                    ord_state = "PAUSED ⏸️" if state["orders_paused"] else "ACTIVE ▶️"
                    lines = [
                        "📊 STATUS",
                        "=" * 40,
                        f"Mode: {state['mode']}",
                        f"DRY_RUN: {state['dry_run']}",
                        f"Orders: {ord_state}",
                        f"Active positions: {state['active_positions_count']}",
                        "",
                    ]
                    for sym, s in state["snapshots"].items():
                        lines.append(
                            f"{sym}: Close={s['close']:.2f} EMA50={s['ema50']:.2f} EMA200={s['ema200']:.2f} "
                            f"Signal={s.get('signal') or '-'} Color={s.get('color', '')} Bar={s.get('as_of', '')}"
                        )
                    _telegram_send_reply(token, chat_id, "\n".join(lines))

                elif text == "/log" or text == "/terminal":
                    # Formato igual que en terminal: mostrar la misma información que se imprime en consola
                    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
                    ts_now_utc = now_utc.isoformat().replace("+00:00", "Z")

                    lines = []
                    if not state["snapshots"]:
                        lines.append(f"[{ts_now_utc}] ⚠️ No hay snapshots disponibles aún")
                    else:
                        for sym, s in state["snapshots"].items():
                            close = s["close"]
                            ema50 = s["ema50"]
                            ema200 = s["ema200"]
                            signal = s.get("signal") or "None"
                            color = s.get("color", "").upper()
                            as_of = s.get("as_of", "")

                            # Línea 1: Formato compacto (igual que terminal)
                            lines.append(
                                f"[{ts_now_utc}] [{sym}] 💰 {close:.2f} | EMA50: {ema50:.2f} | "
                                f"EMA200: {ema200:.2f} | Signal: {signal} | Color: {color}"
                            )

                            # Línea 2: Bias y setup (igual que terminal)
                            bias = "📈 ALCISTA" if ema50 > ema200 else "📉 BAJISTA" if ema50 < ema200 else "➡️ NEUTRAL"
                            price_vs_ema50 = "above" if close > ema50 else "below"
                            setup_status = "🚀 LONG SETUP" if signal == "LONG" else "🔻 SHORT SETUP" if signal == "SHORT" else "⏸️ No Setup"
                            lines.append(
                                f"[{ts_now_utc}] [{sym}] {bias} | Price {price_vs_ema50} EMA50 | {setup_status}"
                            )

                            # Información adicional: distancias y recomendación (como en _show_market_summary)
                            distance_ema50 = close - ema50
                            distance_ema200 = close - ema200
                            distance_between_emas = ema50 - ema200

                            color_emoji = {
                                "GREEN": "🟢",
                                "YELLOW": "🟡",
                                "RED": "🔴",
                                "GRAY": "⚪"
                            }.get(color, "⚪")

                            signal_strength = f"Signal: {signal}" if signal != "None" else "Sin señal"

                            lines.append(f"[{ts_now_utc}] [{sym}] 📊 RESUMEN MERCADO:")
                            lines.append(f"[{ts_now_utc}] [{sym}] 💰 Precio: {close:.2f} | EMA50: {ema50:.2f} | EMA200: {ema200:.2f}")
                            lines.append(f"[{ts_now_utc}] [{sym}] 📏 Distancia EMA50: {distance_ema50:+.2f} | EMA200: {distance_ema200:+.2f}")
                            lines.append(f"[{ts_now_utc}] [{sym}] 🔄 EMAs separadas: {distance_between_emas:+.2f}")
                            lines.append(f"[{ts_now_utc}] [{sym}] {color_emoji} Color: {color} | {signal_strength}")

                            # Recomendación
                            if signal == "LONG":
                                lines.append(f"[{ts_now_utc}] [{sym}] ✅ RECOMENDACIÓN: COMPRAR - Señal LONG activa")
                            elif signal == "SHORT":
                                lines.append(f"[{ts_now_utc}] [{sym}] ✅ RECOMENDACIÓN: VENDER - Señal SHORT activa")
                            else:
                                if distance_ema50 > 0 and distance_ema200 > 0:
                                    lines.append(f"[{ts_now_utc}] [{sym}] ⏳ RECOMENDACIÓN: ESPERAR - Precio por encima de EMAs")
                                elif distance_ema50 < 0 and distance_ema200 < 0:
                                    lines.append(f"[{ts_now_utc}] [{sym}] ⏳ RECOMENDACIÓN: ESPERAR - Precio por debajo de EMAs")
                                else:
                                    lines.append(f"[{ts_now_utc}] [{sym}] ⏳ RECOMENDACIÓN: ESPERAR - Precio entre EMAs")

                            lines.append(f"[{ts_now_utc}] [{sym}] " + "="*60)
                            lines.append("")  # Separador entre símbolos

                        # Información del sistema
                        op = "PAUSED" if state["orders_paused"] else "ACTIVE"
                        lines.append(
                            f"[{ts_now_utc}] Sistema: Mode={state['mode']} DRY_RUN={state['dry_run']} "
                            f"Orders={op} Posiciones={state['active_positions_count']}"
                        )

                    _telegram_send_reply(token, chat_id, "\n".join(lines))

                elif (text.split(None, 1)[0] if text else "").lower() == "/pause":
                    with lock:
                        shared_state["orders_paused"] = True
                    _telegram_send_reply(
                        token,
                        chat_id,
                        "⏸️ Envío de órdenes PAUSADO.\n"
                        "No se colocarán trades nuevos; monitoreo y /status siguen activos.\n"
                        "Usa /resume para reanudar.",
                    )

                elif (text.split(None, 1)[0] if text else "").lower() in ("/resume", "/unpause"):
                    with lock:
                        shared_state["orders_paused"] = False
                    _telegram_send_reply(token, chat_id, "▶️ Envío de órdenes ACTIVO.")

                elif (text.split(None, 1)[0] if text else "").lower() in ("/stop", "/shutdown", "/quit"):
                    parts = text.split(None, 1)
                    arg = parts[1].strip() if len(parts) > 1 else ""
                    if TELEGRAM_STOP_SECRET:
                        if arg != TELEGRAM_STOP_SECRET:
                            _telegram_send_reply(
                                token,
                                chat_id,
                                "❌ Comando rechazado. Envía: /stop <tu_secreto>\n"
                                "(TELEGRAM_STOP_SECRET en .env)",
                            )
                            continue
                    shutdown_event.set()
                    _telegram_send_reply(
                        token,
                        chat_id,
                        "🔴 Parada completa solicitada. El trader se detendrá en breve…",
                    )
        except Exception as e:
            _dbg(f"[TEL][listener] {e}")
        time.sleep(0.5)

def _notify_email(subject: str, body: str) -> None:
    """Envía notificación por email"""
    if not (USE_MAIL and SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and EMAIL_TO and EMAIL_FROM):
        return
    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO

        if SMTP_PORT == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(EMAIL_FROM, [x.strip() for x in EMAIL_TO.split(",") if x.strip()], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(EMAIL_FROM, [x.strip() for x in EMAIL_TO.split(",") if x.strip()], msg.as_string())
    except Exception as e:
        print("[MAIL][WARN]", e)

def _notify_trade(event: dict, dry_run: bool) -> None:
    """Envía notificación de trade con información detallada de cuenta y broker"""
    if dry_run and not NOTIFY_ON_DRY:
        return

    # Extraer información básica
    sym = event.get("symbol", "UNKNOWN")
    sig = event.get("signal", "UNKNOWN")
    qty = event.get("qty", 0)
    asof = event.get("as_of", "")
    fill = event.get("fill_price")
    tp = event.get("tp_price")
    sl = event.get("sl_price")
    acct_id = event.get("account_id", "")
    acct_name = event.get("account_name", "")
    broker = event.get("broker", "").upper()
    tag = event.get("tag", "")
    error = event.get("error")

    # Emoji según el tipo de señal
    emoji = "🚀" if sig == "LONG" else "🔻" if sig == "SHORT" else "📊"
    mode_text = "[DRY RUN] " if dry_run else ""

    # Construir mensaje formateado
    if error:
        # Notificación de error
        subject = f"❌ {mode_text}ERROR: {sym} {sig}"
        body_lines = [
            f"Symbol: {sym}",
            f"Signal: {sig}",
            f"Account: {acct_name} ({acct_id})",
            f"Broker: {broker}",
            f"",
            f"ERROR: {error}",
            f"",
            f"Bar Time: {asof}",
            f"Tag: {tag}"
        ]
    else:
        # Notificación de trade exitoso
        subject = f"{emoji} {mode_text}{sym} {sig} x{qty}"
        body_lines = [
            f"Symbol: {sym}",
            f"Signal: {sig}",
            f"Quantity: {qty}",
            f"",
            f"Account: {acct_name}",
            f"  ID: {acct_id}",
            f"  Broker: {broker}",
        ]

        if fill:
            body_lines.append(f"")
            body_lines.append(f"Fill Price: {fill:.2f}")

        if tp:
            tp_diff = tp - fill if fill else 0
            body_lines.append(f"Take Profit: {tp:.2f} ({tp_diff:+.2f})")

        if sl:
            sl_diff = sl - fill if fill else 0
            body_lines.append(f"Stop Loss: {sl:.2f} ({sl_diff:+.2f})")

        body_lines.append(f"")
        body_lines.append(f"Bar Time: {asof}")
        body_lines.append(f"Tag: {tag}")

    body = "\n".join(body_lines)
    message = f"{subject}\n{'='*40}\n{body}"

    _notify_telegram(message)
    _notify_email(subject, body)

def _check_system_readiness(mons: Dict[str, MarketMonitor], enabled_accounts: List,
                            scanner_px: ProjectXClient, px: ProjectXClient, account_id: int) -> Tuple[bool, List[str]]:
    """
    Verifica si el sistema está listo para tomar trades.
    Retorna (is_ready, issues_list)
    """
    issues = []
    is_ready = True

    # 1. Verificar monitores (snapshots disponibles)
    for sym, mon in mons.items():
        if not mon.contract_id:
            issues.append(f"❌ {sym}: Sin contract_id")
            is_ready = False
        else:
            snap, msg = mon.get_snapshot()
            if not snap:
                issues.append(f"⚠️ {sym}: Sin snapshot disponible ({msg})")
                is_ready = False
            elif snap.bars < REQUIRED_BARS:
                issues.append(f"⚠️ {sym}: Solo {snap.bars}/{REQUIRED_BARS} barras")
                is_ready = False

    # 2. Verificar conexión del scanner
    try:
        # Test simple: buscar una cuenta
        scanner_px.search_accounts(only_active=True)
    except Exception as e:
        issues.append(f"❌ Scanner API: {e}")
        is_ready = False

    # 3. Verificar cuentas de trading
    if not enabled_accounts:
        issues.append("❌ No hay cuentas habilitadas")
        is_ready = False
    else:
        for acc in enabled_accounts:
            try:
                acc_client = acc.get_api_client()
                acc_client.login_with_key()
                # Verificar que la cuenta responde
                acc_client.search_accounts(only_active=True)
            except Exception as e:
                issues.append(f"⚠️ {acc.name}: Error conexión ({str(e)[:50]})")
                # No marcamos como no listo si solo una cuenta falla

    # 4. Verificar posiciones activas (no es un problema, solo info)
    try:
        active_positions = _get_active_positions(px, account_id)
        if active_positions:
            issues.append(f"ℹ️ {len(active_positions)} posiciones activas")
    except Exception as e:
        issues.append(f"⚠️ No se pudo verificar posiciones: {e}")

    return is_ready, issues


def _notify_startup(account_manager) -> None:
    """Envía notificación de inicio del sistema"""
    if not USE_TG:
        return

    try:
        enabled_accounts = account_manager.get_enabled_accounts()
        mode = "DRY RUN" if DRY_RUN else "PRODUCTION"

        lines = [
            f"🤖 TRADERDESK STARTED",
            f"{'='*40}",
            f"",
            f"Mode: {mode}",
            f"Accounts: {len(enabled_accounts)} enabled",
            f""
        ]

        for acc in enabled_accounts:
            broker_name = acc.broker.upper()
            lines.append(f"  ✓ {acc.name}")
            lines.append(f"    Broker: {broker_name}")
            lines.append(f"    ID: {acc.account_id}")
            mnq = acc.contracts.get("MNQ", 0)
            es = acc.contracts.get("ES", 0)
            if mnq or es:
                lines.append(f"    Contracts: MNQ={mnq}, ES={es}")
            lines.append(f"")

        lines.append(f"Bar Interval: {BAR_MINUTES} minutes")
        if ENABLE_TRADING_HOURS:
            lines.append(f"Trading Hours: {TRADING_START_TIME} - {TRADING_END_TIME}")
        lines.append(f"")
        lines.append(f"Ready for trading! 🚀")

        message = "\n".join(lines)
        _notify_telegram(message)
    except Exception as e:
        print(f"[NOTIFY][WARN] Startup notification failed: {e}")


def _notify_signal_detected(symbol: str, signal: str, account_count: int) -> None:
    """Envía notificación cuando se detecta una señal (antes de ejecutar)"""
    if not USE_TG:
        return

    emoji = "🚀" if signal == "LONG" else "🔻" if signal == "SHORT" else "📊"
    message = (
        f"{emoji} SIGNAL DETECTED: {symbol} {signal}\n"
        f"{'='*40}\n"
        f"\n"
        f"Preparing to execute on {account_count} account(s)...\n"
    )
    _notify_telegram(message)


def _notify_execution_summary(symbol: str, signal: str, results: dict, execution_time: float) -> None:
    """Envía resumen de ejecución de todas las cuentas"""
    if not USE_TG:
        return

    emoji = "🚀" if signal == "LONG" else "🔻" if signal == "SHORT" else "📊"
    successful = sum(1 for r in results.values() if r.get("success"))
    total = len(results)

    lines = [
        f"{emoji} EXECUTION COMPLETE: {symbol} {signal}",
        f"{'='*40}",
        f"",
        f"Status: {successful}/{total} successful",
        f"Time: {execution_time:.2f}s",
        f""
    ]

    for acct_key, result in results.items():
        if result.get("success"):
            acct_name = result.get("account_name", acct_key)
            lines.append(f"  ✅ {acct_name}")
        else:
            acct_name = result.get("account_name", acct_key)
            error = result.get("error", "Unknown error")
            lines.append(f"  ❌ {acct_name}: {error}")

    message = "\n".join(lines)
    _notify_telegram(message)


def _get_setup_info(snap) -> Optional[str]:
    """Analiza el estado del mercado y determina si hay setup de compra/venta"""
    if not snap:
        return None

    close = snap.close
    ema50 = snap.ema50
    ema200 = snap.ema200
    signal = snap.signal

    # Determinar bias (tendencia general)
    if ema50 > ema200:
        bias = "ALCISTA"
        bias_emoji = "📈"
    elif ema50 < ema200:
        bias = "BAJISTA"
        bias_emoji = "📉"
    else:
        bias = "NEUTRAL"
        bias_emoji = "➡️"

    # Determinar posición del precio respecto a EMAs
    if close > ema50 and close > ema200:
        price_position = "POR ENCIMA DE AMBAS EMAs"
        price_emoji = "🟢"
    elif close < ema50 and close < ema200:
        price_position = "POR DEBAJO DE AMBAS EMAs"
        price_emoji = "🔴"
    elif ema50 < close < ema200 or ema200 < close < ema50:
        price_position = "ENTRE LAS EMAs"
        price_emoji = "🟡"
    else:
        price_position = "CRUZANDO EMAs"
        price_emoji = "⚡"

    # Determinar setup específico
    setup = ""
    if signal == "LONG":
        setup = "🚀 SETUP DE COMPRA ACTIVO"
    elif signal == "SHORT":
        setup = "🔻 SETUP DE VENTA ACTIVO"
    else:
        # Analizar proximidad a setup
        distance_to_ema50 = abs(close - ema50)
        distance_to_ema200 = abs(close - ema200)

        if bias == "ALCISTA" and close < ema50:
            setup = "⏳ ACERCÁNDOSE A SETUP DE COMPRA (precio < EMA50)"
        elif bias == "BAJISTA" and close > ema50:
            setup = "⏳ ACERCÁNDOSE A SETUP DE VENTA (precio > EMA50)"
        elif bias == "ALCISTA" and close > ema50:
            setup = "✅ EN TENDENCIA ALCISTA (precio > EMA50)"
        elif bias == "BAJISTA" and close < ema50:
            setup = "✅ EN TENDENCIA BAJISTA (precio < EMA50)"
        else:
            setup = "⏸️ SIN SETUP CLARO"

    # Calcular distancia entre EMAs (convergencia/divergencia)
    ema_distance = abs(ema50 - ema200)
    if ema_distance < 10:  # Ajustar según el símbolo
        ema_status = "CONVERGIENDO"
        ema_emoji = "🔗"
    else:
        ema_status = "DIVERGIENDO"
        ema_emoji = "🔀"

    return (f"{bias_emoji} {bias} | {price_emoji} {price_position} | "
            f"{ema_emoji} EMAs {ema_status} | {setup}")

def _show_market_summary(symbol: str, snap, timestamp: str) -> None:
    """Muestra un resumen detallado del estado del mercado"""
    if not snap:
        return

    close = snap.close
    ema50 = snap.ema50
    ema200 = snap.ema200
    signal = snap.signal
    color = snap.color

    # Calcular distancias
    distance_ema50 = close - ema50
    distance_ema200 = close - ema200
    distance_between_emas = ema50 - ema200

    # Determinar fortaleza de la señal
    if signal == "LONG":
        signal_strength = "🚀 FUERTE COMPRA"
    elif signal == "SHORT":
        signal_strength = "🔻 FUERTE VENTA"
    else:
        # Calcular proximidad a señal
        if abs(distance_ema50) < 5:  # Ajustar según símbolo
            signal_strength = "⚡ CERCA DE SEÑAL"
        else:
            signal_strength = "⏸️ SIN SEÑAL"

    # Determinar color del mercado
    color_emoji = {
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
        "gray": "⚪"
    }.get(color, "⚪")

    # Mostrar resumen
    print(f"[{timestamp}] [{symbol}] 📊 RESUMEN MERCADO:")
    print(f"[{timestamp}] [{symbol}] 💰 Precio: {close:.2f} | EMA50: {ema50:.2f} | EMA200: {ema200:.2f}")
    print(f"[{timestamp}] [{symbol}] 📏 Distancia EMA50: {distance_ema50:+.2f} | EMA200: {distance_ema200:+.2f}")
    print(f"[{timestamp}] [{symbol}] 🔄 EMAs separadas: {distance_between_emas:+.2f}")
    print(f"[{timestamp}] [{symbol}] {color_emoji} Color: {color.upper()} | {signal_strength}")

    # Mostrar recomendación
    if signal == "LONG":
        print(f"[{timestamp}] [{symbol}] ✅ RECOMENDACIÓN: COMPRAR - Señal LONG activa")
    elif signal == "SHORT":
        print(f"[{timestamp}] [{symbol}] ✅ RECOMENDACIÓN: VENDER - Señal SHORT activa")
    else:
        if distance_ema50 > 0 and distance_ema200 > 0:
            print(f"[{timestamp}] [{symbol}] ⏳ RECOMENDACIÓN: ESPERAR - Precio por encima de EMAs")
        elif distance_ema50 < 0 and distance_ema200 < 0:
            print(f"[{timestamp}] [{symbol}] ⏳ RECOMENDACIÓN: ESPERAR - Precio por debajo de EMAs")
        else:
            print(f"[{timestamp}] [{symbol}] ⏳ RECOMENDACIÓN: ESPERAR - Precio entre EMAs")

    print(f"[{timestamp}] [{symbol}] " + "="*60)

def _show_initial_market_state(mons: Dict[str, MarketMonitor], timestamp: str) -> None:
    """Muestra el estado actual del mercado al iniciar el programa"""
    print(f"[{timestamp}] 🔍 Obteniendo estado actual del mercado...")

    for sym, mon in mons.items():
        try:
            snap, msg = mon.get_snapshot()
            if not snap:
                print(f"[{timestamp}] [{sym}] ❌ ERROR: {msg}")
                continue

            # Mostrar estado actual
            print(f"[{timestamp}] [{sym}] 📈 ESTADO ACTUAL:")
            print(f"[{timestamp}] [{sym}] 💰 Precio: {snap.close:.2f} | EMA50: {snap.ema50:.2f} | EMA200: {snap.ema200:.2f}")
            print(f"[{timestamp}] [{sym}] 🎯 Señal: {snap.signal or 'Ninguna'}")
            print(f"[{timestamp}] [{sym}] 🎨 Color: {snap.color.upper()}")
            print(f"[{timestamp}] [{sym}] 📅 Última vela: {snap.as_of}")

            # Mostrar setup actual
            setup_info = _get_setup_info(snap)
            if setup_info:
                print(f"[{timestamp}] [{sym}] 🔍 SETUP ACTUAL: {setup_info}")

            # Mostrar resumen detallado
            _show_market_summary(sym, snap, timestamp)

        except Exception as e:
            print(f"[{timestamp}] [{sym}] ❌ ERROR obteniendo estado: {e}")

    print(f"[{timestamp}] 🚀 Sistema listo. Esperando próximo cierre de vela...")
    print(f"[{timestamp}] " + "="*80)

def _show_realtime_status(mons: Dict[str, MarketMonitor], timestamp: str) -> None:
    """Muestra el estado actual del mercado en tiempo real"""
    for sym, mon in mons.items():
        try:
            snap, msg = mon.get_snapshot()
            if not snap:
                print(f"[{timestamp}] [{sym}] ❌ ERROR: {msg}")
                continue

            # Mostrar estado resumido
            print(f"[{timestamp}] [{sym}] 💰 {snap.close:.2f} | EMA50: {snap.ema50:.2f} | EMA200: {snap.ema200:.2f} | {snap.signal or 'Sin señal'}")

        except Exception as e:
            print(f"[{timestamp}] [{sym}] ❌ ERROR: {e}")

    print(f"[{timestamp}] " + "-"*60)

# ===================== Ejecución Paralela de Trades =====================
def _execute_single_market_order(px: ProjectXClient,
                                  account_id: int,
                                  symbol: str,
                                  contract_id: str,
                                  side: int,
                                  qty: int,
                                  tag: str) -> Tuple[str, dict]:
    """
    Ejecuta una sola orden market para un símbolo específico.
    Retorna: (symbol, result_dict)
    """
    result = {
        "symbol": symbol,
        "order_id": None,
        "fill_price": None,
        "contract_id": contract_id,
        "side": side,
        "qty": qty,
        "tag": tag,
        "success": False,
        "error": None
    }

    try:
        # Verificar duplicados
        existing_orders = _check_existing_orders_by_tag(px, account_id, tag)
        if existing_orders:
            print(f"[PARALLEL][{symbol}] SKIP: Ya existen órdenes con tag {tag}")
            result["error"] = "duplicate_orders"
            return (symbol, result)

        print(f"[PARALLEL][{symbol}] Enviando orden MARKET side={side} qty={qty} tag={tag}")

        # Colocar orden market
        placed = px.place_order(
            account_id=account_id,
            contract_id=contract_id,
            side=side,
            size=qty,
            order_type=2,  # MARKET
            customTag=tag
        )

        result["order_id"] = placed.get("orderId")
        print(f"[PARALLEL][{symbol}] ✅ Market order placed: id={result['order_id']}")

        # Esperar 1 segundo para que se ejecute
        time.sleep(1)

        # Obtener fill price
        fill_price = _poll_fill_price(px, account_id, contract_id, max_wait_sec=10)
        result["fill_price"] = fill_price

        if fill_price:
            print(f"[PARALLEL][{symbol}] ✅ Fill confirmado: {fill_price}")
            result["success"] = True
        else:
            print(f"[PARALLEL][{symbol}] ⚠️ No se pudo confirmar fill price")
            result["error"] = "no_fill_price"

    except Exception as e:
        print(f"[PARALLEL][{symbol}] ❌ ERROR: {e}")
        result["error"] = str(e)

    return (symbol, result)

def _execute_parallel_market_orders(px: ProjectXClient,
                                     account_id: int,
                                     trade_requests: List[dict]) -> Dict[str, dict]:
    """
    Ejecuta múltiples órdenes market en paralelo.

    trade_requests: Lista de dicts con:
        - symbol: str
        - contract_id: str
        - side: int
        - qty: int
        - tag: str

    Retorna: Dict[symbol, result_dict]
    """
    if not trade_requests:
        return {}

    print(f"[PARALLEL] 🚀 Ejecutando {len(trade_requests)} órdenes MARKET en paralelo...")
    start_time = time.time()

    results = {}

    # Ejecutar todas las órdenes market en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(trade_requests)) as executor:
        futures = {
            executor.submit(
                _execute_single_market_order,
                px, account_id,
                req["symbol"], req["contract_id"],
                req["side"], req["qty"], req["tag"]
            ): req["symbol"]
            for req in trade_requests
        }

        # Esperar a que todas terminen
        for future in concurrent.futures.as_completed(futures):
            symbol, result = future.result()
            results[symbol] = result

    elapsed = time.time() - start_time
    print(f"[PARALLEL] ✅ Órdenes MARKET completadas en {elapsed:.2f}s")

    # Resumen
    successful = [s for s, r in results.items() if r["success"]]
    failed = [s for s, r in results.items() if not r["success"]]

    print(f"[PARALLEL] 📊 Exitosas: {len(successful)} | Fallidas: {len(failed)}")
    for sym in successful:
        print(f"[PARALLEL]   ✅ {sym}: fill={results[sym]['fill_price']}")
    for sym in failed:
        print(f"[PARALLEL]   ❌ {sym}: error={results[sym]['error']}")

    return results

def _execute_single_bracket_order(px: ProjectXClient,
                                   account_id: int,
                                   symbol: str,
                                   contract_id: str,
                                   side: int,
                                   qty: int,
                                   tp_points: float,
                                   sl_points: float,
                                   tick_size: float,
                                   tag: str) -> Tuple[str, dict]:
    """
    Ejecuta una sola orden bracket para un símbolo específico.
    Retorna: (symbol, result_dict)
    """
    result = {
        "symbol": symbol,
        "order_id": None,
        "contract_id": contract_id,
        "side": side,
        "qty": qty,
        "tag": tag,
        "success": False,
        "error": None
    }

    try:
        print(f"[BRACKET_PARALLEL][{symbol}] Enviando bracket order side={side} qty={qty} tag={tag}")

        bracket_result = _place_bracket_order(
            px, account_id, contract_id, side, qty,
            tp_points, sl_points, tick_size, tag
        )

        result["order_id"] = bracket_result.get("order_id")
        result["success"] = bracket_result.get("success", False)
        result["error"] = bracket_result.get("error")

        if result["success"]:
            print(f"[BRACKET_PARALLEL][{symbol}] ✅ Bracket order placed: id={result['order_id']}")
        else:
            print(f"[BRACKET_PARALLEL][{symbol}] ❌ ERROR: {result['error']}")

    except Exception as e:
        print(f"[BRACKET_PARALLEL][{symbol}] ❌ EXCEPTION: {e}")
        result["error"] = str(e)

    return (symbol, result)

def _execute_parallel_bracket_orders(px: ProjectXClient,
                                      account_id: int,
                                      trade_requests: List[dict]) -> Dict[str, dict]:
    """
    Ejecuta múltiples órdenes bracket en paralelo.

    trade_requests: Lista de dicts con:
        - symbol: str
        - contract_id: str
        - side: int
        - qty: int
        - tp_points: float
        - sl_points: float
        - tick_size: float
        - tag: str

    Retorna: Dict[symbol, result_dict]
    """
    if not trade_requests:
        return {}

    print(f"[BRACKET_PARALLEL] 🚀 Ejecutando {len(trade_requests)} órdenes BRACKET en paralelo...")
    start_time = time.time()

    results = {}

    # Ejecutar todas las órdenes bracket en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(trade_requests)) as executor:
        futures = {
            executor.submit(
                _execute_single_bracket_order,
                px, account_id,
                req["symbol"], req["contract_id"], req["side"], req["qty"],
                req["tp_points"], req["sl_points"], req["tick_size"], req["tag"]
            ): req["symbol"]
            for req in trade_requests
        }

        # Esperar a que todas terminen
        for future in concurrent.futures.as_completed(futures):
            symbol, result = future.result()
            results[symbol] = result

    elapsed = time.time() - start_time
    print(f"[BRACKET_PARALLEL] ✅ Órdenes BRACKET completadas en {elapsed:.2f}s")

    # Resumen
    successful = [s for s, r in results.items() if r["success"]]
    failed = [s for s, r in results.items() if not r["success"]]

    print(f"[BRACKET_PARALLEL] 📊 Exitosas: {len(successful)} | Fallidas: {len(failed)}")
    for sym in successful:
        print(f"[BRACKET_PARALLEL]   ✅ {sym}: order_id={results[sym]['order_id']}")
    for sym in failed:
        print(f"[BRACKET_PARALLEL]   ❌ {sym}: error={results[sym]['error']}")

    return results

# ===================== Gestión de Órdenes =====================
def _place_market_order(px: ProjectXClient,
                        account_id: int,
                        contract_id: str,
                        side: int,  # 0=Buy, 1=Sell
                        qty: int,
                        tag_prefix: str) -> dict:
    """Coloca solo la orden market (sin TP/SL)"""
    out = {
        "order_id": None, "fill_price": None,
    }

    # Verificar si ya hay órdenes con este tag antes de proceder
    existing_orders = _check_existing_orders_by_tag(px, account_id, tag_prefix)
    if existing_orders:
        print(f"[ORDER] WARN: Ya existen órdenes con tag {tag_prefix}: {existing_orders}")
        return out

    print(f"[ORDER] Enviando orden market con tag: {tag_prefix}")

    placed = px.place_order(
        account_id=account_id, contract_id=contract_id,
        side=side, size=qty, order_type=2, customTag=tag_prefix  # Market
    )
    out["order_id"] = placed.get("orderId")
    print(f"[ORDER] MARKET id={out['order_id']} side={side} qty={qty} tag={tag_prefix}")

    return out

def _points_to_ticks(points: float, tick_size: float) -> int:
    """Convierte puntos a número de ticks"""
    if tick_size <= 0:
        return 0
    return int(round(points / tick_size))

def _place_bracket_order(px: ProjectXClient,
                         account_id: int,
                         contract_id: str,
                         side: int,  # 0=Buy, 1=Sell
                         qty: int,
                         tp_points: float,
                         sl_points: float,
                         tick_size: float,
                         tag_prefix: str) -> dict:
    """
    Coloca una orden MARKET con brackets (TP/SL) en una sola llamada.
    Implementación según documentación oficial del API.

    IMPORTANTE: Los ticks deben tener signo correcto:
    - LONG (side=0): TP positivo, SL negativo
    - SHORT (side=1): TP negativo, SL positivo
    """
    out = {
        "order_id": None,
        "success": False,
        "error": None
    }

    # Verificar si ya hay órdenes con este tag antes de proceder
    existing_orders = _check_existing_orders_by_tag(px, account_id, tag_prefix)
    if existing_orders:
        print(f"[BRACKET] WARN: Ya existen órdenes con tag {tag_prefix}")
        out["error"] = "duplicate_orders"
        return out

    # Convertir puntos a ticks con el signo correcto
    tp_ticks_base = _points_to_ticks(tp_points, tick_size)
    sl_ticks_base = _points_to_ticks(sl_points, tick_size)

    # Ajustar signos según la dirección del trade
    if side == 0:  # LONG (Buy)
        tp_ticks = tp_ticks_base   # TP positivo (arriba)
        sl_ticks = -sl_ticks_base  # SL negativo (abajo)
    else:  # SHORT (Sell)
        tp_ticks = -tp_ticks_base  # TP negativo (abajo)
        sl_ticks = sl_ticks_base   # SL positivo (arriba)

    side_name = "LONG" if side == 0 else "SHORT"
    print(f"[BRACKET] Enviando orden BRACKET:")
    print(f"[BRACKET]   side={side} ({side_name}) qty={qty} tag={tag_prefix}")
    print(f"[BRACKET]   TP: {tp_points} pts = {tp_ticks:+d} ticks (type=1 Limit)")
    print(f"[BRACKET]   SL: {sl_points} pts = {sl_ticks:+d} ticks (type=4 Stop)")

    try:
        placed = px.place_bracket_order(
            account_id=account_id,
            contract_id=contract_id,
            side=side,
            size=qty,
            tp_ticks=tp_ticks,
            sl_ticks=sl_ticks,
            customTag=tag_prefix
        )

        out["order_id"] = placed.get("orderId")
        out["success"] = True

        print(f"[BRACKET] ✅ Bracket order placed: id={out['order_id']}")

        # Verificación final
        time.sleep(1)  # Esperar a que se registren todas las órdenes
        all_orders = _check_existing_orders_by_tag(px, account_id, tag_prefix)
        print(f"[BRACKET] Verificación: {len(all_orders)} órdenes creadas con tag {tag_prefix}")

    except Exception as e:
        print(f"[BRACKET] ❌ ERROR: {e}")
        out["error"] = str(e)

    return out


def _place_tp_sl_orders(px: ProjectXClient,
                        account_id: int,
                        contract_id: str,
                        side: int,  # 0=Buy, 1=Sell
                        qty: int,
                        fill_price: float,
                        tp_points: float,
                        sl_points: float,
                        tick_size: float,
                        tag_prefix: str,
                        market_order_id: Optional[int] = None) -> dict:
    """Coloca órdenes de Take Profit y Stop Loss por separado, vinculadas a la orden market"""
    out = {
        "tp_order_id": None, "sl_order_id": None,
        "tp_price": None, "sl_price": None,
    }

    # Verificar si ya hay órdenes TP/SL con este tag
    existing_orders = _check_existing_orders_by_tag(px, account_id, f"{tag_prefix}-TP")
    if existing_orders:
        print(f"[ORDER] WARN: Ya existen órdenes TP con tag {tag_prefix}-TP")
        return out

    existing_orders = _check_existing_orders_by_tag(px, account_id, f"{tag_prefix}-SL")
    if existing_orders:
        print(f"[ORDER] WARN: Ya existen órdenes SL con tag {tag_prefix}-SL")
        return out

    # Calcular precios TP/SL basados en el fill
    if side == 0:  # LONG
        tp_price = _round_to_tick(fill_price + tp_points, tick_size)
        sl_price = _round_to_tick(fill_price - sl_points, tick_size)
        tp_side, sl_side = 1, 1
    else:  # SHORT
        tp_price = _round_to_tick(fill_price - tp_points, tick_size)
        sl_price = _round_to_tick(fill_price + sl_points, tick_size)
        tp_side, sl_side = 0, 0

    out["tp_price"] = tp_price
    out["sl_price"] = sl_price

    if market_order_id:
        print(f"[ORDER] Colocando TP/SL basado en fill={fill_price} linkedOrderId={market_order_id}")
    else:
        print(f"[ORDER] Colocando TP/SL basado en fill={fill_price}")

    # Colocar Take Profit (Limit)
    tp_tag = f"{tag_prefix}-TP"
    res_tp = px.place_order(
        account_id=account_id, contract_id=contract_id,
        side=tp_side, size=qty, order_type=1,  # Limit
        limit_price=tp_price,
        linked_order_id=market_order_id,  # Vincular a la orden market
        customTag=tp_tag
    )
    out["tp_order_id"] = res_tp.get("orderId")
    print(f"[ORDER] TP id={out['tp_order_id']} @ {tp_price} tag={tp_tag} linked={market_order_id}")

    # Colocar Stop Loss (Stop Market)
    sl_tag = f"{tag_prefix}-SL"
    res_sl = px.place_order(
        account_id=account_id, contract_id=contract_id,
        side=sl_side, size=qty, order_type=4,  # Stop (market)
        stop_price=sl_price,
        linked_order_id=market_order_id,  # Vincular a la orden market
        customTag=sl_tag
    )
    out["sl_order_id"] = res_sl.get("orderId")
    print(f"[ORDER] SL id={out['sl_order_id']} @ {sl_price} tag={sl_tag} linked={market_order_id}")

    # Verificación final
    all_orders = _check_existing_orders_by_tag(px, account_id, tag_prefix)
    print(f"[ORDER] Verificación final - Órdenes con tag {tag_prefix}: {len(all_orders)}")
    for order in all_orders:
        print(f"[ORDER]   - {order.get('customTag')} id={order.get('orderId')} status={order.get('status')}")

    return out

def _place_market_and_brackets(px: ProjectXClient,
                               account_id: int,
                               contract_id: str,
                               side: int,  # 0=Buy, 1=Sell
                               qty: int,
                               tp_points: float,
                               sl_points: float,
                               tick_size: float,
                               tag_prefix: str) -> dict:
    """Coloca orden market y luego TP/SL por separado después de 1 segundo"""
    out = {
        "order_id": None, "fill_price": None,
        "tp_order_id": None, "sl_order_id": None,
        "tp_price": None, "sl_price": None,
    }

    # PASO 1: Colocar solo la orden market
    market_result = _place_market_order(px, account_id, contract_id, side, qty, tag_prefix)
    out["order_id"] = market_result["order_id"]

    if not out["order_id"]:
        print("[ORDER] ERROR: No se pudo colocar la orden market")
        return out

    # PASO 2: Esperar 1 segundo para que se ejecute
    print("[ORDER] Esperando 1 segundo para confirmar ejecución...")
    time.sleep(1)

    # PASO 3: Obtener el precio de fill
    fill_price = _poll_fill_price(px, account_id, contract_id, max_wait_sec=10)
    out["fill_price"] = fill_price

    if not fill_price:
        print("[ORDER] WARN: No se pudo confirmar el precio de fill")
        return out

    print(f"[ORDER] Fill confirmado a precio: {fill_price}")

    # PASO 4: Colocar TP/SL por separado, vinculados a la orden market
    tp_sl_result = _place_tp_sl_orders(
        px, account_id, contract_id, side, qty,
        fill_price, tp_points, sl_points, tick_size, tag_prefix,
        market_order_id=out["order_id"]  # Vincular TP/SL a la orden market
    )

    out["tp_order_id"] = tp_sl_result["tp_order_id"]
    out["sl_order_id"] = tp_sl_result["sl_order_id"]
    out["tp_price"] = tp_sl_result["tp_price"]
    out["sl_price"] = tp_sl_result["sl_price"]

    return out

def _get_active_positions(px: ProjectXClient, account_id: int) -> List[dict]:
    """Obtiene posiciones activas (unified- y gocho- para compatibilidad)"""
    try:
        # Buscar órdenes abiertas con nuestros tags (unified- legacy, gocho- actual)
        open_orders = px.search_open_orders(account_id)
        active_positions = []

        for order in open_orders:
            tag = str(order.get("customTag", "") or "")
            if tag.startswith("unified-") or tag.startswith("gocho-"):
                active_positions.append({
                    "order_id": order.get("orderId"),
                    "contract_id": order.get("contractId"),
                    "side": order.get("side"),
                    "size": order.get("size"),
                    "tag": tag,
                    "status": order.get("status"),
                    "fill_price": order.get("fillPrice"),
                    "limit_price": order.get("limitPrice"),
                    "stop_price": order.get("stopPrice"),
                })

        if active_positions and DEBUG_TRADE:
            by_contract = {}
            for p in active_positions:
                c = p.get("contract_id", "?")
                by_contract[c] = by_contract.get(c, 0) + 1
            _dbg(f"[POSICIONES] _get_active_positions(account_id={account_id}): {len(active_positions)} total, por contrato: {by_contract}")

        return active_positions
    except Exception as e:
        print(f"[ACTIVE][WARN] Error getting positions: {e}")
        return []

def _check_existing_orders_by_tag(px: ProjectXClient, account_id: int, tag_prefix: str) -> List[dict]:
    """Retorna todas las órdenes abiertas que tienen un customTag que empieza con tag_prefix"""
    try:
        open_orders = px.search_open_orders(account_id)
        matching_orders = []
        for o in open_orders:
            tag = str(o.get("customTag", "") or "")
            if tag.startswith(tag_prefix):
                matching_orders.append(o)
        return matching_orders
    except Exception as e:
        print(f"[PRECHECK][WARN] Error checking orders: {e}")
        return []

def _already_open_with_tag(px: ProjectXClient, account_id: int, contract_id: str, tag_prefix: str) -> bool:
    """True si ya hay órdenes abiertas con un customTag que empieza con tag_prefix (para ese contrato)."""
    matching_orders = _check_existing_orders_by_tag(px, account_id, tag_prefix)
    for o in matching_orders:
        if o.get("contractId") == contract_id:
            return True
    return False

def _preload_before_candle_close(enabled_accounts: list, mons: dict) -> dict:
    """
    Ejecutar verificaciones ANTES del cierre de vela para eliminar delays.
    Retorna diccionario con resultados pre-cargados.
    """
    if not ENABLE_PRELOAD:
        return {}

    preload_data = {
        "timestamp": time.time(),
        "accounts_ready": {},
        "contracts_ready": {}
    }

    _dbg("[PRELOAD] Iniciando pre-carga antes del cierre de vela...")

    # 1. Verificar autenticación de todos los brokers
    for account in enabled_accounts:
        try:
            client = account.get_api_client()
            # Verificar si el token existe y es válido
            if not client.token or not client.validate_token():
                _dbg(f"[PRELOAD] Re-autenticando {account.name}...")
                client.login_with_key()
            preload_data["accounts_ready"][account.id] = True
            _dbg(f"[PRELOAD] ✓ {account.name} autenticado")
        except Exception as e:
            _dbg(f"[PRELOAD] ⚠️ {account.name} auth failed: {e}")
            preload_data["accounts_ready"][account.id] = False

    # 2. Pre-verificar contract IDs están disponibles
    for sym, mon in mons.items():
        if mon.contract_id:
            preload_data["contracts_ready"][sym] = mon.contract_id
            _dbg(f"[PRELOAD] ✓ {sym} contract ready: {mon.contract_id}")

    _dbg(f"[PRELOAD] Completado - {len(preload_data['accounts_ready'])} cuentas, {len(preload_data['contracts_ready'])} contratos")

    return preload_data

def _close_position_manually(px: ProjectXClient, account_id: int, position: dict) -> bool:
    """Cierra posición manualmente si TP/SL fallaron"""
    try:
        # Determinar lado opuesto para cerrar
        close_side = 1 if position["side"] == 0 else 0

        # Colocar orden de cierre
        close_order = px.place_order(
            account_id=account_id,
            contract_id=position["contract_id"],
            side=close_side,
            size=position["size"],
            order_type=2,  # Market order
            customTag=f"manual-close-{int(time.time())}"
        )

        print(f"[MANUAL_CLOSE] Closed position {position['order_id']} with order {close_order.get('orderId')}")
        return True

    except Exception as e:
        print(f"[MANUAL_CLOSE][ERROR] Failed to close position {position['order_id']}: {e}")
        return False

def _close_all_positions(px: ProjectXClient, account_id: int, reason: str = "AUTO_CLOSE") -> int:
    """
    Close all open positions.
    Returns the number of positions closed.
    """
    print(f"\n{'='*80}")
    print(f"[{reason}] 🔴 Cerrando todas las posiciones abiertas...")
    print(f"{'='*80}")

    try:
        # Get all active positions
        active_positions = _get_active_positions(px, account_id)

        if not active_positions:
            print(f"[{reason}] ✅ No hay posiciones abiertas para cerrar")
            print(f"{'='*80}\n")
            return 0

        print(f"[{reason}] 📊 Encontradas {len(active_positions)} posiciones para cerrar")

        closed_count = 0
        for position in active_positions:
            symbol = "MNQ" if "MNQ" in position.get("contract_id", "") else "ES" if "EP" in position.get("contract_id", "") else "UNKNOWN"
            print(f"[{reason}] Cerrando posición {symbol}: {position.get('order_id')}")

            if _close_position_manually(px, account_id, position):
                closed_count += 1
                # Log the forced close
                log_entry = {
                    "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "event": reason,
                    "symbol": symbol,
                    "contract_id": position.get("contract_id"),
                    "position_id": position.get("order_id"),
                    "side": "BUY" if position.get("side") == 0 else "SELL",
                    "size": position.get("size")
                }
                _write_log(log_entry)

            time.sleep(0.5)  # Small delay between closes

        print(f"[{reason}] ✅ Se cerraron {closed_count}/{len(active_positions)} posiciones")
        print(f"{'='*80}\n")

        return closed_count

    except Exception as e:
        print(f"[{reason}][ERROR] Error cerrando posiciones: {e}")
        print(f"{'='*80}\n")
        return 0


# ===================== Monitoreo Activo =====================
def _check_existing_trades_on_startup(px: ProjectXClient, account_id: int, monitors: Dict[str, MarketMonitor]) -> Tuple[int, Dict[str, int]]:
    """
    Verifica si hay trades abiertos al iniciar el programa.
    NO importa el customTag - detecta CUALQUIER posición abierta.
    Retorna: (total_positions, open_positions_by_symbol)
    """
    print("\n" + "="*80)
    print("[STARTUP] 🔍 Verificando posiciones abiertas al iniciar...")
    print("="*80)

    try:
        # Obtener todas las órdenes abiertas (sin filtro de tag)
        open_orders = px.search_open_orders(account_id)

        if not open_orders:
            print("[STARTUP] ✅ No hay posiciones abiertas")
            print("="*80 + "\n")
            return 0, {}

        print(f"[STARTUP] 📊 Encontradas {len(open_orders)} órdenes abiertas en la cuenta")

        # Agrupar por contrato (símbolo)
        positions_by_contract: Dict[str, List[dict]] = {}

        for order in open_orders:
            contract_id = order.get("contractId")
            if contract_id:
                if contract_id not in positions_by_contract:
                    positions_by_contract[contract_id] = []
                positions_by_contract[contract_id].append(order)

        # Mapear contratos a símbolos y contar posiciones
        open_positions_by_symbol: Dict[str, int] = {}

        print(f"[STARTUP] 📍 Posiciones detectadas por símbolo:\n")

        for contract_id, orders in positions_by_contract.items():
            # Determinar símbolo
            symbol = None
            for sym, mon in monitors.items():
                if mon.contract_id == contract_id:
                    symbol = sym
                    break

            if not symbol:
                # Si no está en los monitores, intentar determinar por el nombre del contrato
                if "MNQ" in contract_id or "NQ" in contract_id:
                    symbol = "MNQ"
                elif "ES" in contract_id or "EP" in contract_id:
                    symbol = "ES"
                else:
                    symbol = f"CONTRACT_{contract_id[:10]}"

            # Contar cuántas órdenes activas hay
            active_orders = [o for o in orders if o.get("status") in ("Working", "Pending", "Accepted")]
            order_count = len(active_orders)

            if order_count > 0:
                open_positions_by_symbol[symbol] = order_count

                print(f"[STARTUP] [{symbol}] {order_count} órdenes activas:")

                for order in active_orders[:5]:  # Mostrar máximo 5 por símbolo
                    order_id = order.get("orderId")
                    side = "BUY" if order.get("side") == 0 else "SELL"
                    size = order.get("size")
                    order_type = order.get("type")
                    tag = order.get("customTag", "sin-tag")

                    type_name = {
                        1: "LIMIT",
                        2: "MARKET",
                        4: "STOP"
                    }.get(order_type, f"TYPE_{order_type}")

                    # Mostrar precio según tipo
                    if order_type == 1:  # Limit
                        price = order.get("limitPrice")
                        price_str = f"@ {price}" if price else ""
                    elif order_type == 4:  # Stop
                        price = order.get("stopPrice")
                        price_str = f"@ {price}" if price else ""
                    else:
                        price = order.get("fillPrice") or order.get("averagePrice")
                        price_str = f"filled @ {price}" if price else ""

                    print(f"[STARTUP]     - {type_name} {side} {size} {price_str} (ID: {order_id}, Tag: {tag})")

                if len(active_orders) > 5:
                    print(f"[STARTUP]     ... y {len(active_orders) - 5} órdenes más")

                print(f"[STARTUP] ⚠️  [{symbol}] BLOQUEADO para nuevos trades hasta que se cierren posiciones\n")

        total_positions = sum(open_positions_by_symbol.values())

        if total_positions > 0:
            print(f"[STARTUP] 📈 Total: {total_positions} órdenes activas en {len(open_positions_by_symbol)} símbolo(s)")
            print(f"[STARTUP] 🔒 Símbolos bloqueados: {', '.join(open_positions_by_symbol.keys())}")
            print(f"[STARTUP] 🟢 Símbolos disponibles: {', '.join([s for s in monitors.keys() if s not in open_positions_by_symbol])}")
        else:
            print(f"[STARTUP] ✅ Todos los símbolos disponibles para trading")

        print("="*80 + "\n")

        return total_positions, open_positions_by_symbol

    except Exception as e:
        print(f"[STARTUP] ❌ ERROR al verificar posiciones: {e}")
        print("="*80 + "\n")
        return 0, {}

def _monitor_active_positions(px: ProjectXClient, account_id: int, monitors: Dict[str, MarketMonitor]) -> None:
    """Monitorea posiciones activas y cierra si es necesario"""
    active_positions = _get_active_positions(px, account_id)

    if not active_positions:
        return

    print(f"[ACTIVE] Monitoring {len(active_positions)} active positions")

    for position in active_positions:
        try:
            # Obtener precio actual
            contract_id = position["contract_id"]
            symbol = None

            # Determinar símbolo del contrato
            for sym, mon in monitors.items():
                if mon.contract_id == contract_id:
                    symbol = sym
                    break

            if not symbol:
                continue

            # Obtener snapshot actual
            snap, msg = monitors[symbol].get_snapshot()
            if not snap:
                continue

            current_price = snap.close
            fill_price = position.get("fill_price")

            if not fill_price:
                continue

            # Verificar si debe cerrar
            should_close = False
            close_reason = ""

            if position["side"] == 0:  # LONG position
                tp_price = position.get("limit_price")  # TP order
                sl_price = position.get("stop_price")   # SL order

                if tp_price and current_price >= tp_price:
                    should_close = True
                    close_reason = f"TP hit: {current_price} >= {tp_price}"
                elif sl_price and current_price <= sl_price:
                    should_close = True
                    close_reason = f"SL hit: {current_price} <= {sl_price}"

            else:  # SHORT position
                tp_price = position.get("limit_price")  # TP order
                sl_price = position.get("stop_price")   # SL order

                if tp_price and current_price <= tp_price:
                    should_close = True
                    close_reason = f"TP hit: {current_price} <= {tp_price}"
                elif sl_price and current_price >= sl_price:
                    should_close = True
                    close_reason = f"SL hit: {current_price} >= {sl_price}"

            if should_close:
                print(f"[ACTIVE] {close_reason} - Closing position {position['order_id']}")
                _close_position_manually(px, account_id, position)

                # Log del cierre manual
                log_entry = {
                    "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "event": "MANUAL_CLOSE",
                    "symbol": symbol,
                    "contract_id": contract_id,
                    "position_id": position["order_id"],
                    "close_reason": close_reason,
                    "current_price": current_price,
                    "fill_price": fill_price,
                    "account_id": account_id
                }
                _write_log(log_entry)

        except Exception as e:
            print(f"[ACTIVE][ERROR] Error monitoring position {position.get('order_id', 'unknown')}: {e}")

# ===================== Función Principal =====================
def main():
    """Función principal del trader unificado"""
    align_tz = _get_align_tz()

    # ==================== ACCOUNT MANAGER SETUP ====================
    print("[Scanner] Inicializando gestión de cuentas...")
    try:
        account_mgr = AccountManager()
    except Exception as e:
        print(f"[ERROR] No se pudo cargar AccountManager: {e}")
        print("[INFO] Creando accounts.json con configuración default...")
        account_mgr = AccountManager()

    # ==================== SCANNER SETUP (SOLO DATOS DE MERCADO) ====================
    print("[Scanner] Conectando al broker para obtener datos de mercado...")
    scanner_px = account_mgr.get_scanner_client()
    scanner_px.login_with_key()
    print(f"[Scanner] ✓ Conectado a {account_mgr.scanner_config.broker.upper()} para datos de mercado")

    # ==================== TRADING ACCOUNTS SETUP ====================
    enabled_accounts = account_mgr.get_enabled_accounts()

    # Modo solo cuenta de práctica (por ejemplo para Raspberry Pi o pruebas)
    if ONLY_PRACTICE_ACCOUNT and enabled_accounts:
        practice_id_env = os.getenv("PRACTICE_ACCOUNT_ID")
        practice_accounts = []

        # 1) Intentar por PRACTICE_ACCOUNT_ID explícito
        if practice_id_env:
            try:
                practice_account_id = int(practice_id_env)
                practice_accounts = [acc for acc in enabled_accounts if acc.account_id == practice_account_id]
            except ValueError:
                print(f"[Trader][WARN] PRACTICE_ACCOUNT_ID inválido: {practice_id_env}")

        # 2) Si no se encontró por ID, intentar por nombre (contiene 'prueba' o 'practice')
        if not practice_accounts:
            for acc in enabled_accounts:
                name_upper = acc.name.upper()
                if "PRUEBA" in name_upper or "PRACTICE" in name_upper:
                    practice_accounts.append(acc)

        if practice_accounts:
            enabled_accounts = practice_accounts
            print("\n[Trader] MODO SOLO CUENTA DE PRUEBA ACTIVADO (ONLY_PRACTICE_ACCOUNT=true)")
            for acc in enabled_accounts:
                print(f"  🎯 Usando solo: {acc.name} (Account ID: {acc.account_id})")
        else:
            print("\n[Trader][WARN] ONLY_PRACTICE_ACCOUNT=true pero no se encontró cuenta de prueba.")
            print("        Revisa PRACTICE_ACCOUNT_ID o el nombre de la cuenta (debe contener 'Prueba' o 'Practice').")

    if not enabled_accounts:
        print("\n" + "="*80)
        print("[ERROR] No hay cuentas habilitadas en accounts.json")
        print("[INFO] Opciones:")
        print("  1. Abrir la GUI y configurar cuentas en la pestaña 'Accounts'")
        print("  2. Editar accounts.json manualmente")
        print("="*80 + "\n")
        return

    print(f"\n[Trader] Cuentas de trading habilitadas: {len(enabled_accounts)}")
    print("="*80)
    for acc in enabled_accounts:
        print(f"  📊 {acc.name}")
        print(f"     Broker: {acc.broker.upper()}")
        print(f"     Account ID: {acc.account_id}")
        print(f"     Contratos: MNQ={acc.contracts.get('MNQ',0)} | ES={acc.contracts.get('ES',0)}")
    print("="*80)

    # Login to all trading accounts
    print("\n[Trader] Conectando a brokers de trading...")
    for acc in enabled_accounts:
        try:
            client = acc.get_api_client()
            client.login_with_key()
            print(f"  ✓ {acc.name} conectado")
        except Exception as e:
            print(f"  ✗ {acc.name} falló: {e}")
            print(f"     Continuando de todos modos...")

    print(f"\n[UnifiedTrader] DRY_RUN={DRY_RUN} TZ={align_tz.key} LAG={CLOSE_LAG_SEC}s")
    print(f"[UnifiedTrader] Position limits: MAX_GLOBAL={MAX_ACTIVE_POSITIONS} MAX_PER_SYMBOL={MAX_POSITIONS_PER_SYMBOL}")

    # Parada remota vía Telegram (/stop); también interrumpe esperas largas (_sleep_until)
    telegram_shutdown_event = threading.Event()

    # Estado compartido para Telegram /status (solo lectura desde el thread)
    telegram_shared_state = {
        "mode": "WAITING",
        "dry_run": DRY_RUN,
        "snapshots": {},
        "active_positions_count": 0,
        "orders_paused": False,
    }
    telegram_shared_lock = threading.Lock()
    delayed_ema_alerts = []  # Cola de alertas "precio entre EMAs" para enviar tras TELEGRAM_EMA_ALERT_DELAY_SEC
    delayed_ema_lock = threading.Lock()
    if USE_TG and TG_TOKEN and TG_CHAT:
        _telegram_listener = threading.Thread(
            target=_telegram_listener_loop,
            args=(telegram_shared_state, telegram_shared_lock, TG_TOKEN, TG_CHAT,
                  delayed_ema_alerts, delayed_ema_lock, TELEGRAM_EMA_ALERT_DELAY_SEC,
                  telegram_shutdown_event),
            daemon=True,
            name="TelegramListener",
        )
        _telegram_listener.start()
        print(
            f"[UnifiedTrader] Telegram: /status, /log, /pause, /resume, /stop"
            f"{' (requiere TELEGRAM_STOP_SECRET)' if TELEGRAM_STOP_SECRET else ''}. "
            f"Alertas EMA retraso {TELEGRAM_EMA_ALERT_DELAY_SEC}s."
        )

    # Set de alertas de setup ya encoladas (evitar duplicados por sesión)
    # Formato: (sym, "alcista"|"bajista", fecha_ny) para trackear por día
    alerted_setup_alerts = set()
    MAX_ALERTED_SET = 100
    MAX_DELAYED_ALERTS = 50

    # Inicializar monitores con el SCANNER (permitir filtrar por símbolo vía RUN_SYMBOLS="MNQ" o "ES" o "MNQ,ES")
    run_symbols_env = os.getenv("RUN_SYMBOLS", "MNQ,ES")
    run_symbols = [s.strip().upper() for s in run_symbols_env.split(",") if s.strip()]
    if not run_symbols:
        run_symbols = ["MNQ", "ES"]

    mons: Dict[str, MarketMonitor] = {sym: MarketMonitor(sym, px=scanner_px) for sym in run_symbols}

    # ============ MONITOR ADICIONAL PARA MES (usado cuando ES SHORT) ============
    mes_monitor: Optional[MarketMonitor] = None
    if ES_SHORT_USE_MES and "ES" in run_symbols:
        print("[Scanner] Inicializando monitor MES para señales ES SHORT...")
        mes_monitor = MarketMonitor("MES", px=scanner_px)
        if mes_monitor.contract_id:
            print(f"[MES] contract_id={mes_monitor.contract_id} (para ES SHORT)")
        else:
            print("[MES] ⚠️ No se pudo resolver contrato MES - ES SHORT usará ES normal")
            mes_monitor = None

    # Obtener tick sizes (usando scanner)
    tick_size: Dict[str, float] = {}
    for sym, mon in mons.items():
        if not mon.contract_id:
            raise RuntimeError(f"Sin contractId para {sym}")
        tsz = _get_tick_size(scanner_px, mon.contract_id, default=0.25)
        tick_size[sym] = tsz
        print(f"[{sym}] contract_id={mon.contract_id} tickSize={tsz}")

    # Tick size para MES (igual que ES: 0.25)
    if mes_monitor and mes_monitor.contract_id:
        mes_tick_size = _get_tick_size(scanner_px, mes_monitor.contract_id, default=0.25)
        tick_size["MES"] = mes_tick_size
        print(f"[MES] contract_id={mes_monitor.contract_id} tickSize={mes_tick_size}")

    # Cargar señales ya procesadas
    seen_signals = _load_seen()

    # Enviar notificación de inicio del sistema
    _notify_startup(account_mgr)

    # Estado del sistema
    mode = "WAITING"  # WAITING, ACTIVE
    last_sent_by_symbol: Dict[str, str] = {}

    # ⚡ ALIASES para compatibilidad con código de monitoreo existente
    # TODO: Mejorar monitoreo para soportar múltiples cuentas simultáneamente
    first_account = enabled_accounts[0]
    px = first_account.get_api_client()
    account_id = first_account.account_id

    # ⚡ VERIFICACIÓN INICIAL: Comprobar si hay posiciones abiertas al iniciar (primera cuenta)
    # TODO: Mejorar para verificar todas las cuentas
    initial_positions, blocked_symbols = _check_existing_trades_on_startup(
        px,
        account_id,
        mons
    )

    # Ajustar modo inicial según posiciones existentes
    if initial_positions > 0:
        mode = "ACTIVE"
        print(f"[UnifiedTrader] ⚠️  Iniciando en modo ACTIVE ({initial_positions} órdenes detectadas)")
        print(f"[UnifiedTrader] 🔒 Símbolos bloqueados: {', '.join(blocked_symbols.keys())}")
        print(f"[UnifiedTrader] 🟢 Símbolos disponibles: {', '.join([s for s in run_symbols if s not in blocked_symbols])}")
        print(f"[UnifiedTrader] El sistema monitoreará posiciones existentes y solo abrirá nuevas en símbolos disponibles\n")
    else:
        print(f"[UnifiedTrader] Starting in {mode} mode")

    if SHOW_REALTIME_STATUS:
        print(f"[UnifiedTrader] 📊 Monitoreo en tiempo real habilitado (cada {REALTIME_STATUS_INTERVAL}s)")

    # Mostrar configuración de horarios si está habilitada
    if ENABLE_TRADING_HOURS:
        print(f"[UnifiedTrader] ⏰ Control de horarios ACTIVADO:")
        print(f"[UnifiedTrader]    - Zona horaria: {TRADING_TIMEZONE}")
        print(f"[UnifiedTrader]    - Horario de apertura: {TRADING_START_TIME} - {TRADING_END_TIME}")
        print(f"[UnifiedTrader]    - Cierre forzoso: {FORCE_CLOSE_TIME}")
        print(f"[UnifiedTrader]    - Auto-cierre: {'SÍ' if AUTO_CLOSE_AT_END else 'NO'}")
        print(f"[UnifiedTrader]    - Alerta diaria sistema listo: {DAILY_READY_ALERT_TIME} {TRADING_TIMEZONE}")
    else:
        print(f"[UnifiedTrader] ⏰ Control de horarios DESACTIVADO (opera 24/7)")

    # Mostrar filtros de señales activos
    filters_active = []
    if not ALLOW_MNQ_LONG:
        filters_active.append("MNQ LONG bloqueado")
    if not ALLOW_MNQ_SHORT:
        filters_active.append("MNQ SHORT bloqueado")
    if not ALLOW_ES_LONG:
        filters_active.append("ES LONG bloqueado")
    if not ALLOW_ES_SHORT:
        filters_active.append("ES SHORT bloqueado")

    if filters_active:
        print(f"[UnifiedTrader] 🚦 Filtros de señales ACTIVOS:")
        for f in filters_active:
            print(f"[UnifiedTrader]    - {f}")
    else:
        print(f"[UnifiedTrader] 🚦 Sin filtros de señales (todas las direcciones permitidas)")

    # Mostrar optimizaciones de velocidad activas
    if SKIP_PRECHECK_DUPLICATES:
        print(f"[UnifiedTrader] ⚡ Optimización de velocidad: Prechecks de duplicados DESACTIVADOS")
    if CLOSE_LAG_SEC < 0.5:
        print(f"[UnifiedTrader] ⚡ Optimización de velocidad: CLOSE_LAG reducido a {CLOSE_LAG_SEC}s")
    if ENABLE_PRELOAD:
        print(f"[UnifiedTrader] ⚡ Optimización de velocidad: Pre-carga activada ({PRELOAD_SECONDS_BEFORE}s antes del cierre)")

    # Mostrar estado inicial del mercado inmediatamente
    print(f"[UnifiedTrader] 📊 ESTADO INICIAL DEL MERCADO:")
    _show_initial_market_state(mons, datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))

    # Variables para monitoreo en tiempo real
    last_realtime_status = time.time()

    # Tracking de alerta diaria de sistema listo (hora configurable)
    last_0915_alert_date = None
    # Cierre forzoso: una pasada por día calendario NY dentro de la ventana (evita spam a la API)
    last_force_close_contract_ny_date = None
    try:
        ready_alert_hour, ready_alert_minute = _parse_time_string(DAILY_READY_ALERT_TIME)
    except Exception:
        ready_alert_hour, ready_alert_minute = 9, 15
        print(f"[UnifiedTrader][WARN] DAILY_READY_ALERT_TIME inválido: '{DAILY_READY_ALERT_TIME}'. Usando 09:15")

    while True:
        try:
            now_tz = datetime.now(align_tz)

            if telegram_shutdown_event.is_set():
                print("\n[UnifiedTrader] 🔴 Detenido por comando Telegram (/stop).")
                _notify_telegram("✅ TraderDesk detenido.")
                break

            # ⏰ VERIFICACIÓN DE HORARIOS DE TRADING
            if ENABLE_TRADING_HOURS:
                # 0. Alerta diaria de sistema listo: verificar si sistema está listo para trading
                tz_ny = ZoneInfo(TRADING_TIMEZONE)
                now_ny = now_tz.astimezone(tz_ny)
                current_date_ny = now_ny.date()
                is_ready_alert_time = (now_ny.hour == ready_alert_hour and now_ny.minute == ready_alert_minute)

                if is_ready_alert_time and USE_TG and TG_TOKEN and TG_CHAT:
                    if last_0915_alert_date != current_date_ny:
                        # Verificar estado del sistema
                        is_ready, issues = _check_system_readiness(mons, enabled_accounts, scanner_px, px, account_id)
                        last_0915_alert_date = current_date_ny

                        emoji = "✅" if is_ready else "⚠️"
                        status_text = "LISTO PARA TRADING" if is_ready else "NO LISTO - REVISAR"

                        lines = [
                            f"{emoji} Estado del Sistema ({ready_alert_hour:02d}:{ready_alert_minute:02d} NY)",
                            "=" * 40,
                            f"Fecha: {current_date_ny}",
                            f"Estado: {status_text}",
                            f"Mode: {mode}",
                            f"DRY_RUN: {DRY_RUN}",
                            "",
                        ]

                        if issues:
                            lines.append("Detalles:")
                            for issue in issues:
                                lines.append(f"  {issue}")
                        else:
                            lines.append("✓ Todos los componentes operativos")

                        lines.append("")
                        lines.append(f"Cuentas habilitadas: {len(enabled_accounts)}")
                        for acc in enabled_accounts:
                            lines.append(f"  - {acc.name} ({acc.broker.upper()})")

                        lines.append("")
                        lines.append(f"Símbolos monitoreados: {', '.join(run_symbols)}")
                        lines.append("")
                        lines.append(_telegram_commands_help_text())

                        _notify_telegram("\n".join(lines))
                        print(
                            f"[UnifiedTrader] 📱 Alerta de {ready_alert_hour:02d}:{ready_alert_minute:02d} enviada: {status_text}"
                        )

                # 1. Cierre forzoso (FORCE_CLOSE_TIME NY): Position/closeContract en MNQ, ES y MES por cuenta
                if _should_close_positions_now(now_tz, TRADING_TIMEZONE, FORCE_CLOSE_TIME):
                    if last_force_close_contract_ny_date != current_date_ny:
                        print(f"\n⏰ HORA DE CIERRE FORZOSO: {FORCE_CLOSE_TIME} {TRADING_TIMEZONE}")
                        force_close_via_close_contract_api(
                            enabled_accounts, mons, mes_monitor, reason="FORCE_CLOSE_16:00"
                        )
                        last_force_close_contract_ny_date = current_date_ny
                        mode = "WAITING"
                        if not _sleep_interruptible(60, telegram_shutdown_event):
                            break
                        continue

                # 2. Verificar si estamos dentro del horario para abrir nuevas posiciones (09:30-13:30 NYC)
                within_hours, hours_status = _is_within_trading_hours(
                    now_tz, TRADING_TIMEZONE, TRADING_START_TIME, TRADING_END_TIME
                )

                # Si estamos fuera del horario de apertura, solo monitorear posiciones existentes
                if not within_hours:
                    # Aún podemos monitorear posiciones activas, pero no abrir nuevas
                    active_positions = _get_active_positions(px, account_id)
                    if active_positions:
                        # Si hay posiciones activas, monitorear en cierre de vela (no polling cada segundos)
                        if mode != "ACTIVE":
                            mode = "ACTIVE"
                            print(f"\n⏰ Fuera de horario de apertura, pero monitoreando {len(active_positions)} posiciones activas")
                        _monitor_active_positions(px, account_id, mons)
                        target_close = _next_quarter_close(now_tz)
                        if not _sleep_until(target_close, telegram_shutdown_event):
                            break
                        continue
                    else:
                        # No hay posiciones y estamos fuera de horario
                        if hours_status == "BEFORE_TRADING_HOURS":
                            _dbg(f"⏰ Antes del horario de trading. Esperando {TRADING_START_TIME} {TRADING_TIMEZONE}")
                            if not _sleep_interruptible(60, telegram_shutdown_event):
                                break
                            continue
                        elif hours_status == "AFTER_TRADING_HOURS":
                            _dbg(f"⏰ Fuera de horario de apertura. Posiciones pueden continuar hasta {FORCE_CLOSE_TIME} {TRADING_TIMEZONE}")
                            if not _sleep_interruptible(60, telegram_shutdown_event):
                                break
                            continue

            # Verificar si hay posiciones activas
            active_positions = _get_active_positions(px, account_id)
            has_active_positions = len(active_positions) > 0

            # Cambiar modo según posiciones activas (opcionalmente seguir procesando señales)
            if has_active_positions and mode != "ACTIVE":
                mode = "ACTIVE"
                print(f"[UnifiedTrader] Switching to ACTIVE mode - {len(active_positions)} positions")
            elif not has_active_positions and mode != "WAITING":
                mode = "WAITING"
                print(f"[UnifiedTrader] Switching to WAITING mode - no active positions")

            # Actualizar estado para Telegram /status (cada iteración)
            with telegram_shared_lock:
                telegram_shared_state["mode"] = mode
                telegram_shared_state["dry_run"] = DRY_RUN
                telegram_shared_state["active_positions_count"] = len(active_positions)

            if mode == "ACTIVE":
                # Monitorear posiciones activas una vez por ciclo de vela
                _monitor_active_positions(px, account_id, mons)

                # Calcular tiempo hasta el próximo cierre de vela
                target_close = _next_quarter_close(now_tz)
                seconds_until_close = (target_close - now_tz).total_seconds()

                if not PROCESS_SIGNALS_WHILE_ACTIVE and seconds_until_close > ACTIVE_MONITOR_INTERVAL:
                    # Comportamiento por velas: esperar al próximo cierre en lugar de polling cada segundos.
                    _dbg(f"ACTIVE mode: {seconds_until_close:.1f}s until next close, sleeping until candle close")
                    if not _sleep_until(target_close, telegram_shutdown_event):
                        break
                    continue
                # Si falta <= ACTIVE_MONITOR_INTERVAL segundos, continuar con el flujo
                # para estar listo cuando cierre la vela

            # Monitoreo en tiempo real (solo en modo WAITING)
            if SHOW_REALTIME_STATUS and mode == "WAITING":
                current_time = time.time()
                if current_time - last_realtime_status >= REALTIME_STATUS_INTERVAL:
                    ts_now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                    print(f"[{ts_now_utc}] 📊 ESTADO EN TIEMPO REAL:")
                    _show_realtime_status(mons, ts_now_utc)
                    last_realtime_status = current_time

            # Modo WAITING: esperar próximo cierre de vela
            target_close = _next_quarter_close(now_tz)
            # Caso especial 9:30 NY: si acabamos de entrar en horario (ej. dormíamos antes de 9:30),
            # _next_quarter_close(9:30) devuelve 9:45 y perderíamos la vela que cierra a las 9:30.
            # Usar como target la vela que cierra exactamente a la hora de apertura.
            if ENABLE_TRADING_HOURS and TRADING_START_TIME:
                try:
                    tz_ny = ZoneInfo(TRADING_TIMEZONE)
                    now_ny = now_tz.astimezone(tz_ny)
                    start_h, start_m = _parse_time_string(TRADING_START_TIME)
                    session_open_ny = now_ny.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                    # Ventana: hasta 2 min después de la apertura para no perder la vela de 9:30
                    if session_open_ny <= now_ny < session_open_ny + timedelta(minutes=2):
                        target_close = session_open_ny.astimezone(align_tz)
                        _dbg(f"⏰ Primera vela de sesión: target_close={target_close} (cierre {TRADING_START_TIME} {TRADING_TIMEZONE})")
                except Exception as e:
                    _dbg(f"[TRADING_HOURS] Fallo al calcular vela de apertura: {e}")

            # PRE-CARGA: Preparar verificaciones ANTES del cierre de vela
            if ENABLE_PRELOAD:
                preload_time = target_close - timedelta(seconds=PRELOAD_SECONDS_BEFORE)
                if not _sleep_until(preload_time, telegram_shutdown_event):
                    break
                preload_data = _preload_before_candle_close(enabled_accounts, mons)
                # Ahora esperar el tiempo restante hasta el cierre
                if not _sleep_until(target_close, telegram_shutdown_event):
                    break
            else:
                if not _sleep_until(target_close, telegram_shutdown_event):
                    break

            time.sleep(CLOSE_LAG_SEC)  # margen de publicación

            expected_close_utc = target_close.astimezone(timezone.utc).replace(microsecond=0)
            expected_open_utc = expected_close_utc - timedelta(minutes=BAR_MINUTES)

            ts_now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

            _dbg(f"Expecting close >= {expected_close_utc.isoformat().replace('+00:00','Z')}, "
                 f"lag={CLOSE_LAG_SEC}s, retries={RETRY_COUNT}x{RETRY_INTERVAL}s")

            # FASE 1: Recolectar señales y snapshots de todos los símbolos
            pending_trades = []  # Lista de trades que se ejecutarán en paralelo
            snapshots = {}  # Guardar snapshots para uso posterior

            for sym, mon in mons.items():
                snap = None
                last_got = None

                # Reintentos hasta que aparezca la vela esperada
                for _ in range(RETRY_COUNT):
                    s, msg = mon.get_snapshot()
                    if s:
                        last_got = s.as_of
                        got = datetime.fromisoformat(s.as_of.replace("Z", "+00:00"))
                        # Si el proveedor etiqueta por apertura (p.ej., 09:15 para la vela que cierra 09:30),
                        # comparamos contra expected_open_utc. Si etiqueta por cierre, contra expected_close_utc.
                        if (BAR_TIMESTAMP_MODE == "open" and got >= expected_open_utc) or \
                           (BAR_TIMESTAMP_MODE == "close" and got >= expected_close_utc):
                            snap = s
                            break
                    time.sleep(RETRY_INTERVAL)

                if not snap:
                    want = expected_open_utc if BAR_TIMESTAMP_MODE == "open" else expected_close_utc
                    print(f"[{ts_now_utc}] [{sym}] WARN: no llegó la vela de {want.isoformat().replace('+00:00','Z')} "
                          f"(última disponible: {last_got})")
                    _dbg(f"{sym} still waiting: last_got={last_got}")
                    continue

                # Mostrar estado del mercado cada 15 minutos (versión compacta para GUI)
                # Formato compacto: [TIME] [SYM] Price | EMA50 | EMA200 | Signal | Color
                print(f"[{ts_now_utc}] [{sym}] 💰 {snap.close:.2f} | EMA50: {snap.ema50:.2f} | "
                      f"EMA200: {snap.ema200:.2f} | Signal: {snap.signal or 'None'} | Color: {snap.color.upper()}")

                # Mostrar bias y setup en una sola línea
                bias = "📈 ALCISTA" if snap.ema50 > snap.ema200 else "📉 BAJISTA" if snap.ema50 < snap.ema200 else "➡️ NEUTRAL"
                price_vs_ema50 = "above" if snap.close > snap.ema50 else "below"
                setup_status = "🚀 LONG SETUP" if snap.signal == "LONG" else "🔻 SHORT SETUP" if snap.signal == "SHORT" else "⏸️ No Setup"
                print(f"[{ts_now_utc}] [{sym}] {bias} | Price {price_vs_ema50} EMA50 | {setup_status}")

                # Solo mostrar resumen detallado si SHOW_REALTIME_STATUS está activado
                if SHOW_REALTIME_STATUS:
                    _show_market_summary(sym, snap, ts_now_utc)

                # Guardar snapshot para uso posterior
                snapshots[sym] = snap

                # Verificar si hay señal válida
                if snap.signal not in ("LONG", "SHORT"):
                    continue

                # Filtrar señales según configuración de dirección permitida
                if sym == "MNQ":
                    if snap.signal == "LONG" and not ALLOW_MNQ_LONG:
                        print(f"[{sym}] ⏸️ Señal LONG filtrada (ALLOW_MNQ_LONG=false)")
                        continue
                    if snap.signal == "SHORT" and not ALLOW_MNQ_SHORT:
                        print(f"[{sym}] ⏸️ Señal SHORT filtrada (ALLOW_MNQ_SHORT=false)")
                        continue
                elif sym == "ES":
                    if snap.signal == "LONG" and not ALLOW_ES_LONG:
                        print(f"[{sym}] ⏸️ Señal LONG filtrada (ALLOW_ES_LONG=false)")
                        continue
                    if snap.signal == "SHORT" and not ALLOW_ES_SHORT:
                        print(f"[{sym}] ⏸️ Señal SHORT filtrada (ALLOW_ES_SHORT=false)")
                        continue

                # Verificar si ya procesamos esta señal
                event_id = _event_id(sym, snap.as_of, snap.signal)
                if event_id in seen_signals:
                    _dbg(f"{sym} SKIP already processed: {event_id}")
                    continue

                # Verificar si ya enviamos por esta vela
                if last_sent_by_symbol.get(sym) == snap.as_of:
                    _dbg(f"{sym} SKIP duplicated as_of={snap.as_of}")
                    continue

                with telegram_shared_lock:
                    orders_paused = bool(telegram_shared_state.get("orders_paused", False))
                if orders_paused:
                    print(f"[{sym}] ⏸️ Señal omitida: envío de órdenes pausado (Telegram: /resume)")
                    _dbg(f"{sym} SKIP orders_paused")
                    continue

                # Configuración por símbolo
                if sym == "MNQ":
                    qty, tp_pts, sl_pts = SIZE_MNQ, TP_MNQ, SL_MNQ
                    trade_symbol = sym
                    trade_contract_id = snap.contract_id
                    trade_tick_size = tick_size[sym]
                elif sym == "ES":
                    # ============ LÓGICA ESPECIAL ES POR DIRECCIÓN ============
                    if snap.signal == "LONG":
                        # ES LONG: usar ES normal
                        qty = ES_LONG_SIZE
                        tp_pts = ES_LONG_TP_POINTS
                        sl_pts = ES_LONG_SL_POINTS
                        trade_symbol = "ES"
                        trade_contract_id = snap.contract_id
                        trade_tick_size = tick_size["ES"]
                        print(f"[ES] 📈 LONG → Usando ES: {qty} contratos, TP={tp_pts}pts, SL={sl_pts}pts")
                    else:  # SHORT
                        # ES SHORT: solo ejecutar en MES (Micro E-mini S&P); si MES no está disponible, mostrar error y no ejecutar
                        if ES_SHORT_USE_MES:
                            if mes_monitor and mes_monitor.contract_id:
                                qty = ES_SHORT_SIZE
                                tp_pts = ES_SHORT_TP_POINTS
                                sl_pts = ES_SHORT_SL_POINTS
                                trade_symbol = "MES"
                                trade_contract_id = mes_monitor.contract_id
                                trade_tick_size = tick_size.get("MES", 0.25)
                                print(f"[ES] 📉 SHORT → Usando MES: {qty} contratos, TP={tp_pts}pts ({int(tp_pts*4)} ticks), SL={sl_pts}pts ({int(sl_pts*4)} ticks)")
                            else:
                                print(f"[ES] ❌ ERROR: Señal SHORT en ES requiere MES pero MES no está disponible (contrato o datos). No se ejecuta la orden.")
                                continue
                        else:
                            # ES_SHORT_USE_MES=false: ejecutar en ES normal
                            qty = ES_SHORT_SIZE
                            tp_pts = ES_SHORT_TP_POINTS
                            sl_pts = ES_SHORT_SL_POINTS
                            trade_symbol = "ES"
                            trade_contract_id = snap.contract_id
                            trade_tick_size = tick_size["ES"]
                            print(f"[ES] 📉 SHORT → Usando ES: {qty} contratos, TP={tp_pts}pts, SL={sl_pts}pts")
                else:
                    qty, tp_pts, sl_pts = SIZE_ES, TP_ES, SL_ES
                    trade_symbol = sym
                    trade_contract_id = snap.contract_id
                    trade_tick_size = tick_size.get(sym, 0.25)

                side = 0 if snap.signal == "LONG" else 1

                print(f"[{sym}] ✅ Señal válida detectada: {snap.signal} → Ejecutando en {trade_symbol}")

                # ============ REPLICATE TO ALL ENABLED ACCOUNTS ============
                for account in enabled_accounts:
                    # Get quantity for this account and symbol
                    account_qty = account.contracts.get(sym, 0)

                    if account_qty <= 0:
                        print(f"  [{account.name}] SKIP: 0 contratos configurados para {sym}")
                        continue

                    # Check for existing position in this account
                    account_px = account.get_api_client()

                    # ⚡ VERIFICACIÓN CRÍTICA POR CUENTA: Comprobar si ESTA CUENTA tiene posición abierta en este símbolo
                    # (sin importar el tag, puede ser manual o de otro sistema)
                    try:
                        account_open_orders = account_px.search_open_orders(account.account_id)
                        account_has_position = False
                        matching_order_ids = []

                        for order in account_open_orders:
                            order_contract_id = order.get("contractId")
                            order_status = order.get("status")

                            # Si la orden es del mismo contrato y está activa
                            if order_contract_id == snap.contract_id and order_status in ("Working", "Pending", "Accepted", "Filled"):
                                account_has_position = True
                                matching_order_ids.append(order.get("orderId"))
                                break

                        _dbg(f"[POSICIONES] {sym} | Cuenta {account.name}: open_orders={len(account_open_orders)}, "
                             f"contract_buscado={snap.contract_id}, account_has_position={account_has_position}"
                             + (f", order_ids_match={matching_order_ids}" if matching_order_ids else ""))

                        if account_has_position:
                            print(f"  [{account.name}] SKIP: Ya tiene posición abierta en {sym} - esperando cierre")
                            _dbg(f"[POSICIONES] {sym} SKIP cuenta {account.name}: ya tiene posición abierta")
                            continue  # ← Solo salta ESTA cuenta, no todas

                        # Límite global por cuenta (no global de la cola completa)
                        active_statuses = ("Working", "Pending", "Accepted", "Filled")
                        active_count_for_account = sum(
                            1 for order in account_open_orders
                            if order.get("status") in active_statuses
                        )
                        pending_count_for_account = sum(
                            1 for t in pending_trades
                            if t.get("account") == account
                        )
                        total_for_account = active_count_for_account + pending_count_for_account
                        _dbg(
                            f"[POSICIONES] {sym} | Cuenta {account.name}: "
                            f"global active={active_count_for_account}, pending={pending_count_for_account}, "
                            f"total={total_for_account}, max={MAX_ACTIVE_POSITIONS}"
                        )
                        if total_for_account >= MAX_ACTIVE_POSITIONS:
                            print(
                                f"  [{account.name}] SKIP: Max active positions reached "
                                f"({total_for_account}/{MAX_ACTIVE_POSITIONS})"
                            )
                            continue

                        # Límite por símbolo/contrato por cuenta
                        active_for_contract = sum(
                            1 for order in account_open_orders
                            if order.get("contractId") == trade_contract_id and order.get("status") in active_statuses
                        )
                        pending_for_contract = sum(
                            1 for t in pending_trades
                            if t.get("account") == account and t.get("contract_id") == trade_contract_id
                        )
                        total_for_contract = active_for_contract + pending_for_contract
                        _dbg(
                            f"[POSICIONES] {sym} | Cuenta {account.name}: "
                            f"contract_id={trade_contract_id}, active_for_contract={active_for_contract}, "
                            f"pending_for_contract={pending_for_contract}, total={total_for_contract}, "
                            f"max_per_symbol={MAX_POSITIONS_PER_SYMBOL}"
                        )
                        if total_for_contract >= MAX_POSITIONS_PER_SYMBOL:
                            print(
                                f"  [{account.name}] SKIP: Max positions for symbol reached "
                                f"({total_for_contract}/{MAX_POSITIONS_PER_SYMBOL})"
                            )
                            continue

                    except Exception as e:
                        _dbg(f"[POSICIONES] Error verificando {sym} para {account.name}: {e}")

                    timestamp_ms = int(time.time() * 1000)
                    tag = f"gocho-{sym}-{account.id}-{timestamp_ms}"

                    # Prechequeo anti-duplicado por tag/contrato (opcional para velocidad)
                    if not DRY_RUN and not SKIP_PRECHECK_DUPLICATES:
                        if _already_open_with_tag(account_px, account.account_id, snap.contract_id, tag_prefix=f"gocho-{sym}-{account.id}-"):
                            print(f"  [{account.name}] SKIP: ya hay una orden abierta con tag gocho-{sym}-{account.id}-*")
                            continue

                    # Para ES, usar la cantidad configurada según dirección, NO la del account
                    if sym == "ES":
                        final_qty = qty  # Usar qty calculada según dirección (ES_LONG_SIZE o ES_SHORT_SIZE)
                    else:
                        final_qty = account_qty  # Usar cantidad configurada en la cuenta

                    print(f"  [{account.name}] ✓ Agregando {final_qty}x{trade_symbol} a cola de ejecución")

                    # Agregar a la lista de trades pendientes
                    pending_trades.append({
                        "symbol": trade_symbol,  # MES si ES SHORT, ES si ES LONG, o símbolo original
                        "original_signal_symbol": sym,  # Símbolo original de la señal (siempre ES o MNQ)
                        "contract_id": trade_contract_id,
                        "side": side,
                        "qty": final_qty,
                        "tag": tag,
                        "tp_points": tp_pts,
                        "sl_points": sl_pts,
                        "tick_size": trade_tick_size,
                        "signal": snap.signal,
                        "as_of": snap.as_of,
                        "ts": ts_now_utc,
                        "event_id": event_id,
                        "account": account,  # Store account reference
                    })

                    # Pequeño delay para asegurar timestamps únicos
                    time.sleep(0.001)

            # Actualizar snapshots en estado compartido para Telegram /status
            with telegram_shared_lock:
                telegram_shared_state["snapshots"] = {
                    s: {
                        "close": snap.close,
                        "ema50": snap.ema50,
                        "ema200": snap.ema200,
                        "signal": snap.signal or "-",
                        "as_of": snap.as_of,
                        "color": snap.color,
                    }
                    for s, snap in snapshots.items()
                }

            # Encolar alertas de setup según nueva lógica (alcista/bajista, horario 9:30 o 9:30-13:30)
            if USE_TG and TG_TOKEN and TG_CHAT:
                tz_ny = ZoneInfo(TRADING_TIMEZONE)
                for sym, snap in snapshots.items():
                    # Parsear hora de cierre de la barra en NY
                    try:
                        bar_close_utc = datetime.fromisoformat(snap.as_of.replace("Z", "+00:00"))
                        bar_close_ny = bar_close_utc.astimezone(tz_ny)
                        bar_hour = bar_close_ny.hour
                        bar_minute = bar_close_ny.minute
                        bar_date = bar_close_ny.date()  # Para trackear por día
                    except Exception as e:
                        _dbg(f"[SETUP_ALERT] Error parseando hora: {e}")
                        continue

                    # Determinar bias (alcista o bajista)
                    is_bullish_bias = snap.ema50 > snap.ema200
                    is_bearish_bias = snap.ema50 < snap.ema200

                    if not (is_bullish_bias or is_bearish_bias):
                        continue  # Sin bias claro, no alertar

                    # Verificar si estamos en la vela de 9:30 (9:15-9:30) o en el rango 9:30-13:30
                    is_0930_bar = (bar_hour == 9 and bar_minute == 30)
                    is_in_trading_window = (bar_hour == 9 and bar_minute >= 30) or \
                                          (9 < bar_hour < 13) or \
                                          (bar_hour == 13 and bar_minute <= 30)

                    if not (is_0930_bar or is_in_trading_window):
                        continue  # Fuera del horario de alertas

                    # Setup Alcista: precio por debajo de EMA50
                    if is_bullish_bias and snap.close < snap.ema50:
                        alert_type = "alcista"
                        if is_0930_bar:
                            # Alerta a las 9:30: siempre encolar (con retraso de 5 min)
                            key_0930 = (sym, alert_type, bar_date, "0930")
                            if key_0930 in alerted_setup_alerts:
                                continue  # Ya se encoló para 9:30 hoy
                            alerted_setup_alerts.add(key_0930)
                            if len(alerted_setup_alerts) > MAX_ALERTED_SET:
                                alerted_setup_alerts.clear()

                            with delayed_ema_lock:
                                delayed_ema_alerts.append({
                                    "sym": sym,
                                    "as_of": snap.as_of,
                                    "ts": time.time(),
                                    "close": snap.close,
                                    "ema50": snap.ema50,
                                    "ema200": snap.ema200,
                                    "setup_type": "alcista",
                                    "bar_time": f"{bar_hour:02d}:{bar_minute:02d}",
                                })
                                if len(delayed_ema_alerts) > MAX_DELAYED_ALERTS:
                                    delayed_ema_alerts.pop(0)
                        else:
                            # Después de 9:30: solo si NO se alertó en 9:30 para este símbolo hoy
                            key_0930_check = (sym, alert_type, bar_date, "0930")
                            if key_0930_check in alerted_setup_alerts:
                                continue  # Ya se alertó a las 9:30, no alertar de nuevo

                            # Encolar alerta para este momento
                            key = (sym, alert_type, bar_date, f"{bar_hour:02d}{bar_minute:02d}")
                            if key in alerted_setup_alerts:
                                continue
                            alerted_setup_alerts.add(key)
                            if len(alerted_setup_alerts) > MAX_ALERTED_SET:
                                alerted_setup_alerts.clear()

                            with delayed_ema_lock:
                                delayed_ema_alerts.append({
                                    "sym": sym,
                                    "as_of": snap.as_of,
                                    "ts": time.time(),
                                    "close": snap.close,
                                    "ema50": snap.ema50,
                                    "ema200": snap.ema200,
                                    "setup_type": "alcista",
                                    "bar_time": f"{bar_hour:02d}:{bar_minute:02d}",
                                })
                                if len(delayed_ema_alerts) > MAX_DELAYED_ALERTS:
                                    delayed_ema_alerts.pop(0)

                    # Setup Bajista: precio por encima de EMA50
                    elif is_bearish_bias and snap.close > snap.ema50:
                        alert_type = "bajista"
                        if is_0930_bar:
                            # Alerta a las 9:30: siempre encolar (con retraso de 5 min)
                            key_0930 = (sym, alert_type, bar_date, "0930")
                            if key_0930 in alerted_setup_alerts:
                                continue  # Ya se encoló para 9:30 hoy
                            alerted_setup_alerts.add(key_0930)
                            if len(alerted_setup_alerts) > MAX_ALERTED_SET:
                                alerted_setup_alerts.clear()

                            with delayed_ema_lock:
                                delayed_ema_alerts.append({
                                    "sym": sym,
                                    "as_of": snap.as_of,
                                    "ts": time.time(),
                                    "close": snap.close,
                                    "ema50": snap.ema50,
                                    "ema200": snap.ema200,
                                    "setup_type": "bajista",
                                    "bar_time": f"{bar_hour:02d}:{bar_minute:02d}",
                                })
                                if len(delayed_ema_alerts) > MAX_DELAYED_ALERTS:
                                    delayed_ema_alerts.pop(0)
                        else:
                            # Después de 9:30: solo si NO se alertó en 9:30 para este símbolo hoy
                            key_0930_check = (sym, alert_type, bar_date, "0930")
                            if key_0930_check in alerted_setup_alerts:
                                continue  # Ya se alertó a las 9:30, no alertar de nuevo

                            # Encolar alerta para este momento
                            key = (sym, alert_type, bar_date, f"{bar_hour:02d}{bar_minute:02d}")
                            if key in alerted_setup_alerts:
                                continue
                            alerted_setup_alerts.add(key)
                            if len(alerted_setup_alerts) > MAX_ALERTED_SET:
                                alerted_setup_alerts.clear()

                            with delayed_ema_lock:
                                delayed_ema_alerts.append({
                                    "sym": sym,
                                    "as_of": snap.as_of,
                                    "ts": time.time(),
                                    "close": snap.close,
                                    "ema50": snap.ema50,
                                    "ema200": snap.ema200,
                                    "setup_type": "bajista",
                                    "bar_time": f"{bar_hour:02d}:{bar_minute:02d}",
                                })
                                if len(delayed_ema_alerts) > MAX_DELAYED_ALERTS:
                                    delayed_ema_alerts.pop(0)

            # FASE 2: Ejecutar todas las órdenes MARKET en paralelo
            if pending_trades:
                print(f"\n{'='*80}")
                print(f"[PARALLEL] 🚀 {len(pending_trades)} señales detectadas - Iniciando ejecución paralela")
                print(f"[PARALLEL] Modo de órdenes: {ORDER_PLACEMENT_MODE.upper()}")
                print(f"{'='*80}\n")

                if DRY_RUN:
                    # Modo DRY_RUN: solo loggear
                    for trade in pending_trades:
                        base_log = {
                            "ts": trade["ts"], "as_of": trade["as_of"], "symbol": trade["symbol"],
                            "contract_id": trade["contract_id"], "signal": trade["signal"],
                            "qty": trade["qty"], "tp_points": trade["tp_points"],
                            "sl_points": trade["sl_points"],
                            "account_id": account_id, "dry_run": True, "tag": trade["tag"]
                        }
                        print(f"[{trade['symbol']}] DRY_RUN -> MARKET {trade['signal']} x{trade['qty']} "
                              f"TP={trade['tp_points']} SL={trade['sl_points']} tag={trade['tag']}")
                        _write_log({**base_log, "event": "DRY_RUN_SIGNAL"})
                        _notify_trade(base_log, dry_run=True)
                        seen_signals.add(trade["event_id"])
                        last_sent_by_symbol[trade["symbol"]] = trade["as_of"]
                    _save_seen(seen_signals)

                elif ORDER_PLACEMENT_MODE == "bracket":
                    # ==================== MODO BRACKET ====================
                    # Enviar órdenes con TP/SL en una sola llamada (usando bracket orders)
                    # OPTIMIZACIÓN: Ejecutar TODAS las cuentas en paralelo simultáneamente

                    def execute_bracket_for_account(trade):
                        """Helper para ejecutar bracket order en paralelo"""
                        account = trade["account"]
                        account_px = account.get_api_client()
                        sym = trade["symbol"]
                        trade_list = [trade]
                        result = _execute_parallel_bracket_orders(account_px, account.account_id, trade_list)
                        result_key = f"{sym}-{account.account_id}"
                        return result_key, result.get(sym, {"success": False, "error": "No result"}), account.name

                    # Ejecutar todas las cuentas en paralelo
                    bracket_results = {}
                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(pending_trades)) as executor:
                        futures = {executor.submit(execute_bracket_for_account, trade): trade for trade in pending_trades}

                        for future in concurrent.futures.as_completed(futures):
                            try:
                                result_key, result, account_name = future.result()
                                bracket_results[result_key] = result
                                bracket_results[result_key]["account_name"] = account_name
                            except Exception as e:
                                trade = futures[future]
                                sym = trade["symbol"]
                                account = trade["account"]
                                result_key = f"{sym}-{account.account_id}"
                                bracket_results[result_key] = {"success": False, "error": str(e), "account_name": account.name}

                    # Logging y notificaciones
                    for trade in pending_trades:
                        sym = trade["symbol"]
                        account = trade["account"]
                        result_key = f"{sym}-{account.account_id}"

                        base_log = {
                            "ts": trade["ts"], "as_of": trade["as_of"], "symbol": sym,
                            "contract_id": trade["contract_id"], "signal": trade["signal"],
                            "qty": trade["qty"], "tp_points": trade["tp_points"],
                            "sl_points": trade["sl_points"],
                            "account_id": account.account_id,
                            "account_name": account.name,
                            "broker": account.broker,
                            "dry_run": False, "tag": trade["tag"]
                        }

                        if result_key in bracket_results and bracket_results[result_key]["success"]:
                            # Trade exitoso con bracket
                            full_details = {
                                **base_log,
                                "event": "BRACKET_ORDER_SENT",
                                "order_id": bracket_results[result_key]["order_id"],
                            }
                            _write_log(full_details)
                            _notify_trade(full_details, dry_run=False)
                            seen_signals.add(trade["event_id"])
                            last_sent_by_symbol[sym] = trade["as_of"]
                            print(f"[{sym}][{account.name}] ✅ Bracket order sent successfully - Order ID: {bracket_results[result_key]['order_id']}")
                        else:
                            # Trade fallido
                            error_msg = bracket_results.get(result_key, {}).get("error", "unknown")
                            error_log = {**base_log, "event": "BRACKET_ORDER_FAILED", "error": error_msg}
                            _write_log(error_log)
                            print(f"[{sym}][{account.name}] ❌ Bracket order failed: {error_msg}")

                    _save_seen(seen_signals)

                    # Dar tiempo al API del broker para actualizar las posiciones
                    # Previene que el sistema cambie a WAITING inmediatamente después de ejecutar
                    if bracket_results:
                        mode = "ACTIVE"
                        print(f"\n[DELAY] ⏱️ Esperando 3 segundos para que el API del broker actualice las posiciones...")
                        time.sleep(3)
                        print(f"[DELAY] ✅ Continuando - las posiciones deberían estar disponibles ahora\n")

                else:
                    # ==================== MODO SEPARATE (original) ====================
                    # Ejecutar órdenes MARKET en paralelo, luego TP/SL por separado
                    market_results = _execute_parallel_market_orders(px, account_id, pending_trades)

                    # FASE 3: Colocar TP/SL para cada trade exitoso (también en paralelo)
                    successful_trades = [t for t in pending_trades if market_results.get(t["symbol"], {}).get("success")]

                    if successful_trades:
                        print(f"\n[PARALLEL] 📊 Colocando TP/SL para {len(successful_trades)} trades exitosos...")

                        def place_tp_sl_for_trade(trade):
                            """Función auxiliar para colocar TP/SL en paralelo"""
                            sym = trade["symbol"]
                            result = market_results[sym]
                            fill_price = result["fill_price"]
                            market_order_id = result.get("order_id")  # Obtener el ID de la orden market

                            if not fill_price:
                                print(f"[{sym}] SKIP TP/SL: No hay fill price")
                                return None

                            try:
                                tp_sl_result = _place_tp_sl_orders(
                                    px=px,
                                    account_id=account_id,
                                    contract_id=trade["contract_id"],
                                    side=trade["side"],
                                    qty=trade["qty"],
                                    fill_price=fill_price,
                                    tp_points=trade["tp_points"],
                                    sl_points=trade["sl_points"],
                                    tick_size=trade["tick_size"],
                                    tag_prefix=trade["tag"],
                                    market_order_id=market_order_id  # Vincular TP/SL a la orden market
                                )
                                return (sym, tp_sl_result)
                            except Exception as e:
                                print(f"[{sym}] ERROR colocando TP/SL: {e}")
                                return (sym, None)

                        # Ejecutar TP/SL en paralelo
                        with concurrent.futures.ThreadPoolExecutor(max_workers=len(successful_trades)) as executor:
                            tp_sl_futures = [executor.submit(place_tp_sl_for_trade, trade)
                                           for trade in successful_trades]
                            tp_sl_results = {}
                            for future in concurrent.futures.as_completed(tp_sl_futures):
                                result = future.result()
                                if result:
                                    sym, tp_sl_data = result
                                    tp_sl_results[sym] = tp_sl_data

                        print(f"[PARALLEL] ✅ TP/SL completados para {len(tp_sl_results)} símbolos")

                        # FASE 4: Logging y notificaciones
                        for trade in pending_trades:
                            sym = trade["symbol"]
                            base_log = {
                                "ts": trade["ts"], "as_of": trade["as_of"], "symbol": sym,
                                "contract_id": trade["contract_id"], "signal": trade["signal"],
                                "qty": trade["qty"], "tp_points": trade["tp_points"],
                                "sl_points": trade["sl_points"],
                                "account_id": account_id, "dry_run": False, "tag": trade["tag"]
                            }

                            if sym in market_results and market_results[sym]["success"]:
                                # Trade exitoso
                                full_details = {
                                    **base_log,
                                    "event": "ORDER_SENT",
                                    "order_id": market_results[sym]["order_id"],
                                    "fill_price": market_results[sym]["fill_price"],
                                }

                                # Agregar info de TP/SL si existe
                                if sym in tp_sl_results and tp_sl_results[sym]:
                                    full_details.update({
                                        "tp_order_id": tp_sl_results[sym]["tp_order_id"],
                                        "sl_order_id": tp_sl_results[sym]["sl_order_id"],
                                        "tp_price": tp_sl_results[sym]["tp_price"],
                                        "sl_price": tp_sl_results[sym]["sl_price"],
                                    })

                                _write_log(full_details)
                                _notify_trade(full_details, dry_run=False)

                                # Marcar como procesada
                                seen_signals.add(trade["event_id"])
                                last_sent_by_symbol[sym] = trade["as_of"]

                                print(f"[{sym}] ✅ Trade completo: Market + TP/SL")
                            else:
                                # Trade fallido
                                error_msg = market_results.get(sym, {}).get("error", "unknown")
                                err = {**base_log, "event": "ORDER_ERROR", "error": error_msg}
                                _write_log(err)
                                _notify_trade(err, dry_run=False)
                                print(f"[{sym}] ❌ Trade fallido: {error_msg}")

                        _save_seen(seen_signals)

                        # Verificación post-orden
                        print(f"\n[PARALLEL] 🔍 Verificación final de órdenes...")
                        time.sleep(1)
                        for trade in successful_trades:
                            sym = trade["symbol"]
                            post_orders = _check_existing_orders_by_tag(px, account_id, trade["tag"])
                            if len(post_orders) > 3:
                                print(f"[{sym}] ⚠️ WARN: {len(post_orders)} órdenes con tag {trade['tag']}, esperado máximo 3")
                                for order in post_orders:
                                    print(f"[{sym}]   - {order.get('customTag')} id={order.get('orderId')} status={order.get('status')}")
                            else:
                                print(f"[{sym}] ✅ Órdenes verificadas: {len(post_orders)}/3")

                        # Dar tiempo al API del broker para actualizar las posiciones
                        print(f"\n[DELAY] ⏱️ Esperando 2 segundos adicionales para que el API actualice las posiciones...")
                        time.sleep(2)
                        print(f"[DELAY] ✅ Continuando - las posiciones deberían estar disponibles ahora\n")
                        mode = "ACTIVE"

                print(f"\n{'='*80}")
                print(f"[PARALLEL] 🏁 Ejecución paralela completada")
                print(f"{'='*80}\n")

        except KeyboardInterrupt:
            print("Bye!")
            break
        except Exception as e:
            print("[LOOP][WARN]", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
