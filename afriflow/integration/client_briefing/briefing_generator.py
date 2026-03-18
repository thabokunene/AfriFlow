"""
@file briefing_generator.py
@description Pre-meeting client intelligence briefing generator.

             We auto-generate a structured briefing 30 minutes before
             any calendar event with a client. This is the single most
             impactful RM-facing feature. It transforms the RM from
             someone who asks "how is business?" to someone who walks
             in knowing more about the client's African operations than
             the client's own CFO.

             This is the demo artifact that makes ExCo say "we want this
             for every client meeting starting Monday."

             DISCLAIMER: This project is not sanctioned by, affiliated with, or
             endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
             It is a demonstration of concept, domain knowledge, and technical skill
             built by Thabo Kunene for portfolio and learning purposes only.
@author Thabo Kunene
@created 2026-03-18
"""

# Standard-library imports used for typed data containers and timestamps
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional
import logging
from afriflow.integration.client_briefing.talking_points_engine import ProcessingTimeoutError


# ---------------------------------------------------------------------------
# Data model: lightweight value objects passed to the Jinja2 template layer
# ---------------------------------------------------------------------------

@dataclass
class ChangeEvent:
    """Something that changed since the last meeting."""

    # The originating business domain (e.g. "forex", "cib")
    domain: str
    # Human-readable summary of what changed
    description: str
    # Qualitative scale: "LOW", "MEDIUM", "HIGH", "CRITICAL"
    magnitude: str
    # Whether the change is positive or negative for the client: "up" / "down" / "neutral"
    direction: str


@dataclass
class Opportunity:
    """A revenue opportunity for the RM to discuss."""

    # Rank ordering — 1 is the highest-priority opportunity
    rank: int
    # Short description of the opportunity surface
    description: str
    # Estimated annual revenue impact in South African Rand
    estimated_value_zar: float
    # Which signal engine surfaced this opportunity
    source_signal: str
    # The natural-language prompt the RM can use to open the conversation
    talking_point: str


@dataclass
class RiskAlert:
    """A risk the RM should be aware of."""

    # The domain where the risk originates
    domain: str
    # Plain-English description of the risk condition
    description: str
    # Severity classification: "LOW", "MEDIUM", "HIGH", "CRITICAL"
    severity: str
    # Suggested question or topic the RM can raise with the client
    recommended_discussion_point: str


@dataclass
class ClientBriefing:
    """The complete pre-meeting client briefing."""

    # Unique identifier from the golden-record store
    client_golden_id: str
    # Resolved canonical name used across all domains
    client_name: str
    # Relationship tier: "Platinum", "Gold", "Silver", "Bronze"
    client_tier: str
    # ISO datetime string of the scheduled meeting
    meeting_datetime: str
    # Full name of the assigned relationship manager
    relationship_manager: str

    # Aggregate ZAR value across all five domains
    total_relationship_value_zar: float
    # Top-level health signal sourced from the golden record
    health_status: str
    # Boolean flags indicating which domains have active data for this client
    domains_active: Dict[str, bool]

    # Changes detected since the last recorded meeting with this client
    changes_since_last_meeting: List[ChangeEvent]
    # Top revenue opportunities, capped at 5 in generate()
    top_opportunities: List[Opportunity]
    # Active risk alerts derived from the golden-record signal fields
    risk_alerts: List[RiskAlert]
    # Prepared natural-language talking points for the RM, capped at 5
    talking_points: List[str]

    # ISO date string of the last recorded meeting, or None for first meetings
    last_meeting_date: Optional[str]
    # Timestamp of when this briefing was generated
    generated_at: str

    def render_text(self) -> str:
        """
        Render the briefing as plain text for display or email.

        :return: A formatted multi-line string suitable for terminal
                 output or plain-text email delivery to the RM.
        """

        # Visual separator line used at the top, bottom, and between sections
        separator = "=" * 60

        # Build a compact one-liner showing which domains are active (Y/N)
        domain_flags = ""
        for domain, active in self.domains_active.items():
            flag = "Y" if active else "N"
            domain_flags += f"  {domain.upper()}: {flag}"

        # Summarise what has changed since the last meeting
        changes_text = ""
        if self.changes_since_last_meeting:
            for change in self.changes_since_last_meeting:
                changes_text += (
                    f"  [{change.domain.upper()}] "
                    f"{change.description}\n"
                )
        else:
            # Explicit fallback so the section is never visually empty
            changes_text = "  No significant changes detected.\n"

        # Render each opportunity with its ZAR value and source signal
        opportunities_text = ""
        for opp in self.top_opportunities:
            opportunities_text += (
                f"  {opp.rank}. {opp.description}\n"
                f"     Estimated value: "
                f"R{opp.estimated_value_zar:,.0f}\n"
                f"     Source: {opp.source_signal}\n\n"
            )

        # Render each risk with severity and domain prefix
        risks_text = ""
        if self.risk_alerts:
            for risk in self.risk_alerts:
                risks_text += (
                    f"  [{risk.severity}] [{risk.domain.upper()}] "
                    f"{risk.description}\n"
                    f"  Discuss: {risk.recommended_discussion_point}\n\n"
                )
        else:
            # Explicit fallback so the section is never visually empty
            risks_text = "  No active risk alerts.\n"

        # Number each talking point so the RM can reference them quickly
        talking_points_text = ""
        for i, point in enumerate(self.talking_points, 1):
            talking_points_text += f"  {i}. {point}\n"

        # Guard against None last_meeting_date (first-meeting scenario)
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


