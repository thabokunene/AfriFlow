"""
Health Routes — re-exported from app module for FastAPI mounting.

In the FastAPI production configuration these would be mounted as:
    app.include_router(health_router, prefix="")
"""

# Re-export the HealthRoutes class from the app module.
# The standalone route module pattern allows the FastAPI router to be
# mounted independently of the full AfriFlowApp.

from afriflow.serving.api.app import HealthRoutes

__all__ = ["HealthRoutes"]
