"""
PBB Branch Alert Engine

Generates alerts for Personal and Business Banking branch
managers and branch-level relationship teams.

Alert types:
  DORMANCY_RISK    — Account approaching dormancy threshold
  SALARY_CAPTURE   — Large employer's workforce not on payroll
  BALANCE_SURGE    — Unusual balance increase (potential fraud or windfall)
  OVERDRAFT_RISK   — Account approaching overdraft limit
  PRODUCT_GAP      — Salary account holder with no savings/investment product
  KYC_EXPIRY       — KYC documents expiring within 60 days

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional


_KYC_WARNING_DAYS = 60
_DORMANCY_WARNING_DAYS = 30   # Days before statutory dormancy limit
_DORMANCY_LIMIT_DAYS = 90     # Dormancy after 90 days of inactivity


@dataclass
class PBBBranchAlert:
    alert_id: str
    branch_id: str
    account_id: str
    client_name: str
    alert_type: str
    urgency: str
    headline: str
    details: str
    recommended_action: str
    revenue_opportunity_zar: float
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class PBBBranchAlertBatch:
    branch_id: str
    alerts: List[PBBBranchAlert]
    total_opportunity_zar: float
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class PBBBranchAlertEngine:
    """
    Generate PBB branch alerts from account and cell profiles.

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
        alerts: List[PBBBranchAlert] = []

        for acct in accounts:
            alerts.extend(
                self._process_account(branch_id, acct)
            )

        for signal in (employer_signals or []):
            alert = self._salary_capture_alert(branch_id, signal)
            if alert:
                alerts.append(alert)

        alerts.sort(
            key=lambda a: {
                "IMMEDIATE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3
            }.get(a.urgency, 9)
        )

        total = sum(a.revenue_opportunity_zar for a in alerts)

        return PBBBranchAlertBatch(
            branch_id=branch_id,
            alerts=alerts,
            total_opportunity_zar=total,
        )

    def _process_account(
        self, branch_id: str, acct: Dict
    ) -> List[PBBBranchAlert]:
        alerts: List[PBBBranchAlert] = []
        acct_id = acct.get("account_id", "UNK")
        name = acct.get("client_name", "Unknown")

        dormancy = self._dormancy_alert(branch_id, acct_id, name, acct)
        if dormancy:
            alerts.append(dormancy)

        balance_surge = self._balance_surge_alert(branch_id, acct_id, name, acct)
        if balance_surge:
            alerts.append(balance_surge)

        overdraft = self._overdraft_alert(branch_id, acct_id, name, acct)
        if overdraft:
            alerts.append(overdraft)

        product_gap = self._product_gap_alert(branch_id, acct_id, name, acct)
        if product_gap:
            alerts.append(product_gap)

        kyc = self._kyc_alert(branch_id, acct_id, name, acct)
        if kyc:
            alerts.append(kyc)

        return alerts

    def _dormancy_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        days = acct.get("days_since_last_txn", 0)
        days_to_dormancy = _DORMANCY_LIMIT_DAYS - days
        if days_to_dormancy > _DORMANCY_WARNING_DAYS or days_to_dormancy < 0:
            return None

        balance = acct.get("average_balance", 0)
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
            revenue_opportunity_zar=balance * 0.02,
        )

    def _balance_surge_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        current = acct.get("current_balance", 0)
        avg = acct.get("average_balance", 1)
        if avg == 0 or current < avg * 3:
            return None

        surge_ratio = current / avg

        return PBBBranchAlert(
            alert_id=f"PBB-SURGE-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="BALANCE_SURGE",
            urgency="HIGH",
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
            revenue_opportunity_zar=current * 0.005,
        )

    def _overdraft_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        balance = acct.get("current_balance", 0)
        limit = acct.get("overdraft_limit", 0)
        if limit == 0 or balance >= 0:
            return None

        usage_pct = abs(balance) / limit
        if usage_pct < 0.80:
            return None

        return PBBBranchAlert(
            alert_id=f"PBB-OD-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="OVERDRAFT_RISK",
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
            revenue_opportunity_zar=abs(balance) * 0.18 / 12,
        )

    def _product_gap_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        is_salary = acct.get("is_salary_account", False)
        linked = acct.get("linked_products", [])
        if not is_salary:
            return None

        has_savings = any(
            p in linked for p in ("savings", "investment", "notice", "tax_free")
        )
        if has_savings:
            return None

        avg_balance = acct.get("average_balance", 0)
        if avg_balance < 2000:
            return None

        return PBBBranchAlert(
            alert_id=f"PBB-PROD-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="PRODUCT_GAP",
            urgency="LOW",
            headline="Salary account with no savings product",
            details=(
                f"Salary account holder with avg balance "
                f"R{avg_balance:,.0f}. No savings/investment product linked."
            ),
            recommended_action=(
                "Offer tax-free savings account or notice deposit "
                "during next client interaction."
            ),
            revenue_opportunity_zar=avg_balance * 0.015,
        )

    def _kyc_alert(
        self, branch_id: str, acct_id: str, name: str, acct: Dict
    ) -> Optional[PBBBranchAlert]:
        kyc_expiry = acct.get("kyc_expiry_date")
        if not kyc_expiry:
            return None

        try:
            expiry = date.fromisoformat(kyc_expiry)
            days = (expiry - date.today()).days
        except (ValueError, TypeError):
            return None

        if days > _KYC_WARNING_DAYS or days < 0:
            return None

        return PBBBranchAlert(
            alert_id=f"PBB-KYC-{acct_id}",
            branch_id=branch_id,
            account_id=acct_id,
            client_name=name,
            alert_type="KYC_EXPIRY",
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
            revenue_opportunity_zar=0.0,
        )

    def _salary_capture_alert(
        self, branch_id: str, signal: Dict
    ) -> Optional[PBBBranchAlert]:
        employer_name = signal.get("employer_name", "Unknown")
        employer_id = signal.get("employer_id", "UNK")
        uncaptured = signal.get("uncaptured_employee_count", 0)
        total = signal.get("total_employee_count", 1)

        if uncaptured < 10:
            return None

        revenue = uncaptured * 2500   # R2,500 per employee per year

        return PBBBranchAlert(
            alert_id=f"PBB-SAL-{employer_id}",
            branch_id=branch_id,
            account_id="N/A",
            client_name=employer_name,
            alert_type="SALARY_CAPTURE",
            urgency="MEDIUM",
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
            revenue_opportunity_zar=revenue,
        )
