"""Inspect the real MCP server in memory without opening a port or desktop app."""

import asyncio

from mcp import Client

from bioagent.mcp_server import mcp


EXPECTED_TOOLS = [
    "validate_fastq",
    "propose_qc_plan",
    "request_pipeline_run",
    "get_run_status",
    "summarise_qc_result",
]


async def check_server() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        listed = await client.list_tools()
        tool_names = [tool.name for tool in listed.tools]
        if tool_names != EXPECTED_TOOLS:
            raise SystemExit(f"Unexpected MCP tools: {tool_names}")

        validation = await client.call_tool(
            "validate_fastq", {"input_file": "data/sample.fastq"}
        )
        if validation.is_error or validation.structured_content["read_count"] != 4:
            raise SystemExit("MCP FASTQ validation check failed")

        proposal = await client.call_tool(
            "propose_qc_plan",
            {"input_file": "data/sample.fastq", "runner": "python"},
        )
        if proposal.is_error or proposal.structured_content["execution_started"]:
            raise SystemExit("MCP plan safety check failed")

    print("MCP integration passed (SDK 2.0.0)")
    print("Five tools discovered; validation and non-executing plan checks passed.")


if __name__ == "__main__":
    asyncio.run(check_server())
