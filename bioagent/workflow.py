"""The complete human-in-the-loop workflow.

This module is the agent's coordinator. It calls tools, saves state and stops
at approval gates. The tools themselves never approve their own actions.
"""

from datetime import datetime, timezone
from pathlib import Path

from bioagent.approvals import ask_for_approval
from bioagent.llm.base import ExplanationProvider
from bioagent.llm.safety import explain_plan_safely, explain_result_safely
from bioagent.monitoring import (
    MAX_RETRIES,
    explain_failure,
    propose_retry,
    transition_job,
)
from bioagent.models import PipelinePlan, RunRecord
from bioagent.provenance import write_run_manifest
from bioagent.runners.base import Runner
from bioagent.runners.local_queue_runner import (
    DEFAULT_CPUS,
    DEFAULT_MEMORY_MB,
    DEFAULT_WALL_TIME_SECONDS,
)
from bioagent.runners.python_runner import PythonRunner
from bioagent.state import add_audit_event, save_record
from bioagent.tools.fastq import validate_fastq
from bioagent.tools.qc import make_recommendation


def create_run_directory(base_directory: Path) -> tuple[str, Path]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    run_id = f"run-{timestamp}"
    run_directory = base_directory / "runs" / run_id
    run_directory.mkdir(parents=True)
    return run_id, run_directory


def print_plan(plan: PipelinePlan) -> None:
    print("\nProposed plan")
    print(f"Input: {plan.input_file}")
    print(f"Analysis: {plan.analysis}")
    print(f"Runner: {plan.runner}")
    print(f"Executor: {plan.executor}")
    if plan.requested_resources:
        print(
            "Resources: "
            f"{plan.requested_resources['cpus']} CPU, "
            f"{plan.requested_resources['memory_mb']} MB memory, "
            f"{plan.requested_resources['wall_time_seconds']} seconds wall time"
        )
    print(f"Cost: {plan.cost}")
    print(f"Low-quality threshold: Phred {plan.quality_threshold}")
    for number, step in enumerate(plan.steps, start=1):
        print(f"  {number}. {step}")


def write_report(record: RunRecord) -> Path:
    report_path = Path(record.run_directory) / "report.md"
    result = record.result
    position_rows = "\n".join(
        f"| {measurement['position']} | {measurement['bases_observed']} | "
        f"{measurement['mean_quality']} |"
        for measurement in result["quality_by_position"]
    )
    recovery_section = ""
    if record.retry_count:
        recovery_section = (
            "## Recovery\n\n"
            f"- **Retries approved:** {record.retry_count}\n"
            f"- **Initial failure:** {record.failure_summary}\n"
            "- **Recovery action:** The same approved analysis was run again without "
            "changing inputs, parameters, or resources.\n\n"
        )
    explanation_section = format_explanation_section(record)
    requested_resources = record.execution["requested_resources"]
    resource_summary = (
        f"{requested_resources['cpus']} CPU, "
        f"{requested_resources['memory_mb']} MB memory, "
        f"{requested_resources['wall_time_seconds']} seconds wall time"
        if requested_resources
        else "not_requested"
    )
    report = (
        "# FASTQ Quality-Control Report\n\n"
        f"**Run:** {record.run_id}  \n"
        f"**Status:** {record.status}\n\n"
        "## Execution\n\n"
        f"- **Job status:** {record.job_status}\n"
        f"- **Runner:** {record.execution['runner']}\n"
        f"- **Executor:** {record.execution['executor']}\n"
        f"- **Requested resources:** {resource_summary}\n"
        f"- **Cost:** {record.execution['cost']}\n"
        f"- **Queue job:** {record.execution['queue_job_id'] or 'not_applicable'}\n"
        f"- **Version:** {record.execution['version']}\n"
        f"- **Exit code:** {record.execution['exit_code']}\n"
        f"- **Duration:** {record.execution['duration_seconds']} seconds\n"
        f"- **Attempts:** {len(record.execution_attempts)}\n\n"
        f"{recovery_section}"
        "## Summary measurements\n\n"
        f"- **Reads:** {result['read_count']}\n"
        f"- **Total bases:** {result['total_bases']}\n"
        f"- **Mean base quality:** {result['mean_base_quality']}\n"
        f"- **Low-quality reads:** {result['low_quality_reads']} "
        f"({result['low_quality_percent']}%) at Phred {result['quality_threshold']}\n"
        f"- **GC bases:** {result['gc_percent']}%\n"
        f"- **Unknown (N) bases:** {result['n_bases']} ({result['n_percent']}%)\n\n"
        "## Read lengths\n\n"
        f"- **Minimum:** {result['shortest_read']} bases\n"
        f"- **Maximum:** {result['longest_read']} bases\n"
        f"- **Mean:** {result['mean_read_length']} bases\n"
        f"- **Median (typical):** {result['median_read_length']} bases\n"
        f"- **Variation:** {result['read_length_variation_percent']}% of the median\n\n"
        f"> {result['read_length_warning']}\n\n"
        "## Quality by base position\n\n"
        "| Position | Bases observed | Mean Phred quality |\n"
        "|---:|---:|---:|\n"
        f"{position_rows}\n\n"
        "## Trimming guidance\n\n"
        f"{result['trimming_recommendation']}\n\n"
        "## Agent recommendation\n\n"
        f"{record.recommendation}\n\n"
        f"{explanation_section}"
        "> This learning report is not a clinical interpretation. A human must review it.\n"
    )
    report_path.write_text(report, encoding="utf-8")
    return report_path


