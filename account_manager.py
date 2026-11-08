#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Account Manager - Manage multiple broker accounts for copy trading
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from broker_factory import BrokerFactory


@dataclass
class TradingAccount:
    """Trading account configuration"""
    id: str
    broker: str
    name: str
    enabled: bool
    api_base: str
    api_key_env: str
    user_env: str
    account_id: int
    contracts: Dict[str, int]  # {"MNQ": 4, "ES": 1}
    _api_client: Any = field(default=None, repr=False, init=False)

    def get_api_client(self):
        """Get or create API client for this account"""
        if self._api_client is None:
            config = {
                "api_base": self.api_base,
                "api_key_env": self.api_key_env,
                "user_env": self.user_env
            }
            self._api_client = BrokerFactory.create_client(self.broker, config)
        return self._api_client


@dataclass
class ScannerConfig:
    """Scanner configuration for market data"""
    broker: str
    api_base: str
    api_key_env: str
    user_env: str


class AccountManager:
    """Manage multiple trading accounts across brokers"""

    def __init__(self, config_file: str = "accounts.json"):
        self.config_file = config_file
        self.scanner_config: Optional[ScannerConfig] = None
        self.accounts: List[TradingAccount] = []
        self.load_accounts()

    def load_accounts(self):
        """Load accounts from JSON file"""
        if not os.path.exists(self.config_file):
            print(f"[AccountManager] Creating default {self.config_file}")
            self._create_default_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[AccountManager][ERROR] Failed to load {self.config_file}: {e}")
            self._create_default_config()
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # Load scanner config (filter out extra fields like 'comment')
        scanner = data.get("scanner", {})
        if scanner:
            scanner_fields = {
                "broker": scanner.get("broker", "projectx"),
                "api_base": scanner.get("api_base", "https://api.topstepx.com"),
                "api_key_env": scanner.get("api_key_env", "PROJECTX_API_KEY"),
                "user_env": scanner.get("user_env", "PROJECTX_USER")
            }
            self.scanner_config = ScannerConfig(**scanner_fields)
        else:
            # Default scanner config
            self.scanner_config = ScannerConfig(
                broker="projectx",
                api_base="https://api.topstepx.com",
                api_key_env="PROJECTX_API_KEY",
                user_env="PROJECTX_USER"
            )

        # Load trading accounts (filter to only valid fields)
        self.accounts = []
        for acc_data in data.get("trading_accounts", []):
            try:
                # Filter to only valid TradingAccount fields
                account_fields = {
                    "id": acc_data.get("id"),
                    "broker": acc_data.get("broker"),
                    "name": acc_data.get("name"),
                    "enabled": acc_data.get("enabled"),
                    "api_base": acc_data.get("api_base"),
                    "api_key_env": acc_data.get("api_key_env"),
                    "user_env": acc_data.get("user_env"),
                    "account_id": acc_data.get("account_id"),
                    "contracts": acc_data.get("contracts", {})
                }
                account = TradingAccount(**account_fields)
                self.accounts.append(account)
            except Exception as e:
                print(f"[AccountManager][WARN] Failed to load account: {e}")

    def save_accounts(self):
        """Save accounts to JSON file"""
        data = {
            "scanner": {
                "broker": self.scanner_config.broker,
                "api_base": self.scanner_config.api_base,
                "api_key_env": self.scanner_config.api_key_env,
                "user_env": self.scanner_config.user_env,
                "comment": "Este broker solo se usa para obtener datos de mercado"
            },
            "trading_accounts": []
        }

        for acc in self.accounts:
            acc_dict = {
                "id": acc.id,
                "broker": acc.broker,
                "name": acc.name,
                "enabled": acc.enabled,
                "api_base": acc.api_base,
                "api_key_env": acc.api_key_env,
                "user_env": acc.user_env,
                "account_id": acc.account_id,
                "contracts": acc.contracts
            }
            data["trading_accounts"].append(acc_dict)

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_enabled_accounts(self) -> List[TradingAccount]:
        """Return only enabled trading accounts"""
        return [acc for acc in self.accounts if acc.enabled]

    def get_scanner_client(self):
        """Get API client for scanner (market data only)"""
        if not self.scanner_config:
            raise RuntimeError("Scanner config not loaded")

        config = {
            "api_base": self.scanner_config.api_base,
            "api_key_env": self.scanner_config.api_key_env,
            "user_env": self.scanner_config.user_env
        }
        return BrokerFactory.create_client(self.scanner_config.broker, config)

    def _create_default_config(self):
        """Create default accounts.json if it doesn't exist"""
        # Read from .env for default account ID
        from dotenv import load_dotenv
        load_dotenv()

        default_account_id = int(os.getenv("PRACTICE_ACCOUNT_ID", "0") or 0)
        default_mnq = int(os.getenv("ORDER_SIZE_MNQ", "1"))
        default_es = int(os.getenv("ORDER_SIZE_ES", "1"))

        default_data = {
            "scanner": {
                "broker": "projectx",
                "api_base": "https://api.topstepx.com",
                "api_key_env": "PROJECTX_API_KEY",
                "user_env": "PROJECTX_USER",
                "comment": "Este broker solo se usa para obtener datos de mercado"
            },
            "trading_accounts": [
                {
                    "id": "projectx_main",
                    "broker": "projectx",
                    "name": "ProjectX - Cuenta Principal (configurar antes de habilitar)",
                    "enabled": False,
                    "api_base": "https://api.topstepx.com",
                    "api_key_env": "PROJECTX_API_KEY",
                    "user_env": "PROJECTX_USER",
                    "account_id": default_account_id,
                    "contracts": {
                        "MNQ": default_mnq,
                        "ES": default_es
                    }
                }
            ]
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)

        print(f"[AccountManager] Created default {self.config_file}")
