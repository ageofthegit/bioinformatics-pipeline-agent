import shutil
import tempfile
import unittest
from pathlib import Path

from bioagent.mcp_tools import McpToolService


try:
    from mcp import Client

    from bioagent.mcp_server import create_mcp_server

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


@unittest.skipUnless(MCP_AVAILABLE, "Install requirements-mcp.txt to test MCP protocol")
class McpServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.project_directory = Path(self.temporary_directory.name)
        data_directory = self.project_directory / "data"
        data_directory.mkdir()
        shutil.copy(SAMPLE_FASTQ, data_directory / "sample.fastq")
        service = McpToolService(self.project_directory)
        self.server = create_mcp_server(service)

    async def asyncTearDown(self) -> None:
        self.temporary_directory.cleanup()

    async def test_server_lists_five_typed_tools(self) -> None:
        async with Client(self.server, raise_exceptions=True) as client:
            listed = await client.list_tools()

        self.assertEqual(
            [tool.name for tool in listed.tools],
            [
                "validate_fastq",
                "propose_qc_plan",
                "request_pipeline_run",
                "get_run_status",
                "summarise_qc_result",
            ],
        )
        request_tool = next(
            tool for tool in listed.tools if tool.name == "request_pipeline_run"
        )
        self.assertFalse(request_tool.annotations.read_only_hint)
        self.assertEqual(
            request_tool.input_schema["properties"]["runner"]["enum"],
            ["python", "nextflow"],
        )

    async def test_protocol_call_validates_fastq(self) -> None:
        async with Client(self.server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "validate_fastq", {"input_file": "data/sample.fastq"}
            )

        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["read_count"], 4)
        self.assertFalse(result.structured_content["execution_started"])

    async def test_protocol_request_creates_only_pending_approval(self) -> None:
        async with Client(self.server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "request_pipeline_run",
                {"input_file": "data/sample.fastq", "runner": "python"},
            )

        self.assertFalse(result.is_error)
        self.assertEqual(
            result.structured_content["status"], "awaiting_human_approval"
        )
        self.assertFalse(result.structured_content["execution_started"])
        self.assertFalse((self.project_directory / "runs").exists())


if __name__ == "__main__":
    unittest.main()
