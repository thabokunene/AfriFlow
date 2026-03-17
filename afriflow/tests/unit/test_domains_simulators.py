"""
Tests for domain simulators to verify logging changes and basic functionality.

We specifically exercise paths where logging previously passed unsupported
kwargs to logger methods, which would raise TypeError at runtime. The tests
assert that generator methods execute without raising and return plausible
structures.
"""

from domains.cell.simulator.airtime_generator import AirtimeGenerator
from domains.cell.simulator.sim_activation_generator import SIMActivationGenerator
from domains.cib.simulator.cash_management_generator import CashManagementGenerator
from domains.cib.simulator.trade_finance_generator import TradeFinanceGenerator


def test_airtime_generate_corporate_bulk_runs():
    gen = AirtimeGenerator(seed=123)
    batch = gen.generate_corporate_bulk(
        corporate_client_id="CORP-TEST-001",
        country="NG",
        employee_count=300,
    )
    assert isinstance(batch, list)
    assert len(batch) >= 1
    assert all(hasattr(b, "topup_id") for b in batch)


def test_sim_activation_expansion_batch_runs():
    gen = SIMActivationGenerator(seed=123)
    batches = gen.generate_expansion_batch(
        corporate_client_id="CLIENT-XYZ",
        country="ZA",
        new_countries=["NG", "KE"],
    )
    assert isinstance(batches, list)
    assert len(batches) >= 2
    assert all(b.activation_type == "expansion_batch" for b in batches)


def test_cash_management_generators_run():
    gen = CashManagementGenerator(seed=123)
    sweep = gen.generate_sweep(
        corporate_id="CORP-ACME",
        source_country="NG",
        target_country="ZA",
    )
    assert sweep.is_cross_border is True

    payroll = gen.generate_payroll_disbursement(
        corporate_id="CORP-ACME",
        country="KE",
        employee_count=250,
    )
    assert isinstance(payroll, list)
    assert len(payroll) >= 1
    assert all(instr.instruction_type == "disbursement" for instr in payroll)


def test_trade_finance_generate_lc_runs():
    gen = TradeFinanceGenerator(seed=123)
    record = gen.generate_lc(
        applicant_id="CORP-ACME",
        applicant_country="GH",
        beneficiary_country="NL",
    )
    assert record.record_type == "letter_of_credit"
    assert record.applicant_country == "GH"
    assert record.beneficiary_country == "NL"
