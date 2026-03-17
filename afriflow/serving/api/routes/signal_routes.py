"""
Signal Routes — cross-domain signal query endpoints.

Routes:
  GET /signals/expansion    — active geographic expansion signals
  GET /signals/shadow       — data shadow signals (competitor wallet)
  GET /clients/{id}/nba     — next best action for client

These endpoints power the RM dashboard signal feed and the
ExCo portfolio-level intelligence view.
"""

from afriflow.serving.api.app import SignalRoutes

__all__ = ["SignalRoutes"]
