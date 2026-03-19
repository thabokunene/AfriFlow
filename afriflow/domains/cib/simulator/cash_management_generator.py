"""
@file cash_management_generator.py
@description Generator for synthetic CIB cash management instructions, simulating corporate treasury activities.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Cash Management Instruction Generator

We generate realistic synthetic cash management
instructions for the CIB domain.

Cash management is the backbone of corporate treasury.
For a bank, a corporate client's cash management
relationship is the most sticky product in the portfolio
— once a company runs its sweeps and pooling through a
bank's systems, they do not move lightly.

The signal value for AfriFlow:

1. New cross-border sweeps: A corporate that previously
   only swept between South Africa and Zimbabwe now
   adding a sweep to a Nigeria account signals that
   they have established an operational entity there.
   This is treasury-level confirmation of an expansion
   that cell and CIB payment data may have already
   hinted at.

2. Payroll disbursements: When a corporate's payroll
   account disbursements grow by 30% in a country it
   means the workforce grew by 30% — a precise signal
   that the cell SIM deflation method validates from
   the other side.

3. Concentration patterns: A corporate concentrating
   cash from seven African subsidiaries into a single
   ZA master account signals a centralised treasury
   structure. A corporate sweeping each country's
   cash to a local account suggests a decentralised
   structure — important for product design.

4. Cross-border FX: A cash management instruction that
   crosses a currency boundary generates an implicit FX
   transaction. If the corporate does not have a hedge
   on that cross, it is an unhedged exposure — a shadow
   in the forex domain.

Instruction types modelled:
  sweep        – Automatic balance sweep from sub-account
                 to master account
  pooling      – Notional or physical cash pooling
  concentration – Multi-entity cash concentration
  disbursement – Payroll or supplier mass payment

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Standard math library for calculating transaction amounts and distributions
import math
# Random library for stochastic event generation based on market profiles
import random
# UUID for generating unique transaction and record identifiers
import uuid
# Dataclass for structured representation of cash management instructions
from dataclasses import dataclass
# Datetime utilities for timestamping generated events
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Dict, Iterator, List, Optional

# Custom exception for configuration-related failures in the generator
from afriflow.exceptions import ConfigurationError
# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger

# Initialize module-level logger for the cash management simulator
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Market profiles
# ---------------------------------------------------------------------------

# Typical domestic sweep threshold (USD) — amount
# above which a subsidiary auto-sweeps to master.
# These thresholds reflect common treasury practices in specific African markets.
SWEEP_THRESHOLDS_USD: Dict[str, float] = {
    "ZA": 10_000,
    "NG": 5_000,
    "KE": 5_000,
    "GH": 3_000,
    "TZ": 2_000,
    "UG": 2_000,
    "ZM": 3_000,
    "MZ": 2_000,
}
# Default sweep threshold for countries not explicitly profiled.
DEFAULT_SWEEP_THRESHOLD_USD = 3_000.0

# Cash management hub countries — corporates typically
# concentrate to these markets from subsidiaries.
# These hubs are often regional financial centers.
TREASURY_HUBS = ["ZA", "KE", "NG", "AE", "GB"]

# Average payroll disbursement per employee per month (USD).
# Used to scale payroll disbursement amounts to realistic levels for each country.
AVG_PAYROLL_USD_PER_EMPLOYEE: Dict[str, float] = {
    "ZA": 1_200,
    "NG": 600,
    "KE": 500,
    "GH": 350,
    "TZ": 280,
    "UG": 260,
    "ZM": 400,
    "MZ": 200,
    "CI": 350,
    "RW": 280,
}
DEFAULT_PAYROLL_USD = 400.0

COUNTRY_CURRENCY: Dict[str, str] = {
    "NG": "NGN", "KE": "KES", "GH": "GHS",
    "TZ": "TZS", "UG": "UGX", "ZM": "ZMW",
    "MZ": "MZN", "ZA": "ZAR", "CI": "XOF",
    "RW": "RWF", "ET": "ETB", "CM": "XAF",
    "AE": "AED", "GB": "GBP",
}

USD_RATES: Dict[str, float] = {
    "NGN": 1580.0, "KES": 130.0, "GHS": 15.5,
    "TZS": 2550.0, "UGX": 3750.0, "ZMW": 27.5,
    "MZN": 64.0,  "ZAR": 18.5,  "XOF": 610.0,
    "RWF": 1280.0, "ETB": 56.0,  "XAF": 610.0,
    "AED": 3.67,  "GBP": 0.79,  "USD": 1.0,
}

INSTRUCTION_TYPES = ["sweep", "pooling", "concentration", "disbursement"]


@dataclass
class CashManagementInstruction:
    """
    A single cash management instruction.

    We publish these to the CIB domain Kafka topic
    (cib.cash_management.instructions) in Avro format.

    is_cross_border is a key signal — cross-border
    instructions that do not have a corresponding FX
    hedge in the forex domain are data shadows.
    """

    instruction_id: str
    corporate_id: str
    instruction_type: str
    source_account: str
    target_account: str
    source_country: str
    target_country: str
    currency: str
    amount: float
    value_date: datetime
    is_cross_border: bool
    fx_rate_applied: Optional[float]


class CashManagementGenerator:
    """
    We generate realistic synthetic cash management
    instructions for testing and demo purposes.

    Usage:

        gen = CashManagementGenerator(seed=42)

        # Generate a cross-border sweep
        sweep = gen.generate_sweep("CORP-001", "NG", "ZA")

        # Generate a payroll disbursement
        payroll = gen.generate_payroll_disbursement(
            corporate_id="CORP-001",
            country="KE",
            employee_count=300,
        )

        # Stream 30 days of instructions for a corporate
        for instr in gen.stream_instructions("CORP-001", days=30):
            publish_to_kafka(instr)
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)

        self._client_pool: List[str] = [
            f"CORP-{uuid.uuid4().hex[:8].upper()}" for _ in range(100)
        ]

    def _account_number(self, country: str, corporate_id: str) -> str:
        """We generate a realistic-looking account reference."""
        return f"ACC-{country}-{corporate_id[-8:]}-{random.randint(1000, 9999)}"

    def _amount(
        self,
        instruction_type: str,
        country: str,
        employee_count: Optional[int] = None,
    ) -> float:
        """
        We generate a realistic instruction amount.

        Sweeps cluster around the sweep threshold.
        Payroll scales with employee count.
        Concentration and pooling instructions are
        larger — they aggregate multiple subsidiary balances.
        """

        if instruction_type == "disbursement" and employee_count:
            avg_usd = AVG_PAYROLL_USD_PER_EMPLOYEE.get(country, DEFAULT_PAYROLL_USD)
            total_usd = employee_count * avg_usd * random.uniform(0.90, 1.10)
        elif instruction_type == "sweep":
            threshold = SWEEP_THRESHOLDS_USD.get(country, DEFAULT_SWEEP_THRESHOLD_USD)
            total_usd = math.exp(
                math.log(threshold * 3) + 0.9 * random.gauss(0, 1)
            )
            total_usd = max(threshold * 0.5, total_usd)
        elif instruction_type in ("pooling", "concentration"):
            # These aggregate multiple entities — larger amounts
            total_usd = math.exp(random.gauss(11.0, 1.2))  # ~$60k median
        else:
            total_usd = math.exp(random.gauss(9.5, 1.0))  # ~$13k median

        currency = COUNTRY_CURRENCY.get(country, "USD")
        rate = USD_RATES.get(currency, 1.0)
        return round(total_usd * rate, 2)

    def _fx_rate(self, source_currency: str, target_currency: str) -> Optional[float]:
        """
        We generate a simulated FX rate for cross-currency
        instructions. Returns None if same currency.
        """

        if source_currency == target_currency:
            return None

        # Convert both to USD equivalents and derive cross rate
        source_usd = 1.0 / USD_RATES.get(source_currency, 1.0)
        target_usd = 1.0 / USD_RATES.get(target_currency, 1.0)

        if target_usd == 0:
            return None

        base_cross = source_usd / target_usd
        # Add realistic bid-ask spread noise
        return round(base_cross * random.uniform(0.995, 1.005), 6)

    def generate_sweep(
        self,
        corporate_id: str,
        source_country: str,
        target_country: str,
        value_date: Optional[datetime] = None,
    ) -> CashManagementInstruction:
        """
        We generate an automatic balance sweep instruction.

        The sweep moves excess funds from a subsidiary
        account to a master account, typically daily.
        Cross-border sweeps convert currency at the
        FX rate applied on the value date.
        """

        source_currency = COUNTRY_CURRENCY.get(source_country, "USD")
        target_currency = COUNTRY_CURRENCY.get(target_country, "USD")
        is_cross_border = source_country != target_country

        # Sweeps use the target country's currency
        currency = target_currency if is_cross_border else source_currency

        amount = self._amount("sweep", source_country)
        fx_rate = self._fx_rate(source_currency, target_currency) if is_cross_border else None

        vd = value_date or datetime.now(timezone.utc)

        # Use 'extra' for structured fields to avoid passing unsupported kwargs
        # to logging methods.
        logger.debug(
            "Generated sweep",
            extra={
                "corporate_id": corporate_id,
                "source_country": source_country,
                "target_country": target_country,
                "is_cross_border": is_cross_border,
            },
        )

        return CashManagementInstruction(
            instruction_id=f"CM-SWP-{uuid.uuid4().hex[:10].upper()}",
            corporate_id=corporate_id,
            instruction_type="sweep",
            source_account=self._account_number(source_country, corporate_id),
            target_account=self._account_number(target_country, corporate_id),
            source_country=source_country,
            target_country=target_country,
            currency=currency,
            amount=amount,
            value_date=vd,
            is_cross_border=is_cross_border,
            fx_rate_applied=fx_rate,
        )

    def generate_payroll_disbursement(
        self,
        corporate_id: str,
        country: str,
        employee_count: int,
        payment_date: Optional[datetime] = None,
    ) -> List[CashManagementInstruction]:
        """
        We generate a payroll disbursement instruction set.

        Large corporates may split payroll across multiple
        batch instructions (e.g. per department or per
        subsidiary). We generate 1–5 instructions
        depending on employee count.

        The total amount across all instructions equals
        approximately employee_count × avg_salary.

        Raises:
            ConfigurationError: If employee_count is not positive
        """
        if employee_count <= 0:
            raise ConfigurationError(
                f"employee_count must be positive, got {employee_count}"
            )

        # Ensure at least 1 batch, scale up for larger employee counts
        num_batches = min(5, max(1, (employee_count + 199) // 200))
        vd = payment_date or datetime.now(timezone.utc)

        instructions = []
        for batch_num in range(num_batches):
            batch_employees = employee_count // num_batches
            if batch_num == num_batches - 1:
                batch_employees += employee_count % num_batches

            amount = self._amount("disbursement", country, employee_count=batch_employees)

            instructions.append(
                CashManagementInstruction(
                    instruction_id=f"CM-PYRL-{uuid.uuid4().hex[:10].upper()}",
                    corporate_id=corporate_id,
                    instruction_type="disbursement",
                    source_account=self._account_number(country, corporate_id),
                    target_account=f"PAYROLL-POOL-{country}-{batch_num + 1:02d}",
                    source_country=country,
                    target_country=country,
                    currency=COUNTRY_CURRENCY.get(country, "USD"),
                    amount=amount,
                    value_date=vd + timedelta(seconds=batch_num * 120),
                    is_cross_border=False,
                    fx_rate_applied=None,
                )
            )

        # Attach batch details via logging 'extra' for compatibility with the
        # standard logging API and our JSON formatter.
        logger.info(
            "Generated payroll disbursement",
            extra={
                "corporate_id": corporate_id,
                "country": country,
                "employee_count": employee_count,
                "batches": num_batches,
            },
        )
        return instructions

    def stream_instructions(
        self,
        corporate_id: str,
        days: int = 30,
    ) -> Iterator[CashManagementInstruction]:
        """
        We yield a stream of cash management instructions
        for the given corporate over the requested days.

        Daily sweeps occur every business day.
        Payroll disbursements cluster around the 25th
        of each month.
        Pooling and concentration instructions occur
        weekly, typically on Mondays.
        """

        start = datetime.now(timezone.utc) - timedelta(days=days)

        # Fixed subsidiary-to-master treasury structure
        # for this corporate
        subsidiaries = random.sample(
            ["NG", "KE", "GH", "TZ", "ZM", "MZ", "CI", "UG"],
            k=min(4, 8),
        )
        treasury_hub = random.choice(TREASURY_HUBS)

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)
            weekday = current_day.weekday()

            if weekday >= 5:  # Weekend
                continue

            # Daily sweeps from each subsidiary to hub
            for sub_country in subsidiaries:
                if random.random() < 0.80:  # Not every sub sweeps daily
                    yield self.generate_sweep(
                        corporate_id=corporate_id,
                        source_country=sub_country,
                        target_country=treasury_hub,
                        value_date=current_day.replace(
                            hour=random.randint(8, 10),
                        ),
                    )

            # Weekly concentration on Monday
            if weekday == 0:
                concentration_amount = self._amount("concentration", treasury_hub)
                yield CashManagementInstruction(
                    instruction_id=f"CM-CONC-{uuid.uuid4().hex[:10].upper()}",
                    corporate_id=corporate_id,
                    instruction_type="concentration",
                    source_account=self._account_number(treasury_hub, corporate_id),
                    target_account=f"MASTER-{treasury_hub}-{corporate_id[-6:]}",
                    source_country=treasury_hub,
                    target_country=treasury_hub,
                    currency=COUNTRY_CURRENCY.get(treasury_hub, "USD"),
                    amount=concentration_amount,
                    value_date=current_day.replace(hour=11),
                    is_cross_border=False,
                    fx_rate_applied=None,
                )

            # Payroll disbursements around the 25th
            if 24 <= current_day.day <= 26 and random.random() < 0.50:
                for country in subsidiaries[:2]:  # Top two subsidiaries
                    employee_count = random.randint(50, 500)
                    for instr in self.generate_payroll_disbursement(
                        corporate_id=corporate_id,
                        country=country,
                        employee_count=employee_count,
                        payment_date=current_day.replace(
                            hour=random.randint(9, 14)
                        ),
                    ):
                        yield instr


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    gen = CashManagementGenerator(seed=42)

    print("=== Cross-Border Sweep (Nigeria → South Africa) ===")
    sweep = gen.generate_sweep("CORP-DEMO-001", "NG", "ZA")
    print(f"  instruction_id   : {sweep.instruction_id}")
    print(f"  instruction_type : {sweep.instruction_type}")
    print(f"  corridor         : {sweep.source_country} → {sweep.target_country}")
    print(f"  currency         : {sweep.currency}")
    print(f"  amount           : {sweep.amount:,.2f}")
    print(f"  is_cross_border  : {sweep.is_cross_border}")
    print(f"  fx_rate_applied  : {sweep.fx_rate_applied}")

    print("\n=== Payroll Disbursement (Kenya, 250 employees) ===")
    payroll = gen.generate_payroll_disbursement("CORP-DEMO-002", "KE", 250)
    for p in payroll:
        print(
            f"  {p.instruction_id} | {p.currency} {p.amount:>14,.2f} | "
            f"{p.source_country}"
        )

    print("\n=== Stream (first 5 instructions over 14 days) ===")
    for i, instr in enumerate(gen.stream_instructions("CORP-DEMO-003", days=14)):
        print(
            f"  [{instr.value_date.date()}] {instr.instruction_type:14s} | "
            f"{instr.source_country} → {instr.target_country} | "
            f"{instr.currency} {instr.amount:>14,.2f}"
        )
        if i >= 4:
            break
