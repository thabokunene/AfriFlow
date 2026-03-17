"""
Unified Golden Record - Consistency Checker

We validate that cross-domain data for a unified golden
record is internally consistent. Inconsistencies can
indicate data quality issues, entity resolution errors,
or genuine business anomalies.

Checks performed:
  1. Name consistency — entity name matches across domains
     within acceptable edit-distance tolerance
  2. Country consistency — domicile country matches
     across CIB, PBB, and insurance records
  3. Sector consistency — industry classification
     matches across CIB and insurance domains
  4. Revenue plausibility — CIB payment volumes are
     plausible given PBB salary data (individual clients)
  5. Date consistency — inception dates and relationship
     start dates are chronologically coherent

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger

logger = get_logger("integration.unified_golden_record.consistency_checker")


class ConsistencyCheckType(Enum):
    """Type of consistency check."""
    NAME_MATCH = "name_match"
    COUNTRY_MATCH = "country_match"
    SECTOR_MATCH = "sector_match"
    REVENUE_PLAUSIBILITY = "revenue_plausibility"
    DATE_COHERENCE = "date_coherence"
    CONTACT_MATCH = "contact_match"


class ConsistencySeverity(Enum):
    """Severity of a consistency issue."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ConsistencyIssue:
    """
    A detected inconsistency between domain records.

    Attributes:
        issue_id: Unique issue identifier
        golden_id: Golden record being checked
        check_type: Type of consistency check
        severity: Severity of the issue
        domain_a: First domain in the comparison
        domain_b: Second domain in the comparison
        value_a: Value from domain_a
        value_b: Value from domain_b
        description: Human-readable description
        is_blocking: Whether this prevents golden record update
    """
    issue_id: str
    golden_id: str
    check_type: ConsistencyCheckType
    severity: ConsistencySeverity
    domain_a: str
    domain_b: str
    value_a: Any
    value_b: Any
    description: str
    is_blocking: bool = False


@dataclass
class ConsistencyReport:
    """
    Full consistency report for a golden record.

    Attributes:
        golden_id: Golden record identifier
        is_consistent: True if no blocking issues found
        issues: List of all issues detected
        checked_at: When the check was performed
        domains_checked: Domains included in the check
    """
    golden_id: str
    is_consistent: bool
    issues: List[ConsistencyIssue]
    checked_at: datetime
    domains_checked: List[str]
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def __post_init__(self) -> None:
        self.error_count = sum(
            1 for i in self.issues if i.severity == ConsistencySeverity.ERROR
        )
        self.warning_count = sum(
            1 for i in self.issues if i.severity == ConsistencySeverity.WARNING
        )
        self.info_count = sum(
            1 for i in self.issues if i.severity == ConsistencySeverity.INFO
        )


def _edit_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 0
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev[j - 1] + cost)
    return dp[n]


