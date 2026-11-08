#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example Broker API Client - Template para nuevos brokers
"""

import os
import requests
from typing import Dict, Any, Optional


class ExampleBrokerClient:
    """
    Cliente API para Example Broker

    IMPORTANTE: Este es un template. Debes adaptarlo según la API real de tu broker.
    """

    def __init__(self):
        """Initialize the Example Broker API client"""
        # Lee configuración desde .env
        self.base_url = os.getenv("EXAMPLE_BROKER_API_BASE", "https://api.examplebroker.com")
        self.api_key = os.getenv("EXAMPLE_BROKER_API_KEY", "")
        self.username = os.getenv("EXAMPLE_BROKER_USER", "")

        self.session = requests.Session()
        self.token = None

        print(f"[ExampleBrokerClient] base_api={self.base_url} user={self.username[:3]}***")

    def login_with_key(self):
        """
        Login al broker usando API key

        ADAPTAR: Cambia esto según el método de autenticación de tu broker
        """
        if not self.api_key or not self.username:
            raise ValueError("EXAMPLE_BROKER_API_KEY and EXAMPLE_BROKER_USER must be set in .env")

        # Ejemplo de login - ADAPTAR según tu broker
        try:
            url = f"{self.base_url}/api/auth/login"
            payload = {
                "username": self.username,
                "apiKey": self.api_key
            }

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            self.token = data.get("token") or data.get("accessToken")

            if not self.token:
                raise RuntimeError("Login failed: No token received")

            # Set authorization header for future requests
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            })

            print(f"[ExampleBrokerClient] ✓ Login successful")
            return True

        except Exception as e:
            print(f"[ExampleBrokerClient][ERROR] Login failed: {e}")
            raise

    def place_bracket_order(self,
                           account_id: int,
                           contract_id: str,
                           side: int,  # 0=Buy, 1=Sell
                           size: int,
                           tp_ticks: int,
                           sl_ticks: int,
                           tag: Optional[str] = None) -> Dict[str, Any]:
        """
        Place bracket order (Market order with TP and SL)

        ADAPTAR: Cambia esto según el formato de órdenes de tu broker

        Args:
            account_id: ID de la cuenta
            contract_id: ID del contrato/instrumento
            side: 0=Buy/Long, 1=Sell/Short
            size: Cantidad de contratos
            tp_ticks: Take Profit en ticks (puede ser positivo o negativo según broker)
            sl_ticks: Stop Loss en ticks (puede ser positivo o negativo según broker)
            tag: Tag opcional para identificar la orden

        Returns:
            Dict con información de la orden creada
        """
        if not self.token:
            raise RuntimeError("Not logged in. Call login_with_key() first.")

        try:
            url = f"{self.base_url}/api/orders/bracket"

            # Payload de ejemplo - ADAPTAR según tu broker
            payload = {
                "accountId": account_id,
                "contractId": contract_id,
                "orderType": "MARKET",
                "side": "BUY" if side == 0 else "SELL",
                "quantity": size,
                "takeProfitTicks": tp_ticks,
                "stopLossTicks": sl_ticks,
                "customTag": tag
            }

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extraer order_id - ADAPTAR según respuesta de tu broker
            order_id = data.get("orderId") or data.get("id")

            return {
                "success": True,
                "order_id": order_id,
                "message": "Order placed successfully",
                "data": data
            }

        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "order_id": None,
                "error": f"HTTP Error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "order_id": None,
                "error": str(e)
            }

    def search_contracts(self, symbol: str) -> list:
        """
        Buscar contratos por símbolo

        ADAPTAR: Implementar según la API de tu broker
        """
        if not self.token:
            raise RuntimeError("Not logged in")

        try:
            url = f"{self.base_url}/api/contracts/search"
            params = {"symbol": symbol}

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get("contracts", [])

        except Exception as e:
            print(f"[ExampleBrokerClient][ERROR] Contract search failed: {e}")
            return []

    def get_account_positions(self, account_id: int) -> list:
        """
        Obtener posiciones abiertas de una cuenta

        ADAPTAR: Implementar según la API de tu broker
        """
        if not self.token:
            raise RuntimeError("Not logged in")

        try:
            url = f"{self.base_url}/api/accounts/{account_id}/positions"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get("positions", [])

        except Exception as e:
            print(f"[ExampleBrokerClient][ERROR] Get positions failed: {e}")
            return []


# Alias for compatibility
ExampleBroker = ExampleBrokerClient
