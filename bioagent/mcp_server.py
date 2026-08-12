"""Local MCP server exposing the agent's controlled tools over stdio."""

from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from bioagent.mcp_tools import McpToolService


class ValidationData(BaseModel):
    status: Literal["valid"]
    read_count: int
    file_size_bytes: int


class FastqValidationOutput(ValidationData):
    input_file: str
    execution_started: Literal[False]


class PlanData(BaseModel):
    input_file: str
    runner: Literal["python", "nextflow"]
    analysis: str
    quality_threshold: float
    steps: list[str]


class PlanProposalOutput(BaseModel):
    status: Literal["proposed"]
    plan: PlanData
    validation: ValidationData
    approval_required: Literal[True]
    execution_started: Literal[False]


class RunRequestOutput(BaseModel):
    request_id: str
    status: Literal["awaiting_human_approval"]
    created_at: str
    plan: PlanData
    validation: ValidationData
    approval_required: Literal[True]
    execution_started: Literal[False]
    next_step: str


class ApprovalRequestStatusOutput(BaseModel):
    kind: Literal["approval_request"]
    request_id: str
    status: str
    approval_required: bool
    execution_started: bool
    linked_run_id: str | None
    linked_run_status: str | None


class WorkflowRunStatusOutput(BaseModel):
    kind: Literal["workflow_run"]
    run_id: str
    status: str
    job_status: str
    attempts: int
    retry_count: int
    failure_summary: str


class QcSummaryOutput(BaseModel):
    run_id: str
    status: str
    read_count: int
    mean_base_quality: float
    low_quality_percent: float
    gc_percent: float
    n_percent: float
    shortest_read: int
    longest_read: int
    trimming_guidance: str
    recommendation: str
    human_review_required: bool


def create_mcp_server(service: McpToolService | None = None) -> MCPServer:
    tool_service = service or McpToolService()
    server = MCPServer(
        "Bioinformatics Pipeline Agent",
        version="0.5.0",
        instructions=(
            "Validate and inspect project-local FASTQ data. Pipeline run requests "
            "always require separate human approval and never execute through MCP."
        ),
    )

    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

    @server.tool(annotations=read_only)
    def validate_fastq(
        input_file: Annotated[
            str,
            Field(description="FASTQ path inside the project's data folder."),
        ],
    ) -> FastqValidationOutput:
        """Validate FASTQ structure without starting an analysis."""
        return FastqValidationOutput.model_validate(
            tool_service.validate_fastq(input_file)
        )

    @server.tool(annotations=read_only)
    def propose_qc_plan(
        input_file: Annotated[
            str,
            Field(description="FASTQ path inside the project's data folder."),
        ],
        runner: Literal["python", "nextflow"] = "python",
    ) -> PlanProposalOutput:
        """Propose the deterministic QC plan; this never executes it."""
        return PlanProposalOutput.model_validate(
            tool_service.propose_qc_plan(input_file, runner)
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    def request_pipeline_run(
        input_file: Annotated[
            str,
            Field(description="FASTQ path inside the project's data folder."),
        ],
        runner: Literal["python", "nextflow"] = "python",
    ) -> RunRequestOutput:
        """Create an approval request without running or approving the pipeline."""
        return RunRequestOutput.model_validate(
            tool_service.request_pipeline_run(input_file, runner)
        )

    @server.tool(annotations=read_only)
    def get_run_status(
        identifier: Annotated[
            str,
            Field(description="A request-... approval ID or run-... workflow ID."),
        ],
    ) -> ApprovalRequestStatusOutput | WorkflowRunStatusOutput:
        """Get saved status for one approval request or workflow run."""
        status = tool_service.get_run_status(identifier)
        if status["kind"] == "approval_request":
            return ApprovalRequestStatusOutput.model_validate(status)
        return WorkflowRunStatusOutput.model_validate(status)

    @server.tool(annotations=read_only)
    def summarise_qc_result(
        run_id: Annotated[
            str,
            Field(description="A run-... workflow ID with saved QC results."),
        ],
    ) -> QcSummaryOutput:
        """Summarise saved deterministic QC measurements for human review."""
        return QcSummaryOutput.model_validate(
            tool_service.summarise_qc_result(run_id)
        )

    return server


mcp = create_mcp_server()


if __name__ == "__main__":
    mcp.run()
