#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Configuration for TraderDesk
Defines colors, styles, window settings, and configuration mappings
"""

# Window Settings
WINDOW_TITLE = "TraderDesk v2 - Trading Management System"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

# Log Colors (RGB format for QTextEdit)
LOG_COLORS = {
    "error": "#FF4444",      # Red
    "warn": "#FFA500",       # Orange
    "warning": "#FFA500",    # Orange
    "success": "#4CAF50",    # Green
    "info": "#2196F3",       # Blue
    "debug": "#9E9E9E",      # Gray
    "order": "#00BCD4",      # Cyan
    "bracket": "#9C27B0",    # Purple
    "parallel": "#FF9800",   # Deep Orange
    "default": "#FFFFFF"     # White
}

# Status Colors
STATUS_COLORS = {
    "running": "#4CAF50",    # Green
    "stopped": "#F44336",    # Red
    "starting": "#FF9800",   # Orange
    "error": "#9C27B0"       # Purple
}

# Process Command Mappings
TRADER_COMMANDS = {
    "unified_trader": {
        "script": "unified_trader.py",
        "name": "Estrategia Gocho",
        "description": "Sistema principal de trading con estrategia EMA50/EMA200",
        "requires_symbols": True
    }
}

# .env Configuration Fields (grouped by category)
ENV_CONFIG = {
    "API Configuration": {
        "PROJECTX_API_BASE": {
            "label": "URL Base del API",
            "type": "text",
            "default": "https://api.topstepx.com",
            "required": True,
            "tooltip": "URL base del API de ProjectX"
        },
        "PROJECTX_API_KEY": {
            "label": "Clave API",
            "type": "password",
            "default": "",
            "required": True,
            "tooltip": "Tu clave API de ProjectX"
        },
        "PRACTICE_ACCOUNT_ID": {
            "label": "ID de Cuenta de Práctica",
            "type": "number",
            "default": "0",
            "required": True,
            "tooltip": "ID de cuenta de práctica para trading"
        }
    },

    "IDs de Contratos": {
        "CONTRACT_ID_MNQ": {
            "label": "ID Contrato MNQ",
            "type": "text",
            "default": "CON.F.US.MNQ.Z25",
            "required": True,
            "tooltip": "ID de contrato para futuros Micro Nasdaq"
        },
        "CONTRACT_ID_ES": {
            "label": "ID Contrato ES",
            "type": "text",
            "default": "CON.F.US.EP.Z25",
            "required": True,
            "tooltip": "ID de contrato para futuros S&P 500"
        }
    },

    "Configuración de Trading": {
        "DRY_RUN": {
            "label": "Modo Prueba (Dry Run)",
            "type": "boolean",
            "default": "true",
            "required": False,
            "tooltip": "Activar modo prueba (sin órdenes reales)"
        },
        "ONLY_PRACTICE_ACCOUNT": {
            "label": "Usar Solo Cuenta de Práctica",
            "type": "boolean",
            "default": "true",
            "required": False,
            "tooltip": "Enviar todas las órdenes solo a la cuenta de práctica (PRACTICE_ACCOUNT_ID / 'Prueba'/'Practice')"
        },
        "ORDER_SIZE_MNQ": {
            "label": "Tamaño de Orden MNQ",
            "type": "number",
            "default": "1",
            "required": False,
            "tooltip": "Número de contratos para trades de MNQ"
        },
        "ORDER_SIZE_ES": {
            "label": "Tamaño de Orden ES",
            "type": "number",
            "default": "1",
            "required": False,
            "tooltip": "Número de contratos para trades de ES"
        },
        "TP_POINTS_MNQ": {
            "label": "Take Profit MNQ (puntos)",
            "type": "float",
            "default": "60",
            "required": False,
            "tooltip": "Take profit en puntos para MNQ"
        },
        "SL_POINTS_MNQ": {
            "label": "Stop Loss MNQ (puntos)",
            "type": "float",
            "default": "30",
            "required": False,
            "tooltip": "Stop loss en puntos para MNQ"
        },
        "TP_POINTS_ES": {
            "label": "Take Profit ES (puntos)",
            "type": "float",
            "default": "8",
            "required": False,
            "tooltip": "Take profit en puntos para ES"
        },
        "SL_POINTS_ES": {
            "label": "Stop Loss ES (puntos)",
            "type": "float",
            "default": "4",
            "required": False,
            "tooltip": "Stop loss en puntos para ES"
        },
        "ORDER_PLACEMENT_MODE": {
            "label": "Modo de Colocación de Órdenes",
            "type": "choice",
            "choices": ["bracket", "separate"],
            "default": "bracket",
            "required": False,
            "tooltip": "bracket = órdenes OCO, separate = TP/SL manual"
        }
    },

    "Límites de Posiciones": {
        "MAX_ACTIVE_POSITIONS": {
            "label": "Máx. Posiciones Activas (Global)",
            "type": "number",
            "default": "1",
            "required": False,
            "tooltip": "Máximo total de posiciones activas en todos los símbolos"
        },
        "MAX_POSITIONS_PER_SYMBOL": {
            "label": "Máx. Posiciones Por Símbolo",
            "type": "number",
            "default": "1",
            "required": False,
            "tooltip": "Máximo de posiciones por símbolo individual"
        },
        "PROCESS_SIGNALS_WHILE_ACTIVE": {
            "label": "Procesar Señales Con Posiciones Activas",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Continuar procesando señales con posiciones activas"
        }
    },

    "Horarios de Trading": {
        "ENABLE_TRADING_HOURS": {
            "label": "Activar Control de Horarios",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Activar restricción de horarios de trading"
        },
        "TRADING_TIMEZONE": {
            "label": "Zona Horaria de Trading",
            "type": "text",
            "default": "America/New_York",
            "required": False,
            "tooltip": "Zona horaria para horarios de trading (ej: America/New_York)"
        },
        "TRADING_START_TIME": {
            "label": "Hora de Inicio (HH:MM)",
            "type": "text",
            "default": "09:30",
            "required": False,
            "tooltip": "Hora de inicio para abrir nuevas posiciones (formato 24h: HH:MM)"
        },
        "TRADING_END_TIME": {
            "label": "Hora Final de Nuevas Posiciones (HH:MM)",
            "type": "text",
            "default": "13:30",
            "required": False,
            "tooltip": "Hora límite para abrir nuevas posiciones (formato 24h: HH:MM)"
        },
        "FORCE_CLOSE_TIME": {
            "label": "Hora de Cierre Forzoso (HH:MM)",
            "type": "text",
            "default": "16:00",
            "required": False,
            "tooltip": "Hora para cerrar forzosamente todas las posiciones (formato 24h: HH:MM)"
        },
        "AUTO_CLOSE_AT_END": {
            "label": "Cerrar Posiciones al Final",
            "type": "boolean",
            "default": "true",
            "required": False,
            "tooltip": "Cerrar automáticamente todas las posiciones a la hora de cierre forzoso"
        }
    },

    "Temporización y Sincronización": {
        "BAR_MINUTES": {
            "label": "Intervalo de Velas (minutos)",
            "type": "number",
            "default": "15",
            "required": False,
            "tooltip": "Intervalo de velas en minutos"
        },
        "ALIGN_TIMEZONE": {
            "label": "Zona Horaria",
            "type": "text",
            "default": "UTC",
            "required": False,
            "tooltip": "Zona horaria para alineación de velas"
        },
        "BAR_TIMESTAMP_MODE": {
            "label": "Modo de Marca de Tiempo",
            "type": "choice",
            "choices": ["open", "close"],
            "default": "open",
            "required": False,
            "tooltip": "Cómo se marcan temporalmente las velas"
        },
        "CLOSE_LAG_SEC": {
            "label": "Retraso de Cierre (segundos)",
            "type": "float",
            "default": "1.2",
            "required": False,
            "tooltip": "Retraso tras cierre de vela antes de procesar"
        },
        "CLOSE_RETRY_COUNT": {
            "label": "Cantidad de Reintentos",
            "type": "number",
            "default": "15",
            "required": False,
            "tooltip": "Número de reintentos para obtener datos de vela"
        },
        "CLOSE_RETRY_INTERVAL": {
            "label": "Intervalo de Reintentos (segundos)",
            "type": "float",
            "default": "0.5",
            "required": False,
            "tooltip": "Retraso entre reintentos"
        }
    },

    "Monitoreo": {
        "ACTIVE_MONITOR_INTERVAL": {
            "label": "Intervalo de Monitoreo Activo (seg)",
            "type": "number",
            "default": "5",
            "required": False,
            "tooltip": "Segundos entre verificaciones de posición"
        },
        "SHOW_REALTIME_STATUS": {
            "label": "Mostrar Estado en Tiempo Real",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Activar actualizaciones de estado del mercado en tiempo real"
        },
        "REALTIME_STATUS_INTERVAL": {
            "label": "Intervalo de Estado en Tiempo Real (seg)",
            "type": "number",
            "default": "900",
            "required": False,
            "tooltip": "Segundos entre actualizaciones de estado"
        }
    },

    "Notificaciones": {
        "NOTIFY_TELEGRAM": {
            "label": "Activar Telegram",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Enviar notificaciones vía Telegram"
        },
        "TELEGRAM_BOT_TOKEN": {
            "label": "Token de Bot de Telegram",
            "type": "password",
            "default": "",
            "required": False,
            "tooltip": "Tu token de bot de Telegram"
        },
        "TELEGRAM_CHAT_ID": {
            "label": "ID de Chat de Telegram",
            "type": "text",
            "default": "",
            "required": False,
            "tooltip": "Tu ID de chat de Telegram"
        },
        "NOTIFY_EMAIL": {
            "label": "Activar Email",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Enviar notificaciones vía email"
        },
        "SMTP_HOST": {
            "label": "Servidor SMTP",
            "type": "text",
            "default": "",
            "required": False,
            "tooltip": "Nombre del servidor SMTP"
        },
        "SMTP_PORT": {
            "label": "Puerto SMTP",
            "type": "number",
            "default": "587",
            "required": False,
            "tooltip": "Puerto del servidor SMTP"
        },
        "SMTP_USER": {
            "label": "Usuario SMTP",
            "type": "text",
            "default": "",
            "required": False,
            "tooltip": "Nombre de usuario para autenticación SMTP"
        },
        "SMTP_PASS": {
            "label": "Contraseña SMTP",
            "type": "password",
            "default": "",
            "required": False,
            "tooltip": "Contraseña para autenticación SMTP"
        },
        "EMAIL_FROM": {
            "label": "Email Desde",
            "type": "text",
            "default": "",
            "required": False,
            "tooltip": "Dirección de email del remitente"
        },
        "EMAIL_TO": {
            "label": "Email Para",
            "type": "text",
            "default": "",
            "required": False,
            "tooltip": "Dirección de email del destinatario"
        },
        "NOTIFY_ON_DRY_RUN": {
            "label": "Notificar en Modo Prueba",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Enviar notificaciones incluso en modo prueba"
        }
    },

    "Avanzado": {
        "DEBUG_TRADE": {
            "label": "Modo de Depuración de Trades",
            "type": "boolean",
            "default": "false",
            "required": False,
            "tooltip": "Activar depuración detallada de trades"
        },
        "DEBUG_LOG": {
            "label": "Archivo de Log de Debug",
            "type": "text",
            "default": "debug.log",
            "required": False,
            "tooltip": "Archivo donde se guardan los mensajes de debug (vacío = solo consola)"
        },
        "SEEN_SIGNALS_FILE": {
            "label": "Archivo de Señales Vistas",
            "type": "text",
            "default": "seen_signals.json",
            "required": False,
            "tooltip": "Archivo para rastrear señales procesadas"
        },
        "TRADES_LOG": {
            "label": "Archivo de Log de Trades",
            "type": "text",
            "default": "trades.log",
            "required": False,
            "tooltip": "Archivo para registrar historial de trades"
        }
    }
}

# Qt Stylesheet
APP_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}

QTabWidget::pane {
    border: 1px solid #3a3a3a;
    background: #252525;
}

QTabBar::tab {
    background: #2d2d2d;
    color: #ffffff;
    padding: 10px 20px;
    border: 1px solid #3a3a3a;
    border-bottom: none;
}

QTabBar::tab:selected {
    background: #252525;
    border-bottom: 2px solid #4CAF50;
}

QTabBar::tab:hover {
    background: #353535;
}

QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #45a049;
}

QPushButton:pressed {
    background-color: #3d8b40;
}

QPushButton:disabled {
    background-color: #555555;
    color: #888888;
}

QPushButton.stop-button {
    background-color: #F44336;
}

QPushButton.stop-button:hover {
    background-color: #da190b;
}

QTextEdit {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10pt;
}

QLabel {
    color: #ffffff;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3a3a3a;
    padding: 5px;
    border-radius: 3px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4CAF50;
}

QCheckBox {
    color: #ffffff;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    background: #2d2d2d;
}

QCheckBox::indicator:checked {
    background: #4CAF50;
    border: 1px solid #4CAF50;
}

QGroupBox {
    color: #ffffff;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 5px 10px;
    background-color: #2d2d2d;
}

QScrollBar:vertical {
    background: #2d2d2d;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #555555;
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #666666;
}

QStatusBar {
    background: #2d2d2d;
    color: #ffffff;
}
"""
