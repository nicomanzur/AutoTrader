#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Broker Factory - Create API clients for different brokers
"""

from typing import Dict, Any
from app.brokers.projectx_api import ProjectXClient
from app.brokers.example_broker_api import ExampleBrokerClient


class BrokerFactory:
    """Factory para crear clientes de diferentes brokers"""

    @staticmethod
    def create_client(broker_type: str, config: Dict[str, Any]):
        """
        Create broker API client based on type

        Args:
            broker_type: "projectx", "examplebroker", "broker2", etc.
            config: Configuration dict with api_base, api_key_env, etc.

        Returns:
            API client instance

        Raises:
            ValueError: If broker type is unknown
            NotImplementedError: If broker is not yet implemented
        """
        broker_type = broker_type.lower().strip()

        if broker_type == "projectx":
            return ProjectXClient()
        elif broker_type == "examplebroker":
            return ExampleBrokerClient()
        elif broker_type == "broker2":
            # Future: return Broker2Client()
            raise NotImplementedError(f"Broker '{broker_type}' not implemented yet")
        else:
            raise ValueError(f"Unknown broker type: '{broker_type}'")

    @staticmethod
    def get_supported_brokers():
        """Get list of supported broker types"""
        return ["projectx", "examplebroker"]
