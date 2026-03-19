"""
@file __init__.py
@description Initialization for the AfriFlow Intelligence API, exposing the
    main application class and standardized response models for RESTful endpoints.
@author Thabo Kunene
@created 2026-03-19
"""

from .app import AfriFlowApp, APIResponse

__all__ = ["AfriFlowApp", "APIResponse"]
