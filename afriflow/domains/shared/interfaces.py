from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Iterator, Optional, Protocol, runtime_checkable
import asyncio
import time
from .config import AppConfig, get_config
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("domains.shared.interfaces")


@runtime_checkable
class BaseSimulator(Protocol):
    def initialize(self, config: Optional[AppConfig] = None) -> None: ...
    def validate_input(self, **kwargs: Any) -> None: ...
    def generate_one(self, **kwargs: Any) -> Dict[str, Any] | Any: ...
    def stream(self, count: int = 1, **kwargs: Any) -> Iterator[Dict[str, Any] | Any]: ...


class SimulatorBase(ABC):
    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or get_config()
        self.initialize(self.config)

    @abstractmethod
    def initialize(self, config: Optional[AppConfig] = None) -> None:
        ...

    @abstractmethod
    def validate_input(self, **kwargs: Any) -> None:
        ...

    @abstractmethod
    def generate_one(self, **kwargs: Any) -> Dict[str, Any] | Any:
        ...

    def stream(self, count: int = 1, **kwargs: Any) -> Iterator[Dict[str, Any] | Any]:
        for _ in range(max(0, int(count))):
            yield self.generate_one(**kwargs)


class BaseProcessor(ABC):
    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or get_config()
        self.configure(self.config)

    @abstractmethod
    def configure(self, config: Optional[AppConfig] = None) -> None:
        ...

    @abstractmethod
    def validate(self, record: Any) -> None:
        ...

    @abstractmethod
    def process_sync(self, record: Any) -> Any:
        ...

    async def process_async(self, record: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.process_sync, record)

    def benchmark(self, records: Iterable[Any], runs: int = 1) -> Dict[str, Any]:
        start = time.perf_counter()
        count = 0
        for _ in range(max(1, runs)):
            for r in records:
                self.process_sync(r)
                count += 1
        elapsed = time.perf_counter() - start
        return {"count": count, "elapsed_seconds": elapsed, "throughput_rps": count / elapsed if elapsed else None}
