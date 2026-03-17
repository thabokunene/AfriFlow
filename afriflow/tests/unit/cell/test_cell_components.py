"""
Unit tests for cell domain processors and simulators.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

import afriflow.domains.cell.simulator.airtime_generator as airtime_module
import afriflow.domains.cell.simulator.sim_activation_generator as sim_activation_module
from afriflow.domains.cell.simulator.airtime_generator import AirtimeGenerator, AirtimeTopUp
from afriflow.domains.cell.simulator.device_upgrade_generator import DeviceUpgradeGenerator, DeviceUpgradeEvent
from afriflow.domains.cell.simulator.sim_activation_generator import SIMActivationGenerator, SIMActivation
from afriflow.domains.cell.simulator.usage_generator import UsageGenerator, UsageRecord

from afriflow.domains.cell.processing.flink.expansion_detector import ExpansionDetector, Processor as ExpansionProcessor
from afriflow.domains.cell.processing.flink.momo_flow_aggregator import Processor as MomoFlowProcessor
from afriflow.domains.cell.processing.flink.workforce_growth_detector import Processor as WorkforceGrowthProcessor
from afriflow.domains.shared.interfaces import BaseProcessor


def _dt_utc(dt: datetime) -> bool:
    return dt.tzinfo == timezone.utc


class TestSIMActivationGenerator:
    def test_generate_activation_valid(self) -> None:
        gen = SIMActivationGenerator(seed=42)
        act = gen.generate_activation(
            corporate_client_id="CLIENT-001",
            country="NG",
            activation_type="new_enterprise",
        )
        assert isinstance(act, SIMActivation)
        assert act.country == "NG"
        assert act.sim_count > 0
        assert _dt_utc(act.activated_at)
        assert sum(act.department_breakdown.values()) == act.sim_count

    def test_invalid_activation_type_raises(self) -> None:
        gen = SIMActivationGenerator()
        with pytest.raises(Exception):
            gen.generate_activation(
                corporate_client_id="CLIENT-001",
                country="ZA",
                activation_type="invalid_type",
            )

    def test_generate_expansion_batch(self) -> None:
        gen = SIMActivationGenerator(seed=123)
        batches = gen.generate_expansion_batch(
            corporate_client_id="CLIENT-002",
            country="ZA",
            new_countries=["NG", "KE"],
        )
        assert len(batches) == 3
        assert all(isinstance(b, SIMActivation) for b in batches)
        assert all(_dt_utc(b.activated_at) for b in batches)

    def test_stream_activations_counts(self) -> None:
        gen = SIMActivationGenerator(seed=7)
        stream = gen.stream_activations(days=3, activations_per_day=5)
        acts = list(stream)
        assert len(acts) >= 3  # at least one per day
        assert all(_dt_utc(a.activated_at) for a in acts)

    def test_activation_generic_account_manager_for_unknown_country(self) -> None:
        gen = SIMActivationGenerator(seed=21)
        act = gen.generate_activation(
            corporate_client_id="CLIENT-777",
            country="BJ",
            activation_type="sme_starter",
        )
        assert isinstance(act.account_manager_id, str)
        assert act.account_manager_id.startswith("AM-BJ-")

    def test_activation_replacement_department_general_only(self) -> None:
        gen = SIMActivationGenerator(seed=33)
        act = gen.generate_activation(
            corporate_client_id="CLIENT-555",
            country="ZA",
            activation_type="replacement",
        )
        assert set(act.department_breakdown.keys()) == {"general"}

    def test_stream_activations_business_hours_skew(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixed_now = datetime(2026, 4, 9, 12, 0, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return fixed_now.replace(tzinfo=None)
                return fixed_now.astimezone(tz)

        monkeypatch.setattr(sim_activation_module, "datetime", FixedDateTime)

        gen = SIMActivationGenerator(seed=7)
        acts = list(
            gen.stream_activations(
                days=1,
                activations_per_day=120,
                business_hours=(7, 17),
                business_hours_only=True,
            )
        )
        business = [a for a in acts if 7 <= a.activated_at.hour <= 17]
        off_hours = [a for a in acts if a.activated_at.hour < 7 or a.activated_at.hour > 17]
        assert len(acts) >= 1
        assert len(off_hours) == 0
        assert len(business) == len(acts)

    def test_stream_activations_off_hours_present_when_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fixed_now = datetime(2026, 4, 9, 12, 0, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return fixed_now.replace(tzinfo=None)
                return fixed_now.astimezone(tz)

        monkeypatch.setattr(sim_activation_module, "datetime", FixedDateTime)

        gen = SIMActivationGenerator(seed=7)
        acts = list(
            gen.stream_activations(
                days=1,
                activations_per_day=250,
                business_hours=(7, 17),
                business_hours_only=False,
                off_hours_rate=0.20,
            )
        )
        business = [a for a in acts if 7 <= a.activated_at.hour <= 17]
        off_hours = [a for a in acts if a.activated_at.hour < 7 or a.activated_at.hour > 17]
        assert len(acts) >= 1
        assert len(business) >= 1
        assert len(off_hours) >= 1
        skew = len(business) / len(acts)
        assert 0.0 < skew < 1.0


class TestAirtimeGenerator:
    def test_generate_topup_valid(self) -> None:
        gen = AirtimeGenerator(seed=11)
        t = gen.generate_topup(country="KE")
        assert isinstance(t, AirtimeTopUp)
        assert t.country == "KE"
        assert t.amount_local > 0
        assert t.amount_usd > 0
        assert _dt_utc(t.timestamp)

    def test_generate_topup_invalid_country(self) -> None:
        gen = AirtimeGenerator()
        with pytest.raises(Exception):
            gen.generate_topup(country="XX")

    def test_generate_corporate_bulk(self) -> None:
        gen = AirtimeGenerator(seed=3)
        bulk = gen.generate_corporate_bulk(
            corporate_client_id="CORP-ABC",
            country="NG",
            employee_count=450,
        )
        assert len(bulk) == max(1, 450 // 200)
        assert all(t.is_corporate_airtime for t in bulk)
        assert all(_dt_utc(t.timestamp) for t in bulk)

    def test_stream_topups_utc_and_min_count(self) -> None:
        gen = AirtimeGenerator(seed=17)
        items = list(gen.stream_topups(country="ZA", days=1, daily_count=25))
        assert len(items) >= 25
        assert all(_dt_utc(t.timestamp) for t in items)

    def test_stream_topups_month_end_boost_boundary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fixed_now = datetime(2026, 1, 26, 12, 0, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return fixed_now.replace(tzinfo=None)
                return fixed_now.astimezone(tz)

        monkeypatch.setattr(airtime_module, "datetime", FixedDateTime)

        gen = AirtimeGenerator(seed=17)
        items = list(
            gen.stream_topups(
                country="KE",
                days=2,
                daily_count=100,
                month_end_start_day=25,
                month_end_boost_factor=1.3,
            )
        )
        assert all(_dt_utc(t.timestamp) for t in items)

        day_1 = (fixed_now - timedelta(days=2)).date()
        day_2 = (fixed_now - timedelta(days=1)).date()
        counts = {day_1: 0, day_2: 0}
        for t in items:
            if t.timestamp.date() in counts:
                counts[t.timestamp.date()] += 1
        assert counts[day_1] == 100
        assert counts[day_2] == 130
        assert len(items) == 230

    def test_stream_topups_boost_factor_and_start_day_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return fixed_now.replace(tzinfo=None)
                return fixed_now.astimezone(tz)

        monkeypatch.setattr(airtime_module, "datetime", FixedDateTime)

        gen = AirtimeGenerator(seed=17)
        items = list(
            gen.stream_topups(
                country="KE",
                days=2,
                daily_count=80,
                month_end_start_day=28,
                month_end_boost_factor=1.5,
            )
        )
        day_1 = (fixed_now - timedelta(days=2)).date()
        day_2 = (fixed_now - timedelta(days=1)).date()
        counts = {day_1: 0, day_2: 0}
        for t in items:
            if t.timestamp.date() in counts:
                counts[t.timestamp.date()] += 1
        assert counts[day_1] == 80
        assert counts[day_2] == 120
        assert len(items) == 200

    def test_stream_topups_invalid_month_end_config_raises(self) -> None:
        gen = AirtimeGenerator(seed=17)
        with pytest.raises(ValueError):
            list(
                gen.stream_topups(
                    country="ZA",
                    days=1,
                    daily_count=10,
                    month_end_start_day=25,
                    month_end_boost_factor=0.9,
                )
            )
        with pytest.raises(ValueError):
            list(
                gen.stream_topups(
                    country="ZA",
                    days=1,
                    daily_count=10,
                    month_end_start_day=0,
                    month_end_boost_factor=1.3,
                )
            )


class TestDeviceUpgradeGenerator:
    def test_device_upgrade_event(self) -> None:
        gen = DeviceUpgradeGenerator()
        ev = gen.generate_one(country="ZA")
        assert isinstance(ev, DeviceUpgradeEvent)
        assert _dt_utc(ev.timestamp)
        tiers = ["feature", "entry-smart", "mid-smart", "flagship"]
        assert ev.old_device_tier in tiers
        assert ev.new_device_tier in tiers
        assert tiers.index(ev.new_device_tier) >= tiers.index(ev.old_device_tier)

    def test_msisdn_validation(self) -> None:
        gen = DeviceUpgradeGenerator()
        with pytest.raises(ValueError):
            gen.generate_one(msisdn="NOTNUMERIC")

    def test_device_upgrade_stream(self) -> None:
        gen = DeviceUpgradeGenerator()
        events = list(gen.stream(count=7))
        assert len(events) == 7
        assert all(_dt_utc(e.timestamp) for e in events)


class TestUsageGenerator:
    def test_generate_record_voice_and_data(self) -> None:
        gen = UsageGenerator(seed=99)
        r = gen.generate_record("PSN-ZA-TEST1234567890", "ZA")
        assert isinstance(r, UsageRecord)
        assert r.country == "ZA"
        assert _dt_utc(r.timestamp)
        assert r.usage_type in {"voice_outgoing", "voice_incoming", "data", "sms"}
        if r.usage_type in {"voice_outgoing", "voice_incoming"}:
            assert isinstance(r.duration_seconds, int) and r.duration_seconds > 0
        elif r.usage_type == "data":
            assert isinstance(r.data_mb, float) and r.data_mb > 0

    def test_roaming_logic(self) -> None:
        gen = UsageGenerator(seed=101)
        # Force roaming probability via seed consistency
        recs = [gen.generate_record("PSN-NG-TESTXYZ", "NG") for _ in range(20)]
        roaming_events = [r for r in recs if r.roaming]
        assert len(roaming_events) >= 1
        assert all(r.roaming_country for r in roaming_events)
        assert all(_dt_utc(r.timestamp) for r in roaming_events)

    def test_stream_usage_small(self) -> None:
        gen = UsageGenerator(seed=5)
        recs = list(gen.stream_usage("KE", days=1, sims=5))
        assert len(recs) >= 5
        assert all(_dt_utc(r.timestamp) for r in recs)

    def test_data_roaming_reduced_size(self) -> None:
        gen = UsageGenerator(seed=123)
        records = [gen.generate_record("PSN-NG-ABCD", "NG") for _ in range(200)]
        roaming_data = [r for r in records if r.roaming and r.usage_type == "data"]
        assert len(roaming_data) >= 1
        assert all(r.data_mb is not None and r.data_mb > 0 for r in roaming_data)
        assert all(r.data_mb < 10.0 for r in roaming_data)


class TestCellProcessors:
    def test_expansion_detector_detects_new_country(self) -> None:
        det = ExpansionDetector(min_sim_threshold=10, time_window_days=30)
        now = datetime.utcnow()
        det.add_activation("CLIENT-9", "ZA", 50, timestamp=now - timedelta(days=60))
        det.add_activation("CLIENT-9", "NG", 12, timestamp=now - timedelta(days=2))
        signals = det.detect_expansion("CLIENT-9")
        assert len(signals) == 1
        sig = signals[0]
        assert sig.new_country == "NG"
        assert sig.sim_count >= 12
        assert 0 <= sig.confidence <= 100

    def test_processor_security_rbac(self) -> None:
        for Proc in (ExpansionProcessor, MomoFlowProcessor, WorkforceGrowthProcessor):
            proc = Proc()
            assert isinstance(proc, BaseProcessor)
            out = proc.process_sync({"access_role": "system", "source": "unit-test"})
            assert out.get("processed") is True
            with pytest.raises(ValueError):
                proc.process_sync({"access_role": "system"})
            with pytest.raises(PermissionError):
                proc.process_sync({"access_role": "guest", "source": "unit-test"})

    def test_expansion_detector_footprint(self) -> None:
        det = ExpansionDetector(min_sim_threshold=5, time_window_days=60)
        now = datetime.utcnow()
        det.add_activation("CLIENT-42", "ZA", 20, timestamp=now - timedelta(days=10))
        det.add_activation("CLIENT-42", "ZA", 15, timestamp=now - timedelta(days=5))
        det.add_activation("CLIENT-42", "KE", 8, timestamp=now - timedelta(days=2))
        footprint = det.get_client_footprint("CLIENT-42")
        assert footprint["ZA"] == 35
        assert footprint["KE"] == 8
