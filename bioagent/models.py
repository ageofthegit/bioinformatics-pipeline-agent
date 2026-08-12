"""Small data structures shared by the workflow modules."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PipelinePlan:
    input_file: str
    runner: str = "python"
    executor: str = "direct"
    requested_resources: dict[str, int] = field(default_factory=dict)
    cost: str = "not_applicable"
    analysis: str = "FASTQ quality control"
    quality_threshold: float = 20.0
    steps: list[str] = field(
        default_factory=lambda: [
            "Validate FASTQ structure",
            "Measure read length, GC content, unknown bases and base quality",
            "Check quality by base position and flag low-quality reads",
            "Recommend whether a low-quality tail should be reviewed for trimming",
            "Create a human-readable report",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunRecord:
    run_id: str
    run_directory: str
    status: str = "created"
    plan: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    job_status: str = "not_started"
    job_history: list[dict[str, Any]] = field(default_factory=list)
    execution: dict[str, Any] = field(default_factory=dict)
    execution_attempts: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 1
    retry_proposal: dict[str, Any] = field(default_factory=dict)
    failure_summary: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    explanation_provider: str = ""
    plan_explanation: dict[str, Any] = field(default_factory=dict)
    result_explanation: dict[str, Any] = field(default_factory=dict)
    explanation_errors: list[str] = field(default_factory=list)
    invocation: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
