#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom GUI Widgets for TraderDesk
Reusable components for the trading GUI
"""

import os
import sys
import re
from typing import Dict, Optional, Callable
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QGroupBox, QScrollArea, QFileDialog, QMessageBox,
    QTabWidget, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal, QProcess, QTimer, Slot
from PySide6.QtGui import QTextCursor, QColor, QFont

from gui_config import LOG_COLORS, STATUS_COLORS, ENV_CONFIG


def styled_message_box(parent, icon, title, text, buttons=None, default_button=None, informative_text=None):
    """Create a QMessageBox with consistent black text styling"""
    msg = QMessageBox(parent)
    msg.setIcon(icon)
    msg.setWindowTitle(title)
    msg.setText(text)

    if informative_text:
        msg.setInformativeText(informative_text)

    if buttons:
        msg.setStandardButtons(buttons)

    if default_button:
        msg.setDefaultButton(default_button)

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
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
    """)

    return msg


class LogViewer(QTextEdit):
    """Custom text widget for displaying colored logs with auto-scroll"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Set monospace font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.auto_scroll = True

    def append_colored_text(self, text: str):
        """Append text with color coding based on keywords"""
        if not text.strip():
            return

        # Determine color based on content
        text_lower = text.lower()
        color = LOG_COLORS["default"]

        if any(keyword in text_lower for keyword in ["error", "failed", "exception"]):
            color = LOG_COLORS["error"]
        elif any(keyword in text_lower for keyword in ["warn", "warning"]):
            color = LOG_COLORS["warn"]
        elif any(keyword in text_lower for keyword in ["success", "✅", "completed"]):
            color = LOG_COLORS["success"]
        elif any(keyword in text_lower for keyword in ["[order]", "order_sent"]):
            color = LOG_COLORS["order"]
        elif any(keyword in text_lower for keyword in ["bracket", "[bracket"]):
            color = LOG_COLORS["bracket"]
        elif any(keyword in text_lower for keyword in ["parallel", "[parallel"]):
            color = LOG_COLORS["parallel"]
        elif any(keyword in text_lower for keyword in ["info", "[info]"]):
            color = LOG_COLORS["info"]
        elif any(keyword in text_lower for keyword in ["debug", "[debug"]):
            color = LOG_COLORS["debug"]

        # Insert colored text
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f'<span style="color: {color};">{self.escape_html(text)}</span><br>')

        # Auto-scroll if enabled
        if self.auto_scroll:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))

    def clear_log(self):
        """Clear all log content"""
        self.clear()

    def save_log(self, filename: str):
        """Save log content to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            return True
        except Exception as e:
            print(f"Error saving log: {e}")
            return False


