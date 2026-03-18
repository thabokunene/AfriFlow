"""
@file consistency_checker.py
@description Validates cross-domain data consistency for unified golden records.
    Runs five ordered checks — name match, country match, sector match, revenue
    plausibility, and date coherence — to detect data quality issues, entity
    resolution errors, and genuine business anomalies before records are
    surfaced to relationship managers or downstream NBA scoring models.
@author Thabo Kunene
@created 2026-03-18
"""
# Checks performed (in order):
#   1. Name consistency — entity name matches across domains
#      within acceptable Levenshtein edit-distance tolerance
#   2. Country consistency — domicile country matches
#      across CIB, PBB, and insurance records
#   3. Sector consistency — industry classification
#      matches across CIB and insurance domains
#   4. Revenue plausibility — CIB payment volumes are
#      plausible given PBB salary data (individual clients)
#   5. Date coherence — inception dates and relationship
#      start dates are chronologically coherent and not in the future
#
# DISCLAIMER: This project is not a sanctioned initiative
# of Standard Bank Group, MTN, or any affiliated entity.
# It is a demonstration of concept, domain knowledge,
# and data engineering skill by Thabo Kunene.

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger

logger = get_logger("integration.unified_golden_record.consistency_checker")


class ConsistencyCheckType(Enum):
    """Identifies which of the five consistency checks raised an issue.

    Used for grouping issues in the statistics report and for filtering
    by consuming dashboards that only care about specific check categories.
    """
    NAME_MATCH = "name_match"                   # Levenshtein name comparison
    COUNTRY_MATCH = "country_match"             # ISO-2 domicile country comparison
    SECTOR_MATCH = "sector_match"               # Industry/sector label comparison
    REVENUE_PLAUSIBILITY = "revenue_plausibility"  # CIB volume vs PBB salary ratio
    DATE_COHERENCE = "date_coherence"           # Relationship start/inception date check
    CONTACT_MATCH = "contact_match"             # Reserved: phone/email cross-domain match


class ConsistencySeverity(Enum):
    """Severity level assigned to a detected consistency issue.

    Determines whether the issue blocks golden record updates (ERROR)
    or is logged as advisory context for the RM (INFO/WARNING).
    """
    INFO = "info"           # Informational — no action required
    WARNING = "warning"     # Investigate but does not block the record
    ERROR = "error"         # Blocking — must be resolved before record is surfaced


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
    """Compute Levenshtein edit distance between two strings.

    Case-insensitive and strip-normalised before comparison so that
    "Dangote Industries" and "dangote industries" return distance 0.

    :param s1: First string.
    :param s2: Second string.
    :return: Integer edit distance (0 = identical after normalisation).
    """
    # Normalise: lowercase and strip leading/trailing whitespace
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 0  # Identical after normalisation — no distance needed
    m, n = len(s1), len(s2)
    # Standard DP initialisation: cost of transforming empty prefix to s2 prefix
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]      # Save previous row before overwriting
        dp[0] = i         # Cost of deleting i chars from s1 to reach empty s2 prefix
        for j in range(1, n + 1):
            # Substitution cost: 0 if chars match, 1 if different
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            # Minimum of: delete from s1, insert into s1, or substitute
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev[j - 1] + cost)
    return dp[n]


