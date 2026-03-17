from datetime import datetime
from typing import Iterator, Any

from domains.forex.simulator.volatility_spike_generator import VolatilitySpikeGenerator
from domains.forex.simulator.liquidity_provider_simulator import LiquidityProviderSimulator
from domains.forex.simulator.order_book_simulator import OrderBookSimulator
from domains.cell.simulator.device_upgrade_generator import DeviceUpgradeGenerator
from domains.cell.simulator.tower_outage_simulator import TowerOutageSimulator
from domains.cib.simulator.supplier_payment_generator import SupplierPaymentGenerator
from domains.cib.simulator.corridor_heatmap_generator import CorridorHeatmapGenerator
from domains.cib.simulator.treasury_fx_exposure_generator import TreasuryFXExposureGenerator
from domains.cib.simulator.invoice_finance_application_generator import InvoiceFinanceApplicationGenerator
from domains.insurance.simulator.fraud_signal_generator import FraudSignalGenerator
from domains.insurance.simulator.claim_settlement_generator import ClaimSettlementGenerator
from domains.insurance.simulator.reinsurance_cession_generator import ReinsuranceCessionGenerator


def _assert_stream(gen: Any) -> None:
    records = list(gen.stream(count=5))
    assert len(records) == 5


def test_volatility_spike_generator_runs():
    gen = VolatilitySpikeGenerator()
    evt = gen.generate_one()
    assert evt.spike_vol >= evt.base_vol
    _assert_stream(gen)


def test_liquidity_provider_simulator_runs():
    gen = LiquidityProviderSimulator()
    q = gen.generate_one()
    assert q.ask > q.bid
    _assert_stream(gen)


def test_order_book_simulator_runs():
    gen = OrderBookSimulator()
    lvl = gen.generate_one()
    assert lvl.price > 0 and lvl.size_musd > 0
    _assert_stream(gen)


def test_device_upgrade_generator_runs():
    gen = DeviceUpgradeGenerator()
    ev = gen.generate_one()
    assert ev.new_device_tier in {"entry-smart", "mid-smart", "flagship"}
    _assert_stream(gen)


def test_tower_outage_simulator_runs():
    gen = TowerOutageSimulator()
    ev = gen.generate_one()
    assert ev.duration_minutes > 0
    _assert_stream(gen)


def test_supplier_payment_generator_runs():
    gen = SupplierPaymentGenerator()
    ev = gen.generate_one()
    assert ev.amount > 0 and ev.currency
    _assert_stream(gen)


def test_corridor_heatmap_generator_runs():
    gen = CorridorHeatmapGenerator()
    ev = gen.generate_one()
    assert ev.transactions >= 0 and ev.volume_usd >= 0
    _assert_stream(gen)


def test_treasury_fx_exposure_generator_runs():
    gen = TreasuryFXExposureGenerator()
    ev = gen.generate_one()
    assert ev.currency_pair and isinstance(ev.hedged_pct, float)
    _assert_stream(gen)


def test_invoice_finance_application_generator_runs():
    gen = InvoiceFinanceApplicationGenerator()
    ev = gen.generate_one()
    assert ev.tenor_days >= 1
    _assert_stream(gen)


def test_fraud_signal_generator_runs():
    gen = FraudSignalGenerator()
    ev = gen.generate_one()
    assert 0.0 <= ev.score <= 1.0
    _assert_stream(gen)


def test_claim_settlement_generator_runs():
    gen = ClaimSettlementGenerator()
    ev = gen.generate_one()
    assert ev.settled_amount > 0
    _assert_stream(gen)


def test_reinsurance_cession_generator_runs():
    gen = ReinsuranceCessionGenerator()
    ev = gen.generate_one()
    assert 0.0 <= ev.ceded_pct <= 1.0
    _assert_stream(gen)