class ProcessController(QWidget):
    """Widget to control a single trader process"""

    status_changed = Signal(str, str)  # (process_name, status)
    log_message = Signal(str)  # Log message to emit

    def __init__(self, process_name: str, script_path: str, display_name: str, parent=None):
        super().__init__(parent)
        self.process_name = process_name
        self.script_path = script_path
        self.display_name = display_name
        self.process: Optional[QProcess] = None
        self.start_time: Optional[datetime] = None

        self.init_ui()

    def init_ui(self):
        """Initialize the UI components"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Status indicator (colored circle)
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS['stopped']}; font-size: 20px;")
        self.status_label.setFixedWidth(30)
        layout.addWidget(self.status_label)

        # Process name
        name_label = QLabel(self.display_name)
        name_label.setMinimumWidth(200)
        layout.addWidget(name_label)

        # Status text
        self.status_text = QLabel("Stopped")
        self.status_text.setMinimumWidth(100)
        layout.addWidget(self.status_text)

        # Runtime display
        self.runtime_label = QLabel("--:--:--")
        self.runtime_label.setMinimumWidth(80)
        layout.addWidget(self.runtime_label)

        # PID display
        self.pid_label = QLabel("PID: --")
        self.pid_label.setMinimumWidth(80)
        layout.addWidget(self.pid_label)

        layout.addStretch()

        # Start button
        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self.start_process)
        layout.addWidget(self.start_btn)

        # Stop button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setProperty("class", "stop-button")
        self.stop_btn.clicked.connect(self.stop_process)
        layout.addWidget(self.stop_btn)

        # Runtime update timer
        self.runtime_timer = QTimer(self)
        self.runtime_timer.timeout.connect(self.update_runtime)
        self.runtime_timer.start(1000)  # Update every second

    def start_process(self):
        """Start the trader process"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.log_message.emit(f"[{self.process_name}] Already running")
            return

        # Create new process
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.stateChanged.connect(self.handle_state_change)
        self.process.finished.connect(self.handle_finished)

        # Set working directory to the script's directory
        script_dir = os.path.dirname(os.path.abspath(self.script_path))
        if not script_dir:
            script_dir = os.getcwd()
        self.process.setWorkingDirectory(script_dir)

        # Detectar y usar el venv si existe (.venv-v2 en Windows, venv en Linux/RPi)
        python_cmd = "python"
        venv_python = None

        # Buscar .venv-v2 (Windows) o venv (Linux/RPi)
        for venv_name in [".venv-v2", "venv"]:
            venv_path = os.path.join(script_dir, venv_name)
            if os.path.exists(venv_path):
                if sys.platform == "win32":
                    venv_python = os.path.join(venv_path, "Scripts", "python.exe")
                else:
                    venv_python = os.path.join(venv_path, "bin", "python")
                if os.path.exists(venv_python):
                    python_cmd = venv_python
                    self.log_message.emit(f"[{self.process_name}] Using venv: {venv_name}")
                    break

        # Start process with unbuffered output (-u flag)
        args = ["-u", self.script_path]  # -u for unbuffered output
        self.log_message.emit(f"[{self.process_name}] Command: {python_cmd} -u {self.script_path}")
        self.log_message.emit(f"[{self.process_name}] Working directory: {script_dir}")

        self.start_time = datetime.now()

        self.process.start(python_cmd, args)

        # Wait for process to actually start
        if not self.process.waitForStarted(5000):  # 5 second timeout
            self.log_message.emit(f"[{self.process_name}] ERROR: Process failed to start")
            self.update_status("stopped", "Failed to start")
            return

        # Process started successfully
        pid = self.process.processId()
        self.log_message.emit(f"[{self.process_name}] Process started successfully (PID: {pid})")

        # Update UI immediately after confirming start
        self.update_status("running", "Running")
        self.pid_label.setText(f"PID: {pid}")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_process(self):
        """Stop the trader process"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.log_message.emit(f"[{self.process_name}] Stopping...")
            self.process.terminate()

            # Force kill after 5 seconds if not terminated
            QTimer.singleShot(5000, lambda: self.process.kill() if self.process.state() == QProcess.ProcessState.Running else None)

    @Slot()
    def handle_stdout(self):
        """Handle standard output from process"""
        if self.process:
            data = self.process.readAllStandardOutput()
            text = bytes(data).decode('utf-8', errors='ignore')
            for line in text.splitlines():
                if line.strip():
                    self.log_message.emit(f"[{self.process_name}] {line}")

    @Slot()
    def handle_stderr(self):
        """Handle standard error from process"""
        if self.process:
            data = self.process.readAllStandardError()
            text = bytes(data).decode('utf-8', errors='ignore')
            for line in text.splitlines():
                if line.strip():
                    self.log_message.emit(f"[{self.process_name}] ERROR: {line}")

    @Slot(QProcess.ProcessState)
    def handle_state_change(self, state: QProcess.ProcessState):
        """Handle process state changes"""
        if state == QProcess.ProcessState.Running:
            pid = self.process.processId()
            self.update_status("running", "Running")
            self.pid_label.setText(f"PID: {pid}")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif state == QProcess.ProcessState.NotRunning:
            self.update_status("stopped", "Stopped")
            self.pid_label.setText("PID: --")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.start_time = None

    @Slot(int, QProcess.ExitStatus)
    def handle_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        """Handle process completion"""
        if exit_code == 0:
            self.log_message.emit(f"[{self.process_name}] Exited normally")
        else:
            self.log_message.emit(f"[{self.process_name}] Exited with code {exit_code}")

    def update_status(self, status: str, text: str):
        """Update status indicator and text"""
        color = STATUS_COLORS.get(status, STATUS_COLORS["stopped"])
        self.status_label.setStyleSheet(f"color: {color}; font-size: 20px;")
        self.status_text.setText(text)
        self.status_changed.emit(self.process_name, status)

    def update_runtime(self):
        """Update runtime display"""
        if self.start_time and self.process and self.process.state() == QProcess.ProcessState.Running:
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.runtime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.runtime_label.setText("--:--:--")


class EnvFormEditor(QWidget):
    """Form-based editor for .env configuration"""

    config_changed = Signal()

    def __init__(self, env_file_path: str = ".env", parent=None):
        super().__init__(parent)
        self.env_file_path = env_file_path
        self.fields: Dict[str, QWidget] = {}

        self.init_ui()
        self.load_env_file()

    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)

        # Scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background-color: #FFFFFF; border: none; }")

        # Container widget
        container = QWidget()
        container.setStyleSheet("background-color: #FFFFFF;")
        container_layout = QVBoxLayout(container)

        # Create groups for each category
        for category, fields in ENV_CONFIG.items():
            group = QGroupBox(category)
            group.setStyleSheet("""
                QGroupBox {
                    background-color: #F5F5F5;
                    border: 1px solid #CCCCCC;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 15px;
                    font-weight: bold;
                    color: #000000;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 5px 10px;
                    background-color: #E0E0E0;
                    color: #000000;
                }
            """)
            group_layout = QGridLayout()
            group_layout.setColumnStretch(1, 1)

            row = 0
            for field_name, field_config in fields.items():
                # Label
                label = QLabel(field_config["label"] + ("*" if field_config["required"] else "") + ":")
                label.setToolTip(field_config["tooltip"])
                label.setStyleSheet("color: #000000; font-weight: bold; background-color: transparent;")  # Negro sobre fondo claro
                group_layout.addWidget(label, row, 0)

                # Input widget based on type
                field_type = field_config["type"]

                if field_type == "boolean":
                    widget = QCheckBox()
                    widget.setChecked(field_config["default"].lower() in ("true", "1", "yes"))
                    widget.setStyleSheet("QCheckBox { color: #000000; }")
                elif field_type == "number":
                    widget = QSpinBox()
                    widget.setMaximum(99999999)
                    widget.setValue(int(field_config["default"]) if field_config["default"] else 0)
                    widget.setStyleSheet("QSpinBox { background-color: #FFFFFF; color: #000000; border: 1px solid #CCCCCC; }")
                elif field_type == "float":
                    widget = QDoubleSpinBox()
                    widget.setMaximum(999999.0)
                    widget.setDecimals(2)
                    widget.setValue(float(field_config["default"]) if field_config["default"] else 0.0)
                    widget.setStyleSheet("QDoubleSpinBox { background-color: #FFFFFF; color: #000000; border: 1px solid #CCCCCC; }")
                elif field_type == "choice":
                    widget = QComboBox()
                    widget.addItems(field_config.get("choices", []))
                    widget.setCurrentText(field_config["default"])
                    widget.setStyleSheet("QComboBox { background-color: #FFFFFF; color: #000000; border: 1px solid #CCCCCC; }")
                elif field_type == "password":
                    widget = QLineEdit()
                    widget.setEchoMode(QLineEdit.EchoMode.Password)
                    widget.setText(field_config["default"])
                    widget.setStyleSheet("QLineEdit { background-color: #FFFFFF; color: #000000; border: 1px solid #CCCCCC; }")
                else:  # text
                    widget = QLineEdit()
                    widget.setText(field_config["default"])
                    widget.setStyleSheet("QLineEdit { background-color: #FFFFFF; color: #000000; border: 1px solid #CCCCCC; }")

                widget.setToolTip(field_config["tooltip"])
                group_layout.addWidget(widget, row, 1)

                # Store reference
                self.fields[field_name] = widget

                row += 1

            group.setLayout(group_layout)
            container_layout.addWidget(group)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        load_btn = QPushButton("Reload from File")
        load_btn.clicked.connect(self.load_env_file)
        button_layout.addWidget(load_btn)

        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_env_file)
        button_layout.addWidget(save_btn)

        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)
        button_layout.addWidget(backup_btn)

        main_layout.addLayout(button_layout)

    def load_env_file(self):
        """Load values from .env file"""
        if not os.path.exists(self.env_file_path):
            msg = styled_message_box(self, QMessageBox.Icon.Warning, "File Not Found",
                                    f".env file not found at: {self.env_file_path}")
            msg.exec()
            return

        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")

                        if key in self.fields:
                            widget = self.fields[key]
                            if isinstance(widget, QCheckBox):
                                widget.setChecked(value.lower() in ("true", "1", "yes"))
                            elif isinstance(widget, QSpinBox):
                                widget.setValue(int(value) if value else 0)
                            elif isinstance(widget, QDoubleSpinBox):
                                widget.setValue(float(value) if value else 0.0)
                            elif isinstance(widget, QComboBox):
                                widget.setCurrentText(value)
                            elif isinstance(widget, QLineEdit):
                                widget.setText(value)

            # Solo emitir señal, no mostrar mensaje de éxito
            self.config_changed.emit()

        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error loading .env file: {str(e)}")
            msg.exec()

    def save_env_file(self):
        """Save current form values to .env file"""
        try:
            lines = []
            lines.append("# TraderDesk v2 Configuration")
            lines.append(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

            for category, fields in ENV_CONFIG.items():
                lines.append(f"# {category}")
                for field_name, field_config in fields.items():
                    widget = self.fields[field_name]

                    if isinstance(widget, QCheckBox):
                        value = "true" if widget.isChecked() else "false"
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        value = str(widget.value())
                    elif isinstance(widget, QComboBox):
                        value = widget.currentText()
                    elif isinstance(widget, QLineEdit):
                        value = widget.text()
                    else:
                        value = ""

                    lines.append(f"{field_name}={value}")
                lines.append("")

            with open(self.env_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            msg = styled_message_box(self, QMessageBox.Icon.Information, "Success",
                                    "Configuration saved successfully")
            msg.exec()
            self.config_changed.emit()

        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error saving .env file: {str(e)}")
            msg.exec()

    def create_backup(self):
        """Create a backup of the current .env file"""
        if not os.path.exists(self.env_file_path):
            msg = styled_message_box(self, QMessageBox.Icon.Warning, "File Not Found",
                                    ".env file not found")
            msg.exec()
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f".env.backup_{timestamp}"

        try:
            with open(self.env_file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            msg = styled_message_box(self, QMessageBox.Icon.Information, "Success",
                                    f"Backup created: {backup_path}")
            msg.exec()
        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error creating backup: {str(e)}")
            msg.exec()


class RawTextEditor(QWidget):
    """Raw text editor for .env file"""

    config_changed = Signal()

    def __init__(self, env_file_path: str = ".env", parent=None):
        super().__init__(parent)
        self.env_file_path = env_file_path

        self.init_ui()
        self.load_file()

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)

        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_edit.setFont(font)
        layout.addWidget(self.text_edit)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self.load_file)
        button_layout.addWidget(reload_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_file)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def load_file(self):
        """Load .env file content"""
        if os.path.exists(self.env_file_path):
            try:
                with open(self.env_file_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setPlainText(f.read())
            except Exception as e:
                msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                        f"Error loading file: {str(e)}")
                msg.exec()
        else:
            self.text_edit.setPlainText("# .env file not found\n# Create configuration here")

    def save_file(self):
        """Save content to .env file"""
        try:
            with open(self.env_file_path, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            msg = styled_message_box(self, QMessageBox.Icon.Information, "Success",
                                    "File saved successfully")
            msg.exec()
            self.config_changed.emit()
        except Exception as e:
            msg = styled_message_box(self, QMessageBox.Icon.Critical, "Error",
                                    f"Error saving file: {str(e)}")
            msg.exec()


class OrderTestWidget(QWidget):
    """Widget for testing manual bracket orders"""

    order_sent = Signal(str)  # Message signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel("Manual Order Testing (sends real bracket orders to practice account)")
        info_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        layout.addWidget(info_label)

        # Form
        form_layout = QGridLayout()

        # Symbol
        form_layout.addWidget(QLabel("Symbol:"), 0, 0)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["MNQ", "ES"])
        form_layout.addWidget(self.symbol_combo, 0, 1)

        # Direction
        form_layout.addWidget(QLabel("Direction:"), 1, 0)
        direction_layout = QHBoxLayout()
        self.buy_radio = QPushButton("BUY (Long)")
        self.buy_radio.setCheckable(True)
        self.buy_radio.setChecked(True)
        self.sell_radio = QPushButton("SELL (Short)")
        self.sell_radio.setCheckable(True)
        self.buy_radio.clicked.connect(lambda: self.sell_radio.setChecked(False))
        self.sell_radio.clicked.connect(lambda: self.buy_radio.setChecked(False))
        direction_layout.addWidget(self.buy_radio)
        direction_layout.addWidget(self.sell_radio)
        form_layout.addLayout(direction_layout, 1, 1)

        # Quantity
        form_layout.addWidget(QLabel("Quantity:"), 2, 0)
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(100)
        self.qty_spin.setValue(1)
        form_layout.addWidget(self.qty_spin, 2, 1)

        layout.addLayout(form_layout)

        # Status label
        self.status_label = QLabel("Ready to send order")
        self.status_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.status_label)

        # Send button
        self.send_btn = QPushButton("Send Bracket Order")
        self.send_btn.setFixedHeight(50)
        self.send_btn.clicked.connect(self.send_order)
        layout.addWidget(self.send_btn)

        # Warning
        warning = QLabel("⚠ This will send a REAL order to your practice account")
        warning.setStyleSheet("color: #FF4444; font-size: 9pt;")
        layout.addWidget(warning)

        layout.addStretch()

    def send_order(self):
        """Send a manual bracket order"""
        from app.brokers.projectx_api import ProjectXClient
        from dotenv import load_dotenv
        import time

        load_dotenv()

        symbol = self.symbol_combo.currentText()
        direction = 0 if self.buy_radio.isChecked() else 1
        direction_name = "BUY" if direction == 0 else "SELL"
        qty = self.qty_spin.value()

        # Disable button
        self.send_btn.setEnabled(False)
        self.status_label.setText("Sending order...")
        self.status_label.setStyleSheet("color: #FF9800;")

        try:
            # Get contract IDs and configuration
            contract_id = os.getenv(f"CONTRACT_ID_{symbol}")
            account_id = int(os.getenv("PRACTICE_ACCOUNT_ID", "0") or 0)

            # Get TP/SL points
            if symbol == "MNQ":
                tp_points = float(os.getenv("TP_POINTS_MNQ", "60"))
                sl_points = float(os.getenv("SL_POINTS_MNQ", "30"))
                tick_size = 0.25
            else:  # ES
                tp_points = float(os.getenv("TP_POINTS_ES", "8"))
                sl_points = float(os.getenv("SL_POINTS_ES", "4"))
                tick_size = 0.25

            # Calculate ticks
            tp_ticks_base = int(tp_points / tick_size)
            sl_ticks_base = int(sl_points / tick_size)

            # Adjust signs
            if direction == 0:  # LONG
                tp_ticks = tp_ticks_base
                sl_ticks = -sl_ticks_base
            else:  # SHORT
                tp_ticks = -tp_ticks_base
                sl_ticks = sl_ticks_base

            # Connect to API
            px = ProjectXClient()
            px.login_with_key()

            # Generate unique tag
            tag = f"gui_test_{symbol}_{int(time.time()*1000)}"

            # Send order
            result = px.place_bracket_order(
                account_id=account_id,
                contract_id=contract_id,
                side=direction,
                size=qty,
                tp_ticks=tp_ticks,
                sl_ticks=sl_ticks,
                customTag=tag
            )

            if result.get("success"):
                order_id = result.get("orderId")
                msg = f"✅ Order sent successfully!\nSymbol: {symbol}, Direction: {direction_name}, Qty: {qty}\nOrder ID: {order_id}"
                self.status_label.setText("Order sent successfully!")
                self.status_label.setStyleSheet("color: #4CAF50;")
                self.order_sent.emit(msg)
                msgbox = styled_message_box(self, QMessageBox.Icon.Information, "Success", msg)
                msgbox.exec()
            else:
                error_msg = result.get("errorMessage", "Unknown error")
                msg = f"❌ Order failed: {error_msg}"
                self.status_label.setText("Order failed")
                self.status_label.setStyleSheet("color: #FF4444;")
                self.order_sent.emit(msg)
                msgbox = styled_message_box(self, QMessageBox.Icon.Critical, "Error", msg)
                msgbox.exec()

        except Exception as e:
            msg = f"❌ Error: {str(e)}"
            self.status_label.setText("Error sending order")
            self.status_label.setStyleSheet("color: #FF4444;")
            self.order_sent.emit(msg)
            msgbox = styled_message_box(self, QMessageBox.Icon.Critical, "Error", msg)
            msgbox.exec()

        finally:
            # Re-enable button
            self.send_btn.setEnabled(True)
