"""Safe, SDK-independent functions exposed by the local MCP adapter."""

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bioagent.models import PipelinePlan, RunRecord
from bioagent.state import add_audit_event
from bioagent.tools.fastq import validate_fastq
from bioagent.tools.qc import make_recommendation


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SUPPORTED_FASTQ_SUFFIXES = {".fastq", ".fq"}
SUPPORTED_RUNNERS = {"python", "nextflow"}
IDENTIFIER_PATTERN = re.compile(r"^(request|run)-[A-Za-z0-9-]+$")


class McpToolService:
    """Own path checks and persistent approval requests for the MCP tools."""

    def __init__(
        self,
        project_directory: Path = PROJECT_DIRECTORY,
        request_directory: Path | None = None,
    ) -> None:
        self.project_directory = project_directory.resolve()
        self.data_directory = (self.project_directory / "data").resolve()
        self.run_directory = (self.project_directory / "runs").resolve()
        self.request_directory = (
            request_directory.resolve()
            if request_directory is not None
            else (self.project_directory / "approval_requests").resolve()
        )

    def _safe_fastq_path(self, input_file: str) -> Path:
        if "\x00" in input_file:
            raise ValueError("Input path contains an unsafe null character")

        candidate = Path(input_file).expanduser()
        if not candidate.is_absolute():
            candidate = self.project_directory / candidate
        resolved = candidate.resolve()

        if not resolved.is_relative_to(self.data_directory):
            raise ValueError(
                "MCP may only read FASTQ files inside the project data folder"
            )
        if resolved.suffix.lower() not in SUPPORTED_FASTQ_SUFFIXES:
            raise ValueError("Only .fastq and .fq input files are supported")
        return resolved

    @staticmethod
    def _check_runner(runner: str) -> None:
        if runner not in SUPPORTED_RUNNERS:
            raise ValueError("Runner must be either python or nextflow")

    def validate_fastq(self, input_file: str) -> dict[str, Any]:
        """Validate one project-local FASTQ without starting an analysis."""
        path = self._safe_fastq_path(input_file)
        return {
            "input_file": str(path),
            **validate_fastq(path),
            "execution_started": False,
        }

    def propose_qc_plan(
        self,
        input_file: str,
        runner: str = "python",
    ) -> dict[str, Any]:
        """Build the same deterministic QC plan used by the CLI."""
        self._check_runner(runner)
        path = self._safe_fastq_path(input_file)
        validation = validate_fastq(path)
        plan = PipelinePlan(input_file=str(path), runner=runner)
        return {
            "status": "proposed",
            "plan": plan.to_dict(),
            "validation": validation,
            "approval_required": True,
            "execution_started": False,
        }

    def _write_request(self, request: dict[str, Any]) -> None:
        self.request_directory.mkdir(parents=True, exist_ok=True)
        request_path = self.request_directory / f"{request['request_id']}.json"
        request_path.write_text(
            json.dumps(request, indent=2) + "\n",
            encoding="utf-8",
        )

    def _audit_request(self, event: str, details: dict[str, Any]) -> None:
        self.request_directory.mkdir(parents=True, exist_ok=True)
        add_audit_event(self.request_directory, event, details)

    def request_pipeline_run(
        self,
        input_file: str,
        runner: str = "python",
    ) -> dict[str, Any]:
        """Create a pending request; this method deliberately cannot execute it."""
        proposal = self.propose_qc_plan(input_file, runner)
        timestamp = datetime.now(timezone.utc)
        request_id = (
            f"request-{timestamp.strftime('%Y%m%d-%H%M%S-%f')}-"
            f"{secrets.token_hex(4)}"
        )
        request = {
            "request_id": request_id,
            "status": "awaiting_human_approval",
            "created_at": timestamp.isoformat(),
            "plan": proposal["plan"],
            "validation": proposal["validation"],
            "approval_required": True,
            "execution_started": False,
            "next_step": (
                "A person must review this request and run: "
                f".venv/bin/python -m bioagent.run_request {request_id}"
            ),
        }
        self._write_request(request)
        self._audit_request(
            "pipeline_run_requested",
            {
                "request_id": request_id,
                "status": request["status"],
                "input_file": proposal["plan"]["input_file"],
                "runner": runner,
                "execution_started": False,
            },
        )
        return request

    @staticmethod
    def _check_identifier(identifier: str) -> None:
        if not IDENTIFIER_PATTERN.fullmatch(identifier):
            raise ValueError("Invalid request or run identifier")

    @staticmethod
    def _read_json(path: Path, missing_message: str) -> dict[str, Any]:
        if not path.is_file():
            raise ValueError(missing_message)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Saved state could not be read: {error}") from error
        if not isinstance(value, dict):
            raise ValueError("Saved state is not a JSON object")
        return value

    def get_run_status(self, identifier: str) -> dict[str, Any]:
        """Read one pending approval request or one existing workflow run."""
        self._check_identifier(identifier)
        if identifier.startswith("request-"):
            request = self._read_json(
                self.request_directory / f"{identifier}.json",
                f"Unknown request ID: {identifier}",
            )
            return {
                "kind": "approval_request",
                "request_id": request["request_id"],
                "status": request["status"],
                "approval_required": request["approval_required"],
                "execution_started": request["execution_started"],
                "linked_run_id": request.get("linked_run_id"),
                "linked_run_status": request.get("linked_run_status"),
            }

        state = self._read_json(
            self.run_directory / identifier / "state.json",
            f"Unknown run ID: {identifier}",
        )
        return {
            "kind": "workflow_run",
            "run_id": state["run_id"],
            "status": state["status"],
            "job_status": state.get("job_status", "not_started"),
            "attempts": len(state.get("execution_attempts", [])),
            "retry_count": state.get("retry_count", 0),
            "failure_summary": state.get("failure_summary", ""),
        }

    def summarise_qc_result(self, run_id: str) -> dict[str, Any]:
        """Summarise measurements already saved by a completed workflow run."""
        self._check_identifier(run_id)
        if not run_id.startswith("run-"):
            raise ValueError("A workflow run ID is required to summarise QC results")
        state = self._read_json(
            self.run_directory / run_id / "state.json",
            f"Unknown run ID: {run_id}",
        )
        result = state.get("result")
        if not isinstance(result, dict) or not result:
            raise ValueError(f"Run {run_id} has no completed QC result")

        return {
            "run_id": run_id,
            "status": state["status"],
            "read_count": result["read_count"],
            "mean_base_quality": result["mean_base_quality"],
            "low_quality_percent": result["low_quality_percent"],
            "gc_percent": result["gc_percent"],
            "n_percent": result["n_percent"],
            "shortest_read": result["shortest_read"],
            "longest_read": result["longest_read"],
            "trimming_guidance": result["trimming_recommendation"],
            "recommendation": state.get("recommendation")
            or make_recommendation(result),
            "human_review_required": state["status"]
            not in {"accepted_by_human", "accepted_for_demo"},
        }

    def load_request(self, request_id: str) -> dict[str, Any]:
        """Load a request for the separate human-operated CLI."""
        self._check_identifier(request_id)
        if not request_id.startswith("request-"):
            raise ValueError("A request ID is required")
        return self._read_json(
            self.request_directory / f"{request_id}.json",
            f"Unknown request ID: {request_id}",
        )

    def resolve_request(self, request_id: str, record: RunRecord) -> None:
        """Link a manually handled request to its resulting workflow run."""
        request = self.load_request(request_id)
        request.update(
            {
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "execution_started": bool(record.execution_attempts),
                "linked_run_id": record.run_id,
                "linked_run_status": record.status,
            }
        )
        self._write_request(request)
        self._audit_request(
            "pipeline_request_resolved",
            {
                "request_id": request_id,
                "run_id": record.run_id,
                "run_status": record.status,
            },
        )
