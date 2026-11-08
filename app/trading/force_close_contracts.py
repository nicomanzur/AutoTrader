# app/trading/force_close_contracts.py
"""
Cierre forzoso vía TopstepX: Position/closeContract y luego cancelación de
órdenes abiertas en los mismos contratos (Order/cancel).
Compartido por unified_trader y scripts de prueba (ej. temp_close_practice_contracts.py).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple

from app.brokers.projectx_api import ProjectXClient
from app.services.market_monitor import MarketMonitor


def collect_force_close_contract_targets(
    mons: Dict[str, MarketMonitor],
    mes_monitor: Optional[MarketMonitor],
) -> List[Tuple[str, str]]:
    """Pares (etiqueta, contract_id) para MNQ, ES y MES si existe monitor; sin duplicar contract_id."""
    targets: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for sym in ("MNQ", "ES"):
        mon = mons.get(sym)
        cid = mon.contract_id if mon else None
        if cid and cid not in seen:
            targets.append((sym, cid))
            seen.add(cid)
    if mes_monitor and mes_monitor.contract_id and mes_monitor.contract_id not in seen:
        targets.append(("MES", mes_monitor.contract_id))
        seen.add(mes_monitor.contract_id)
    return targets


def _norm_contract_id(cid: Optional[Any]) -> str:
    return str(cid or "").strip()


def _extract_order_id(o: Dict[str, Any]) -> Optional[int]:
    """searchOpen puede devolver orderId o id según versión/capa de la API."""
    raw = o.get("orderId")
    if raw is None:
        raw = o.get("id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# Solo omitir estados claramente terminales. Los brackets (Limit TP / Stop SL)
# a menudo vienen como Inactive, Suspended, Open, etc. y quedaban fuera de la
# lista blanca antigua — no se cancelaban tras closeContract.
_TERMINAL_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        "filled",
        "cancelled",
        "canceled",
        "rejected",
        "complete",
        "completed",
        "done",
        "expired",
        "eliminated",
        "bust",
        "failed",
    }
)


def _order_status_allows_cancel(status: Any) -> bool:
    st = str(status or "").strip().lower()
    if not st:
        return True
    return st not in _TERMINAL_ORDER_STATUSES


def cancel_pending_orders_for_contracts(
    account_px: ProjectXClient,
    account_id: int,
    contract_ids: Set[str],
    reason: str,
) -> int:
    """
    Tras cerrar posición: cancela órdenes aún abiertas en searchOpen para los contract_id dados.
    """
    if not contract_ids:
        return 0
    if not hasattr(account_px, "cancel_order"):
        print(f"[{reason}][WARN] Cliente sin cancel_order; no se cancelan pendientes")
        return 0
    cancel_fn = getattr(account_px, "cancel_order")
    contract_norm: Set[str] = {_norm_contract_id(c) for c in contract_ids}
    cancelled_total = 0
    for _ in range(8):
        try:
            orders = account_px.search_open_orders(account_id)
        except Exception as e:
            print(f"[{reason}][WARN] search_open_orders (fase cancel): {e}")
            break
        pass_cancelled = 0
        for o in orders:
            cid = _norm_contract_id(o.get("contractId"))
            if not cid or cid not in contract_norm:
                continue
            st_raw = o.get("status")
            if not _order_status_allows_cancel(st_raw):
                continue
            oid = _extract_order_id(o)
            if oid is None:
                continue
            try:
                cancel_fn(account_id, oid)
                tag = o.get("customTag") or ""
                st_log = str(st_raw or "").strip() or "?"
                print(
                    f"[{reason}] Cancel OK id={oid} contract={cid} status={st_log} tag={tag}"
                )
                pass_cancelled += 1
            except Exception as e:
                print(f"[{reason}][WARN] Cancel fail id={oid} contract={cid}: {e}")
        cancelled_total += pass_cancelled
        if pass_cancelled == 0:
            break
    if cancelled_total:
        print(f"[{reason}] Órdenes canceladas en contratos objetivo: {cancelled_total}")
    return cancelled_total


def force_close_via_close_contract_api(
    enabled_accounts: list,
    mons: Dict[str, MarketMonitor],
    mes_monitor: Optional[MarketMonitor],
    reason: str = "FORCE_CLOSE_16:00",
) -> None:
    """POST /api/Position/closeContract por cada cuenta y cada contrato MNQ/ES/MES."""
    targets = collect_force_close_contract_targets(mons, mes_monitor)
    if not targets:
        print(f"[{reason}][WARN] Sin contract_id para MNQ/ES/MES; no se llama closeContract")
        return
    contract_id_set: Set[str] = {cid for _, cid in targets}
    print(
        f"[{reason}] Position/closeContract: {len(enabled_accounts)} cuenta(s) × "
        f"{len(targets)} contrato(s)"
    )
    for account in enabled_accounts:
        account_px = account.get_api_client()
        if not hasattr(account_px, "close_contract"):
            print(f"[{reason}][WARN] {account.name}: cliente sin método close_contract; se omite")
            continue
        close_fn = getattr(account_px, "close_contract")
        for label, cid in targets:
            try:
                close_fn(account.account_id, cid)
                print(f"[{reason}] OK {account.name} ({account.account_id}) {label} {cid}")
            except Exception as e:
                print(f"[{reason}][WARN] {account.name} ({account.account_id}) {label}: {e}")
        cancel_pending_orders_for_contracts(
            account_px, account.account_id, contract_id_set, reason=reason
        )


def build_scanner_mons_mes_for_force_close(
    account_mgr: Optional[object] = None,
) -> Tuple[ProjectXClient, Dict[str, MarketMonitor], Optional[MarketMonitor]]:
    """
    Misma resolución de contratos que unified_trader: scanner + RUN_SYMBOLS + MES si aplica.
    """
    from account_manager import AccountManager

    mgr = account_mgr or AccountManager()
    scanner_px = mgr.get_scanner_client()
    scanner_px.login_with_key()

    run_symbols_env = os.getenv("RUN_SYMBOLS", "MNQ,ES")
    run_symbols = [s.strip().upper() for s in run_symbols_env.split(",") if s.strip()]
    if not run_symbols:
        run_symbols = ["MNQ", "ES"]

    mons: Dict[str, MarketMonitor] = {sym: MarketMonitor(sym, px=scanner_px) for sym in run_symbols}

    es_short_use_mes = os.getenv("ES_SHORT_USE_MES", "true").lower() in ("1", "true", "yes")
    mes_monitor: Optional[MarketMonitor] = None
    if es_short_use_mes and "ES" in run_symbols:
        mes_monitor = MarketMonitor("MES", px=scanner_px)
        if not mes_monitor.contract_id:
            mes_monitor = None

    return scanner_px, mons, mes_monitor
