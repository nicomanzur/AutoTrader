#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraderDesk v2 - Main GUI Application
Professional trading management interface using PySide6
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QStatusBar, QMessageBox,
    QFileDialog, QSplitter, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QAction

from gui_widgets import (
    LogViewer, ProcessController, EnvFormEditor,
    RawTextEditor, OrderTestWidget, styled_message_box
)
from gui_accounts import AccountsWidget
from gui_config import (
    WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    APP_STYLESHEET, TRADER_COMMANDS
)


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.process_controllers: Dict[str, ProcessController] = {}
        self.init_ui()
        self.load_trade_history()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        # Set window icon
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _icon_path = os.path.join(_script_dir, "assets", "traderdesk_icon.png")
        if os.path.exists(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))

        # Apply stylesheet
        self.setStyleSheet(APP_STYLESHEET)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        main_layout.addWidget(self.tabs)

        # Create tabs
        self.create_traders_tab()
        self.create_accounts_tab()
        self.create_logs_tab()
        self.create_config_tab()
        self.create_manual_orders_tab()
        self.create_trade_history_tab()

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Menu bar
        self.create_menu_bar()

        # Update status bar with trader states
        self.update_status_bar()
        QTimer.singleShot(1000, self.update_status_bar)

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        refresh_logs_action = QAction("Refresh Logs", self)
        refresh_logs_action.setShortcut("F5")
        refresh_logs_action.triggered.connect(self.refresh_logs)
        view_menu.addAction(refresh_logs_action)

        clear_logs_action = QAction("Clear Logs", self)
        clear_logs_action.triggered.connect(self.clear_logs)
        view_menu.addAction(clear_logs_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_traders_tab(self):
        """Create the traders control tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Header
        header = QLabel("Trader Process Management")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Description
        desc = QLabel("Start and stop trading processes. Monitor their status and runtime.")
        desc.setStyleSheet("padding: 0 10px 10px 10px; color: #AAAAAA;")
        layout.addWidget(desc)

        # Process controllers
        for process_name, config in TRADER_COMMANDS.items():
            controller = ProcessController(
                process_name=process_name,
                script_path=config["script"],
                display_name=config["name"]
            )
            controller.log_message.connect(self.add_log_message)
            controller.status_changed.connect(self.on_trader_status_changed)

            self.process_controllers[process_name] = controller
            layout.addWidget(controller)

        layout.addStretch()

        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        start_all_btn = QPushButton("Start All")
        start_all_btn.clicked.connect(self.start_all_traders)
        button_layout.addWidget(start_all_btn)

        stop_all_btn = QPushButton("Stop All")
        stop_all_btn.setProperty("class", "stop-button")
        stop_all_btn.clicked.connect(self.stop_all_traders)
        button_layout.addWidget(stop_all_btn)

        layout.addLayout(button_layout)

        self.tabs.addTab(widget, "Traders")

    def create_accounts_tab(self):
        """Create the accounts management tab"""
        self.accounts_widget = AccountsWidget()
        self.accounts_widget.accounts_changed.connect(self.on_accounts_changed)
        self.tabs.addTab(self.accounts_widget, "Accounts")

    def create_logs_tab(self):
        """Create the logs viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Header with controls
        header_layout = QHBoxLayout()

        label = QLabel("Live Logs")
        label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        header_layout.addWidget(label)

        header_layout.addStretch()

        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QPushButton("Auto-scroll: ON")
        self.auto_scroll_checkbox.setCheckable(True)
        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.clicked.connect(self.toggle_auto_scroll)
        header_layout.addWidget(self.auto_scroll_checkbox)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(clear_btn)

        # Save button
        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_logs)
        header_layout.addWidget(save_btn)

        layout.addLayout(header_layout)

        # Log viewer
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer)

        # Add initial message
        self.log_viewer.append_colored_text(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] GUI Started")

        self.tabs.addTab(widget, "Logs")

    def create_config_tab(self):
        """Create the configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sub-tabs for form and raw text
        config_tabs = QTabWidget()

        # Form editor
        self.env_form_editor = EnvFormEditor()
        self.env_form_editor.config_changed.connect(self.on_config_changed)
        config_tabs.addTab(self.env_form_editor, "Form View")

        # Raw text editor
        self.env_text_editor = RawTextEditor()
        self.env_text_editor.config_changed.connect(self.on_config_changed)
        config_tabs.addTab(self.env_text_editor, "Raw Text")

        layout.addWidget(config_tabs)

        self.tabs.addTab(widget, "Configuration")

    def create_manual_orders_tab(self):
        """Create the manual orders testing tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Header
        header = QLabel("Manual Order Testing")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Description
        desc = QLabel(
            "Send test bracket orders to your practice account. "
            "Orders will use TP/SL values from configuration."
        )
        desc.setStyleSheet("padding: 0 10px 10px 10px; color: #AAAAAA;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Order widget
        self.order_widget = OrderTestWidget()
        self.order_widget.order_sent.connect(self.add_log_message)
        layout.addWidget(self.order_widget)

        self.tabs.addTab(widget, "Manual Orders")

    def create_trade_history_tab(self):
        """Create the trade history viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Header with controls
        header_layout = QHBoxLayout()

        label = QLabel("Trade History")
        label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        header_layout.addWidget(label)

        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_trade_history)
        header_layout.addWidget(refresh_btn)

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_trade_history)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        # Trade history table
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(8)
        self.trade_table.setHorizontalHeaderLabels([
            "Timestamp", "Symbol", "Signal", "Qty", "Fill Price",
            "TP Price", "SL Price", "Status"
        ])
        self.trade_table.horizontalHeader().setStretchLastSection(True)
        self.trade_table.setAlternatingRowColors(True)
        self.trade_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.trade_table)

        self.tabs.addTab(widget, "Trade History")

    @Slot(str, str)
    def on_trader_status_changed(self, trader_name: str, status: str):
        """Handle trader status changes"""
        self.update_status_bar()
        self.add_log_message(f"[STATUS] {trader_name}: {status}")

    @Slot()
    def on_config_changed(self):
        """Handle configuration changes"""
        self.add_log_message("[CONFIG] Configuration file updated")
        self.statusBar.showMessage("Configuration updated", 3000)

    @Slot()
    def on_accounts_changed(self):
        """Handle accounts configuration changes"""
        self.add_log_message("[ACCOUNTS] Trading accounts configuration updated")
        self.statusBar.showMessage("Accounts configuration saved", 3000)

    @Slot(str)
    def add_log_message(self, message: str):
        """Add a message to the log viewer"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_viewer.append_colored_text(f"[{timestamp}] {message}")

    def start_all_traders(self):
        """Start all trader processes"""
        for controller in self.process_controllers.values():
            controller.start_process()

    def stop_all_traders(self):
        """Stop all trader processes"""
        msg = styled_message_box(
            self,
            QMessageBox.Icon.Question,
            "Confirm Stop All",
            "Are you sure you want to stop all traders?",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No
        )
        reply = msg.exec()

        if reply == QMessageBox.StandardButton.Yes:
            for controller in self.process_controllers.values():
                controller.stop_process()

    def toggle_auto_scroll(self):
        """Toggle auto-scroll in log viewer"""
        enabled = self.auto_scroll_checkbox.isChecked()
        self.log_viewer.auto_scroll = enabled
        self.auto_scroll_checkbox.setText(f"Auto-scroll: {'ON' if enabled else 'OFF'}")

    def clear_logs(self):
        """Clear the log viewer"""
        msg = styled_message_box(
            self,
            QMessageBox.Icon.Question,
            "Confirm Clear",
            "Are you sure you want to clear all logs?",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No
        )
        reply = msg.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self.log_viewer.clear_log()
            self.add_log_message("[SYSTEM] Logs cleared")

    def save_logs(self):
        """Save logs to a file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs",
            f"traderdesk_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if filename:
            if self.log_viewer.save_log(filename):
                msg = styled_message_box(self, QMessageBox.Icon.Information, "Success",
                                        f"Logs saved to: {filename}")
                msg.exec()
                self.add_log_message(f"[SYSTEM] Logs saved to: {filename}")
            else:
                msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                        "Failed to save logs")
                msg.exec()

    def refresh_logs(self):
        """Refresh the logs display"""
        self.add_log_message("[SYSTEM] Logs refreshed")

    def load_trade_history(self):
        """Load trade history from trades.log"""
        trades_file = "trades.log"

        if not os.path.exists(trades_file):
            self.trade_table.setRowCount(0)
            return

        try:
            trades: List[dict] = []
            with open(trades_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            trade = json.loads(line)
                            trades.append(trade)
                        except json.JSONDecodeError:
                            continue

            # Sort by timestamp (newest first)
            trades.sort(key=lambda x: x.get('ts', ''), reverse=True)

            # Populate table
            self.trade_table.setRowCount(len(trades))

            for row, trade in enumerate(trades):
                # Timestamp
                ts = trade.get('ts', '')
                self.trade_table.setItem(row, 0, QTableWidgetItem(ts))

                # Symbol
                symbol = trade.get('symbol', '')
                self.trade_table.setItem(row, 1, QTableWidgetItem(symbol))

                # Signal
                signal = trade.get('signal', '')
                self.trade_table.setItem(row, 2, QTableWidgetItem(signal))

                # Quantity
                qty = str(trade.get('qty', ''))
                self.trade_table.setItem(row, 3, QTableWidgetItem(qty))

                # Fill Price
                fill_price = trade.get('fill_price', '')
                self.trade_table.setItem(row, 4, QTableWidgetItem(str(fill_price) if fill_price else '--'))

                # TP Price
                tp_price = trade.get('tp_price', '')
                self.trade_table.setItem(row, 5, QTableWidgetItem(str(tp_price) if tp_price else '--'))

                # SL Price
                sl_price = trade.get('sl_price', '')
                self.trade_table.setItem(row, 6, QTableWidgetItem(str(sl_price) if sl_price else '--'))

                # Status (event type)
                event = trade.get('event', 'UNKNOWN')
                status_text = event.replace('_', ' ').title()
                self.trade_table.setItem(row, 7, QTableWidgetItem(status_text))

            # Resize columns to content
            self.trade_table.resizeColumnsToContents()

        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error loading trade history: {str(e)}")
            msg.exec()

    def export_trade_history(self):
        """Export trade history to CSV"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Trade History",
            f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Header
                headers = []
                for col in range(self.trade_table.columnCount()):
                    headers.append(self.trade_table.horizontalHeaderItem(col).text())
                f.write(','.join(headers) + '\n')

                # Data
                for row in range(self.trade_table.rowCount()):
                    row_data = []
                    for col in range(self.trade_table.columnCount()):
                        item = self.trade_table.item(row, col)
                        text = item.text() if item else ''
                        # Escape commas and quotes
                        if ',' in text or '"' in text:
                            text = '"' + text.replace('"', '""') + '"'
                        row_data.append(text)
                    f.write(','.join(row_data) + '\n')

            msg = styled_message_box(self, QMessageBox.Icon.Information, "Success",
                                    f"Trade history exported to: {filename}")
            msg.exec()
            self.add_log_message(f"[EXPORT] Trade history exported to: {filename}")

        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error exporting: {str(e)}")
            msg.exec()

    def update_status_bar(self):
        """Update the status bar with trader states"""
        running_count = 0
        for controller in self.process_controllers.values():
            if controller.process and controller.process.state() == controller.process.ProcessState.Running:
                running_count += 1

        total_count = len(self.process_controllers)
        self.statusBar.showMessage(f"Traders: {running_count}/{total_count} running")

    def show_about(self):
        """Show about dialog"""
        msg = styled_message_box(
            self,
            QMessageBox.Icon.Information,
            "About TraderDesk v2",
            "<h2>TraderDesk v2</h2>"
            "<p>Professional Trading Management System</p>"
            "<p>Version: 2.0</p>"
            "<p>Built with PySide6</p>"
            "<br>"
            "<p>© 2024 TraderDesk</p>"
        )
        msg.exec()

    def closeEvent(self, event):
        """Handle window close event"""
        # Check if any traders are running
        running_traders = []
        for name, controller in self.process_controllers.items():
            if controller.process and controller.process.state() == controller.process.ProcessState.Running:
                running_traders.append(controller.display_name)

        if running_traders:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Traders en Ejecucion")
            msg.setText("Los siguientes traders estan ejecutandose:")
            msg.setInformativeText("\n".join(f"  - {name}" for name in running_traders) +
                                 "\n\nDeseas detenerlos y salir?")

            # Aplicar estilo para texto negro en el mensaje
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #F0F0F0;
                }
                QMessageBox QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)

            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            msg.button(QMessageBox.StandardButton.Yes).setText("Si, detener y salir")
            msg.button(QMessageBox.StandardButton.No).setText("No, salir sin detener")
            msg.button(QMessageBox.StandardButton.Cancel).setText("Cancelar")
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)

            reply = msg.exec()

            if reply == QMessageBox.StandardButton.Yes:
                # Stop all traders and wait for them to finish
                for controller in self.process_controllers.values():
                    if controller.process and controller.process.state() == controller.process.ProcessState.Running:
                        controller.stop_process()
                        # Wait up to 3 seconds for process to stop
                        controller.process.waitForFinished(3000)
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                # Exit without stopping (processes will be orphaned)
                event.accept()
            else:
                # Cancel exit
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point for the GUI application"""
    app = QApplication(sys.argv)
    app.setApplicationName("TraderDesk v2")
    app.setOrganizationName("TraderDesk")

    # Set application icon (for taskbar, alt-tab, etc.)
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _icon_path = os.path.join(_script_dir, "assets", "traderdesk_icon.png")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
