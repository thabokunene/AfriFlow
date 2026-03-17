"""
FX Advisor Alert Engine

Generates currency-specific alerts for FX advisors and treasury
sales teams. Unlike the RM alert engine which covers all products,
this engine focuses exclusively on:

  1. Rate threshold breach — a monitored rate hits the client's
     target level (stop-loss or take-profit)
  2. Corridor volatility spike — a payment corridor enters a
     high-volatility period that changes the hedging calculus
  3. Forward expiry warning — a client forward is approaching
     maturity with no rollover booked
  4. Parallel market divergence — the official rate and parallel
     market rate are diverging beyond safe trading bands
     (critical for NG, EG, ZW corridors)
  5. Central bank intervention signal — unusual volume pattern
     consistent with central bank buying/selling activity

Alerts include pre-calculated hedge recommendations with
indicative pricing (simplified model — not live pricing).

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# Parallel market divergence thresholds by country
_PARALLEL_DIVERGENCE_THRESHOLD: Dict[str, float] = {
    "NG": 0.15,   # NGN: >15% spread triggers alert
    "EG": 0.12,   # EGP: >12%
    "ZW": 0.25,   # ZWL: >25% (historically volatile)
    "ET": 0.18,   # ETB: >18%
    "AO": 0.20,   # AOA: >20%
}

# Volatility spike thresholds (annualised vol)
_VOLATILITY_SPIKE_THRESHOLD = 0.30   # 30% annualised vol


@dataclass
class FXAdvisorAlert:
    """A single FX advisor alert."""

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
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    expires_at: str = ""


@dataclass
class FXAdvisorAlertBatch:
    """All FX alerts for an advisor, sorted by urgency."""

    advisor_id: str
    alerts: List[FXAdvisorAlert]
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class FXAdvisorAlertEngine:
    """
    Generate FX-specific alerts for an FX advisor's client book.

    Usage::

        engine = FXAdvisorAlertEngine()
        batch = engine.build_batch(
            advisor_id="FX-ADV-007",
            rate_ticks=[...],
            client_exposures=[...],
            active_forwards=[...],
        )
    """

    _URGENCY_ORDER = {"IMMEDIATE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    def build_batch(
        self,
        advisor_id: str,
        rate_ticks: List[Dict],
        client_exposures: List[Dict],
        active_forwards: Optional[List[Dict]] = None,
    ) -> FXAdvisorAlertBatch:
        alerts: List[FXAdvisorAlert] = []

        for exposure in client_exposures:
            alerts.extend(
                self._process_exposure(
                    advisor_id, exposure,
                    rate_ticks, active_forwards or []
                )
            )

        for tick in rate_ticks:
            alert = self._check_parallel_divergence(advisor_id, tick)
            if alert:
                alerts.append(alert)

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
        alerts: List[FXAdvisorAlert] = []
        golden_id = exposure.get("client_golden_id", "UNK")
        client_name = exposure.get("client_name", "Unknown")
        pair = exposure.get("currency_pair", "?/ZAR")
        notional = exposure.get("notional_zar", 0.0)

        current_rate = self._current_rate(ticks, pair)
        stop_loss = exposure.get("stop_loss_rate")
        take_profit = exposure.get("take_profit_rate")

        if current_rate and stop_loss and current_rate <= stop_loss:
            alerts.append(FXAdvisorAlert(
                alert_id=f"FX-SL-{golden_id}-{pair.replace('/', '')}",
                fx_advisor_id=advisor_id,
                client_golden_id=golden_id,
                client_name=client_name,
                alert_type="RATE_THRESHOLD",
                currency_pair=pair,
                urgency="IMMEDIATE",
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
                expires_at=(datetime.now() + timedelta(hours=2)).isoformat(),
            ))

        if current_rate and take_profit and current_rate >= take_profit:
            alerts.append(FXAdvisorAlert(
                alert_id=f"FX-TP-{golden_id}-{pair.replace('/', '')}",
                fx_advisor_id=advisor_id,
                client_golden_id=golden_id,
                client_name=client_name,
                alert_type="RATE_THRESHOLD",
                currency_pair=pair,
                urgency="HIGH",
                headline=f"{pair} take-profit reached at {current_rate:.4f}",
                details=(
                    f"Rate {current_rate:.4f} reached take-profit "
                    f"{take_profit:.4f}."
                ),
                suggested_action="Present take-profit execution options to client.",
                indicative_rate=current_rate,
                notional_at_risk_zar=notional,
                expires_at=(datetime.now() + timedelta(hours=8)).isoformat(),
            ))

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
                expires_at=(datetime.now() + timedelta(hours=24)).isoformat(),
            ))

        client_forwards = [
            f for f in forwards
            if f.get("client_golden_id") == golden_id
            and f.get("currency_pair") == pair
        ]
        for fwd in client_forwards:
            days = fwd.get("days_to_maturity", 999)
            if days <= 14:
                fwd_notional = fwd.get("notional_zar", notional)
                alerts.append(FXAdvisorAlert(
                    alert_id=f"FX-EXP-{golden_id}-{fwd.get('forward_id', 'UNK')}",
                    fx_advisor_id=advisor_id,
                    client_golden_id=golden_id,
                    client_name=client_name,
                    alert_type="FORWARD_EXPIRY",
                    currency_pair=pair,
                    urgency="IMMEDIATE" if days <= 3 else "HIGH",
                    headline=f"{pair} forward expires in {days} days",
                    details=(
                        f"Forward #{fwd.get('forward_id', 'UNK')} for "
                        f"R{fwd_notional:,.0f} matures in {days} days. "
                        f"No rollover booked."
                    ),
                    suggested_action=(
                        "Contact client to confirm rollover or delivery."
                    ),
                    indicative_rate=fwd.get("contracted_rate"),
                    notional_at_risk_zar=fwd_notional,
                    expires_at=(
                        datetime.now() + timedelta(days=days)
                    ).isoformat(),
                ))

        return alerts

    def _check_parallel_divergence(
        self, advisor_id: str, tick: Dict
    ) -> Optional[FXAdvisorAlert]:
        pair = tick.get("currency_pair", "")
        country = pair[:2] if pair else ""
        threshold = _PARALLEL_DIVERGENCE_THRESHOLD.get(country)
        if not threshold:
            return None

        official = tick.get("mid_rate", 0)
        parallel = tick.get("parallel_rate")
        if not parallel or not official:
            return None

        divergence = abs(parallel - official) / official
        if divergence < threshold:
            return None

        return FXAdvisorAlert(
            alert_id=f"FX-PAR-{pair.replace('/', '')}-{country}",
            fx_advisor_id=advisor_id,
            client_golden_id="MARKET",
            client_name="Market Alert",
            alert_type="PARALLEL_DIVERGENCE",
            currency_pair=pair,
            urgency="HIGH",
            headline=f"{pair} parallel-official spread: {divergence*100:.1f}%",
            details=(
                f"Official {official:.4f} vs parallel {parallel:.4f} — "
                f"{divergence*100:.1f}% spread. Threshold: {threshold*100:.0f}%."
            ),
            suggested_action=(
                f"Review {country} corridor exposures. "
                f"Advise clients on {pair} timing."
            ),
            indicative_rate=official,
            notional_at_risk_zar=0.0,
            expires_at=(datetime.now() + timedelta(hours=12)).isoformat(),
        )

    def _current_rate(self, ticks: List[Dict], pair: str) -> Optional[float]:
        matching = [t for t in ticks if t.get("currency_pair") == pair]
        return matching[-1].get("mid_rate") if matching else None

    def _current_vol(self, ticks: List[Dict], pair: str) -> Optional[float]:
        matching = [t for t in ticks if t.get("currency_pair") == pair]
        return matching[-1].get("annualised_vol") if matching else None
