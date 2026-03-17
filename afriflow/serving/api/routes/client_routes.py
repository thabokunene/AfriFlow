"""
Client Routes — re-exported from app module for FastAPI mounting.

Routes:
  GET /clients/{golden_id}         — unified golden record
  GET /clients/{golden_id}/summary — non-PII summary
  GET /clients/{golden_id}/briefing — pre-meeting briefing
  GET /clients/{golden_id}/nba      — next best action
"""

from afriflow.serving.api.app import ClientRoutes, BriefingRoutes

__all__ = ["ClientRoutes", "BriefingRoutes"]
