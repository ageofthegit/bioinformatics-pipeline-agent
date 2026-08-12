"""Human-operated bridge from an MCP approval request to the existing CLI workflow."""

import argparse
import sys
from pathlib import Path

from bioagent.mcp_tools import McpToolService
from bioagent.runners import create_runner
from bioagent.workflow import run_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review and handle one MCP pipeline approval request."
    )
    parser.add_argument("request_id", help="Pending request-... identifier")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = McpToolService()
    request = service.load_request(args.request_id)
    if request["status"] != "awaiting_human_approval":
        raise SystemExit(f"Request is not awaiting approval: {request['status']}")

    plan = request["plan"]
    record = run_workflow(
        Path(plan["input_file"]),
        runner=create_runner(plan["runner"]),
        quality_threshold=plan.get("quality_threshold", 20.0),
        invocation=[sys.executable, *sys.argv],
    )
    service.resolve_request(args.request_id, record)
    print(f"\nRequest status: resolved")
    print(f"Linked run: {record.run_id} ({record.status})")


if __name__ == "__main__":
    main()