def format_explanation_section(record: RunRecord) -> str:
    if not record.explanation_provider:
        return ""

    parts = ["## Explanation layer\n"]
    for title, explanation in (
        ("Plan explanation", record.plan_explanation),
        ("Result explanation", record.result_explanation),
    ):
        if not explanation:
            continue
        evidence_lines = "\n".join(
            f"- **{key.replace('_', ' ').title()}:** {value}"
            for key, value in explanation["evidence"].items()
        )
        parts.append(
            f"### {title}\n\n"
            f"> {explanation['label']}\n\n"
            f"{explanation['summary']}\n\n"
            f"Evidence supplied to the explanation:\n\n{evidence_lines}\n"
        )
    if record.explanation_errors:
        error_lines = "\n".join(f"- {error}" for error in record.explanation_errors)
        parts.append(f"### Rejected explanation output\n\n{error_lines}\n")
    return "\n".join(parts) + "\n"


def add_optional_explanation(
    record: RunRecord,
    provider: ExplanationProvider,
    kind: str,
    run_directory: Path,
) -> None:
    """Add validated explanation text without allowing it to control workflow state."""
    try:
        if kind == "plan":
            explanation = explain_plan_safely(
                provider,
                record.plan,
                record.validation,
            )
            record.plan_explanation = explanation.to_dict()
        elif kind == "result":
            explanation = explain_result_safely(provider, record.result)
            record.result_explanation = explanation.to_dict()
        else:
            raise ValueError(f"Unknown explanation kind: {kind}")
    except Exception as error:
        safe_error = f"{kind.title()} explanation unavailable ({type(error).__name__})"
        record.explanation_errors.append(safe_error)
        save_record(record)
        add_audit_event(
            run_directory,
            "explanation_rejected",
            {
                "kind": kind,
                "provider": provider.name,
                "error_type": type(error).__name__,
            },
        )
        return

    save_record(record)
    add_audit_event(
        run_directory,
        "explanation_created",
        {
            "kind": kind,
            "provider": provider.name,
            "evidence_keys": list(explanation.evidence),
        },
    )
    print(f"\n{kind.title()} explanation ({provider.name})")
    print(explanation.summary)


