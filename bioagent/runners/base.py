"""Shared runner contract and execution result."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class RunnerOutcome:
    runner: str
    command: list[str]
    exit_code: int
    duration_seconds: float
    version: str
    stdout: str = ""
    stderr: str = ""
    output_file: str = ""
    executor: str = "direct"
    requested_resources: dict[str, int] = field(default_factory=dict)
    cost: str = "not_applicable"
    queue_job_id: str = ""
    result: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and bool(self.result)

    def execution_dict(self) -> dict[str, Any]:
        execution = asdict(self)
        execution.pop("result")
        return execution


class Runner(Protocol):
    name: str

    def run(
        self,
        input_file: Path,
        quality_threshold: float,
        run_directory: Path,
    ) -> RunnerOutcome: ...
