"""
@file briefing_generator.py
@description Core assembly logic for pre-meeting client intelligence briefings.
             Combines unified golden-record data, cross-domain signals, data
             shadow gaps, seasonal context, and currency event impacts into a
             single structured ClientBriefing artifact.  Also integrates with
             the optional TalkingPointsEngine to enhance RM conversation starters.
@author Thabo Kunene
@created 2026-03-17
"""

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
from afriflow.integration.client_briefing.talking_points_engine import (
    TalkingPointsEngine,
    EmptyInputError,
    ModelLoadError,
    ProcessingTimeoutError,
)

# Module-level logger — scoped to client_briefing.generator so log filters
# can target this module independently of the rest of the application.
logger = get_logger("client_briefing.generator")


# ---------------------------------------------------------------------------
# Data-transfer objects (dataclasses)
# These lightweight containers carry structured data through the pipeline
# without any external dependencies; they are safe to serialise, compare,
# and pass across service boundaries.
# ---------------------------------------------------------------------------


@dataclass
class ChangeEvent:
    """Something that changed since the last meeting.

    :param domain: Source domain that produced the change (e.g. 'forex', 'shadow').
    :param description: Human-readable summary of the change.
    :param magnitude: Relative size of the change — 'NORMAL', 'HIGH', etc.
    :param direction: Whether the change is positive, negative, or neutral.
    """

    domain: str
    description: str
    magnitude: str = "NORMAL"   # Default: treat unclassified changes as normal
    direction: str = "NEUTRAL"  # Default: unknown direction until enriched


@dataclass
class Opportunity:
    """A revenue opportunity for the RM to discuss.

    :param rank: Ordering priority — lower rank means higher priority.
    :param description: Short narrative of the opportunity.
    :param estimated_value_zar: Rough ZAR revenue or deal-value estimate.
    :param source_signal: Which signal or data source surfaced this opportunity.
    :param talking_point: Pre-built conversation starter for the RM.
    """

    rank: int
    description: str
    estimated_value_zar: float
    source_signal: str
    talking_point: str


@dataclass
class RiskAlert:
    """A risk the RM should be aware of.

    :param domain: Domain that owns the risk (e.g. 'forex', 'insurance').
    :param description: Concise description of the risk.
    :param severity: Criticality level — 'LOW', 'MEDIUM', or 'HIGH'.
    :param recommended_discussion_point: Suggested action or talking point for the RM.
    """

    domain: str
    description: str
    severity: str
    recommended_discussion_point: str


@dataclass
class BriefingSection:
    """A titled, prioritised content block within a ClientBriefing.

    :param title: Section heading displayed in the rendered output.
    :param icon: Short prefix marker (e.g. '[R]') for visual scanning.
    :param content: Ordered list of line items in this section.
    :param priority: Urgency level used for rendering emphasis — 'NORMAL', 'HIGH', 'CRITICAL'.
    """

    title: str
    icon: str
    content: List[str]
    priority: str


