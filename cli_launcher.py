#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Launcher for TraderDesk V2
Command-line interface for running traders
"""

from __future__ import annotations
import os
import sys
import time
import subprocess
import argparse
from typing import List
from app.services.market_monitor import MarketMonitor


def show_banner():
    """Muestra el banner del sistema"""
    print("=" * 80)
    print("🚀 TRADERDESK V2 - Sistema de Trading Automatizado")
    print("=" * 80)
    print("📊 Símbolos soportados: MNQ, ES")
    print("⚙️  Modos: monitor, trader, start")
    print("=" * 80)


def run_monitor_once():
    """Ejecuta una vez el monitor de mercado (modo original)"""
    for sym in ("MNQ", "ES"):
        mon = MarketMonitor(sym)
        snap, msg = mon.get_snapshot()
        if not snap:
            print(f"[{sym}] WARN:", msg)
            continue
        print(f"[{sym}] {snap.as_of} close={snap.close:.2f} "
              f"ema50={snap.ema50:.2f} ema200={snap.ema200:.2f} color={snap.color}")


def run_monitor_continuous():
    """Ejecuta el monitor continuo (modo original)"""
    print("📊 Iniciando monitor continuo del mercado...")
    print("⏹️  Presiona Ctrl+C para detener")
    while True:
        try:
            run_monitor_once()
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Monitor detenido")
            break


def run_trader(symbols: List[str], mode: str = "dry", verbose: bool = False):
    """Ejecuta el trader unificado para los símbolos especificados"""
    print(f"🚀 Iniciando trader en modo {mode.upper()} para: {', '.join(symbols)}")
    if verbose:
        print("📊 Modo detallado activado - Mostrando información completa cada 15 minutos")
    else:
        print("🔇 Modo silencioso activado - Solo mensajes de órdenes")

    # Configurar variables de entorno
    env = os.environ.copy()
    env["RUN_SYMBOLS"] = ",".join(symbols)
    env["DRY_RUN"] = "false" if mode == "live" else "true"
    env["BAR_TIMESTAMP_MODE"] = "open"
    env["MAX_ACTIVE_POSITIONS"] = "1"
    env["PROCESS_SIGNALS_WHILE_ACTIVE"] = "false"

    # Configurar modo de salida
    env["SHOW_REALTIME_STATUS"] = "true" if verbose else "false"
    env["REALTIME_STATUS_INTERVAL"] = "900" if verbose else "0"  # 15 minutos si verbose

    # Configurar archivos de log separados si hay múltiples símbolos
    if len(symbols) == 1:
        symbol = symbols[0]
        env["TRADES_LOG"] = f"trades_{symbol}.log"
        env["SEEN_SIGNALS_FILE"] = f"seen_signals_{symbol}.json"

    try:
        # Importar y ejecutar el trader unificado
        from unified_trader import main as trader_main
        trader_main()
    except ImportError:
        print("❌ Error: unified_trader.py no encontrado")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Trader detenido")


def start_separate_traders(symbols: List[str], mode: str = "dry", verbose: bool = False):
    """Inicia traders separados para cada símbolo"""
    print(f"🚀 Iniciando traders separados en modo {mode.upper()} para: {', '.join(symbols)}")
    if verbose:
        print("📊 Modo detallado activado - Mostrando información completa cada 15 minutos")
    else:
        print("🔇 Modo silencioso activado - Solo mensajes de órdenes")

    processes = []

    for symbol in symbols:
        print(f"📊 Iniciando trader para {symbol}...")

        # Configurar variables de entorno para este proceso
        env = os.environ.copy()
        env["RUN_SYMBOLS"] = symbol
        env["DRY_RUN"] = "false" if mode == "live" else "true"
        env["BAR_TIMESTAMP_MODE"] = "open"
        env["MAX_ACTIVE_POSITIONS"] = "1"
        env["PROCESS_SIGNALS_WHILE_ACTIVE"] = "false"
        env["TRADES_LOG"] = f"trades_{symbol}.log"
        env["SEEN_SIGNALS_FILE"] = f"seen_signals_{symbol}.json"

        # Configurar modo de salida
        env["SHOW_REALTIME_STATUS"] = "true" if verbose else "false"
        env["REALTIME_STATUS_INTERVAL"] = "900" if verbose else "0"  # 15 minutos si verbose

        try:
            # Lanzar proceso separado
            process = subprocess.Popen(
                [sys.executable, "unified_trader.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            processes.append((symbol, process))
            print(f"✅ Trader {symbol} iniciado (PID: {process.pid})")
            time.sleep(1)  # Pequeña pausa entre lanzamientos

        except Exception as e:
            print(f"❌ Error iniciando trader {symbol}: {e}")

    if not processes:
        print("❌ No se pudo iniciar ningún trader")
        return

    print(f"\n🎯 {len(processes)} traders iniciados:")
    for symbol, process in processes:
        print(f"  - {symbol} (PID: {process.pid})")

    print("\n📋 Comandos útiles:")
    print("  - Ver logs: Get-Content trades_*.log -Tail 20")
    print("  - Ver procesos: Get-Process python")
    print("  - Detener todos: Stop-Process -Name python")

    print("\n⏹️  Presiona Ctrl+C para detener todos los traders...")

    try:
        while True:
            time.sleep(1)
            # Verificar si algún proceso terminó
            for symbol, process in processes:
                if process.poll() is not None:
                    print(f"⚠️  Trader {symbol} terminó inesperadamente")
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo todos los traders...")
        for symbol, process in processes:
            if process.poll() is None:
                print(f"  - Deteniendo trader {symbol}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        print("✅ Todos los traders detenidos")


def run_default_trader():
    """Ejecuta el trader por defecto (modo silencioso)"""
    print("🚀 Iniciando TraderDesk V2 en modo por defecto...")
    print("🔇 Modo silencioso - Solo se mostrarán mensajes al enviar órdenes")
    print("📊 Símbolos: MNQ, ES")
    print("⏹️  Presiona Ctrl+C para detener")

    # Configurar variables de entorno para modo por defecto
    env = os.environ.copy()
    env["RUN_SYMBOLS"] = "MNQ,ES"
    env["DRY_RUN"] = "true"  # Por defecto en simulación
    env["BAR_TIMESTAMP_MODE"] = "open"
    env["MAX_ACTIVE_POSITIONS"] = "1"
    env["PROCESS_SIGNALS_WHILE_ACTIVE"] = "false"
    env["SHOW_REALTIME_STATUS"] = "false"  # Modo silencioso
    env["REALTIME_STATUS_INTERVAL"] = "0"

    try:
        # Importar y ejecutar el trader unificado
        from unified_trader import main as trader_main
        trader_main()
    except ImportError:
        print("❌ Error: unified_trader.py no encontrado")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Trader detenido")


def main():
    """Función principal con interfaz de línea de comandos"""
    # Si no hay argumentos o solo hay --verbose, ejecutar modo por defecto
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--verbose', '-v']):
        show_banner()
        verbose = '--verbose' in sys.argv or '-v' in sys.argv
        if verbose:
            print("📊 Modo por defecto con información detallada activada")
            # Configurar variables de entorno para modo verbose
            env = os.environ.copy()
            env["RUN_SYMBOLS"] = "MNQ,ES"
            env["DRY_RUN"] = "true"
            env["BAR_TIMESTAMP_MODE"] = "open"
            env["MAX_ACTIVE_POSITIONS"] = "1"
            env["PROCESS_SIGNALS_WHILE_ACTIVE"] = "false"
            env["SHOW_REALTIME_STATUS"] = "true"
            env["REALTIME_STATUS_INTERVAL"] = "900"  # 15 minutos

            try:
                from unified_trader import main as trader_main
                trader_main()
            except ImportError:
                print("❌ Error: unified_trader.py no encontrado")
                sys.exit(1)
            except KeyboardInterrupt:
                print("\n🛑 Trader detenido")
        else:
            run_default_trader()
        return

    parser = argparse.ArgumentParser(
        description="TraderDesk V2 - Sistema de Trading Automatizado (CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python cli_launcher.py                          # Modo por defecto (silencioso)
  python cli_launcher.py monitor                  # Monitor continuo (modo original)
  python cli_launcher.py trader --symbols MNQ     # Trader unificado para MNQ (silencioso)
  python cli_launcher.py trader --symbols MNQ --verbose  # Trader unificado con información detallada
  python cli_launcher.py start --symbols MNQ,ES   # Traders separados para ambos (silencioso)
  python cli_launcher.py start --symbols MNQ --mode live --verbose  # Traders separados con información detallada
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["monitor", "trader", "start"],
        help="Comando a ejecutar: monitor (continuo), trader (unificado), start (separados)"
    )

    parser.add_argument(
        "--symbols", "-s",
        default="MNQ,ES",
        help="Símbolos a procesar (default: MNQ,ES)"
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["dry", "live"],
        default="dry",
        help="Modo de operación: dry (simulación) o live (real) (default: dry)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar información detallada cada 15 minutos (EMAs, precios, setups)"
    )

    args = parser.parse_args()

    # Parsear símbolos
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        print("❌ Error: No se especificaron símbolos válidos")
        sys.exit(1)

    # Validar símbolos
    valid_symbols = {"MNQ", "ES"}
    invalid_symbols = set(symbols) - valid_symbols
    if invalid_symbols:
        print(f"❌ Error: Símbolos no válidos: {', '.join(invalid_symbols)}")
        print(f"✅ Símbolos válidos: {', '.join(valid_symbols)}")
        sys.exit(1)

    show_banner()

    if args.command == "monitor":
        run_monitor_continuous()
    elif args.command == "trader":
        run_trader(symbols, args.mode, args.verbose)
    elif args.command == "start":
        start_separate_traders(symbols, args.mode, args.verbose)
    else:
        # Si se especificó un comando pero no es válido, mostrar ayuda
        parser.print_help()


if __name__ == "__main__":
    main()