# ---------------------------------------------------------------------------
# Generator: orchestrates data retrieval and briefing assembly
# ---------------------------------------------------------------------------

class BriefingGenerator:
    """
    Generates pre-meeting client briefings from the
    unified golden record and cross-domain signal layer.
    """

    def __init__(
        self,
        golden_record_store,
        signal_store,
        shadow_store,
        meeting_history_store,
    ):
        """
        Initialise the generator with injected data-store dependencies.

        :param golden_record_store: Provides resolved client profiles via .get()
        :param signal_store: Provides recent signals via .get_signals_since() and
                             .get_expansion_signals()
        :param shadow_store: Provides data-gap shadows via .get_shadows()
        :param meeting_history_store: Provides meeting history via .get_last_meeting()
        """
        # Store each dependency as an instance attribute for use in generate()
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

        :param client_golden_id: The golden-record identifier for the client
        :param meeting_datetime: ISO datetime string for the scheduled meeting
        :return: A fully populated ClientBriefing dataclass instance
        :raises ValueError: If the client is not found in the golden-record store
        """

        # Resolve the client golden record — raises ValueError if not found
        client = self.golden_record.get(client_golden_id)
        if not client:
            raise ValueError(
                f"Client {client_golden_id} not found "
                f"in golden record"
            )

        # Look up the most recent meeting so we can contextualise changes
        last_meeting = self.meetings.get_last_meeting(
            client_golden_id
        )
        # None if this is the first recorded meeting
        last_meeting_date = (
            last_meeting.get("date") if last_meeting else None
        )

        # Build each briefing section using private helper methods
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
            # Use primary_risk_signal as a proxy for overall relationship health
            health_status=client.get(
                "primary_risk_signal", "STABLE"
            ),
            # Boolean flags per domain, defaulting to False when absent
            domains_active={
                "cib": client.get("has_cib", False),
                "forex": client.get("has_forex", False),
                "insurance": client.get("has_insurance", False),
                "cell": client.get("has_cell", False),
                "pbb": client.get("has_pbb", False),
            },
            changes_since_last_meeting=changes,
            # Cap opportunities at 5 to keep the briefing focused
            top_opportunities=opportunities[:5],
            risk_alerts=risks,
            # Cap talking points at 5 — an RM cannot hold more in a meeting
            talking_points=talking_points[:5],
            last_meeting_date=last_meeting_date,
            # Record exact generation timestamp for audit purposes
            generated_at=datetime.now().isoformat(),
        )

    def _detect_changes(
        self,
        client_golden_id: str,
        since_date: Optional[str],
    ) -> List[ChangeEvent]:
        """
        Detect what changed since the last meeting.

        :param client_golden_id: The client to query signals for
        :param since_date: ISO date string of the last meeting, or None for
                           first meetings
        :return: List of ChangeEvent objects describing signal-driven changes
        """

        # First meeting — no prior baseline to compare against
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
        # Fetch all signals that fired after the last meeting date
        recent_signals = self.signals.get_signals_since(
            client_golden_id, since_date
        )

        # Convert each raw signal dict into a typed ChangeEvent
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
        """
        Find revenue opportunities from signals and shadows.

        :param client_golden_id: The client to query for shadows and signals
        :param client: The golden-record dict for this client
        :return: List of Opportunity objects sorted by estimated_value_zar
                 descending, with ranks re-assigned after sorting
        """

        opportunities = []
        rank = 1  # Will be re-assigned after sorting, but initialised here

        # Data-shadow opportunities: products the client should have but does not
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

        # Expansion-signal opportunities: client entering a new geography
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
                    # Personalised talking point referencing the specific country
                    talking_point=(
                        f"We have noticed your team growing in "
                        f"{signal.get('expansion_country', 'that market')}. "
                        f"Have you considered our working capital "
                        f"and FX solutions there?"
                    ),
                )
            )
            rank += 1

        # Sort by value so the highest-revenue opportunity is always #1
        opportunities.sort(
            key=lambda o: o.estimated_value_zar, reverse=True
        )

        # Re-assign rank integers after sorting to reflect the new order
        for i, opp in enumerate(opportunities, 1):
            opp.rank = i

        return opportunities

    def _assess_risks(
        self,
        client_golden_id: str,
        client: Dict,
    ) -> List[RiskAlert]:
        """
        Assess current risks for the client.

        :param client_golden_id: Client identifier (reserved for future
                                 per-client signal queries)
        :param client: The golden-record dict containing primary_risk_signal
        :return: List of RiskAlert objects; empty list if no risks detected
        """

        risks = []

        # Read the primary risk classification from the golden record
        primary_risk = client.get("primary_risk_signal", "STABLE")

        # ATTRITION_RISK: payment flows suggest the client is migrating away
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

        # UNHEDGED_EXPOSURE: client has FX exposure without adequate forwards
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

        # INSURANCE_GAP: operations in countries with no insurance coverage
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
        """
        Generate natural-language talking points for the RM.

        :param changes: Detected change events (not currently used here but
                        available for future prompt enrichment)
        :param opportunities: Ranked opportunities whose talking_point fields
                              are harvested
        :param risks: Risk alerts whose recommended_discussion_point fields
                      are harvested
        :return: Ordered list of talking-point strings
        """

        points = []

        # Pull the pre-composed talking point from the top 3 opportunities
        for opp in opportunities[:3]:
            if opp.talking_point:
                points.append(opp.talking_point)

        # Append the discussion prompt from the top 2 risk alerts
        for risk in risks[:2]:
            if risk.recommended_discussion_point:
                points.append(risk.recommended_discussion_point)

        return points

    # -----------------------------------------------------------------------
    # Legacy / alternate implementation below — kept for reference
    # The section below represents an earlier implementation variant with a
    # slightly different ClientBriefing schema (DomainSnapshot-based). It is
    # retained here because the tests may exercise some of its methods.
    # -----------------------------------------------------------------------

    domain_snapshots: List["DomainSnapshot"]          # type: ignore[name-defined]
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

        # Map health status codes to short bracket icons for quick scanning
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

        # Build a compact domain status bar from the snapshot list
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

    def __init__(self, talking_points_engine=None, enable_talking_points_engine: bool = False):
        self._engine = talking_points_engine
        self._enable_engine = bool(enable_talking_points_engine)
        self._log = logging.getLogger(__name__)

    def generate(
        self,
        golden_id: str,
        unified_record: Dict,
        recent_signals: List[Dict],
        shadow_gaps: List[Dict],
        meeting_datetime: Optional[str] = None,
        previous_meeting_date: Optional[str] = None,
    ) -> ClientBriefing:
        """Generate a complete client briefing with optional TalkingPointsEngine enhancement."""

        changes = self._extract_changes(recent_signals, previous_meeting_date)
        opportunities = self._extract_opportunities(recent_signals, unified_record)
        risks = self._extract_risks(unified_record, recent_signals)

        base_points = self._generate_talking_points(changes, opportunities, risks)
        points = base_points

        if self._enable_engine and self._engine:
            try:
                texts = [s.get("description", "") for s in recent_signals if s.get("description")]
                input_text = "\n".join(texts).strip()
                if input_text:
                    out = self._engine.process(input_text, output_format="json")
                    if isinstance(out, dict) and out.get("points"):
                        candidate_points = [p.get("text", "") for p in out["points"] if p.get("text")]
                        if candidate_points:
                            points = candidate_points
                        else:
                            points = base_points
                    else:
                        points = base_points
                else:
                    points = base_points
            except ProcessingTimeoutError:
                self._log.warning("TalkingPointsEngine timeout; rolling back to baseline points")
                points = base_points
            except Exception as e:
                self._log.error("TalkingPointsEngine failure: %s", str(e))
                points = base_points

        return ClientBriefing(
            client_golden_id=golden_id,
            client_name=unified_record.get("canonical_name", "Unknown"),
            client_tier=unified_record.get("client_tier", "Unknown"),
            meeting_datetime=meeting_datetime or datetime.now().isoformat(timespec="minutes"),
            relationship_manager=unified_record.get("relationship_manager", "Unassigned"),
            total_relationship_value_zar=unified_record.get("total_relationship_value_zar", 0),
            domains_active={
                "cib": unified_record.get("has_cib", False),
                "forex": unified_record.get("has_forex", False),
                "insurance": unified_record.get("has_insurance", False),
                "cell": unified_record.get("has_cell", False),
                "pbb": unified_record.get("has_pbb", False),
            },
            health_status=unified_record.get("primary_risk_signal", "STABLE"),
            changes_since_last_meeting=changes,
            top_opportunities=opportunities,
            risk_alerts=risks,
            talking_points=points[:5],
            last_meeting_date=previous_meeting_date,
            generated_at=datetime.now().isoformat(),
        )

    def _build_domain_snapshots(
        self, golden_record: Dict
    ) -> List["DomainSnapshot"]:  # type: ignore[name-defined]
        """
        Build DomainSnapshot objects from boolean golden-record flags.

        :param golden_record: The client golden-record dict
        :return: Ordered list of DomainSnapshot objects, one per domain
        """
        snapshots = []
        # Map human-readable domain names to their golden-record flag keys
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
                DomainSnapshot(  # type: ignore[name-defined]
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
        """
        Extract plain-text change descriptions from recent signals.

        :param recent_signals: List of signal dicts from the signal store
        :param previous_meeting_date: ISO date of last meeting (not currently
                                      used in filtering but kept for future use)
        :return: Up to 5 change description strings
        """
        changes = []
        for signal in recent_signals:
            desc = signal.get("description", "")
            if desc:
                changes.append(desc)
        # Cap at 5 changes so the briefing remains concise
        return changes[:5]

    def _extract_opportunities(
        self, recent_signals: List[Dict], golden_record: Dict
    ) -> List[Dict]:
        """
        Build ranked revenue opportunities from signals and product gaps.

        :param recent_signals: Raw signals from the signal store
        :param golden_record: Client golden-record dict for gap detection
        :return: List of opportunity dicts sorted by value_zar descending
        """
        opportunities = []
        # Expansion signals are the highest-quality revenue leads
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

        # If the client has no insurance, add a standing product-gap opportunity
        if not golden_record.get("has_insurance", False):
            opportunities.append({
                "description": (
                    "Insurance coverage gap across "
                    "operations"
                ),
                "value_zar": 500_000,  # Placeholder estimate in ZAR
            })

        return sorted(
            opportunities,
            key=lambda o: o["value_zar"],
            reverse=True,  # Highest-value opportunity first
        )

    def _extract_risks(
        self, golden_record: Dict, recent_signals: List[Dict]
    ) -> List[str]:
        """
        Convert golden-record risk signals into plain-text risk strings.

        :param golden_record: Client golden-record dict
        :param recent_signals: Recent signals (reserved for future enrichment)
        :return: List of risk description strings
        """
        risks = []
        # Read the primary risk classification stored in the golden record
        risk_signal = golden_record.get(
            "primary_risk_signal", ""
        )
        # Unhedged FX exposure: quantify the hedge ratio for the RM
        if risk_signal == "UNHEDGED_EXPOSURE":
            hedge_ratio = golden_record.get(
                "forex_hedge_ratio_pct", 0
            )
            risks.append(
                f"FX exposure only {hedge_ratio}% hedged. "
                f"Review hedging strategy."
            )
        # Attrition risk: payment volume has been declining toward competitors
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
        """
        Compose natural-language talking points for the RM.

        :param changes: Plain-text change descriptions (reserved for future use)
        :param opportunities: Ranked opportunity dicts
        :param risks: Plain-text risk descriptions
        :return: List of conversational talking-point strings
        """
        points = []
        # If there are opportunities, open with a growth-oriented conversation starter
        if opportunities:
            top = opportunities[0]
            points.append(
                f"\"We have noticed some interesting "
                f"developments in your operations that "
                f"suggest an opportunity to support "
                f"your growth...\""
            )
        # If there are risks, pivot to a protective / advisory framing
        if risks:
            points.append(
                f"\"We want to make sure your currency "
                f"exposures are well managed given "
                f"recent market movements...\""
            )
        # Fallback: always give the RM at least one opener
        if not points:
            points.append(
                "\"How are your expansion plans "
                "progressing? We have some ideas on "
                "how we can add value...\""
            )
        return points
