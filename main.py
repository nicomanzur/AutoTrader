#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraderDesk V2 - Main Entry Point
Launches GUI by default, CLI with --cli flag
"""

import sys
import os


def show_splash():
    """Show startup splash screen"""
    print("=" * 80)
    print("🚀 TRADERDESK V2 - Professional Trading Management System")
    print("=" * 80)
    print("📊 Starting GUI...")
    print("=" * 80)


def main():
    """Main entry point - GUI by default, CLI with --cli flag"""

    # Check for --cli flag
    if "--cli" in sys.argv:
        # Remove --cli flag and launch CLI
        sys.argv.remove("--cli")

        # Import and run CLI launcher
        try:
            from cli_launcher import main as cli_main
            cli_main()
        except ImportError as e:
            print(f"❌ Error: Could not load CLI launcher: {e}")
            sys.exit(1)
    else:
        # Launch GUI
        try:
            # Check if PySide6 is available
            try:
                import PySide6
            except ImportError:
                print("=" * 80)
                print("❌ ERROR: PySide6 not installed")
                print("=" * 80)
                print("The GUI requires PySide6. Please install it:")
                print("  pip install PySide6>=6.6.0 PySide6-Addons>=6.6.0")
                print()
                print("Alternatively, use CLI mode:")
                print("  python main.py --cli")
                print("=" * 80)
                sys.exit(1)

            # Show splash
            show_splash()

            # Import and run GUI
            from gui_app import main as gui_main
            gui_main()

        except ImportError as e:
            print(f"❌ Error: Could not load GUI: {e}")
            print("\nTry running in CLI mode:")
            print("  python main.py --cli")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
