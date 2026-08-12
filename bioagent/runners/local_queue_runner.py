"""Local queued-execution wrapper with conservative resource governance."""

from dataclasses import dataclass
from pathlib import Path

from bioagent.runners.base import Runner, RunnerOutcome


DEFAULT_CPUS = 1
DEFAULT_MEMORY_MB = 1024
DEFAULT_WALL_TIME_SECONDS = 600
MAX_CPUS = 4
MAX_MEMORY_MB = 4096
MAX_WALL_TIME_SECONDS = 3600


@dataclass(frozen=True)
class ResourceRequest:
    cpus: int = DEFAULT_CPUS
    memory_mb: int = DEFAULT_MEMORY_MB
    wall_time_seconds: int = DEFAULT_WALL_TIME_SECONDS

    def to_dict(self) -> dict[str, int]:
        return {
            "cpus": self.cpus,
            "memory_mb": self.memory_mb,
            "wall_time_seconds": self.wall_time_seconds,
        }

    def hard_limit_violations(self) -> list[str]:
        violations: list[str] = []
        for name, value in self.to_dict().items():
            if value < 1:
                violations.append(f"{name} must be at least 1")
        if self.cpus > MAX_CPUS:
            violations.append(f"cpus exceeds the local maximum of {MAX_CPUS}")
        if self.memory_mb > MAX_MEMORY_MB:
            violations.append(
                f"memory_mb exceeds the local maximum of {MAX_MEMORY_MB}"
            )
        if self.wall_time_seconds > MAX_WALL_TIME_SECONDS:
            violations.append(
                "wall_time_seconds exceeds the local maximum of "
                f"{MAX_WALL_TIME_SECONDS}"
            )
        return violations

    def exceeds_defaults(self) -> bool:
        return (
            self.cpus > DEFAULT_CPUS
            or self.memory_mb > DEFAULT_MEMORY_MB
            or self.wall_time_seconds > DEFAULT_WALL_TIME_SECONDS
        )


class LocalQueueRunner:
    """Run an existing backend through a testable local queue simulation."""

    executor = "local_queue"
    cost = "not_applicable"

    def __init__(
        self,
        backend: Runner,
        resource_request: ResourceRequest | None = None,
    ) -> None:
        self.backend = backend
        self.resource_request = resource_request or ResourceRequest()

    @property
    def name(self) -> str:
        return self.backend.name

    @property
    def requires_resource_increase_approval(self) -> bool:
        return self.resource_request.exceeds_defaults()

    def run(
        self,
        input_file: Path,
        quality_threshold: float,
        run_directory: Path,
    ) -> RunnerOutcome:
        violations = self.resource_request.hard_limit_violations()
        if violations:
            return RunnerOutcome(
                runner=self.name,
                command=[],
                exit_code=2,
                duration_seconds=0,
                version="not started",
                stderr="; ".join(violations),
                executor=self.executor,
                requested_resources=self.resource_request.to_dict(),
                cost=self.cost,
                queue_job_id=f"local-{run_directory.name}",
            )

        outcome = self.backend.run(input_file, quality_threshold, run_directory)
        outcome.executor = self.executor
        outcome.requested_resources = self.resource_request.to_dict()
        outcome.cost = self.cost
        outcome.queue_job_id = f"local-{run_directory.name}"

        if outcome.duration_seconds > self.resource_request.wall_time_seconds:
            message = (
                "Local queue wall-time limit of "
                f"{self.resource_request.wall_time_seconds} seconds was exceeded."
            )
            outcome.exit_code = 124
            outcome.stderr = f"{outcome.stderr}\n{message}".strip()
            outcome.result = {}
        return outcome
