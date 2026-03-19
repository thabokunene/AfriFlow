"""
@file processor_adapter.py
@description Adapter utilities to wrap callables as BaseProcessor implementations, enabling functional composition in data pipelines.
@author Thabo Kunene
@created 2026-03-19
"""

# Enables postponed evaluation of type annotations
from __future__ import annotations
# Typing hints for defining strong contracts for functions and containers
from typing import Any, Callable, Iterable, Optional
# Base class for all domain processors, ensuring consistent lifecycle and execution methods
from .interfaces import BaseProcessor
# Configuration container for environment-specific processor settings
from .config import AppConfig
# Structured logging utilities for tracking processor execution and errors
from afriflow.logging_config import get_logger, log_operation

# Initialize logger for the processor adapter namespace
logger = get_logger("domains.shared.processor_adapter")


class FunctionProcessor(BaseProcessor):
    """
    Adapter that wraps a plain Python function to comply with the BaseProcessor interface.
    This allows simple transformation functions to be used within complex domain pipelines.

    Attributes:
        func: The core transformation function to be executed.
        validator: An optional function to validate records before processing.
        config: Configuration object for the processor.
    """
    def __init__(self, func: Callable[[Any], Any], validator: Optional[Callable[[Any], None]] = None, config: Optional[AppConfig] = None) -> None:
        """
        Initializes the function processor adapter.
        
        :param func: The callable that performs the record transformation.
        :param validator: Optional callable that raises an exception if a record is invalid.
        :param config: Optional AppConfig override.
        """
        # Store injected behavior so process_sync can remain minimal and composable
        self._func = func
        self._validator = validator
        super().__init__(config=config)

    def configure(self, config: Optional[AppConfig] = None) -> None:
        """
        Implementation of the BaseProcessor configure hook.
        For simple function wrappers, this primarily logs the initialization event.
        
        :param config: Configuration object.
        """
        log_operation(logger, "configure", "completed")

    def validate(self, record: Any) -> None:
        """
        Executes the injected validator function if one was provided during initialization.
        
        :param record: The record to be validated.
        """
        if self._validator:
            self._validator(record)

    def process_sync(self, record: Any) -> Any:
        """
        Validates and then processes a record using the wrapped function.
        
        :param record: The input record to process.
        :return: The result of the wrapped function's execution.
        """
        self.validate(record)
        return self._func(record)
