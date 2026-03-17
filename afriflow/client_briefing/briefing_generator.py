"""
Client Briefing Generator

We generate a structured 2-minute briefing card for
Relationship Managers before every client meeting.
This pulls from the unified golden record, cross-domain
signals, data shadow gaps, seasonal context, and
currency event impact.

This is the feature that makes an ExCo member say
"I want this for every client meeting starting Monday."

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging

from afriflow.exceptions import BriefingGenerationError
from afriflow.logging_config import get_logger

logger = get_logger("client_briefing.generator")


@dataclass
class ChangeEvent:
    """Something that changed since the last meeting."""

    domain: str
    description: str
    magnitude: str = "NORMAL"
    direction: str = "NEUTRAL"


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
class BriefingSection:
    title: str
    icon: str
    content: List[str]
    priority: str


@dataclass
class ClientBriefing:
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
    relationship_snapshot: BriefingSection
    seasonal_context: Optional[BriefingSection]
    last_meeting_date: Optional[str]
    generated_at: str

    def render_text(self) -> str:
        lines = []
        lines.append(f"CLIENT: {self.client_name}")
        lines.append(f"RM: {self.relationship_manager}")
        lines.append(f"Tier: {self.client_tier}")
        lines.append(f"When: {self.meeting_datetime}")
        lines.append(f"Value: {self.total_relationship_value_zar:,.0f}")
        if self.last_meeting_date:
            lines.append(f"Last meeting: {self.last_meeting_date}")
        
        # Snapshot
        lines.append("")
        lines.append(f"{self.relationship_snapshot.icon} {self.relationship_snapshot.title}")
        for item in self.relationship_snapshot.content:
            lines.append(f"- {item}")

        # Changes
        lines.append("")
        lines.append("[C] CHANGES SINCE LAST MEETING")
        if self.changes_since_last_meeting:
            for c in self.changes_since_last_meeting:
                lines.append(f"- [{c.domain}] {c.description}")
        else:
            lines.append("- No significant changes")
        
        # Opportunities
        lines.append("")
        lines.append("[$] TOP OPPORTUNITIES")
        if self.top_opportunities:
            for o in self.top_opportunities:
                lines.append(f"- {o.description} (R{o.estimated_value_zar:,.0f})")
        else:
            lines.append("- No immediate opportunities detected")
        
        # Risks
        lines.append("")
        lines.append("[!] RISK ALERTS")
        if self.risk_alerts:
            for r in self.risk_alerts:
                lines.append(f"- [{r.domain.upper()}] {r.description} ({r.severity})")
        else:
            lines.append("- No active risk alerts")
        
        # Seasonal
        if self.seasonal_context:
            lines.append("")
            lines.append(f"{self.seasonal_context.icon} {self.seasonal_context.title}")
            for item in self.seasonal_context.content:
                lines.append(f"- {item}")

        # Talking Points
        lines.append("")
        lines.append("[T] SUGGESTED TALKING POINTS")
        if self.talking_points:
            for t in self.talking_points:
                lines.append(f"- {t}")
        else:
            lines.append("- Review general performance")

        lines.append("")
        lines.append(f"Generated: {self.generated_at}")
        return "\n".join(lines)


class BriefingGenerator:
    """
    Generates client briefings from the unified golden
    record and cross-domain signal outputs.

    In production, this would query the Gold layer
    tables. For demonstration, we accept pre-assembled
    data dictionaries.
    """

    def __init__(self):
        pass

    def generate(
        self,
        golden_id: str,
        unified_record: Dict,
        recent_signals: List[Dict],
        shadow_gaps: List[Dict],
        seasonal_info: Optional[Dict] = None,
        currency_impacts: Optional[List[Dict]] = None,
        last_meeting_date: Optional[str] = None,
        meeting_context: str = "Quarterly Review",
    ) -> ClientBriefing:
        """
        Generate a complete client briefing.

        Args:
            golden_id: Unique client identifier
            unified_record: Client data from golden record
            recent_signals: Recent cross-domain signals
            shadow_gaps: Data shadow gaps
            seasonal_info: Optional seasonal context
            currency_impacts: Optional currency event impacts
            last_meeting_date: Date of last meeting
            meeting_context: Meeting type/context

        Returns:
            Complete ClientBriefing object

        Raises:
            BriefingGenerationError: If input validation fails
        """
        if not golden_id:
            raise BriefingGenerationError(
                "golden_id cannot be empty",
                details={"golden_id": golden_id}
            )

        if not isinstance(unified_record, dict):
            raise BriefingGenerationError(
                "unified_record must be a dictionary",
                details={"type": type(unified_record).__name__}
            )

        client_name = unified_record.get(
            "canonical_name", golden_id
        )
        client_tier = unified_record.get(
            "client_tier", "Unknown"
        )
        rm = unified_record.get(
            "relationship_manager", "Unassigned"
        )
        total_value = unified_record.get(
            "total_relationship_value_zar", 0.0
        )
        health_status = unified_record.get(
            "primary_risk_signal", "STABLE"
        )
        
        # Build domains_active dict
        domains_active = {}
        for domain in ["cib", "forex", "insurance", "cell", "pbb"]:
            domains_active[domain] = unified_record.get(f"has_{domain}", False)

        logger.info(
            f"Generating briefing for {golden_id} ({client_name})"
        )

        snapshot = self._build_snapshot(unified_record)
        changes = self._build_changes(
            recent_signals=recent_signals,
            shadow_gaps=shadow_gaps,
        )
        opportunities = self._build_opportunities(
            recent_signals=recent_signals,
            shadow_gaps=shadow_gaps,
            unified_record=unified_record,
        )
        risks = self._build_risks(
            unified_record=unified_record,
            currency_impacts=currency_impacts,
            shadow_gaps=shadow_gaps,
        )
        talking = self._build_talking_points(
            opportunities=opportunities,
            risks=risks,
        )

        seasonal_section = None
        if seasonal_info:
            seasonal_section = self._build_seasonal(
                seasonal_info
            )

        logger.info(
            f"Briefing generated for {golden_id}: "
            f"{len(opportunities)} opportunities, "
            f"{len(risks)} risks"
        )

        return ClientBriefing(
            client_golden_id=golden_id,
            client_name=client_name,
            client_tier=client_tier,
            meeting_datetime=datetime.now().strftime("%Y-%m-%d %H:%M"), # Or use passed context/date if needed
            relationship_manager=rm,
            total_relationship_value_zar=total_value,
            health_status=health_status,
            domains_active=domains_active,
            changes_since_last_meeting=changes,
            top_opportunities=opportunities,
            risk_alerts=risks,
            talking_points=talking,
            relationship_snapshot=snapshot,
            seasonal_context=seasonal_section,
            last_meeting_date=last_meeting_date,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _build_snapshot(
        self, unified_record: Dict
    ) -> BriefingSection:
        """Build the relationship snapshot section."""

        trv = unified_record.get(
            "total_relationship_value_zar", 0
        )
        domains = unified_record.get("domains_active", 0)
        health = unified_record.get(
            "primary_risk_signal", "STABLE"
        )
        cross_sell = unified_record.get(
            "cross_sell_priority", "STANDARD"
        )

        health_icon = "OK" if health == "STABLE" else "!!"
        content = [
            f"Total Relationship Value: R{trv:,.0f}",
            f"Domains Active: {domains}/5",
            f"Health: {health_icon} {health}",
            f"Cross-sell priority: {cross_sell}",
        ]

        domain_flags = []
        for domain in ["cib", "forex", "insurance",
                        "cell", "pbb"]:
            has = unified_record.get(
                f"has_{domain}", False
            )
            flag = "Y" if has else "N"
            domain_flags.append(
                f"{domain.upper()}: {flag}"
            )
        content.append(
            "Domains: " + " | ".join(domain_flags)
        )

        priority = "NORMAL"
        if health != "STABLE":
            priority = "HIGH"
        if cross_sell == "CRITICAL":
            priority = "CRITICAL"

        return BriefingSection(
            title="RELATIONSHIP SNAPSHOT",
            icon="[R]",
            content=content,
            priority=priority,
        )

    def _build_changes(
        self,
        recent_signals: List[Dict],
        shadow_gaps: List[Dict],
    ) -> List[ChangeEvent]:
        """Build the changes since last meeting section."""
        changes = []

        for signal in recent_signals[:5]:
            signal_type = signal.get("type", "Signal")
            description = signal.get("description", "No description")
            changes.append(ChangeEvent(
                domain="signal",
                description=f"[{signal_type}] {description}",
                magnitude=signal.get("magnitude", "NORMAL"),
                direction="NEUTRAL" # Could be inferred
            ))

        new_gaps = [
            g for g in shadow_gaps
            if g.get("is_new", False)
        ]
        if new_gaps:
            changes.append(ChangeEvent(
                domain="shadow",
                description=f"{len(new_gaps)} new data shadow gap(s) detected.",
                magnitude="HIGH",
                direction="NEGATIVE"
            ))
        
        return changes

    def _build_opportunities(
        self,
        recent_signals: List[Dict],
        shadow_gaps: List[Dict],
        unified_record: Dict,
    ) -> List[Opportunity]:
        """Build the opportunities section."""
        opportunities = []
        rank = 1

        expansion = [
            s for s in recent_signals
            if s.get("type") == "EXPANSION"
        ]
        for s in expansion[:2]:
            country = s.get("country", "Unknown")
            value = s.get("opportunity_zar", 0)
            opportunities.append(Opportunity(
                rank=rank,
                description=f"Expansion into {country} detected",
                estimated_value_zar=value,
                source_signal="EXPANSION_SIGNAL",
                talking_point=f"Support expansion into {country}"
            ))
            rank += 1

        leakage = [
            g for g in shadow_gaps
            if g.get("gap_type") == "competitive_leakage"
        ]
        for g in leakage[:2]:
            country = g.get("country", "Unknown")
            value = g.get("revenue_opportunity_zar", 0)
            opportunities.append(Opportunity(
                rank=rank,
                description=f"Competitive leakage in {country}",
                estimated_value_zar=value,
                source_signal="SHADOW_GAP",
                talking_point=f"Streamline banking in {country}"
            ))
            rank += 1

        if not unified_record.get("has_forex", False):
            cib_value = unified_record.get(
                "cib_annual_value", 0
            )
            if cib_value > 10_000_000:
                opportunities.append(Opportunity(
                    rank=rank,
                    description=f"FX hedging opportunity (R{cib_value:,.0f} flow)",
                    estimated_value_zar=cib_value * 0.01, # Est revenue
                    source_signal="CROSS_SELL",
                    talking_point="Discuss FX hedging strategy"
                ))
                rank += 1

        return opportunities

    def _build_risks(
        self,
        unified_record: Dict,
        currency_impacts: Optional[List[Dict]],
        shadow_gaps: List[Dict],
    ) -> List[RiskAlert]:
        """Build the risk alerts section."""
        risks = []

        risk = unified_record.get(
            "primary_risk_signal", "STABLE"
        )
        if risk != "STABLE":
            risks.append(RiskAlert(
                domain="overall",
                description=f"Primary risk: {risk}",
                severity="HIGH",
                recommended_discussion_point="Review overall risk profile"
            ))

        hedge_pct = unified_record.get(
            "forex_hedge_ratio_pct", 0
        )
        if 0 < hedge_pct < 30:
            risks.append(RiskAlert(
                domain="forex",
                description=f"Low FX hedge ratio ({hedge_pct}%)",
                severity="MEDIUM",
                recommended_discussion_point="Discuss increasing hedge ratio"
            ))

        if currency_impacts:
            for impact in currency_impacts[:2]:
                risks.append(RiskAlert(
                    domain="currency",
                    description=impact.get('description', 'Currency impact'),
                    severity="HIGH",
                    recommended_discussion_point="Review currency exposure"
                ))

        ins_gaps = unified_record.get(
            "insurance_coverage_gaps", 0
        )
        if ins_gaps > 0:
            risks.append(RiskAlert(
                domain="insurance",
                description=f"{ins_gaps} coverage gap(s)",
                severity="MEDIUM",
                recommended_discussion_point="Review insurance coverage"
            ))

        compliance = [
            g for g in shadow_gaps
            if g.get("gap_type") == "compliance_concern"
        ]
        if compliance:
            risks.append(RiskAlert(
                domain="compliance",
                description=f"{len(compliance)} data shadow compliance concern(s)",
                severity="HIGH",
                recommended_discussion_point="Address compliance gaps"
            ))

        return risks

    def _build_talking_points(
        self,
        opportunities: List[Opportunity],
        risks: List[RiskAlert],
    ) -> List[str]:
        """
        Build suggested talking points for the RM.
        These are AI-generated conversation starters.
        """
        talking_points = []

        for opp in opportunities[:2]:
            if "Expansion" in opp.description:
                talking_points.append(
                    '"I noticed your team has been growing in a new market. '
                    'Have you considered how we can support your working capital needs there?"'
                )
            elif "leakage" in opp.description.lower():
                talking_points.append(
                    '"We have a comprehensive view of your group relationship and see an '
                    'opportunity to streamline your banking across all markets."'
                )
            elif "FX hedging" in opp.description:
                talking_points.append(
                    '"Given recent currency movements, I wanted to discuss how we can '
                    'help you manage your cross-border FX exposure more effectively."'
                )

        for risk in risks[:1]:
            if "hedge" in risk.description.lower():
                talking_points.append(
                    '"Your current hedging coverage leaves some exposure. '
                    'Given recent volatility, shall we review your FX strategy?"'
                )

        if not talking_points:
            talking_points.append(
                '"How are your operations performing across your African markets this quarter?"'
            )

        return talking_points

    def _build_seasonal(
        self, seasonal_info: Dict
    ) -> BriefingSection:
        """Build seasonal context section."""

        content = []

        upcoming_peaks = seasonal_info.get(
            "upcoming_peaks", []
        )
        for peak in upcoming_peaks[:3]:
            content.append(
                f"Upcoming peak: {peak['commodity']} "
                f"in {peak['months_away']} month(s). "
                f"Expect {peak['expected_weight']:.0%} "
                f"of normal activity."
            )

        current_season = seasonal_info.get(
            "current_season", ""
        )
        if current_season:
            content.append(
                f"Current context: {current_season}"
            )

        if not content:
            content.append(
                "No significant seasonal factors."
            )

        return BriefingSection(
            title="SEASONAL CONTEXT",
            icon="[S]",
            content=content,
            priority="NORMAL",
        )
