"""
PRE MEETING CLIENT INTELLIGENCE BRIEFING

We auto generate a structured briefing 30 minutes before
any calendar event with a client. This is the single most
impactful RM facing feature. It transforms the RM from
someone who asks "how is business?" to someone who walks
in knowing more about the client's African operations than
the client's own CFO.

This is the demo artifact that makes ExCo say "we want this
for every client meeting starting Monday."

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional


@dataclass
class ChangeEvent:
    """Something that changed since the last meeting."""

    domain: str
    description: str
    magnitude: str
    direction: str


@dataclass
class Opportunity:
    """A revenue opportunity for the RM to discuss."""

    rank: int
    description: str
    estimated_value_zar: float
    source_signal: str
    talking_point: str


@dataclass
class RiskAlert:
    """A risk the RM should be aware of."""

    domain: str
    description: str
    severity: str
    recommended_discussion_point: str


@dataclass
class ClientBriefing:
    """The complete pre meeting client briefing."""

    client_golden_id: str
    client_name: str
    client_tier: str
    meeting_datetime: str
    relationship_manager: str

    total_relationship_value_zar: float
    health_status: str
    domains_active: Dict[str, bool]

    changes_since_last_meeting: List[ChangeEvent]
    top_opportunities: List[Opportunity]
    risk_alerts: List[RiskAlert]
    talking_points: List[str]

    last_meeting_date: Optional[str]
    generated_at: str

    def render_text(self) -> str:
        """Render the briefing as plain text for display or email."""

        separator = "=" * 60

        domain_flags = ""
        for domain, active in self.domains_active.items():
            flag = "Y" if active else "N"
            domain_flags += f"  {domain.upper()}: {flag}"

        changes_text = ""
        if self.changes_since_last_meeting:
            for change in self.changes_since_last_meeting:
                changes_text += (
                    f"  [{change.domain.upper()}] "
                    f"{change.description}\n"
                )
        else:
            changes_text = "  No significant changes detected.\n"

        opportunities_text = ""
        for opp in self.top_opportunities:
            opportunities_text += (
                f"  {opp.rank}. {opp.description}\n"
                f"     Estimated value: "
                f"R{opp.estimated_value_zar:,.0f}\n"
                f"     Source: {opp.source_signal}\n\n"
            )

        risks_text = ""
        if self.risk_alerts:
            for risk in self.risk_alerts:
                risks_text += (
                    f"  [{risk.severity}] [{risk.domain.upper()}] "
                    f"{risk.description}\n"
                    f"  Discuss: {risk.recommended_discussion_point}\n\n"
                )
        else:
            risks_text = "  No active risk alerts.\n"

        talking_points_text = ""
        for i, point in enumerate(self.talking_points, 1):
            talking_points_text += f"  {i}. {point}\n"

        last_meeting = self.last_meeting_date or "Unknown"

        return f"""{separator}
CLIENT BRIEFING: {self.client_name}
Meeting: {self.meeting_datetime}
{separator}

RELATIONSHIP SNAPSHOT
  Total Value: R{self.total_relationship_value_zar:,.0f}
  Health: {self.health_status}
  Tier: {self.client_tier}
  Domains Active:{domain_flags}