@dataclass
class ClientBriefing:
    """The complete pre-meeting briefing artifact delivered to the RM.

    :param client_golden_id: Canonical entity-resolution ID from the golden record.
    :param client_name: Display name of the client.
    :param client_tier: Tier classification (e.g. 'PLATINUM', 'GOLD').
    :param meeting_datetime: ISO-formatted date/time of the upcoming meeting.
    :param relationship_manager: Full name of the assigned RM.
    :param total_relationship_value_zar: Aggregate wallet-of-business in ZAR.
    :param health_status: High-level risk signal for the relationship.
    :param domains_active: Map of domain name → bool indicating active presence.
    :param changes_since_last_meeting: List of notable changes detected recently.
    :param top_opportunities: Ranked list of revenue opportunities.
    :param risk_alerts: Active risks requiring RM attention.
    :param talking_points: Suggested conversation starters for the meeting.
    :param relationship_snapshot: Structured overview section.
    :param seasonal_context: Optional seasonal/commodity context section.
    :param last_meeting_date: Date of the previous meeting, if known.
    :param generated_at: Timestamp when this briefing was assembled.
    """

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
        """Render the briefing as a plain-text string suitable for email or terminal.

        Sections are printed in the following order:
        header → snapshot → changes → opportunities → risks → seasonal → talking points.

        :return: Multi-line string representation of the full briefing.
        """
        lines = []

        # --- Header block: key client metadata the RM needs at a glance ---
        lines.append(f"CLIENT: {self.client_name}")
        lines.append(f"RM: {self.relationship_manager}")
        lines.append(f"Tier: {self.client_tier}")
        lines.append(f"When: {self.meeting_datetime}")
        lines.append(f"Value: {self.total_relationship_value_zar:,.0f}")
        if self.last_meeting_date:
            # Only surface this line when a previous meeting date is known
            lines.append(f"Last meeting: {self.last_meeting_date}")

        # --- Relationship Snapshot section ---
        lines.append("")
        lines.append(f"{self.relationship_snapshot.icon} {self.relationship_snapshot.title}")
        for item in self.relationship_snapshot.content:
            lines.append(f"- {item}")

        # --- Changes since last meeting: surface deltas so the RM is up to date ---
        lines.append("")
        lines.append("[C] CHANGES SINCE LAST MEETING")
        if self.changes_since_last_meeting:
            for c in self.changes_since_last_meeting:
                # Format: [domain] description
                lines.append(f"- [{c.domain}] {c.description}")
        else:
            lines.append("- No significant changes")

        # --- Top opportunities: ranked revenue actions for this meeting ---
        lines.append("")
        lines.append("[$] TOP OPPORTUNITIES")
        if self.top_opportunities:
            for o in self.top_opportunities:
                # Show estimated ZAR value alongside the description
                lines.append(f"- {o.description} (R{o.estimated_value_zar:,.0f})")
        else:
            lines.append("- No immediate opportunities detected")

        # --- Risk alerts: issues that must not leave the meeting unaddressed ---
        lines.append("")
        lines.append("[!] RISK ALERTS")
        if self.risk_alerts:
            for r in self.risk_alerts:
                # Domain uppercased for visual scanning; severity in parentheses
                lines.append(f"- [{r.domain.upper()}] {r.description} ({r.severity})")
        else:
            lines.append("- No active risk alerts")

        # --- Seasonal context: only rendered when provided by the caller ---
        if self.seasonal_context:
            lines.append("")
            lines.append(f"{self.seasonal_context.icon} {self.seasonal_context.title}")
            for item in self.seasonal_context.content:
                lines.append(f"- {item}")

        # --- Talking points: scripted conversation starters for the RM ---
        lines.append("")
        lines.append("[T] SUGGESTED TALKING POINTS")
        if self.talking_points:
            for t in self.talking_points:
                lines.append(f"- {t}")
        else:
            # Fallback when no signal-driven points could be generated
            lines.append("- Review general performance")

        # --- Footer: audit trail showing when this briefing was assembled ---
        lines.append("")
        lines.append(f"Generated: {self.generated_at}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# BriefingGenerator
# ---------------------------------------------------------------------------

class BriefingGenerator:
    """
    Generates client briefings from the unified golden
    record and cross-domain signal outputs.

    In production, this would query the Gold layer
    tables. For demonstration, we accept pre-assembled
    data dictionaries.
    """

    def __init__(
        self,
        talking_points_engine: Optional[TalkingPointsEngine] = None,
        enable_talking_points_engine: bool = True,
    ):
        """Initialise the generator with an optional NLP talking-points engine.

        :param talking_points_engine: Pre-initialised TalkingPointsEngine instance.
                                      Pass None to skip NLP enhancement.
        :param enable_talking_points_engine: Feature flag — set False to bypass
                                             engine calls even when one is supplied.
        """
        # Store the engine reference; may be None if caller opts out
        self.talking_points_engine = talking_points_engine
        # Separate boolean flag lets tests disable the engine without monkey-patching
        self.enable_talking_points_engine = enable_talking_points_engine

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

        :param golden_id: Unique client identifier from entity resolution.
        :param unified_record: Client data dict from the golden record (Gold layer).
        :param recent_signals: List of cross-domain signal dicts surfaced recently.
        :param shadow_gaps: List of data-shadow gap dicts (competitive or compliance).
        :param seasonal_info: Optional dict containing upcoming peaks and current season.
        :param currency_impacts: Optional list of active currency event impact dicts.
        :param last_meeting_date: ISO date string of the previous RM meeting, if known.
        :param meeting_context: Free-text label for the meeting type (e.g. 'Annual Review').
        :return: A fully populated ClientBriefing dataclass instance.
        :raises BriefingGenerationError: If golden_id is empty or unified_record is invalid.
        """
        # Guard: golden_id is the primary key — reject immediately if missing
        if not golden_id:
            raise BriefingGenerationError(
                "golden_id cannot be empty",
                details={"golden_id": golden_id}
            )

        # Guard: unified_record must be a dict; reject wrong types early to
        # prevent confusing KeyError failures deep inside the helper methods
        if not isinstance(unified_record, dict):
            raise BriefingGenerationError(
                "unified_record must be a dictionary",
                details={"type": type(unified_record).__name__}
            )

        # --- Extract top-level client attributes from the unified record ---
        # Fall back to golden_id when canonical_name is absent (edge case for
        # new clients not yet through full entity resolution)
        client_name = unified_record.get(
            "canonical_name", golden_id
        )
        # Tier drives priority-routing in some downstream systems
        client_tier = unified_record.get(
            "client_tier", "Unknown"
        )
        # RM name is displayed prominently on the briefing header
        rm = unified_record.get(
            "relationship_manager", "Unassigned"
        )
        # Total relationship value (TRV) is the headline financial metric
        total_value = unified_record.get(
            "total_relationship_value_zar", 0.0
        )
        # primary_risk_signal is the top-level health indicator from the risk model
        health_status = unified_record.get(
            "primary_risk_signal", "STABLE"
        )

        # Build domains_active dict: one boolean per supported domain
        # This tells the RM which product lines the client is currently using
        domains_active = {}
        for domain in ["cib", "forex", "insurance", "cell", "pbb"]:
            # Convention: unified record stores domain flags as has_<domain>
            domains_active[domain] = unified_record.get(f"has_{domain}", False)

        logger.info(
            f"Generating briefing for {golden_id} ({client_name})"
        )

        # --- Delegate to private builder methods for each briefing section ---
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
        # Build rule-based talking points first, then optionally enrich with NLP
        talking = self._build_talking_points(
            opportunities=opportunities,
            risks=risks,
        )
        talking = self._enhance_talking_points(
            recent_signals=recent_signals,
            existing_points=talking,
        )

        # Seasonal section is optional — only build it when the caller supplied data
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

    def _enhance_talking_points(
        self,
        recent_signals: List[Dict],
        existing_points: List[str],
    ) -> List[str]:
        """Optionally enrich rule-based talking points using the NLP engine.

        Extracts free-text fields from each signal, submits them to the
        TalkingPointsEngine, de-duplicates, and merges the results with the
        existing rule-based points.  Any engine failure is caught and logged so
        the briefing still completes with the rule-based points intact.

        :param recent_signals: Cross-domain signal dicts to harvest text from.
        :param existing_points: Rule-based talking points produced by _build_talking_points.
        :return: Merged list of talking points (rule-based + engine-generated, de-duped).
        """
        # Short-circuit: engine disabled via feature flag or not supplied
        if not self.enable_talking_points_engine:
            return existing_points
        if not self.talking_points_engine:
            return existing_points

        # Collect free-text strings from signal fields that carry narrative content
        texts: List[str] = []
        for signal in recent_signals:
            # Harvest whichever text fields are present in each signal dict
            for key in ("description", "source_evidence", "headline", "recommended_action"):
                v = signal.get(key)
                if isinstance(v, str) and v.strip():
                    texts.append(v.strip())

        # Nothing to process — return existing points unchanged
        if not texts:
            return existing_points

        try:
            # Submit the harvested texts to the NLP engine for summarisation
            out = self.talking_points_engine.process(
                {"texts": texts},
                output_format="json",
            )
            # Engine returns a dict with a 'points' list; guard against unexpected shapes
            points_raw = out.get("points", []) if isinstance(out, dict) else []

            # Extract the 'text' field from each point dict; skip malformed entries
            engine_points: List[str] = []
            for p in points_raw:
                if isinstance(p, dict):
                    t = p.get("text")
                    if isinstance(t, str) and t.strip():
                        engine_points.append(t.strip())

            # Merge rule-based (priority) and engine-generated points, then de-duplicate
            merged: List[str] = []
            seen: set[str] = set()
            for t in list(existing_points) + engine_points:
                tt = t.strip()
                if not tt:
                    continue
                # Hard cap: talking points exceeding 240 chars are too long to read at a glance
                if len(tt) > 240:
                    continue
                # Case-insensitive de-duplication prevents near-identical points appearing twice
                key = tt.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(tt)
            return merged

        except (EmptyInputError, ModelLoadError, ProcessingTimeoutError) as e:
            # Known engine errors — degrade gracefully, keep rule-based points
            logger.warning(f"Talking points engine failed: {e}")
            return existing_points
        except Exception as e:
            # Catch-all for unexpected engine failures so the briefing is never blocked
            logger.warning(f"Talking points engine unexpected failure: {e}")
            return existing_points

    def _build_snapshot(
        self, unified_record: Dict
    ) -> BriefingSection:
        """Build the relationship snapshot section.

        Summarises the client's financial size, domain footprint, health signal,
        and cross-sell priority into a compact top-of-briefing block.

        :param unified_record: Golden-record dict for this client.
        :return: A BriefingSection labelled 'RELATIONSHIP SNAPSHOT'.
        """
        # --- Pull key metrics from the unified record ---
        trv = unified_record.get(
            "total_relationship_value_zar", 0
        )
        # domains is an integer count of active product lines (0–5)
        domains = unified_record.get("domains_active", 0)
        health = unified_record.get(
            "primary_risk_signal", "STABLE"
        )
        cross_sell = unified_record.get(
            "cross_sell_priority", "STANDARD"
        )

        # Simple visual indicator: non-STABLE health gets a '!!' warning prefix
        health_icon = "OK" if health == "STABLE" else "!!"
        content = [
            f"Total Relationship Value: R{trv:,.0f}",
            f"Domains Active: {domains}/5",
            f"Health: {health_icon} {health}",
            f"Cross-sell priority: {cross_sell}",
        ]

        # Build a per-domain Y/N flag string so the RM can see the product footprint
        domain_flags = []
        for domain in ["cib", "forex", "insurance",
                        "cell", "pbb"]:
            has = unified_record.get(
                f"has_{domain}", False
            )
            # Y = client is active in this domain; N = not present or not confirmed
            flag = "Y" if has else "N"
            domain_flags.append(
                f"{domain.upper()}: {flag}"
            )
        content.append(
            "Domains: " + " | ".join(domain_flags)
        )

        # Escalate section priority based on health and cross-sell urgency
        priority = "NORMAL"
        if health != "STABLE":
            priority = "HIGH"          # Unstable health always elevates priority
        if cross_sell == "CRITICAL":
            priority = "CRITICAL"      # CRITICAL cross-sell overrides health level

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
        """Build the changes-since-last-meeting section.

        Converts recent cross-domain signals and newly detected shadow gaps
        into a chronological list of ChangeEvent objects for the RM.

        :param recent_signals: Cross-domain signal dicts from the signal store.
        :param shadow_gaps: Data-shadow gap dicts flagged since the last briefing.
        :return: List of ChangeEvent objects, ordered by signal recency then gaps.
        """
        changes = []

        # Cap at 5 signals to keep the briefing readable within the 2-minute target
        for signal in recent_signals[:5]:
            signal_type = signal.get("type", "Signal")
            description = signal.get("description", "No description")
            changes.append(ChangeEvent(
                domain="signal",
                description=f"[{signal_type}] {description}",
                magnitude=signal.get("magnitude", "NORMAL"),
                direction="NEUTRAL" # Could be inferred from signal metadata in future
            ))

        # Surface newly detected shadow gaps as a single aggregate change event
        new_gaps = [
            g for g in shadow_gaps
            if g.get("is_new", False)   # is_new flag set by the shadow detector
        ]
        if new_gaps:
            changes.append(ChangeEvent(
                domain="shadow",
                description=f"{len(new_gaps)} new data shadow gap(s) detected.",
                magnitude="HIGH",       # New gaps always warrant HIGH magnitude
                direction="NEGATIVE"    # Gaps represent missing/lost business
            ))

        return changes

    def _build_opportunities(
        self,
        recent_signals: List[Dict],
        shadow_gaps: List[Dict],
        unified_record: Dict,
    ) -> List[Opportunity]:
        """Build the ranked opportunities section.

        Scans three sources in priority order:
        1. EXPANSION signals — client entering new markets.
        2. competitive_leakage gaps — wallet being lost to other banks.
        3. Cross-sell logic — e.g. large CIB client without FX coverage.

        :param recent_signals: Cross-domain signal dicts.
        :param shadow_gaps: Data-shadow gap dicts.
        :param unified_record: Golden-record dict for cross-sell eligibility checks.
        :return: Ranked list of Opportunity objects (rank 1 = highest priority).
        """
        opportunities = []
        rank = 1  # Rank counter; increments each time an opportunity is added

        # --- Source 1: EXPANSION signals (highest value, new market entry) ---
        expansion = [
            s for s in recent_signals
            if s.get("type") == "EXPANSION"
        ]
        # Cap at 2 expansion opportunities to avoid briefing overload
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

        # --- Source 2: competitive_leakage gaps (wallet lost to competitors) ---
        leakage = [
            g for g in shadow_gaps
            if g.get("gap_type") == "competitive_leakage"
        ]
        # Cap at 2 leakage opportunities per briefing
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

        # --- Source 3: Cross-sell logic — FX hedging for large CIB clients ---
        # Only suggest FX if the client does NOT already have a forex relationship
        if not unified_record.get("has_forex", False):
            cib_value = unified_record.get(
                "cib_annual_value", 0
            )
            # Threshold: only worth surfacing when annual CIB value exceeds R10m
            if cib_value > 10_000_000:
                opportunities.append(Opportunity(
                    rank=rank,
                    description=f"FX hedging opportunity (R{cib_value:,.0f} flow)",
                    estimated_value_zar=cib_value * 0.01, # Est. 1% revenue on notional flow
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
        """Build the risk alerts section.

        Checks four risk categories: overall health, FX hedge shortfall,
        active currency events, and insurance coverage gaps, plus compliance
        concerns surfaced by the data-shadow model.

        :param unified_record: Golden-record dict.
        :param currency_impacts: Active currency event impact dicts, or None.
        :param shadow_gaps: Data-shadow gap dicts.
        :return: List of RiskAlert objects ordered by detection sequence.
        """
        risks = []

        # --- Risk 1: primary risk signal from the golden record ---
        risk = unified_record.get(
            "primary_risk_signal", "STABLE"
        )
        # Only flag when the status is non-STABLE; STABLE is the healthy baseline
        if risk != "STABLE":
            risks.append(RiskAlert(
                domain="overall",
                description=f"Primary risk: {risk}",
                severity="HIGH",
                recommended_discussion_point="Review overall risk profile"
            ))

        # --- Risk 2: low FX hedge ratio ---
        hedge_pct = unified_record.get(
            "forex_hedge_ratio_pct", 0
        )
        # Threshold: below 30% hedge is considered dangerously exposed in volatile markets
        if 0 < hedge_pct < 30:
            risks.append(RiskAlert(
                domain="forex",
                description=f"Low FX hedge ratio ({hedge_pct}%)",
                severity="MEDIUM",
                recommended_discussion_point="Discuss increasing hedge ratio"
            ))

        # --- Risk 3: active currency event impacts ---
        if currency_impacts:
            # Cap at 2 currency risks to prevent alert fatigue on the briefing
            for impact in currency_impacts[:2]:
                risks.append(RiskAlert(
                    domain="currency",
                    description=impact.get('description', 'Currency impact'),
                    severity="HIGH",
                    recommended_discussion_point="Review currency exposure"
                ))

        # --- Risk 4: insurance coverage gaps ---
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

        # --- Risk 5: compliance concerns from the data shadow model ---
        compliance = [
            g for g in shadow_gaps
            if g.get("gap_type") == "compliance_concern"
        ]
        if compliance:
            risks.append(RiskAlert(
                domain="compliance",
                description=f"{len(compliance)} data shadow compliance concern(s)",
                severity="HIGH",   # Compliance issues are always HIGH severity
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

        Rule-based first pass: maps opportunity and risk types to pre-written
        question templates.  These may later be enriched by _enhance_talking_points.

        :param opportunities: Ranked list of opportunities from _build_opportunities.
        :param risks: Risk alerts from _build_risks.
        :return: List of talking-point strings ready for display.
        """
        talking_points = []

        # --- Opportunity-driven talking points (top 2 only for brevity) ---
        for opp in opportunities[:2]:
            if "Expansion" in opp.description:
                # Expansion signal: open with working capital support question
                talking_points.append(
                    '"I noticed your team has been growing in a new market. '
                    'Have you considered how we can support your working capital needs there?"'
                )
            elif "leakage" in opp.description.lower():
                # Competitive leakage: position group-wide banking consolidation
                talking_points.append(
                    '"We have a comprehensive view of your group relationship and see an '
                    'opportunity to streamline your banking across all markets."'
                )
            elif "FX hedging" in opp.description:
                # FX cross-sell: frame as risk management rather than product push
                talking_points.append(
                    '"Given recent currency movements, I wanted to discuss how we can '
                    'help you manage your cross-border FX exposure more effectively."'
                )

        # --- Risk-driven talking points (only the top risk to avoid overwhelm) ---
        for risk in risks[:1]:
            if "hedge" in risk.description.lower():
                # Low hedge ratio: pivot to a forward-looking strategy conversation
                talking_points.append(
                    '"Your current hedging coverage leaves some exposure. '
                    'Given recent volatility, shall we review your FX strategy?"'
                )

        # Fallback: ensure the RM always has at least one conversation opener
        if not talking_points:
            talking_points.append(
                '"How are your operations performing across your African markets this quarter?"'
            )

        return talking_points

    def _build_seasonal(
        self, seasonal_info: Dict
    ) -> BriefingSection:
        """Build seasonal context section.

        Converts upcoming commodity peaks and current-season labels from the
        seasonal model into human-readable briefing lines.

        :param seasonal_info: Dict with 'upcoming_peaks' list and 'current_season' string.
        :return: A BriefingSection labelled 'SEASONAL CONTEXT'.
        """
        content = []

        # --- Upcoming commodity peaks ---
        upcoming_peaks = seasonal_info.get(
            "upcoming_peaks", []
        )
        # Cap at 3 peaks so seasonal context doesn't dominate the briefing
        for peak in upcoming_peaks[:3]:
            content.append(
                f"Upcoming peak: {peak['commodity']} "
                f"in {peak['months_away']} month(s). "
                f"Expect {peak['expected_weight']:.0%} "
                f"of normal activity."
            )

        # --- Current season label (e.g. 'Harvest season — East Africa') ---
        current_season = seasonal_info.get(
            "current_season", ""
        )
        if current_season:
            content.append(
                f"Current context: {current_season}"
            )

        # Fallback when no seasonal data was available in the model output
        if not content:
            content.append(
                "No significant seasonal factors."
            )

        return BriefingSection(
            title="SEASONAL CONTEXT",
            icon="[S]",
            content=content,
            priority="NORMAL",  # Seasonal context is informational; never escalates priority
        )