def run_attempt(
    record: RunRecord,
    runner: Runner,
    input_file: Path,
    quality_threshold: float,
    run_directory: Path,
) -> bool:
    attempt = record.retry_count + 1
    transition_job(record, run_directory, "queued", attempt)
    transition_job(record, run_directory, "running", attempt)
    add_audit_event(
        run_directory,
        "analysis_started",
        {
            "runner": runner.name,
            "executor": record.plan["executor"],
            "requested_resources": record.plan["requested_resources"],
            "cost": record.plan["cost"],
            "attempt": attempt,
        },
    )

    outcome = runner.run(input_file, quality_threshold, run_directory)
    execution = {"attempt": attempt, **outcome.execution_dict()}
    record.execution = execution
    record.execution_attempts.append(execution)

    if outcome.succeeded:
        record.result = outcome.result
        transition_job(
            record,
            run_directory,
            "completed",
            attempt,
            {"exit_code": outcome.exit_code},
        )
        return True

    record.failure_summary = explain_failure(outcome)
    transition_job(
        record,
        run_directory,
        "failed",
        attempt,
        {"exit_code": outcome.exit_code, "summary": record.failure_summary},
    )
    add_audit_event(
        run_directory,
        "analysis_failed",
        {
            "attempt": attempt,
            "summary": record.failure_summary,
            "execution": record.execution,
        },
    )
    return False


def finish_failed_run(record: RunRecord, run_directory: Path, reason: str) -> RunRecord:
    record.status = "analysis_failed"
    record.recommendation = f"Analysis failed: {record.failure_summary} {reason}".strip()
    save_record(record)
    add_audit_event(
        run_directory,
        "run_failed",
        {
            "reason": reason,
            "retry_count": record.retry_count,
            "summary": record.failure_summary,
        },
    )
    print(f"\n{record.recommendation}")
    write_run_manifest(record, run_directory)
    return record


