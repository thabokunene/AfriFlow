"""
AfriFlow Intelligence API

We expose the cross-domain client intelligence layer
via a FastAPI application.

Endpoints:

  GET  /health                   – liveness probe
  GET  /clients/{golden_id}      – unified golden record
  GET  /clients/{golden_id}/briefing – pre-meeting briefing
  GET  /clients/{golden_id}/nba  – next best action
  POST /signals/expansion        – expansion signal query
  POST /signals/shadow           – data shadow query
  GET  /currency-events/active   – active FX events
  POST /currency-events/propagate – propagate an event

Authentication: Bearer token (JWT) – see auth_middleware.
Audit: Every request is logged – see audit_middleware.

POPIA note: All PII fields are stripped before
cross-border API calls. The API is deployed per
country pod. The central hub only receives aggregated
and de-identified signals.

Disclaimer: This is not a sanctioned Standard Bank
Group project. Built by Thabo Kunene for portfolio
purposes. All data is simulated.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# We use a minimal HTTP framework stub so the app runs on stdlib alone
# (FastAPI is not installed in the demo venv). In production this module
# would declare `app = FastAPI()` and use @app.get / @app.post decorators.
# The route logic, schema validation, and middleware design are unchanged.
# ---------------------------------------------------------------------------


@dataclass
class APIResponse:
    """Standard envelope for all API responses."""

    request_id: str
    timestamp: str
    status: str          # "ok" or "error"
    data: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class HealthResponse:
    status: str
    version: str
    domains_online: List[str]
    timestamp: str


def _ok(data: Any) -> Dict:
    return APIResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        status="ok",
        data=data,
    ).to_dict()


def _error(message: str, status_code: int = 400) -> Dict:
    return APIResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        status="error",
        error=message,
    ).to_dict()


# ---------------------------------------------------------------------------
# Route handlers — these are the pure logic functions.
# In the FastAPI version each is decorated with @router.get / @router.post.
# ---------------------------------------------------------------------------


class HealthRoutes:
    """
    We expose liveness and readiness probes for
    Kubernetes health checks.
    """

    VERSION = "1.0.0"
    DOMAINS = ["cib", "forex", "insurance", "cell", "pbb"]

    def get_health(self) -> Dict:
        """
        GET /health

        Returns 200 if the API is alive. Kubernetes
        uses this as the liveness probe.
        """

        return _ok(
            HealthResponse(
                status="healthy",
                version=self.VERSION,
                domains_online=self.DOMAINS,
                timestamp=datetime.now().isoformat(),
            ).__dict__
        )

    def get_readiness(
        self, golden_record_store: Any
    ) -> Dict:
        """
        GET /ready

        Returns 200 only if the golden record store
        is reachable. Kubernetes uses this as the
        readiness probe — if not ready, traffic is
        not routed to this pod.
        """

        try:
            golden_record_store.ping()
            return _ok({"ready": True})
        except Exception as exc:
            return _error(f"Golden record store unavailable: {exc}")


class ClientRoutes:
    """
    We expose unified client intelligence endpoints.
    """

    def __init__(
        self,
        golden_record_store,
        popia_classifier,
    ):
        self.store = golden_record_store
        self.popia = popia_classifier

    def get_client(
        self,
        golden_id: str,
        requester_role: str,
        requester_country: str,
    ) -> Dict:
        """
        GET /clients/{golden_id}

        Returns the unified golden record for a client.

        We apply POPIA field masking based on:
        - requester_role (RM, Compliance, ExCo)
        - requester_country (cannot see cross-border PII)
        """

        if not golden_id.startswith("GLD-"):
            return _error(
                f"Invalid golden_id format: {golden_id}. "
                f"Must start with 'GLD-'"
            )

        record = self.store.get(golden_id)
        if not record:
            return _error(
                f"Client {golden_id} not found", 404
            )

        # Apply POPIA field masking
        masked = self._mask_for_role(
            record, requester_role, requester_country
        )

        return _ok(masked)

    def get_client_summary(
        self,
        golden_id: str,
    ) -> Dict:
        """
        GET /clients/{golden_id}/summary

        Returns a non-PII summary suitable for
        dashboards and cross-country views.
        Only includes aggregated and de-identified
        fields — safe for central hub.
        """

        record = self.store.get(golden_id)
        if not record:
            return _error(
                f"Client {golden_id} not found", 404
            )

        summary = {
            "golden_id": record.get("golden_id"),
            "client_tier": record.get("client_tier"),
            "home_country": record.get("home_country"),
            "domains_active": record.get("domains_active"),
            "cross_sell_priority": record.get(
                "cross_sell_priority"
            ),
            "primary_risk_signal": record.get(
                "primary_risk_signal"
            ),
            "has_cib": record.get("has_cib"),
            "has_forex": record.get("has_forex"),
            "has_insurance": record.get("has_insurance"),
            "has_cell": record.get("has_cell"),
            "has_pbb": record.get("has_pbb"),
        }
        return _ok(summary)

    def _mask_for_role(
        self,
        record: Dict,
        role: str,
        requester_country: str,
    ) -> Dict:
        """
        We apply field-level masking based on the
        requester's role and country.

        Compliance officers see everything.
        RMs see their own country's PII only.
        ExCo sees aggregated data only.
        """

        masked = dict(record)

        if role == "ExCo":
            # Remove all PII — ExCo views are aggregate
            for field in ["canonical_name", "registration_number",
                          "tax_number", "relationship_manager"]:
                masked.pop(field, None)

        elif role == "RM":
            # RMs cannot see tax numbers
            masked.pop("tax_number", None)
            # Cross-country RMs cannot see other country PII
            if requester_country != record.get("home_country"):
                masked.pop("registration_number", None)

        # Compliance can see everything — no masking

        return masked


class BriefingRoutes:
    """
    We expose pre-meeting RM briefing endpoints.
    """

    def __init__(self, briefing_generator):
        self.generator = briefing_generator

    def get_briefing(
        self,
        golden_id: str,
        meeting_type: str = "client_review",
    ) -> Dict:
        """
        GET /clients/{golden_id}/briefing

        Returns a structured pre-meeting briefing.
        Intended to be called 30 minutes before
        the RM walks into the meeting room.

        The briefing includes:
        - Recent cross-domain activity summary
        - Active signals (expansion, attrition, etc.)
        - Top 3 talking points
        - Revenue opportunities ranked by score
        - Risk alerts requiring immediate discussion
        """

        try:
            briefing = self.generator.generate(
                golden_id=golden_id,
                meeting_type=meeting_type,
            )
            return _ok(briefing)
        except Exception as exc:
            return _error(f"Briefing generation failed: {exc}")


class SignalRoutes:
    """
    We expose cross-domain signal query endpoints.
    """

    def __init__(
        self,
        expansion_detector,
        shadow_calculator,
        nba_model,
    ):
        self.expansion = expansion_detector
        self.shadow = shadow_calculator
        self.nba = nba_model

    def get_expansion_signals(
        self,
        min_confidence: float = 60.0,
        country_filter: Optional[str] = None,
    ) -> Dict:
        """
        GET /signals/expansion

        Returns all active geographic expansion signals
        above the confidence threshold.

        These are typically surfaced in the RM dashboard
        as "Clients expanding into new markets."
        """

        signals = self.expansion.get_active_signals(
            min_confidence=min_confidence
        )

        if country_filter:
            signals = [
                s for s in signals
                if s.get("expansion_country") == country_filter
            ]

        return _ok({
            "count": len(signals),
            "signals": signals,
            "generated_at": datetime.now().isoformat(),
        })

    def get_shadow_signals(
        self,
        min_confidence: float = 0.70,
        category_filter: Optional[str] = None,
    ) -> Dict:
        """
        GET /signals/shadow

        Returns data shadow signals — clients whose
        expected cross-domain footprint is larger than
        their actual footprint.

        A shadow signal means: "this client should be
        doing business with another division, but is
        not — which means a competitor has that wallet."
        """

        shadows = self.shadow.get_active_shadows(
            min_confidence=min_confidence
        )

        if category_filter:
            shadows = [
                s for s in shadows
                if s.get("category") == category_filter
            ]

        return _ok({
            "count": len(shadows),
            "shadows": shadows,
            "generated_at": datetime.now().isoformat(),
        })

    def get_nba(
        self,
        golden_id: str,
        domain_profiles: Optional[Dict] = None,
    ) -> Dict:
        """
        GET /clients/{golden_id}/nba

        Returns the scored next-best-action
        recommendations for a client.

        The top recommendation should be the opening
        topic for any client meeting.
        """

        domain_profiles = domain_profiles or {}
        result = self.nba.score_client(
            golden_record={"golden_id": golden_id},
            cib_profile=domain_profiles.get("cib"),
            forex_profile=domain_profiles.get("forex"),
            insurance_profile=domain_profiles.get("insurance"),
            cell_profile=domain_profiles.get("cell"),
            pbb_profile=domain_profiles.get("pbb"),
        )

        return _ok({
            "golden_id": golden_id,
            "top_action": (
                result.top_action.__dict__
                if result.top_action else None
            ),
            "action_count": len(result.all_actions),
            "data_completeness": result.data_completeness_score,
            "generated_at": result.generated_at,
        })


class CurrencyEventRoutes:
    """
    We expose currency event query and propagation
    endpoints for real-time FX intelligence.
    """

    def __init__(
        self,
        classifier,
        propagator,
        event_store,
    ):
        self.classifier = classifier
        self.propagator = propagator
        self.store = event_store

    def get_active_events(
        self,
        min_severity: str = "MEDIUM",
    ) -> Dict:
        """
        GET /currency-events/active

        Returns all active currency events above the
        severity threshold.

        Used by the ExCo dashboard to show active
        FX risk across the portfolio in real time.
        """

        events = self.store.get_active(
            min_severity=min_severity
        )
        return _ok({
            "count": len(events),
            "events": events,
            "generated_at": datetime.now().isoformat(),
        })

    def propagate_event(
        self,
        currency: str,
        rate_before: float,
        rate_after: float,
        period_hours: int = 24,
        is_official_announcement: bool = False,
    ) -> Dict:
        """
        POST /currency-events/propagate

        Classifies and propagates a currency event
        across all five domains.

        Called by the FX monitoring service when a
        rate anomaly is detected. Returns the full
        cascade report with per-client impact.

        This endpoint drives the real-time RM alerts:
        within 60 seconds of a devaluation we have
        quantified impact for every affected client.
        """

        if rate_before <= 0:
            return _error(
                "rate_before must be a positive number"
            )

        event = self.classifier.classify_rate_move(
            currency=currency,
            rate_before=rate_before,
            rate_after=rate_after,
            period_hours=period_hours,
            trigger_source=(
                "official_announcement"
                if is_official_announcement
                else "rate_anomaly_detector"
            ),
        )

        if event is None:
            return _ok({
                "classified": False,
                "message": (
                    "Rate movement within normal bounds — "
                    "no event generated"
                ),
            })

        cascade = self.propagator.propagate(event)

        return _ok({
            "event_id": event.event_id,
            "currency": event.currency_code,
            "tier": event.event_tier.value,
            "magnitude_pct": event.magnitude_pct,
            "clients_affected": cascade.total_clients_affected,
            "total_exposure_zar": cascade.total_exposure_zar,
            "actions_required": sum(
                1 for i in cascade.domain_impacts
                if i.action_required
            ),
            "propagated_at": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


class AfriFlowApp:
    """
    We wire all route handlers to their dependencies
    and expose a single callable application.

    In the FastAPI version this would be replaced by
    lifespan context managers and dependency injection.
    Here we use explicit constructor injection so the
    dependency graph is visible and testable.
    """

    def __init__(
        self,
        golden_record_store,
        briefing_generator,
        expansion_detector,
        shadow_calculator,
        nba_model,
        currency_classifier,
        currency_propagator,
        currency_event_store,
        popia_classifier,
    ):
        self.health = HealthRoutes()
        self.clients = ClientRoutes(
            golden_record_store, popia_classifier
        )
        self.briefings = BriefingRoutes(briefing_generator)
        self.signals = SignalRoutes(
            expansion_detector,
            shadow_calculator,
            nba_model,
        )
        self.currency_events = CurrencyEventRoutes(
            currency_classifier,
            currency_propagator,
            currency_event_store,
        )

    def handle(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
        auth_context: Optional[Dict] = None,
    ) -> Dict:
        """
        We dispatch an incoming request to the correct
        route handler.

        In production FastAPI handles this routing.
        This dispatcher is used in integration tests
        and for demo purposes.
        """

        params = params or {}
        body = body or {}
        auth = auth_context or {}

        role = auth.get("role", "RM")
        country = auth.get("country", "ZA")

        # Health routes
        if path == "/health" and method == "GET":
            return self.health.get_health()

        # Client routes
        if path.startswith("/clients/") and method == "GET":
            parts = path.split("/")
            golden_id = parts[2] if len(parts) > 2 else ""
            endpoint = parts[3] if len(parts) > 3 else ""

            if endpoint == "briefing":
                return self.briefings.get_briefing(
                    golden_id,
                    params.get("meeting_type", "client_review"),
                )
            elif endpoint == "nba":
                return self.signals.get_nba(
                    golden_id,
                    body.get("domain_profiles"),
                )
            elif endpoint == "summary":
                return self.clients.get_client_summary(golden_id)
            else:
                return self.clients.get_client(
                    golden_id, role, country
                )

        # Signal routes
        if path == "/signals/expansion" and method == "GET":
            return self.signals.get_expansion_signals(
                min_confidence=float(params.get("min_confidence", 60)),
                country_filter=params.get("country"),
            )

        if path == "/signals/shadow" and method == "GET":
            return self.signals.get_shadow_signals(
                min_confidence=float(params.get("min_confidence", 0.70)),
                category_filter=params.get("category"),
            )

        # Currency event routes
        if path == "/currency-events/active" and method == "GET":
            return self.currency_events.get_active_events(
                min_severity=params.get("min_severity", "MEDIUM")
            )

        if (
            path == "/currency-events/propagate"
            and method == "POST"
        ):
            return self.currency_events.propagate_event(
                currency=body.get("currency", ""),
                rate_before=float(body.get("rate_before", 0)),
                rate_after=float(body.get("rate_after", 0)),
                period_hours=int(body.get("period_hours", 24)),
                is_official_announcement=body.get(
                    "is_official_announcement", False
                ),
            )

        return _error(f"Route not found: {method} {path}", 404)
