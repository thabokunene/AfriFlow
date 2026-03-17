import asyncio
from typing import Any
from domains.shared.interfaces import SimulatorBase, SimulatorBase as _SimulatorBase, BaseProcessor
from domains.shared.processor_adapter import FunctionProcessor


def test_function_processor_sync_and_async():
    fp = FunctionProcessor(lambda x: x * 2, validator=lambda v: isinstance(v, (int, float)) or (_ for _ in ()).throw(ValueError()))
    assert fp.process_sync(3) == 6
    out = asyncio.run(fp.process_async(5))
    assert out == 10
    bench = fp.benchmark([1, 2, 3], runs=2)
    assert bench["count"] == 6 and bench["elapsed_seconds"] >= 0


def test_simulator_base_stream_contract():
    class S(_SimulatorBase):
        def initialize(self, config=None): ...
        def validate_input(self, **kwargs: Any): ...
        def generate_one(self, **kwargs: Any): return {"ok": True}
    s = S()
    records = list(s.stream(count=3))
    assert len(records) == 3 and records[0]["ok"]
