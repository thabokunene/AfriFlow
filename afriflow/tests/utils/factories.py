from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Protocol
import threading


class ProducerFactory(Protocol):
    def build(self, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]: ...


@dataclass
class BaseBuilder:
    defaults: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def with_(self, **kwargs) -> "BaseBuilder":
        with self._lock:
            new_defaults = dict(self.defaults)
            new_defaults.update(kwargs)
            return type(self)(defaults=new_defaults)

    def build(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.defaults)


@dataclass
class ForexTradeFactory(ProducerFactory):
    def build(self, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
        obj = {
            "trade_id": "FX-ABCDEFGHIJ",
            "currency_pair": "USD/ZAR",
            "trade_type": "SPOT",
            "direction": "BUY",
            "base_amount": 1000.0,
            "quote_amount": 18500.0,
            "rate": 18.5,
            "trade_date": "2026-03-01",
            "value_date": "2026-03-03",
            "client_id": "CLIENT-1",
            "status": "PENDING",
        }
        if overrides:
            obj.update(overrides)
        return obj


@dataclass
class EquitiesOrderFactory(ProducerFactory):
    def build(self, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
        obj = {
            "order_id": "EQ-ORDER-001",
            "symbol": "SBK",
            "side": "BUY",
            "quantity": 100,
            "price": 120.5,
            "status": "NEW",
        }
        if overrides:
            obj.update(overrides)
        return obj


@dataclass
class FixedIncomeTradeFactory(ProducerFactory):
    def build(self, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
        obj = {
            "trade_id": "FI-TRD-001",
            "instrument": "BOND_ZA_2030",
            "notional": 1_000_000.0,
            "yield": 9.5,
            "settlement_date": "2026-03-10",
            "status": "PENDING",
        }
        if overrides:
            obj.update(overrides)
        return obj


@dataclass
class CommoditiesContractFactory(ProducerFactory):
    def build(self, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
        obj = {
            "contract_id": "CMD-001",
            "commodity": "GOLD",
            "quantity": 50,
            "unit": "oz",
            "price": 2200.0,
            "status": "OPEN",
        }
        if overrides:
            obj.update(overrides)
        return obj
