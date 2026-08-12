"""Deterministic job monitoring, failure explanations, and retry guidance."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bioagent.models import RunRecord
from bioagent.runners.base import RunnerOutcome
from bioagent.state import add_audit_event, save_record


JOB_STATES = {
    "queued",
    "running",
    "completed",
    "failed",
    "awaiting_retry_approval",
}
MAX_RETRIES = 1


def transition_job(
    record: RunRecord,
    run_directory: Path,
    status: str,
    attempt: int,
    details: dict[str, Any] | None = None,
) -> None:
    if status not in JOB_STATES:
        raise ValueError(f"Unknown job status: {status}")

    transition: dict[str, Any] = {
        "status": status,
        "time": datetime.now(timezone.utc).isoformat(),
        "attempt": attempt,
    }
    if details:
        transition.update(details)

    record.job_status = status
    record.job_history.append(transition)
    save_record(record)
    add_audit_event(run_directory, "job_state_changed", transition)


def explain_failure(outcome: RunnerOutcome) -> str:
    output = f"{outcome.stderr}\n{outcome.stdout}".lower()

    if outcome.exit_code == 124 or "wall-time limit" in output:
        return (
            "The local queue job exceeded its approved wall-time limit. Review the "
            "job before requesting any increase."
        )
    if outcome.exit_code == 127:
        return (
            "The runner could not start. Check that the selected runner and Java "
            "runtime are installed and available."
        )
    if "unable to create plugins dir" in output or "permission denied" in output:
        return (
            "Nextflow could not write to a required runtime folder. Check the cache "
            "folder permissions before trying again."
        )
    if "qc.json" in output:
        return (
            "The pipeline did not produce a readable qc.json result. Review the "
            "captured output and Nextflow log."
        )
    if "fastq_qc" in output or ("process" in output and "failed" in output):
        return (
            "The FASTQ quality-control process failed. Review the captured error "
            "output and Nextflow log before retrying."
        )
    if "no such file" in output or "not found" in output:
        return (
            "The runner could not find a required file or command. Review the "
            "captured path and installation details before retrying."
        )
    return (
        f"The {outcome.runner} runner stopped with exit code {outcome.exit_code}. "
        "Review its captured output before retrying."
    )


def propose_retry() -> str:
    return (
        "Retry the same approved analysis once with unchanged input, quality "
        "threshold, runner, and resources."
    )
