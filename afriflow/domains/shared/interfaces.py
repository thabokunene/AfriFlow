"""
@file interfaces.py
@description Shared simulator and processor interfaces used across all AfriFlow domains to ensure consistent data handling.
@author Thabo Kunene
@created 2026-03-19
"""

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations
# ABC and abstractmethod define the base contracts for processors/simulators
from abc import ABC, abstractmethod
# Type hints for strong contracts between domain modules and the integration layer
from typing import Any, Dict, Iterable, Iterator, Optional, Protocol, runtime_checkable
# asyncio enables non-blocking processing wrappers around synchronous processors
import asyncio
# time provides high-resolution timing for benchmark throughput measurements
import time
# AppConfig/get_config provide environment-aware defaults for domain components
from .config import AppConfig, get_config
# Central structured logging utilities for consistent observability across modules
from afriflow.logging_config import get_logger, log_operation

# Dedicated logger namespace for interface-level events and benchmarks
logger = get_logger("domains.shared.interfaces")


@runtime_checkable
class BaseSimulator(Protocol):
    """
    Structural protocol for simulator components.
    Ensures any class implementing these methods can be used as a simulator.
    """
    # initialize allows simulators to load configuration and precompute lookup data
    def initialize(self, config: Optional[AppConfig] = None) -> None: ...
    # validate_input enforces domain-specific constraints before generating records
    def validate_input(self, **kwargs: Any) -> None: ...
    # generate_one produces a single synthetic record used for demos, tests, and load
    def generate_one(self, **kwargs: Any) -> Dict[str, Any] | Any: ...
    # stream yields a sequence of generated records for batch or streaming simulations
    def stream(self, count: int = 1, **kwargs: Any) -> Iterator[Dict[str, Any] | Any]: ...


class SimulatorBase(ABC):
    """
    Abstract base for domain simulators providing deterministic synthetic data.
    
    Design intent:
    - Subclasses should validate inputs to prevent generating invalid contract records.
    - stream() standardizes bulk generation without requiring each simulator to reimplement loops.
    """
    def __init__(self, config: Optional[AppConfig] = None) -> None:
        """
        Initializes the simulator with an optional configuration override.
        
        :param config: Custom AppConfig instance. Defaults to the global singleton.
        """
        # Default to global config so simulators behave consistently across environments
        self.config = config or get_config()
        self.initialize(self.config)

    @abstractmethod
    def initialize(self, config: Optional[AppConfig] = None) -> None:
        """
        Prepares internal state such as reference data, distributions, or random seeds.
        
        :param config: Configuration object used for initialization.
        """
        ...

    @abstractmethod
    def validate_input(self, **kwargs: Any) -> None:
        """
        Validates input parameters before generation. Should raise an exception on failure.
        
        :param kwargs: Keyword arguments to be validated.
        """
        ...

    @abstractmethod
    def generate_one(self, **kwargs: Any) -> Dict[str, Any] | Any:
        """
        Generates a single synthetic record or domain object.
        
        :param kwargs: Generation parameters (e.g., specific country, date range).
        :return: A dictionary or object representing the generated record.
        """
        ...

    def stream(self, count: int = 1, **kwargs: Any) -> Iterator[Dict[str, Any] | Any]:
        """
        Yields a stream of generated records.
        
        :param count: Number of records to generate.
        :param kwargs: Parameters passed to generate_one.
        :return: An iterator of generated records.
        """
        # Guard count to avoid negative ranges and unintended infinite generation patterns
        for _ in range(max(0, int(count))):
            yield self.generate_one(**kwargs)


class BaseProcessor(ABC):
    """
    Abstract base for domain processors used in sync and async execution contexts.
    
    Design intent:
    - configure() loads environment-aware safety controls (RBAC, limits).
    - validate() enforces contract and security requirements before processing.
    - process_sync() implements the actual domain transformation/enrichment logic.
    """
    def __init__(self, config: Optional[AppConfig] = None) -> None:
        """
        Initializes the processor with an optional configuration override.
        
        :param config: Custom AppConfig instance. Defaults to the global singleton.
        """
        # Default to global config so processors inherit consistent environment settings
        self.config = config or get_config()
        self.configure(self.config)

    @abstractmethod
    def configure(self, config: Optional[AppConfig] = None) -> None:
        """
        Sets internal limits, roles, or endpoints based on the provided configuration.
        
        :param config: Configuration object used for setup.
        """
        ...

    @abstractmethod
    def validate(self, record: Any) -> None:
        """
        Checks record integrity, required fields, and authorization constraints.
        
        :param record: The input record to be validated.
        """
        ...

    @abstractmethod
    def process_sync(self, record: Any) -> Any:
        """
        Executes the primary synchronous transformation or enrichment logic.
        
        :param record: The input record to process.
        :return: The processed/enriched result.
        """
        ...

    async def process_async(self, record: Any) -> Any:
        """
        Async wrapper for the synchronous processing logic.
        
        :param record: The input record to process.
        :return: The processed/enriched result.
        """
        # Offload CPU-bound sync processing to a thread executor to keep async loops responsive
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.process_sync, record)

    def benchmark(self, records: Iterable[Any], runs: int = 1) -> Dict[str, Any]:
        # Benchmark is intended for profiling and baseline establishment, not production request paths
        start = time.perf_counter()
        count = 0
        for _ in range(max(1, runs)):
            for r in records:
                self.process_sync(r)
                count += 1
        elapsed = time.perf_counter() - start
        return {"count": count, "elapsed_seconds": elapsed, "throughput_rps": count / elapsed if elapsed else None}