def run_workflow(
    input_file: Path,
    auto_approve: bool = False,
    runner: Runner | None = None,
    explanation_provider: ExplanationProvider | None = None,
    quality_threshold: float = 20.0,
    invocation: list[str] | None = None,
    provenance_context: dict | None = None,
) -> RunRecord:
    project_directory = Path(__file__).resolve().parent.parent
    input_file = input_file.expanduser().resolve()
    selected_runner = runner or PythonRunner()
    run_id, run_directory = create_run_directory(project_directory)

    executor = getattr(selected_runner, "executor", "direct")
    resource_request = getattr(selected_runner, "resource_request", None)
    requested_resources = (
        resource_request.to_dict() if resource_request is not None else {}
    )
    cost = getattr(selected_runner, "cost", "not_applicable")

    plan = PipelinePlan(
        input_file=str(input_file),
        runner=selected_runner.name,
        executor=executor,
        requested_resources=requested_resources,
        cost=cost,
        quality_threshold=quality_threshold,
    )
    record = RunRecord(
        run_id=run_id,
        run_directory=str(run_directory),
        plan=plan.to_dict(),
        invocation=invocation or [],
        provenance={"context": provenance_context or {}},
    )
    save_record(record)
    add_audit_event(
        run_directory,
        "run_created",
        {
            "input_file": str(input_file),
            "runner": selected_runner.name,
            "executor": executor,
        },
    )
    if resource_request is not None:
        add_audit_event(
            run_directory,
            "resource_request_recorded",
            {
                "requested_resources": requested_resources,
                "cost": cost,
            },
        )
        violations = resource_request.hard_limit_violations()
        if violations:
            record.status = "resource_request_rejected"
            record.recommendation = "; ".join(violations)
            save_record(record)
            add_audit_event(
                run_directory,
                "resource_request_rejected",
                {
                    "requested_resources": requested_resources,
                    "violations": violations,
                },
            )
            print(f"Resource request rejected: {record.recommendation}")
            write_run_manifest(record, run_directory)
            return record

    try:
        record.validation = validate_fastq(input_file)
    except ValueError as error:
        record.status = "validation_failed"
        record.recommendation = str(error)
        save_record(record)
        add_audit_event(run_directory, "validation_failed", {"error": str(error)})
        print(f"Validation failed: {error}")
        write_run_manifest(record, run_directory)
        return record

    record.status = "awaiting_run_approval"
    save_record(record)
    add_audit_event(run_directory, "input_validated", record.validation)
    print_plan(plan)

    approval_mode = "automatic_demo" if auto_approve else "human"
    if getattr(selected_runner, "requires_resource_increase_approval", False):
        record.status = "awaiting_resource_approval"
        save_record(record)
        add_audit_event(
            run_directory,
            "resource_increase_requested",
            {
                "requested_resources": requested_resources,
                "baseline": {
                    "cpus": DEFAULT_CPUS,
                    "memory_mb": DEFAULT_MEMORY_MB,
                    "wall_time_seconds": DEFAULT_WALL_TIME_SECONDS,
                },
            },
        )
        resource_approved = ask_for_approval(
            "Approve this increase above the local queue defaults?",
            auto_approve,
        )
        add_audit_event(
            run_directory,
            "resource_increase_approved"
            if resource_approved
            else "resource_increase_rejected",
            {
                "approved": resource_approved,
                "mode": approval_mode,
                "requested_resources": requested_resources,
            },
        )
        if not resource_approved:
            record.status = "resource_increase_rejected"
            record.recommendation = (
                "The increased local resource request was not approved."
            )
            save_record(record)
            write_run_manifest(record, run_directory)
            return record

        record.status = "awaiting_run_approval"
        save_record(record)

    if not ask_for_approval("Approve this analysis plan?", auto_approve):
        record.status = "run_rejected"
        save_record(record)
        add_audit_event(run_directory, "run_rejected", {"approved": False})
        write_run_manifest(record, run_directory)
        return record

    record.status = "running"
    save_record(record)
    add_audit_event(
        run_directory,
        "run_approved",
        {"approved": True, "mode": approval_mode},
    )
    if explanation_provider is not None:
        record.explanation_provider = explanation_provider.name
        add_optional_explanation(
            record,
            explanation_provider,
            "plan",
            run_directory,
        )

    succeeded = run_attempt(
        record,
        selected_runner,
        input_file,
        plan.quality_threshold,
        run_directory,
    )

    if not succeeded:
        if record.retry_count >= MAX_RETRIES:
            return finish_failed_run(record, run_directory, "The retry limit was reached.")

        retry_action = propose_retry()
        record.status = "awaiting_retry_approval"
        record.retry_proposal = {
            "action": retry_action,
            "requested_after_attempt": record.retry_count + 1,
        }
        transition_job(
            record,
            run_directory,
            "awaiting_retry_approval",
            record.retry_count + 1,
            {"proposal": retry_action},
        )
        add_audit_event(
            run_directory,
            "retry_proposed",
            record.retry_proposal,
        )

        print(f"\n{record.failure_summary}")
        print(f"Proposed recovery: {retry_action}")
        retry_approved = ask_for_approval(
            "Approve this one unchanged retry?",
            auto_approve,
        )
        add_audit_event(
            run_directory,
            "retry_approved" if retry_approved else "retry_rejected",
            {
                "approved": retry_approved,
                "mode": approval_mode,
                "attempt": record.retry_count + 1,
                "proposal": retry_action,
            },
        )

        if not retry_approved:
            transition_job(
                record,
                run_directory,
                "failed",
                record.retry_count + 1,
                {"reason": "retry_rejected"},
            )
            return finish_failed_run(
                record,
                run_directory,
                "The proposed retry was not approved.",
            )

        record.retry_count += 1
        record.status = "running"
        save_record(record)
        succeeded = run_attempt(
            record,
            selected_runner,
            input_file,
            plan.quality_threshold,
            run_directory,
        )
        if not succeeded:
            return finish_failed_run(
                record,
                run_directory,
                "The single approved retry also failed; no further retry was attempted.",
            )

    record.recommendation = make_recommendation(record.result)
    if explanation_provider is not None:
        add_optional_explanation(
            record,
            explanation_provider,
            "result",
            run_directory,
        )
    record.status = "awaiting_human_review"
    report_path = write_report(record)
    save_record(record)
    add_audit_event(
        run_directory,
        "analysis_completed",
        {"execution": record.execution, "result": record.result},
    )

    print("\nAnalysis complete")
    print(record.recommendation)
    print(f"Report: {report_path}")

    if ask_for_approval("Have you reviewed and accepted this report?", auto_approve):
        record.status = "accepted_for_demo" if auto_approve else "accepted_by_human"
        add_audit_event(
            run_directory,
            "report_accepted",
            {"approved": True, "mode": approval_mode},
        )
    else:
        record.status = "needs_human_review"
        add_audit_event(run_directory, "report_not_accepted", {"approved": False})

    write_report(record)
    save_record(record)
    write_run_manifest(record, run_directory)
    return record
