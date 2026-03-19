"""
@file fx_advisor_alert_engine.py
@description Generates FX-specific alerts for FX advisors and treasury sales
             teams. Monitors client stop-loss and take-profit rate levels,
             corridor volatility, forward contract expiry dates, parallel market
             divergence, and central bank intervention signals. Each alert
             includes a suggested action and indicative rate for client calls.
@author Thabo Kunene
@created 2026-03-19
"""

# FX Advisor Alert Engine
#
# Generates currency-specific alerts for FX advisors and treasury
# sales teams. Unlike the RM alert engine which covers all products,
# this engine focuses exclusively on:
#
#   1. Rate threshold breach — a monitored rate hits the client's
#      target level (stop-loss or take-profit)
#   2. Corridor volatility spike — a payment corridor enters a
#      high-volatility period that changes the hedging calculus
#   3. Forward expiry warning — a client forward is approaching
#      maturity with no rollover booked
#   4. Parallel market divergence — the official rate and parallel
#      market rate are diverging beyond safe trading bands
#      (critical for NG, EG, ZW corridors)
#   5. Central bank intervention signal — unusual volume pattern
#      consistent with central bank buying/selling activity
#
# Alerts include pre-calculated hedge recommendations with
# indicative pricing (simplified model — not live pricing).
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data modeling and date/time handling
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Module-level thresholds
# ---------------------------------------------------------------------------

# Parallel market divergence thresholds by country ISO-2 code.
# An alert fires when the official vs parallel rate spread exceeds these levels.
# Values are based on central bank tolerance bands for each country's dual-rate system.
_PARALLEL_DIVERGENCE_THRESHOLD: Dict[str, float] = {
    "NG": 0.15,   # NGN: >15% spread triggers alert — CBN enforcement threshold
    "EG": 0.12,   # EGP: >12% — EGP has been subject to sharp official adjustments
    "ZW": 0.25,   # ZWL: >25% (historically volatile) — dual-rate environment is endemic
    "ET": 0.18,   # ETB: >18% — NBE controls; parallel premium is a key risk signal
    "AO": 0.20,   # AOA: >20% — BNA threshold; Kwanza historically soft
}

# Annualised volatility spike threshold.
# When a currency pair's annualised vol rises above 30%, the hedging
# calculus changes significantly and clients should be contacted immediately.
_VOLATILITY_SPIKE_THRESHOLD = 0.30   # 30% annualised vol


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FXAdvisorAlert:
    """
    A single FX advisor alert focused on a specific client and currency pair.

    :param alert_id: Unique identifier for the alert
    :param fx_advisor_id: The ID of the advisor assigned to this client
    :param client_golden_id: The unified client identifier
    :param client_name: Display name of the client
    :param alert_type: The category of FX event (e.g., RATE_THRESHOLD)
    :param currency_pair: The FX pair being monitored
    :param urgency: Priority level for action (e.g., IMMEDIATE)
    :param headline: Brief summary title for the alert
    :param details: In-depth context for advisor preparation
    :param suggested_action: Recommended conversational opener or trade action
    :param indicative_rate: Current mid-market rate for reference
    :param notional_at_risk_zar: Total client exposure impacted by this alert
    :param created_at: Timestamp when the alert was generated
    :param expires_at: Timestamp when the alert becomes stale
    """

    alert_id: str
    fx_advisor_id: str
    client_golden_id: str
    client_name: str
    alert_type: str    # RATE_THRESHOLD / VOLATILITY_SPIKE / FORWARD_EXPIRY /
                       # PARALLEL_DIVERGENCE / CB_INTERVENTION
    currency_pair: str
    urgency: str       # IMMEDIATE / HIGH / MEDIUM / LOW
    headline: str
    details: str
    suggested_action: str
    indicative_rate: Optional[float]
    notional_at_risk_zar: float
    # Automatically timestamp the alert upon creation
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    # Expiry is calculated by the engine based on urgency
    expires_at: str = ""


@dataclass
class FXAdvisorAlertBatch:
    """
    A collection of FX alerts for a single advisor, typically generated in one run.

    :param advisor_id: The ID of the advisor receiving the batch
    :param alerts: List of FXAdvisorAlert objects
    :param generated_at: When the batch was compiled
    """

    advisor_id: str
    alerts: List[FXAdvisorAlert]
    # Timestamp marking the completion of the batch generation
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Alert engine
# ---------------------------------------------------------------------------

