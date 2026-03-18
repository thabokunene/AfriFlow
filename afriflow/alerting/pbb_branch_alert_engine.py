"""
@file pbb_branch_alert_engine.py
@description Generates Personal and Business Banking branch-level alerts for
             branch managers and branch relationship teams. Covers account
             dormancy risk, unusual balance surges (potential fraud or windfall),
             overdraft usage approaching limit, salary account product gaps,
             KYC document expiry, and salary capture opportunities from employers
             with low payroll banking penetration.
@author Thabo Kunene
@created 2026-03-18
"""

# PBB Branch Alert Engine
#
# Generates alerts for Personal and Business Banking branch
# managers and branch-level relationship teams.
#
# Alert types:
#   DORMANCY_RISK    — Account approaching dormancy threshold
#   SALARY_CAPTURE   — Large employer's workforce not on payroll
#   BALANCE_SURGE    — Unusual balance increase (potential fraud or windfall)
#   OVERDRAFT_RISK   — Account approaching overdraft limit
#   PRODUCT_GAP      — Salary account holder with no savings/investment product
#   KYC_EXPIRY       — KYC documents expiring within 60 days
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

from __future__ import annotations  # PEP 563: postponed annotation evaluation

from dataclasses import dataclass, field  # Lightweight structured data with auto-__init__
from datetime import datetime, timedelta, date  # Timestamps and KYC/dormancy date maths
from typing import Dict, List, Optional          # Type annotations for safety and IDE support


# ---------------------------------------------------------------------------
# Module-level thresholds
# ---------------------------------------------------------------------------

# Days before statutory dormancy at which KYC expiry alerts fire.
# 60 days gives the branch enough lead time to contact clients.
_KYC_WARNING_DAYS = 60

# Early warning window before the dormancy limit is hit.
# An alert fires when 30 or fewer days remain before the account goes dormant.
_DORMANCY_WARNING_DAYS = 30   # Days before statutory dormancy limit

# South African statutory dormancy threshold: 90 days of inactivity.
# After this, the account transitions to a dormant state with restricted access.
_DORMANCY_LIMIT_DAYS = 90     # Dormancy after 90 days of inactivity


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PBBBranchAlert:
    """A single PBB branch-level alert.

    :param alert_id: Unique ID with prefix PBB-<TYPE>-<ACCT_OR_EMPLOYER_ID>
    :param branch_id: ID of the branch this alert is assigned to
    :param account_id: Account ID; 'N/A' for employer-level salary capture alerts
    :param client_name: Customer or employer name for dashboard display
    :param alert_type: DORMANCY_RISK / BALANCE_SURGE / OVERDRAFT_RISK /
                       PRODUCT_GAP / KYC_EXPIRY / SALARY_CAPTURE
    :param urgency: IMMEDIATE / HIGH / MEDIUM / LOW
    :param headline: One-line alert title for branch dashboard display
    :param details: Expanded context for branch staff preparation
    :param recommended_action: Specific next step for the branch team
    :param revenue_opportunity_zar: Estimated annual revenue if action is taken
    :param created_at: ISO timestamp of alert generation
    """

    alert_id: str
    branch_id: str
    account_id: str             # 'N/A' for employer-level alerts (SALARY_CAPTURE)
    client_name: str
    alert_type: str
    urgency: str
    headline: str
    details: str
    recommended_action: str
    revenue_opportunity_zar: float  # Estimated annual revenue opportunity from this alert
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()  # Auto-stamped at creation
    )


@dataclass
class PBBBranchAlertBatch:
    """Batch of all PBB alerts for a branch, sorted by urgency.

    :param branch_id: ID of the branch this batch belongs to
    :param alerts: Priority-sorted list of PBBBranchAlert objects
    :param total_opportunity_zar: Sum of revenue_opportunity_zar across all alerts
    :param generated_at: ISO timestamp when the batch was built
    """

    branch_id: str
    alerts: List[PBBBranchAlert]
    total_opportunity_zar: float   # KPI: total revenue in the branch's action queue
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

