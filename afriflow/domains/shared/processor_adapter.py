"""
@file processor_adapter.py
@description Adapter utilities to wrap callables as BaseProcessor implementations
@author Thabo Kunene
@created 2026-03-17
"""
from __future__ import annotations
from typing import Any, Callable, Iterable, Optional  # typing contracts for adapters and validators
from .interfaces import BaseProcessor  # processor base contract used throughout domain modules
from .config import AppConfig  # optional config injection for environment-aware processor behavior
from afriflow.logging_config import get_logger, log_operation  # structured logging helpers

logger = get_logger("domains.shared.processor_adapter")


class FunctionProcessor(BaseProcessor):
    """
    Wrap a plain function as a BaseProcessor for pipeline compatibility.
    Parameters:
    - func: callable that performs the synchronous transformation
    - validator: optional callable enforcing input constraints before processing
    - config: optional AppConfig to override the global environment settings
    """
    def __init__(self, func: Callable[[Any], Any], validator: Optional[Callable[[Any], None]] = None, config: Optional[AppConfig] = None) -> None:
        # Store injected behavior so process_sync can remain minimal and composable
        self._func = func
        self._validator = validator
        super().__init__(config=config)

    def configure(self, config: Optional[AppConfig] = None) -> None:
        """
        Configure hook required by BaseProcessor.
        For function wrappers, there is no state to configure beyond logging.
        """
        log_operation(logger, "configure", "completed")

    def validate(self, record: Any) -> None:
        """
        Validate record via the injected validator when provided.
        """
        if self._validator:
            self._validator(record)

    def process_sync(self, record: Any) -> Any:
        """
        Run validation and then execute the wrapped function synchronously.
        Returns:
            The wrapped function's output for the given record
        """
        self.validate(record)
        return self._func(record)