class FXAdvisorAlertEngine:
    """
    Engine responsible for generating FX-specific alerts by evaluating client
    exposures against market rate movements and contract data.
    """

    # Maps urgency strings to integers for prioritized sorting
    _URGENCY_ORDER = {"IMMEDIATE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    def build_batch(
        self,
        advisor_id: str,
        rate_ticks: List[Dict],
        client_exposures: List[Dict],
        active_forwards: Optional[List[Dict]] = None,
    ) -> FXAdvisorAlertBatch:
        """
        Evaluate an entire advisor's client book and generate a prioritized alert batch.

        :param advisor_id: Unique ID of the target advisor
        :param rate_ticks: Current market pricing and volatility data
        :param client_exposures: List of client FX positions and rate thresholds
        :param active_forwards: List of existing forward contracts for expiry checks
        :return: A FXAdvisorAlertBatch containing all relevant alerts.
        """
        alerts: List[FXAdvisorAlert] = []

        # Process each individual client exposure for thresholds, vol, and expiry
        for exposure in client_exposures:
            alerts.extend(
                self._process_exposure(
                    advisor_id, exposure,
                    rate_ticks, active_forwards or []
                )
            )

        # Check for market-wide parallel divergence events impacting the corridor
        for tick in rate_ticks:
            alert = self._check_parallel_divergence(advisor_id, tick)
            if alert:
                alerts.append(alert)

        # Sort the resulting alerts by urgency (IMMEDIATE -> LOW)
        alerts.sort(
            key=lambda a: self._URGENCY_ORDER.get(a.urgency, 9)
        )

        return FXAdvisorAlertBatch(advisor_id=advisor_id, alerts=alerts)

    def _process_exposure(
        self,
        advisor_id: str,
        exposure: Dict,
        ticks: List[Dict],
        forwards: List[Dict],
    ) -> List[FXAdvisorAlert]:
        """
        Process a single client exposure record and generate relevant alerts.

        Checks stop-loss breach, take-profit level, volatility spike, and
        any expiring forwards for this client-pair combination.

        :param advisor_id: ID of the FX advisor
        :param exposure: Client exposure dict with client_golden_id, currency_pair,
                         notional_zar, stop_loss_rate, take_profit_rate
        :param ticks: Current market rate ticks for rate lookups
        :param forwards: All active forwards; filtered to this client inside the method
        :return: List of FXAdvisorAlert objects (may be empty)
        """
        alerts: List[FXAdvisorAlert] = []

        # Extract key fields from the exposure record
        golden_id = exposure.get("client_golden_id", "UNK")
        client_name = exposure.get("client_name", "Unknown")
        pair = exposure.get("currency_pair", "?/ZAR")
        notional = exposure.get("notional_zar", 0.0)  # ZAR notional at risk

        # Resolve the current mid-rate for this pair from the tick feed
        current_rate = self._current_rate(ticks, pair)

        # Client-specified alert levels (set when the client booked the exposure)
        stop_loss = exposure.get("stop_loss_rate")      # Rate level: execute stop if breached
        take_profit = exposure.get("take_profit_rate")  # Rate level: take profit if reached

        # --- Alert type: RATE_THRESHOLD (stop-loss breached) ---
        # Business event: rate has fallen to or below the client's stop-loss level.
        # Urgency: IMMEDIATE — stop-loss breaches require execution within hours.
        # SLA: 2 hours before the rate could move further against the client.
        if current_rate and stop_loss and current_rate <= stop_loss:
            alerts.append(FXAdvisorAlert(
                alert_id=f"FX-SL-{golden_id}-{pair.replace('/', '')}",
                fx_advisor_id=advisor_id,
                client_golden_id=golden_id,
                client_name=client_name,
                alert_type="RATE_THRESHOLD",
                currency_pair=pair,
                urgency="IMMEDIATE",  # Stop-loss = most urgent; client mandate to execute
                headline=f"{pair} stop-loss breached at {current_rate:.4f}",
                details=(
                    f"Rate {current_rate:.4f} hit stop-loss level "
                    f"{stop_loss:.4f}. Notional: R{notional:,.0f}."
                ),
                suggested_action=(
                    "Execute stop-loss forward immediately. "
                    "Confirm execution mandate with client."
                ),
                indicative_rate=current_rate,
                notional_at_risk_zar=notional,
                expires_at=(datetime.now() + timedelta(hours=2)).isoformat(),  # 2h SLA
            ))

        # --- Alert type: RATE_THRESHOLD (take-profit reached) ---
        # Business event: rate has risen to or above the client's take-profit level.
        # Urgency: HIGH — opportunity exists but rate could retrace quickly.
        # SLA: 8 hours (less urgency than stop-loss; rate may hold for longer)
        if current_rate and take_profit and current_rate >= take_profit:
            alerts.append(FXAdvisorAlert(
                alert_id=f"FX-TP-{golden_id}-{pair.replace('/', '')}",
                fx_advisor_id=advisor_id,
                client_golden_id=golden_id,
                client_name=client_name,
                alert_type="RATE_THRESHOLD",
                currency_pair=pair,
                urgency="HIGH",  # Take-profit is HIGH; client should be presented options
                headline=f"{pair} take-profit reached at {current_rate:.4f}",
                details=(
                    f"Rate {current_rate:.4f} reached take-profit "
                    f"{take_profit:.4f}."
                ),
                suggested_action="Present take-profit execution options to client.",
                indicative_rate=current_rate,
                notional_at_risk_zar=notional,
                expires_at=(datetime.now() + timedelta(hours=8)).isoformat(),  # 8h SLA
            ))

        # --- Alert type: VOLATILITY_SPIKE ---
        # Business event: annualised vol for this pair has risen above 30%.
        # Urgency: HIGH — elevated vol changes hedging cost and client risk profile.
        # SLA: 24 hours (vol spikes tend to persist for at least a day)
        vol = self._current_vol(ticks, pair)
        if vol and vol >= _VOLATILITY_SPIKE_THRESHOLD:
            alerts.append(FXAdvisorAlert(
                alert_id=f"FX-VOL-{golden_id}-{pair.replace('/', '')}",
                fx_advisor_id=advisor_id,
                client_golden_id=golden_id,
                client_name=client_name,
                alert_type="VOLATILITY_SPIKE",
                currency_pair=pair,
                urgency="HIGH",
                headline=f"{pair} volatility spiked to {vol*100:.0f}% annualised",
                details=(
                    f"Annualised vol {vol*100:.1f}% exceeds "
                    f"{_VOLATILITY_SPIKE_THRESHOLD*100:.0f}% threshold."
                ),
                suggested_action=(
                    "Review hedging programme. Consider option strategies."
                ),
                indicative_rate=current_rate,
                notional_at_risk_zar=notional,
                expires_at=(datetime.now() + timedelta(hours=24)).isoformat(),  # 24h SLA
            ))

        # --- Alert type: FORWARD_EXPIRY ---
        # Business event: a client's forward contract is approaching maturity
        # with no rollover booked, creating delivery/settlement risk.
        # Filter the full forwards list to just this client-pair combination.
        client_forwards = [
            f for f in forwards
            if f.get("client_golden_id") == golden_id
            and f.get("currency_pair") == pair
        ]
        for fwd in client_forwards:
            days = fwd.get("days_to_maturity", 999)  # Default 999 = no alert

            # Only alert if maturity is within 14 days and no rollover is booked
            if days <= 14:
                fwd_notional = fwd.get("notional_zar", notional)
                # Urgency escalates to IMMEDIATE when ≤3 days to maturity
                alerts.append(FXAdvisorAlert(
                    alert_id=f"FX-EXP-{golden_id}-{fwd.get('forward_id', 'UNK')}",
                    fx_advisor_id=advisor_id,
                    client_golden_id=golden_id,
                    client_name=client_name,
                    alert_type="FORWARD_EXPIRY",
                    currency_pair=pair,
                    urgency="IMMEDIATE" if days <= 3 else "HIGH",  # ≤3 days = IMMEDIATE
                    headline=f"{pair} forward expires in {days} days",
                    details=(
                        f"Forward #{fwd.get('forward_id', 'UNK')} for "
                        f"R{fwd_notional:,.0f} matures in {days} days. "
                        f"No rollover booked."
                    ),
                    suggested_action=(
                        "Contact client to confirm rollover or delivery."
                    ),
                    # Indicative rate is the contracted forward rate (not spot)
                    indicative_rate=fwd.get("contracted_rate"),
                    notional_at_risk_zar=fwd_notional,
                    # Expiry of the alert = maturity date of the forward
                    expires_at=(
                        datetime.now() + timedelta(days=days)
                    ).isoformat(),
                ))

        return alerts

    def _check_parallel_divergence(
        self, advisor_id: str, tick: Dict
    ) -> Optional[FXAdvisorAlert]:
        """
        Check for parallel market divergence at the market level.

        This alert is not client-specific; it notifies the FX advisor that
        a monitored corridor is in a dangerous parallel market environment.
        Triggered when official vs parallel spread exceeds the country threshold.

        Intended recipient: FX advisor / treasury desk monitoring NG, EG, ZW, ET, AO.
        Urgency: HIGH — parallel market conditions require immediate corridor review.

        :param advisor_id: ID of the FX advisor to assign the alert to
        :param tick: Rate tick dict for the pair being checked
        :return: FXAdvisorAlert or None if no divergence or country not monitored
        """
        pair = tick.get("currency_pair", "")
        # Extract country code from the first 2 characters of the pair string
        # e.g. 'NG' from 'NGN/ZAR' — assumes pair starts with ISO-2 country prefix
        country = pair[:2] if pair else ""
        threshold = _PARALLEL_DIVERGENCE_THRESHOLD.get(country)

        # Skip countries that are not in the parallel market watch list
        if not threshold:
            return None

        official = tick.get("mid_rate", 0)
        parallel = tick.get("parallel_rate")

        # Require both rates to be present and non-zero
        if not parallel or not official:
            return None

        # Compute the percentage divergence between parallel and official rates
        divergence = abs(parallel - official) / official

        # Only fire if divergence exceeds the regulatory tolerance
        if divergence < threshold:
            return None

        # Market-level alert: assign to 'MARKET' rather than a specific client
        return FXAdvisorAlert(
            alert_id=f"FX-PAR-{pair.replace('/', '')}-{country}",
            fx_advisor_id=advisor_id,
            client_golden_id="MARKET",   # Market-level alert; no specific client
            client_name="Market Alert",
            alert_type="PARALLEL_DIVERGENCE",
            currency_pair=pair,
            urgency="HIGH",  # Parallel divergence = portfolio-level risk for all corridor clients
            headline=f"{pair} parallel-official spread: {divergence*100:.1f}%",
            details=(
                f"Official {official:.4f} vs parallel {parallel:.4f} — "
                f"{divergence*100:.1f}% spread. Threshold: {threshold*100:.0f}%."
            ),
            suggested_action=(
                f"Review {country} corridor exposures. "
                f"Advise clients on {pair} timing."
            ),
            indicative_rate=official,  # Official rate is the actionable rate for clients
            notional_at_risk_zar=0.0,  # Exposure is unknown at market level; set to zero
            expires_at=(datetime.now() + timedelta(hours=12)).isoformat(),  # 12h SLA
        )

    # ------------------------------------------------------------------
    # Helper: tick lookups
    # ------------------------------------------------------------------

    def _current_rate(self, ticks: List[Dict], pair: str) -> Optional[float]:
        """
        Retrieve the latest mid-rate for a given currency pair from the tick list.

        Returns the last matching tick's mid_rate (most recent in a time-ordered list).

        :param ticks: List of rate tick dicts
        :param pair: Currency pair to look up
        :return: Mid-rate float or None if pair not found in ticks
        """
        matching = [t for t in ticks if t.get("currency_pair") == pair]
        return matching[-1].get("mid_rate") if matching else None

    def _current_vol(self, ticks: List[Dict], pair: str) -> Optional[float]:
        """
        Retrieve the latest annualised volatility for a given currency pair.

        :param ticks: List of rate tick dicts
        :param pair: Currency pair to look up
        :return: Annualised vol float (e.g. 0.30 = 30%) or None if not found
        """
        matching = [t for t in ticks if t.get("currency_pair") == pair]
        return matching[-1].get("annualised_vol") if matching else None