class ConsistencyChecker:
    """
    We validate cross-domain consistency for golden records.

    Attributes:
        name_tolerance: Max edit distance for name match (chars)
        issues_log: All issues found across all checks
        issue_counter: Sequential counter for issue IDs
    """

    NAME_EDIT_TOLERANCE = 5     # Max edit distance for name fuzzy match
    REVENUE_RATIO_MAX = 50.0    # Max CIB/PBB revenue ratio before flagging

    def __init__(self) -> None:
        self.issues_log: List[ConsistencyIssue] = []
        self._counter = 0
        logger.info("ConsistencyChecker initialized")

    def check(
        self,
        golden_id: str,
        domain_records: Dict[str, Dict[str, Any]],
    ) -> ConsistencyReport:
        """
        Run all consistency checks for a golden record.

        Args:
            golden_id: Golden record identifier
            domain_records: Dict of domain → record data

        Returns:
            ConsistencyReport with all issues
        """
        issues: List[ConsistencyIssue] = []
        domains_checked = list(domain_records.keys())

        # Run each check
        issues += self._check_name_consistency(golden_id, domain_records)
        issues += self._check_country_consistency(golden_id, domain_records)
        issues += self._check_sector_consistency(golden_id, domain_records)
        issues += self._check_revenue_plausibility(golden_id, domain_records)
        issues += self._check_date_coherence(golden_id, domain_records)

        self.issues_log.extend(issues)

        is_consistent = not any(i.is_blocking for i in issues)
        report = ConsistencyReport(
            golden_id=golden_id,
            is_consistent=is_consistent,
            issues=issues,
            checked_at=datetime.utcnow(),
            domains_checked=domains_checked,
        )

        logger.info(
            f"Consistency check for {golden_id}: "
            f"{'PASS' if is_consistent else 'FAIL'} "
            f"({report.error_count} errors, {report.warning_count} warnings)"
        )
        return report

    def _check_name_consistency(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that entity names match across domains."""
        issues = []
        name_by_domain = {
            d: r.get("entity_name") or r.get("client_name")
            for d, r in records.items()
            if (r.get("entity_name") or r.get("client_name"))
        }
        domains = list(name_by_domain.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                da, db = domains[i], domains[j]
                name_a, name_b = name_by_domain[da], name_by_domain[db]
                dist = _edit_distance(name_a, name_b)
                if dist > self.NAME_EDIT_TOLERANCE:
                    self._counter += 1
                    severity = (
                        ConsistencySeverity.ERROR if dist > 15
                        else ConsistencySeverity.WARNING
                    )
                    issues.append(ConsistencyIssue(
                        issue_id=f"CST-{golden_id}-{self._counter:04d}",
                        golden_id=golden_id,
                        check_type=ConsistencyCheckType.NAME_MATCH,
                        severity=severity,
                        domain_a=da, domain_b=db,
                        value_a=name_a, value_b=name_b,
                        description=(
                            f"Name mismatch between {da} ('{name_a}') "
                            f"and {db} ('{name_b}'). Edit distance: {dist}."
                        ),
                        is_blocking=dist > 20,
                    ))
        return issues

    def _check_country_consistency(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that domicile country matches across domains."""
        issues = []
        country_by_domain = {
            d: r.get("country") or r.get("domicile_country")
            for d, r in records.items()
            if (r.get("country") or r.get("domicile_country"))
        }
        domains = list(country_by_domain.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                da, db = domains[i], domains[j]
                ca, cb = country_by_domain[da], country_by_domain[db]
                if ca and cb and ca.upper() != cb.upper():
                    self._counter += 1
                    issues.append(ConsistencyIssue(
                        issue_id=f"CST-{golden_id}-{self._counter:04d}",
                        golden_id=golden_id,
                        check_type=ConsistencyCheckType.COUNTRY_MATCH,
                        severity=ConsistencySeverity.WARNING,
                        domain_a=da, domain_b=db,
                        value_a=ca, value_b=cb,
                        description=(
                            f"Country mismatch: {da}='{ca}', {db}='{cb}'. "
                            f"May indicate multi-country presence or data error."
                        ),
                        is_blocking=False,
                    ))
        return issues

    def _check_sector_consistency(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that sector/industry classification is consistent."""
        issues = []
        sector_by_domain = {
            d: r.get("sector") or r.get("industry")
            for d, r in records.items()
            if (r.get("sector") or r.get("industry"))
        }
        domains = list(sector_by_domain.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                da, db = domains[i], domains[j]
                sa, sb = sector_by_domain[da], sector_by_domain[db]
                if sa and sb and sa.lower() != sb.lower():
                    self._counter += 1
                    issues.append(ConsistencyIssue(
                        issue_id=f"CST-{golden_id}-{self._counter:04d}",
                        golden_id=golden_id,
                        check_type=ConsistencyCheckType.SECTOR_MATCH,
                        severity=ConsistencySeverity.INFO,
                        domain_a=da, domain_b=db,
                        value_a=sa, value_b=sb,
                        description=(
                            f"Sector mismatch: {da}='{sa}', {db}='{sb}'."
                        ),
                        is_blocking=False,
                    ))
        return issues

    def _check_revenue_plausibility(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check CIB/PBB revenue plausibility (corporate vs individual)."""
        issues = []
        cib = records.get("cib", {})
        pbb = records.get("pbb", {})
        if not cib or not pbb:
            return issues

        cib_vol = cib.get("annual_payment_volume_usd", 0)
        pbb_salary = pbb.get("annual_salary_usd", 0)

        if pbb_salary > 0 and cib_vol > 0:
            ratio = cib_vol / pbb_salary
            if ratio > self.REVENUE_RATIO_MAX:
                self._counter += 1
                issues.append(ConsistencyIssue(
                    issue_id=f"CST-{golden_id}-{self._counter:04d}",
                    golden_id=golden_id,
                    check_type=ConsistencyCheckType.REVENUE_PLAUSIBILITY,
                    severity=ConsistencySeverity.WARNING,
                    domain_a="cib", domain_b="pbb",
                    value_a=cib_vol, value_b=pbb_salary,
                    description=(
                        f"CIB volume (USD {cib_vol:,.0f}) is "
                        f"{ratio:.0f}x PBB salary (USD {pbb_salary:,.0f}). "
                        f"May indicate entity merge error."
                    ),
                    is_blocking=False,
                ))
        return issues

    def _check_date_coherence(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that relationship dates are chronologically coherent."""
        issues = []
        date_fields = [
            ("cib", "relationship_start_date"),
            ("pbb", "account_open_date"),
            ("insurance", "first_policy_date"),
        ]
        dates = {}
        for domain, field_name in date_fields:
            rec = records.get(domain, {})
            val = rec.get(field_name) if rec else None
            if val:
                if isinstance(val, str):
                    try:
                        val = datetime.fromisoformat(val)
                    except ValueError:
                        continue
                dates[domain] = val

        # Check: no date should be in the future
        now = datetime.utcnow()
        for domain, dt in dates.items():
            if dt > now:
                self._counter += 1
                issues.append(ConsistencyIssue(
                    issue_id=f"CST-{golden_id}-{self._counter:04d}",
                    golden_id=golden_id,
                    check_type=ConsistencyCheckType.DATE_COHERENCE,
                    severity=ConsistencySeverity.ERROR,
                    domain_a=domain, domain_b="system",
                    value_a=dt.isoformat(), value_b=now.isoformat(),
                    description=f"{domain} date {dt.date()} is in the future.",
                    is_blocking=True,
                ))
        return issues

    def get_statistics(self) -> Dict[str, Any]:
        """Get consistency check statistics."""
        by_check: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for issue in self.issues_log:
            by_check[issue.check_type.value] = by_check.get(issue.check_type.value, 0) + 1
            by_severity[issue.severity.value] = by_severity.get(issue.severity.value, 0) + 1
        return {
            "total_issues": len(self.issues_log),
            "blocking_issues": sum(1 for i in self.issues_log if i.is_blocking),
            "by_check_type": by_check,
            "by_severity": by_severity,
        }


if __name__ == "__main__":
    checker = ConsistencyChecker()

    records = {
        "cib": {
            "entity_name": "Dangote Industries Ltd",
            "country": "NG",
            "sector": "manufacturing",
            "annual_payment_volume_usd": 5_000_000,
            "relationship_start_date": "2018-03-01",
        },
        "insurance": {
            "entity_name": "Dangote Indstries",  # typo
            "country": "NG",
            "sector": "industrial",
            "first_policy_date": "2019-06-15",
        },
        "pbb": {
            "entity_name": "Aliko Dangote",
            "country": "NG",
            "annual_salary_usd": 500_000,
            "account_open_date": "2015-01-10",
        },
    }

    report = checker.check("GLD-001", records)
    print(f"Consistent: {report.is_consistent}")
    print(f"Errors: {report.error_count}, Warnings: {report.warning_count}")
    for issue in report.issues:
        print(f"  [{issue.severity.value}] {issue.check_type.value}: {issue.description}")