class ConsistencyChecker:
    """We validate cross-domain consistency for golden records.

    Before a golden record is surfaced to an RM or used in NBA scoring,
    all five consistency checks are run in sequence. Each check may produce
    zero or more ConsistencyIssue objects; blocking issues prevent the
    record from being marked is_consistent=True.

    Attributes:
        issues_log: Accumulated issues across all check() calls for statistics
        _counter: Sequential counter used to generate unique issue IDs
    """

    NAME_EDIT_TOLERANCE = 5     # Max edit distance for name fuzzy match (5 chars)
    REVENUE_RATIO_MAX = 50.0    # CIB/PBB volume ratio above which entity merge error is suspected

    def __init__(self) -> None:
        """Initialise with an empty issues log and a zeroed issue counter."""
        self.issues_log: List[ConsistencyIssue] = []
        self._counter = 0        # Increments with each new issue to guarantee unique IDs
        logger.info("ConsistencyChecker initialized")

    def check(
        self,
        golden_id: str,
        domain_records: Dict[str, Dict[str, Any]],
    ) -> ConsistencyReport:
        """Run all consistency checks for a golden record.

        Executes all five checks and aggregates their issues into a single
        ConsistencyReport. A record is marked is_consistent=False if ANY
        issue has is_blocking=True.

        :param golden_id: Unique golden record identifier.
        :param domain_records: Dict mapping domain name → record data dict.
        :return: ConsistencyReport with all issues, counts, and a pass/fail flag.
        """
        issues: List[ConsistencyIssue] = []
        # Capture which domains were present in this check for the report
        domains_checked = list(domain_records.keys())

        # Run each check in sequence — all five always execute (no short-circuit)
        issues += self._check_name_consistency(golden_id, domain_records)
        issues += self._check_country_consistency(golden_id, domain_records)
        issues += self._check_sector_consistency(golden_id, domain_records)
        issues += self._check_revenue_plausibility(golden_id, domain_records)
        issues += self._check_date_coherence(golden_id, domain_records)

        # Persist issues to the lifetime log for statistics and auditing
        self.issues_log.extend(issues)

        # The record is consistent only if no blocking issues were found
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
        """Check that entity names match across domains within edit-distance tolerance.

        Accepts both 'entity_name' and 'client_name' field keys so the checker
        works with heterogeneous domain schemas. Domains that provide neither
        field are silently skipped.

        :param golden_id: Golden record being checked.
        :param records: Domain record dict from check().
        :return: List of ConsistencyIssue objects for any name mismatches found.
        """
        issues = []
        # Build a dict of domain → name, accepting either field key
        name_by_domain = {
            d: r.get("entity_name") or r.get("client_name")
            for d, r in records.items()
            if (r.get("entity_name") or r.get("client_name"))
        }
        domains = list(name_by_domain.keys())
        # Compare every unique pair of domains (avoid duplicate comparisons)
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                da, db = domains[i], domains[j]
                name_a, name_b = name_by_domain[da], name_by_domain[db]
                dist = _edit_distance(name_a, name_b)
                # Only flag when distance exceeds the tolerance threshold
                if dist > self.NAME_EDIT_TOLERANCE:
                    self._counter += 1
                    # Escalate to ERROR for very large divergences (likely different entities)
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
                        # Block the record if distance is so large it suggests a merge error
                        is_blocking=dist > 20,
                    ))
        return issues

    def _check_country_consistency(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that domicile country matches across domains.

        Accepts both 'country' and 'domicile_country' field keys. A mismatch
        is WARNING (not blocking) because multi-country clients are legitimate
        — the RM needs to decide whether it reflects real presence or a
        data quality problem.

        :param golden_id: Golden record being checked.
        :param records: Domain record dict from check().
        :return: List of ConsistencyIssue objects for any country mismatches.
        """
        issues = []
        # Accept either 'country' or 'domicile_country' field from each domain
        country_by_domain = {
            d: r.get("country") or r.get("domicile_country")
            for d, r in records.items()
            if (r.get("country") or r.get("domicile_country"))
        }
        domains = list(country_by_domain.keys())
        # Compare all unique domain pairs
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                da, db = domains[i], domains[j]
                ca, cb = country_by_domain[da], country_by_domain[db]
                # Case-insensitive comparison; guard against None values
                if ca and cb and ca.upper() != cb.upper():
                    self._counter += 1
                    issues.append(ConsistencyIssue(
                        issue_id=f"CST-{golden_id}-{self._counter:04d}",
                        golden_id=golden_id,
                        check_type=ConsistencyCheckType.COUNTRY_MATCH,
                        severity=ConsistencySeverity.WARNING,  # Advisory, not blocking
                        domain_a=da, domain_b=db,
                        value_a=ca, value_b=cb,
                        description=(
                            f"Country mismatch: {da}='{ca}', {db}='{cb}'. "
                            f"May indicate multi-country presence or data error."
                        ),
                        is_blocking=False,  # Multi-country presence is valid
                    ))
        return issues

    def _check_sector_consistency(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that sector/industry classification is consistent across domains.

        Sector mismatches are typically INFO severity because different domain
        systems may use different classification standards (e.g. 'manufacturing'
        in CIB vs 'industrial' in insurance). This gives RMs visibility without
        blocking operations.

        :param golden_id: Golden record being checked.
        :param records: Domain record dict from check().
        :return: List of ConsistencyIssue objects for any sector mismatches.
        """
        issues = []
        # Accept both 'sector' and 'industry' field keys from domain records
        sector_by_domain = {
            d: r.get("sector") or r.get("industry")
            for d, r in records.items()
            if (r.get("sector") or r.get("industry"))
        }
        domains = list(sector_by_domain.keys())
        # Compare all unique domain pairs for sector/industry label divergence
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                da, db = domains[i], domains[j]
                sa, sb = sector_by_domain[da], sector_by_domain[db]
                # Case-insensitive comparison; skip if either value is None
                if sa and sb and sa.lower() != sb.lower():
                    self._counter += 1
                    issues.append(ConsistencyIssue(
                        issue_id=f"CST-{golden_id}-{self._counter:04d}",
                        golden_id=golden_id,
                        check_type=ConsistencyCheckType.SECTOR_MATCH,
                        severity=ConsistencySeverity.INFO,  # Informational only
                        domain_a=da, domain_b=db,
                        value_a=sa, value_b=sb,
                        description=(
                            f"Sector mismatch: {da}='{sa}', {db}='{sb}'."
                        ),
                        is_blocking=False,  # Sector label differences are not blocking
                    ))
        return issues

    def _check_revenue_plausibility(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check CIB/PBB revenue plausibility to detect corporate-individual entity merges.

        A very high CIB payment volume relative to a PBB salary record suggests
        the entity resolution matched a corporate entity with an individual's
        personal banking record — a classic entity merge error.

        :param golden_id: Golden record being checked.
        :param records: Domain record dict from check().
        :return: List of ConsistencyIssue objects if the ratio exceeds REVENUE_RATIO_MAX.
        """
        issues = []
        # Both CIB and PBB records must be present for this check
        cib = records.get("cib", {})
        pbb = records.get("pbb", {})
        if not cib or not pbb:
            return issues  # Cannot check without both domains

        # Extract the relevant financial fields
        cib_vol = cib.get("annual_payment_volume_usd", 0)
        pbb_salary = pbb.get("annual_salary_usd", 0)

        # Only compute ratio when both values are positive (avoid division by zero)
        if pbb_salary > 0 and cib_vol > 0:
            ratio = cib_vol / pbb_salary
            # A ratio > 50x is implausible for a single individual's salary
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
                    is_blocking=False,  # Advisory — RM should investigate
                ))
        return issues

    def _check_date_coherence(
        self,
        golden_id: str,
        records: Dict[str, Dict[str, Any]],
    ) -> List[ConsistencyIssue]:
        """Check that relationship start and inception dates are chronologically coherent.

        Currently enforces a single rule: no date should be in the future.
        Future dates indicate data entry errors or incorrect timezone handling
        and are blocking because they corrupt the client relationship timeline.

        :param golden_id: Golden record being checked.
        :param records: Domain record dict from check().
        :return: List of ConsistencyIssue objects for any future-dated fields.
        """
        issues = []
        # Domain → field name pairs to extract dates from
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
                # Parse ISO-format strings; skip values that cannot be parsed
                if isinstance(val, str):
                    try:
                        val = datetime.fromisoformat(val)
                    except ValueError:
                        continue  # Unparseable date string — skip rather than crash
                dates[domain] = val

        # Rule: relationship start dates must not be in the future
        now = datetime.utcnow()
        for domain, dt in dates.items():
            if dt > now:
                self._counter += 1
                issues.append(ConsistencyIssue(
                    issue_id=f"CST-{golden_id}-{self._counter:04d}",
                    golden_id=golden_id,
                    check_type=ConsistencyCheckType.DATE_COHERENCE,
                    severity=ConsistencySeverity.ERROR,  # Future date is always a data error
                    domain_a=domain, domain_b="system",
                    value_a=dt.isoformat(), value_b=now.isoformat(),
                    description=f"{domain} date {dt.date()} is in the future.",
                    is_blocking=True,  # Blocking: corrupts the relationship timeline
                ))
        return issues

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics across all consistency checks performed.

        Useful for monitoring dashboards, CI quality gates, and identifying
        which check types fire most frequently in the current data estate.

        :return: Dict with total issue counts broken down by check type and severity.
        """
        # Accumulate issue counts grouped by check type and severity
        by_check: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for issue in self.issues_log:
            # Increment the check-type counter
            by_check[issue.check_type.value] = by_check.get(issue.check_type.value, 0) + 1
            # Increment the severity counter
            by_severity[issue.severity.value] = by_severity.get(issue.severity.value, 0) + 1
        return {
            "total_issues": len(self.issues_log),
            # Blocking issues are the ones that prevent golden record surfacing
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