WHAT CHANGED SINCE LAST MEETING ({last_meeting})
{changes_text}
TOP OPPORTUNITIES
{opportunities_text}
RISK ALERTS
{risks_text}
SUGGESTED TALKING POINTS
{talking_points_text}
{separator}
Generated: {self.generated_at}
Prepared for: {self.relationship_manager}
{separator}
"""


class BriefingGenerator:
    """
    Generates pre meeting client briefings from the
    unified golden record and cross domain signal layer.
    """

    def __init__(
        self,
        golden_record_store,
        signal_store,
        shadow_store,
        meeting_history_store,
    ):
        self.golden_record = golden_record_store
        self.signals = signal_store
        self.shadows = shadow_store
        self.meetings = meeting_history_store

    def generate(
        self,
        client_golden_id: str,
        meeting_datetime: str,
    ) -> ClientBriefing:
        """
        Generate a complete client briefing.

        We pull data from:
        - Golden record (relationship snapshot)
        - Signal store (recent signals for this client)
        - Shadow store (data gaps and opportunities)
        - Meeting history (what changed since last time)
        """

        client = self.golden_record.get(client_golden_id)
        if not client:
            raise ValueError(
                f"Client {client_golden_id} not found "
                f"in golden record"
            )

        last_meeting = self.meetings.get_last_meeting(
            client_golden_id
        )
        last_meeting_date = (
            last_meeting.get("date") if last_meeting else None
        )

        changes = self._detect_changes(
            client_golden_id, last_meeting_date
        )
        opportunities = self._find_opportunities(
            client_golden_id, client
        )
        risks = self._assess_risks(client_golden_id, client)
        talking_points = self._generate_talking_points(
            changes, opportunities, risks
        )

        return ClientBriefing(
            client_golden_id=client_golden_id,
            client_name=client.get("canonical_name", "Unknown"),
            client_tier=client.get("client_tier", "Unknown"),
            meeting_datetime=meeting_datetime,
            relationship_manager=client.get(
                "relationship_manager", "Unassigned"
            ),
            total_relationship_value_zar=client.get(
                "total_relationship_value_zar", 0
            ),
            health_status=client.get(
                "primary_risk_signal", "STABLE"
            ),
            domains_active={
                "cib": client.get("has_cib", False),
                "forex": client.get("has_forex", False),
                "insurance": client.get("has_insurance", False),
                "cell": client.get("has_cell", False),
                "pbb": client.get("has_pbb", False),
            },
            changes_since_last_meeting=changes,
            top_opportunities=opportunities[:5],
            risk_alerts=risks,
            talking_points=talking_points[:5],
            last_meeting_date=last_meeting_date,
            generated_at=datetime.now().isoformat(),
        )

    def _detect_changes(
        self,
        client_golden_id: str,
        since_date: Optional[str],
    ) -> List[ChangeEvent]:
        """Detect what changed since the last meeting."""

        if not since_date:
            return [
                ChangeEvent(
                    domain="system",
                    description=(
                        "First meeting. Full relationship "
                        "profile available."
                    ),
                    magnitude="N/A",
                    direction="neutral",
                )
            ]

        changes = []
        recent_signals = self.signals.get_signals_since(
            client_golden_id, since_date
        )

        for signal in recent_signals:
            changes.append(
                ChangeEvent(
                    domain=signal.get("source_domain", "unknown"),
                    description=signal.get("description", ""),
                    magnitude=signal.get("magnitude", "unknown"),
                    direction=signal.get("direction", "neutral"),
                )
            )

        return changes

    def _find_opportunities(
        self,
        client_golden_id: str,
        client: Dict,
    ) -> List[Opportunity]:
        """Find revenue opportunities from signals and shadows."""

        opportunities = []
        rank = 1

        shadows = self.shadows.get_shadows(client_golden_id)
        for shadow in shadows:
            if shadow.get("estimated_revenue_opportunity_zar", 0) > 0:
                opportunities.append(
                    Opportunity(
                        rank=rank,
                        description=shadow.get(
                            "recommended_action", ""
                        ),
                        estimated_value_zar=shadow.get(
                            "estimated_revenue_opportunity_zar", 0
                        ),
                        source_signal=shadow.get("category", ""),
                        talking_point=shadow.get(
                            "source_evidence", ""
                        ),
                    )
                )
                rank += 1

        expansion_signals = self.signals.get_expansion_signals(
            client_golden_id
        )
        for signal in expansion_signals:
            opportunities.append(
                Opportunity(
                    rank=rank,
                    description=(
                        f"Expansion into "
                        f"{signal.get('expansion_country', 'unknown')} "
                        f"detected"
                    ),
                    estimated_value_zar=signal.get(
                        "estimated_opportunity_zar", 0
                    ),
                    source_signal="expansion_signal",
                    talking_point=(
                        f"We have noticed your team growing in "
                        f"{signal.get('expansion_country', 'that market')}. "
                        f"Have you considered our working capital "
                        f"and FX solutions there?"
                    ),
                )
            )
            rank += 1

        opportunities.sort(
            key=lambda o: o.estimated_value_zar, reverse=True
        )

        for i, opp in enumerate(opportunities, 1):
            opp.rank = i

        return opportunities

    def _assess_risks(
        self,
        client_golden_id: str,
        client: Dict,
    ) -> List[RiskAlert]:
        """Assess current risks for the client."""

        risks = []

        primary_risk = client.get("primary_risk_signal", "STABLE")

        if primary_risk == "ATTRITION_RISK":
            risks.append(
                RiskAlert(
                    domain="cib",
                    description=(
                        "Payment flow patterns suggest possible "
                        "relationship migration."
                    ),
                    severity="HIGH",
                    recommended_discussion_point=(
                        "Are we meeting your expectations on "
                        "turnaround times and pricing?"
                    ),
                )
            )

        if primary_risk == "UNHEDGED_EXPOSURE":
            risks.append(
                RiskAlert(
                    domain="forex",
                    description=(
                        "Significant unhedged foreign currency "
                        "exposure detected."
                    ),
                    severity="MEDIUM",
                    recommended_discussion_point=(
                        "Given recent currency volatility, "
                        "have you reviewed your hedging strategy?"
                    ),
                )
            )

        if primary_risk == "INSURANCE_GAP":
            risks.append(
                RiskAlert(
                    domain="insurance",
                    description=(
                        "Operations in one or more countries "
                        "lack adequate insurance coverage."
                    ),
                    severity="MEDIUM",
                    recommended_discussion_point=(
                        "We have noticed your operations have "
                        "expanded but insurance coverage has "
                        "not kept pace. Can we help?"
                    ),
                )
            )

        return risks

    def _generate_talking_points(
        self,
        changes: List[ChangeEvent],
        opportunities: List[Opportunity],
        risks: List[RiskAlert],
    ) -> List[str]:
        """Generate natural language talking points for the RM."""

        points = []

        for opp in opportunities[:3]:
            if opp.talking_point:
                points.append(opp.talking_point)

        for risk in risks[:2]:
            if risk.recommended_discussion_point:
                points.append(risk.recommended_discussion_point)

        return points

    domain_snapshots: List[DomainSnapshot]
    changes_since_last_meeting: List[str]
    top_opportunities: List[Dict]
    risk_alerts: List[str]
    talking_points: List[str]

    def render_text(self) -> str:
        """We render the briefing as a plain text document
        suitable for mobile display or email."""

        separator = "=" * 58
        sub_separator = "-" * 58

        lines = [
            separator,
            f"CLIENT BRIEFING: {self.client_name}",
            f"Meeting: {self.meeting_date} {self.meeting_time}",
            separator,
            "",
            "RELATIONSHIP SNAPSHOT",
        ]

        health_icon = {
            "STABLE": "[OK]",
            "ATTENTION": "[!!]",
            "AT_RISK": "[XX]",
        }.get(self.health_status, "[??]")

        lines.append(
            f"  Total Value: "
            f"R{self.total_relationship_value_zar:,.0f} "
            f"across {self.domains_active} domains"
        )
        lines.append(
            f"  Health: {health_icon} {self.health_status}"
        )

        domain_status_parts = []
        for snap in self.domain_snapshots:
            icon = "[x]" if snap.is_active else "[ ]"
            domain_status_parts.append(
                f"{snap.domain} {icon}"
            )
        lines.append(
            "  Domains: " + " | ".join(domain_status_parts)
        )

        if self.changes_since_last_meeting:
            lines.append("")
            lines.append("WHAT CHANGED SINCE LAST MEETING")
            for change in self.changes_since_last_meeting:
                lines.append(f"  * {change}")

        if self.top_opportunities:
            lines.append("")
            lines.append("TOP OPPORTUNITIES")
            for i, opp in enumerate(
                self.top_opportunities[:3], 1
            ):
                lines.append(
                    f"  {i}. {opp['description']} "
                    f"-- est. R{opp['value_zar']:,.0f}"
                )

        if self.risk_alerts:
            lines.append("")
            lines.append("RISK ALERTS")
            for alert in self.risk_alerts:
                lines.append(f"  [!] {alert}")

        if self.talking_points:
            lines.append("")
            lines.append("SUGGESTED TALKING POINTS")
            for i, point in enumerate(
                self.talking_points[:3], 1
            ):
                lines.append(f"  {i}. {point}")

        lines.append("")
        lines.append(separator)
        lines.append(
            f"Generated: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')} "
            f"| AfriFlow Intelligence Platform"
        )
        lines.append(separator)

        return "\n".join(lines)


class BriefingGenerator:
    """We generate pre-meeting client intelligence
    briefings by combining data from the unified golden
    record, cross-domain signal history, and opportunity
    pipeline.

    In production, this generator would query the gold
    layer via the API service. In this demonstration, we
    accept structured inputs directly.
    """

    def generate(
        self,
        golden_record: Dict,
        recent_signals: List[Dict],
        meeting_info: Dict,
        previous_meeting_date: Optional[str] = None,
    ) -> ClientBriefing:
        """We generate a complete client briefing from
        the golden record and recent signals."""

        snapshots = self._build_domain_snapshots(
            golden_record
        )
        changes = self._extract_changes(
            recent_signals, previous_meeting_date
        )
        opportunities = self._extract_opportunities(
            recent_signals, golden_record
        )
        risks = self._extract_risks(
            golden_record, recent_signals
        )
        points = self._generate_talking_points(
            changes, opportunities, risks
        )

        return ClientBriefing(
            golden_id=golden_record["golden_id"],
            client_name=golden_record["canonical_name"],
            client_tier=golden_record.get(
                "client_tier", "Unknown"
            ),
            relationship_manager=golden_record.get(
                "relationship_manager", "Unassigned"
            ),
            meeting_date=meeting_info.get(
                "date",
                date.today().isoformat(),
            ),
            meeting_time=meeting_info.get("time", "TBD"),
            total_relationship_value_zar=golden_record.get(
                "total_relationship_value_zar", 0
            ),
            domains_active=golden_record.get(
                "domains_active", 0
            ),
            health_status=golden_record.get(
                "primary_risk_signal", "STABLE"
            ),
            domain_snapshots=snapshots,
            changes_since_last_meeting=changes,
            top_opportunities=opportunities,
            risk_alerts=risks,
            talking_points=points,
        )

    def _build_domain_snapshots(
        self, golden_record: Dict
    ) -> List[DomainSnapshot]:
        snapshots = []
        domain_map = {
            "CIB": "has_cib",
            "Forex": "has_forex",
            "Insurance": "has_insurance",
            "Cell": "has_cell",
            "PBB": "has_pbb",
        }
        for domain_name, flag_key in domain_map.items():
            is_active = golden_record.get(flag_key, False)
            snapshots.append(
                DomainSnapshot(
                    domain=domain_name,
                    is_active=is_active,
                    headline_metric="Active" if is_active else "No data",
                    change_since_last_meeting=None,
                )
            )
        return snapshots

    def _extract_changes(
        self,
        recent_signals: List[Dict],
        previous_meeting_date: Optional[str],
    ) -> List[str]:
        changes = []
        for signal in recent_signals:
            desc = signal.get("description", "")
            if desc:
                changes.append(desc)
        return changes[:5]

    def _extract_opportunities(
        self, recent_signals: List[Dict], golden_record: Dict
    ) -> List[Dict]:
        opportunities = []
        for signal in recent_signals:
            if signal.get("signal_type") == "EXPANSION":
                opportunities.append({
                    "description": signal.get(
                        "description",
                        "Expansion opportunity detected",
                    ),
                    "value_zar": signal.get(
                        "estimated_opportunity_zar", 0
                    ),
                })

        if not golden_record.get("has_insurance", False):
            opportunities.append({
                "description": (
                    "Insurance coverage gap across "
                    "operations"
                ),
                "value_zar": 500_000,
            })

        return sorted(
            opportunities,
            key=lambda o: o["value_zar"],
            reverse=True,
        )

    def _extract_risks(
        self, golden_record: Dict, recent_signals: List[Dict]
    ) -> List[str]:
        risks = []
        risk_signal = golden_record.get(
            "primary_risk_signal", ""
        )
        if risk_signal == "UNHEDGED_EXPOSURE":
            hedge_ratio = golden_record.get(
                "forex_hedge_ratio_pct", 0
            )
            risks.append(
                f"FX exposure only {hedge_ratio}% hedged. "
                f"Review hedging strategy."
            )
        if risk_signal == "ATTRITION_RISK":
            risks.append(
                "Payment patterns indicate possible "
                "relationship migration to competitor."
            )
        return risks

    def _generate_talking_points(
        self,
        changes: List[str],
        opportunities: List[Dict],
        risks: List[str],
    ) -> List[str]:
        points = []
        if opportunities:
            top = opportunities[0]
            points.append(
                f"\"We have noticed some interesting "
                f"developments in your operations that "
                f"suggest an opportunity to support "
                f"your growth...\""
            )
        if risks:
            points.append(
                f"\"We want to make sure your currency "
                f"exposures are well managed given "
                f"recent market movements...\""
            )
        if not points:
            points.append(
                "\"How are your expansion plans "
                "progressing? We have some ideas on "
                "how we can add value...\""
            )
        return points