class PBBBranchAlertEngine:
    """
    Generate PBB branch alerts from account and cell profiles.

    Processes each account in the branch's portfolio through five account-level
    detectors (dormancy, balance surge, overdraft, product gap, KYC), then
    processes employer signals for salary capture opportunities. The combined
    alert list is sorted by urgency before returning.

    Intended recipient: PBB branch managers and branch relationship officers.

    Usage::

        engine = PBBBranchAlertEngine()
        batch = engine.build_batch(
            branch_id="BRANCH-CPT-042",
            accounts=[
                {
                    "account_id": "ACC-001",
                    "client_name": "John Dlamini",
                    "account_type": "current",
                    "average_balance": 12500,
                    "days_since_last_txn": 55,
                    "kyc_expiry_date": "2026-04-15",
                    ...
                }
            ],
            employer_signals=[...],
        )
    """

    def build_batch(
        self,
        branch_id: str,
        accounts: List[Dict],
        employer_signals: Optional[List[Dict]] = None,
    ) -> PBBBranchAlertBatch:
        """
        Build a sorted alert batch for a single branch.

        Runs all account-level detectors for each account, then processes
        employer salary capture signals. Sorts the combined list by urgency.

        :param branch_id: Branch identifier
        :param accounts: List of account dicts for the branch's customer portfolio
        :param employer_signals: Optional list of employer payroll signals for
                                 salary capture opportunity detection
        :return: PBBBranchAlertBatch sorted IMMEDIATE → LOW
        """
        alerts: List[PBBBranchAlert] = []

        # Run all five account-level detectors for each account in the branch portfolio
        for acct in accounts:
            alerts.extend(
                self._process_account(branch_id, acct)
            )

        # Process employer signals for salary capture opportunities (separate to accounts)
        for signal in (employer_signals or []):  # Default to empty list if not provided
            alert = self._salary_capture_alert(branch_id, signal)
            if alert:
                alerts.append(alert)

        # Sort by urgency: IMMEDIATE first, then HIGH, MEDIUM, LOW; unknown urgency last
        alerts.sort(
            key=lambda a: {
                "IMMEDIATE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3
            }.get(a.urgency, 9)
        )

        # KPI: total revenue in the branch's current action queue
        total = sum(a.revenue_opportunity_zar for a in alerts)

        return PBBBranchAlertBatch(
            branch_id=branch_id,
            alerts=alerts,
            total_opportunity_zar=total,
        )

    def _process_account(
        self, branch_id: str, acct: Dict
    ) -> List[PBBBranchAlert]:
        """
        Run all account-level detectors for a single account.

        :param branch_id: Branch identifier
        :param acct: Account dict with account_id, client_name, balances, dates
        :return: List of PBBBranchAlert objects (may be empty)
        """
        alerts: List[PBBBranchAlert] = []

        # Extract common account identifiers used by all sub-detectors
        acct_id = acct.get("account_id", "UNK")
        name = acct.get("client_name", "Unknown")

        # --- Detector 1: Dormancy risk ---
        dormancy = self._dormancy_alert(branch_id, acct_id, name, acct)
        if dormancy:
            alerts.append(dormancy)

        # --- Detector 2: Balance surge (fraud or windfall signal) ---
        balance_surge = self._balance_surge_alert(branch_id, acct_id, name, acct)
        if balance_surge:
            alerts.append(balance_surge)

        # --- Detector 3: Overdraft usage near limit ---
        overdraft = self._overdraft_alert(branch_id, acct_id, name, acct)
        if overdraft:
            alerts.append(overdraft)

        # --- Detector 4: Product gap (salary account, no savings product) ---
        product_gap = self._product_gap_alert(branch_id, acct_id, name, acct)
        if product_gap:
            alerts.append(product_gap)

        # --- Detector 5: KYC document expiry ---
        kyc = self._kyc_alert(branch_id, acct_id, name, acct)
        if kyc:
            alerts.append(kyc)

        return alerts

    # ------------------------------------------------------------------
    # Individual account-level detectors
    # ------------------------------------------------------------------

    def _dormancy_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        """
        Detect an account approaching statutory dormancy.

        Business event: account has been inactive for 60–90 days and will
        become dormant within the next 30 days unless activity is recorded.
        Dormant accounts generate no transaction fee revenue and are costly
        to re-activate. Branch intervention (often a fee waiver offer) is
        the standard playbook.

        Urgency: HIGH if ≤7 days to dormancy; MEDIUM otherwise.

        :param branch_id: Branch identifier
        :param acct_id: Account ID
        :param name: Client name
        :param acct: Account dict with 'days_since_last_txn' and 'average_balance'
        :return: PBBBranchAlert or None if not in the warning window
        """
        days = acct.get("days_since_last_txn", 0)

        # Compute how many days remain before the account hits the 90-day dormancy limit
        days_to_dormancy = _DORMANCY_LIMIT_DAYS - days

        # Only alert if within the 30-day warning window; skip already-dormant accounts
        if days_to_dormancy > _DORMANCY_WARNING_DAYS or days_to_dormancy < 0:
            return None

        balance = acct.get("average_balance", 0)

        # Escalate to HIGH urgency when fewer than 7 days remain
        urgency = "HIGH" if days_to_dormancy <= 7 else "MEDIUM"

        return PBBBranchAlert(
            alert_id=f"PBB-DORM-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="DORMANCY_RISK",
            urgency=urgency,
            headline=(
                f"Account dormancy in {days_to_dormancy} days"
            ),
            details=(
                f"No transactions in {days} days. "
                f"Balance: R{balance:,.0f}. "
                f"Dormancy threshold: {_DORMANCY_LIMIT_DAYS} days."
            ),
            recommended_action=(
                "Contact client to re-activate account. "
                "Consider fee waiver incentive."
            ),
            # Revenue estimate: 2% of balance as proxy for annual transaction fees
            revenue_opportunity_zar=balance * 0.02,
        )

    def _balance_surge_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        """
        Detect an unusual balance surge: current balance is 3× or more above
        the 90-day average.

        Business event: a large unexpected deposit may indicate:
          - A legitimate windfall (inheritance, asset sale) → investment opportunity
          - An AML/fraud signal (structuring, layering) → compliance escalation

        The branch should investigate the source before taking commercial action.
        Urgency: always HIGH due to dual AML and commercial significance.

        :param branch_id: Branch identifier
        :param acct_id: Account ID
        :param name: Client name
        :param acct: Account dict with 'current_balance' and 'average_balance'
        :return: PBBBranchAlert or None if surge ratio < 3×
        """
        current = acct.get("current_balance", 0)
        avg = acct.get("average_balance", 1)  # Default 1 to avoid division by zero

        # Only alert on a meaningful surge: 3× the 90-day average
        if avg == 0 or current < avg * 3:
            return None

        surge_ratio = current / avg  # How many times above average the current balance is

        return PBBBranchAlert(
            alert_id=f"PBB-SURGE-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="BALANCE_SURGE",
            urgency="HIGH",  # Always HIGH: both AML review and investment pitch time-sensitive
            headline=(
                f"Balance surge: {surge_ratio:.1f}× average"
            ),
            details=(
                f"Current balance R{current:,.0f} is {surge_ratio:.1f}× "
                f"the 90-day average R{avg:,.0f}. "
                f"Review for potential fraud or windfall event."
            ),
            recommended_action=(
                "Flag for AML review if no clear business reason. "
                "If legitimate windfall, offer investment product."
            ),
            # Revenue estimate: 0.5% of the surge balance as proxy for investment fees
            revenue_opportunity_zar=current * 0.005,
        )

    def _overdraft_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        """
        Detect overdraft usage approaching the account's limit.

        Business event: account is in overdraft and usage is above 80% of the
        approved overdraft limit. Indicates potential liquidity stress for the
        customer. Branch can offer a limit increase or a personal loan to address
        the underlying need more cost-effectively.

        Urgency: HIGH at ≥95% utilisation (near-limit = immediate action);
                 MEDIUM at 80–95% (monitoring required).

        :param branch_id: Branch identifier
        :param acct_id: Account ID
        :param name: Client name
        :param acct: Account dict with 'current_balance' (negative = overdrawn)
                     and 'overdraft_limit' (negative limit e.g. -50000)
        :return: PBBBranchAlert or None if usage is below 80% or account is in credit
        """
        balance = acct.get("current_balance", 0)
        limit = acct.get("overdraft_limit", 0)

        # Only applies to accounts with an overdraft facility and a negative balance
        if limit == 0 or balance >= 0:
            return None

        # Usage percentage: how much of the overdraft limit has been consumed
        usage_pct = abs(balance) / limit

        # Alert threshold: 80% of the overdraft limit
        if usage_pct < 0.80:
            return None

        return PBBBranchAlert(
            alert_id=f"PBB-OD-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="OVERDRAFT_RISK",
            # HIGH at ≥95% (near limit, imminent dishonour risk); MEDIUM at 80–95%
            urgency="HIGH" if usage_pct >= 0.95 else "MEDIUM",
            headline=(
                f"Overdraft at {usage_pct*100:.0f}% of limit"
            ),
            details=(
                f"Balance R{balance:,.0f} vs limit R{-limit:,.0f}. "
                f"Usage: {usage_pct*100:.0f}%."
            ),
            recommended_action=(
                "Contact client to discuss repayment plan. "
                "Assess eligibility for limit increase or personal loan."
            ),
            # Revenue estimate: monthly interest on the overdrawn balance (18% p.a. / 12)
            revenue_opportunity_zar=abs(balance) * 0.18 / 12,
        )

    def _product_gap_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        """
        Detect a product gap: salary account holder with no savings or investment product.

        Business event: a client receives their salary through the branch but
        has no savings account, investment account, notice deposit, or tax-free
        account. This represents a cross-sell opportunity for deposits and investments.

        Only fires if the average balance exceeds R2,000 (indicating capacity to save).
        Urgency: LOW (not time-sensitive; suitable for next interaction or campaign).

        :param branch_id: Branch identifier
        :param acct_id: Account ID
        :param name: Client name
        :param acct: Account dict with 'is_salary_account', 'linked_products',
                     and 'average_balance'
        :return: PBBBranchAlert or None if not a salary account or already has savings
        """
        is_salary = acct.get("is_salary_account", False)
        linked = acct.get("linked_products", [])  # List of product type strings

        # Only relevant for salary accounts: payroll is the primary funding source
        if not is_salary:
            return None

        # Check if any savings-type product is already linked to this account
        has_savings = any(
            p in linked for p in ("savings", "investment", "notice", "tax_free")
        )
        if has_savings:
            return None  # Client already has a savings product; no gap

        avg_balance = acct.get("average_balance", 0)

        # Minimum balance filter: below R2,000 means insufficient capacity to save
        if avg_balance < 2000:
            return None

        return PBBBranchAlert(
            alert_id=f"PBB-PROD-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="PRODUCT_GAP",
            urgency="LOW",  # Not time-sensitive; suitable for next branch visit or campaign
            headline="Salary account with no savings product",
            details=(
                f"Salary account holder with avg balance "
                f"R{avg_balance:,.0f}. No savings/investment product linked."
            ),
            recommended_action=(
                "Offer tax-free savings account or notice deposit "
                "during next client interaction."
            ),
            # Revenue estimate: 1.5% of average balance as proxy for deposit fee income
            revenue_opportunity_zar=avg_balance * 0.015,
        )

    def _kyc_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        """
        Detect KYC document expiry within the 60-day warning window.

        Business event: a client's KYC documents (ID, proof of address, etc.)
        are expiring. If not renewed, the account may be restricted under FICA
        regulations, preventing transactions and generating customer complaints.

        Urgency: HIGH if ≤14 days to expiry; MEDIUM if 15–60 days.
        Revenue opportunity: R0 (compliance requirement, not commercial action).

        :param branch_id: Branch identifier
        :param acct_id: Account ID
        :param name: Client name
        :param acct: Account dict with 'kyc_expiry_date' (ISO date string)
        :return: PBBBranchAlert or None if KYC is valid beyond 60 days or already expired
        """
        kyc_expiry = acct.get("kyc_expiry_date")
        if not kyc_expiry:
            return None  # No KYC expiry date recorded; cannot generate alert

        try:
            expiry = date.fromisoformat(kyc_expiry)   # Parse ISO date string
            days = (expiry - date.today()).days         # Positive = future, negative = expired
        except (ValueError, TypeError):
            return None  # Malformed date; skip silently

        # Alert window: 1–60 days to expiry. Skip already-expired KYC (days < 0).
        if days > _KYC_WARNING_DAYS or days < 0:
            return None

        return PBBBranchAlert(
            alert_id=f"PBB-KYC-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="KYC_EXPIRY",
            # HIGH at ≤14 days (account restriction imminent); MEDIUM at 15–60 days
            urgency="HIGH" if days <= 14 else "MEDIUM",
            headline=f"KYC documents expire in {days} days",
            details=(
                f"KYC expiry: {kyc_expiry}. "
                f"Account may be restricted after expiry."
            ),
            recommended_action=(
                "Contact client for KYC refresh. "
                "Send document checklist via email/USSD."
            ),
            revenue_opportunity_zar=0.0,  # KYC renewal is a compliance requirement, not revenue
        )

    # ------------------------------------------------------------------
    # Employer-level detector (not account-level)
    # ------------------------------------------------------------------

    def _salary_capture_alert(
        self, branch_id: str, signal: Dict
    ) -> Optional[PBBBranchAlert]:
        """
        Generate a salary capture opportunity alert for an employer with low
        payroll banking penetration at the branch.

        Business event: an employer in the branch's catchment area has employees
        who are not using the bank's payroll banking product. Each uncaptured
        employee represents R2,500/year in estimated banking revenue (transaction
        fees, overdraft, and savings products).

        Minimum threshold of 10 uncaptured employees to avoid trivial alerts.
        Urgency: MEDIUM (strategic payroll pitches require planning but not immediate action).

        :param branch_id: Branch identifier
        :param signal: Employer signal dict with employer_name, employer_id,
                       uncaptured_employee_count, total_employee_count
        :return: PBBBranchAlert or None if fewer than 10 uncaptured employees
        """
        employer_name = signal.get("employer_name", "Unknown")
        employer_id = signal.get("employer_id", "UNK")
        uncaptured = signal.get("uncaptured_employee_count", 0)
        total = signal.get("total_employee_count", 1)

        # Only alert when there is a meaningful number of uncaptured employees
        if uncaptured < 10:
            return None

        # Revenue estimate: R2,500 per employee per year (transaction fees + products)
        revenue = uncaptured * 2500   # R2,500 per employee per year

        return PBBBranchAlert(
            alert_id=f"PBB-SAL-{employer_id}",
            branch_id=branch_id,
            account_id="N/A",  # Employer-level alert; no specific account
            client_name=employer_name,
            alert_type="SALARY_CAPTURE",
            urgency="MEDIUM",  # Strategic opportunity; no immediate deadline
            headline=(
                f"{uncaptured} employees of {employer_name} "
                f"not on payroll banking"
            ),
            details=(
                f"{employer_name} has {total} employees. "
                f"Only {total - uncaptured} use our payroll banking. "
                f"{uncaptured} unbanked = R{revenue:,.0f}/year opportunity."
            ),
            recommended_action=(
                "Arrange payroll banking presentation with HR department. "
                "Bring payroll banking product team."
            ),
            revenue_opportunity_zar=revenue,  # Annual revenue if all uncaptured employees onboard
        )
