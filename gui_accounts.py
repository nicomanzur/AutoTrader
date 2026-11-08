#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Accounts Widget - Manage trading accounts across multiple brokers
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QLineEdit, QSpinBox, QPushButton,
    QGroupBox, QScrollArea, QGridLayout, QFrame, QMessageBox,
    QComboBox
)
from PySide6.QtCore import Signal
from account_manager import AccountManager, TradingAccount
from gui_widgets import styled_message_box


class AccountsWidget(QWidget):
    """Widget para gestionar cuentas de trading en múltiples brokers"""

    accounts_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.account_manager = AccountManager()
        except Exception as e:
            print(f"[AccountsWidget][ERROR] Failed to initialize AccountManager: {e}")
            self.account_manager = None

        self.account_widgets = {}  # Track widgets for each account
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Title
        title = QLabel("Trading Accounts Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #FFFFFF;")
        main_layout.addWidget(title)

        if self.account_manager is None:
            error_label = QLabel("ERROR: Failed to load account manager. Check accounts.json")
            error_label.setStyleSheet("color: #FF4444; font-weight: bold; padding: 20px;")
            main_layout.addWidget(error_label)
            return

        # Scanner info (read-only)
        scanner_group = self._create_scanner_info()
        main_layout.addWidget(scanner_group)

        # Scroll area for accounts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: #2b2b2b; border: none; }")

        container = QWidget()
        container.setStyleSheet("background-color: #2b2b2b;")
        self.accounts_layout = QVBoxLayout(container)

        # Load and display accounts
        self.refresh_accounts()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Bottom buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("+ Add Account")
        add_btn.clicked.connect(self.add_new_account)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(add_btn)

        button_layout.addStretch()

        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self.refresh_accounts)
        reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        button_layout.addWidget(reload_btn)

        save_btn = QPushButton("Save All")
        save_btn.clicked.connect(self.save_all_accounts)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(save_btn)

        main_layout.addLayout(button_layout)

    def _create_scanner_info(self):
        """Create scanner configuration display (read-only)"""
        group = QGroupBox("Scanner Configuration (Data Source)")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e1e;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: #4CAF50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
            }
        """)

        layout = QGridLayout()
        scanner = self.account_manager.scanner_config

        broker_label = QLabel("Broker:")
        broker_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(broker_label, 0, 0)

        broker_value = QLabel(scanner.broker.upper())
        broker_value.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        layout.addWidget(broker_value, 0, 1)

        api_label = QLabel("API Base:")
        api_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(api_label, 1, 0)

        api_value = QLabel(scanner.api_base)
        api_value.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(api_value, 1, 1)

        info = QLabel("⚠️  Este broker solo se usa para obtener datos de mercado y generar señales")
        info.setStyleSheet("color: #FFA726; font-style: italic; padding-top: 10px;")
        layout.addWidget(info, 2, 0, 1, 2)

        group.setLayout(layout)
        return group

    def refresh_accounts(self, reload_from_file=True):
        """Reload accounts from file and refresh UI"""
        if self.account_manager is None:
            return

        # Clear existing widgets
        for i in reversed(range(self.accounts_layout.count())):
            widget = self.accounts_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.account_widgets.clear()

        # Only reload from file if requested
        if reload_from_file:
            self.account_manager.load_accounts()

        # Add account rows
        for account in self.account_manager.accounts:
            account_widget = self._create_account_row(account)
            self.accounts_layout.addWidget(account_widget)

        self.accounts_layout.addStretch()

    def _create_account_row(self, account: TradingAccount):
        """Create UI row for one trading account"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
        """)

        layout = QGridLayout(frame)
        row = 0

        # Checkbox + Name
        enabled_cb = QCheckBox(account.name)
        enabled_cb.setChecked(account.enabled)
        enabled_cb.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFFFFF;")
        layout.addWidget(enabled_cb, row, 0, 1, 3)

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                max-width: 80px;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_account(account.id))
        layout.addWidget(delete_btn, row, 3)

        row += 1

        # Name field (editable)
        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(name_label, row, 0)

        name_edit = QLineEdit(account.name)
        name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        layout.addWidget(name_edit, row, 1, 1, 3)

        row += 1

        # Broker + Account ID
        broker_label = QLabel("Broker:")
        broker_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(broker_label, row, 0)

        broker_combo = QComboBox()
        broker_combo.addItems(["projectx", "examplebroker", "broker2", "broker3"])
        broker_combo.setCurrentText(account.broker.lower())
        broker_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #FFFFFF;
                margin-right: 5px;
            }
        """)
        layout.addWidget(broker_combo, row, 1)

        account_id_label = QLabel("Account ID:")
        account_id_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(account_id_label, row, 2)

        account_id_edit = QSpinBox()
        account_id_edit.setMaximum(99999999)
        account_id_edit.setValue(account.account_id)
        account_id_edit.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        layout.addWidget(account_id_edit, row, 3)

        row += 1

        # Contracts
        mnq_label = QLabel("MNQ Contracts:")
        mnq_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(mnq_label, row, 0)

        mnq_spin = QSpinBox()
        mnq_spin.setMaximum(100)
        mnq_spin.setValue(account.contracts.get("MNQ", 0))
        mnq_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        layout.addWidget(mnq_spin, row, 1)

        es_label = QLabel("ES Contracts:")
        es_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(es_label, row, 2)

        es_spin = QSpinBox()
        es_spin.setMaximum(100)
        es_spin.setValue(account.contracts.get("ES", 0))
        es_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        layout.addWidget(es_spin, row, 3)

        # Store widgets for later retrieval
        self.account_widgets[account.id] = {
            "enabled": enabled_cb,
            "name": name_edit,
            "broker": broker_combo,
            "account_id": account_id_edit,
            "mnq": mnq_spin,
            "es": es_spin,
            "account": account
        }

        return frame

    def save_all_accounts(self):
        """Save all account changes to file"""
        if self.account_manager is None:
            return

        try:
            # Update account objects from widgets
            for account_id, widgets in self.account_widgets.items():
                account = widgets["account"]
                account.enabled = widgets["enabled"].isChecked()
                account.name = widgets["name"].text()
                account.broker = widgets["broker"].currentText()
                account.account_id = widgets["account_id"].value()
                account.contracts["MNQ"] = widgets["mnq"].value()
                account.contracts["ES"] = widgets["es"].value()

            # Save to file
            self.account_manager.save_accounts()

            msg = styled_message_box(self, QMessageBox.Icon.Information, "Success",
                                    "Accounts saved successfully!")
            msg.exec()

            self.accounts_changed.emit()

        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error saving accounts: {str(e)}")
            msg.exec()

    def add_new_account(self):
        """Add new trading account"""
        if self.account_manager is None:
            return

        # Create new account with default values
        new_id = f"account_{len(self.account_manager.accounts) + 1}"
        new_account = TradingAccount(
            id=new_id,
            broker="projectx",
            name=f"New Account {len(self.account_manager.accounts) + 1}",
            enabled=False,
            api_base="https://api.topstepx.com",
            api_key_env="PROJECTX_API_KEY",
            user_env="PROJECTX_USER",
            account_id=0,
            contracts={"MNQ": 1, "ES": 1}
        )

        self.account_manager.accounts.append(new_account)
        # Refresh UI without reloading from file (to keep the new account in memory)
        self.refresh_accounts(reload_from_file=False)

    def delete_account(self, account_id: str):
        """Delete an account"""
        if self.account_manager is None:
            return

        msg = styled_message_box(
            self, QMessageBox.Icon.Question, "Confirm Delete",
            f"Are you sure you want to delete this account?",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No
        )
        reply = msg.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self.account_manager.accounts = [acc for acc in self.account_manager.accounts if acc.id != account_id]
            # Refresh UI without reloading from file (to apply the deletion immediately)
            self.refresh_accounts(reload_from_file=False)
