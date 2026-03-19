"""
@file __init__.py
@description Initialization for the AfriFlow serving layer, exposing the core
    API application and the feature store server for consumption by downstream
    clients and front-end applications.
@author Thabo Kunene
@created 2026-03-19
"""

from .api import AfriFlowApp
from .feature_store import FeatureServer, FeatureDefinition

__all__ = ["AfriFlowApp", "FeatureServer", "FeatureDefinition"]
