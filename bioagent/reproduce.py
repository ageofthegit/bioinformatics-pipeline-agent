"""Reconstruct an earlier run while preserving all human approval gates."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bioagent.llm import create_explanation_provider
from bioagent.models import RunRecord
from bioagent.provenance import PROJECT_DIRECTORY, sha256_file
from bioagent.runners import LocalQueueRunner, ResourceRequest, create_runner
from bioagent.workflow import run_workflow


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Run manifest not found: {manifest_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Run manifest is not valid JSON: {manifest_path}") from error
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported or missing manifest schema version")
    return manifest


def resolve_manifest(reference: str) -> Path:
    if Path(reference).name == reference and reference.startswith("run-"):
        return PROJECT_DIRECTORY / "runs" / reference / "manifest.json"
    path = Path(reference).expanduser().resolve()
    if path.name != "manifest.json":
        raise ValueError("Provide a run ID or a manifest.json path")
    return path


def reproduce_from_manifest(
    manifest_path: Path,
    invocation: list[str] | None = None,
) -> RunRecord:
    manifest_path = manifest_path.expanduser().resolve()
    manifest = load_manifest(manifest_path)
    input_identity = manifest["input"]
    input_file = Path(input_identity["path"])
    if not input_file.is_file():
        raise ValueError(f"Original input file is unavailable: {input_file}")
    actual_sha256 = sha256_file(input_file)
    if actual_sha256 != input_identity["sha256"]:
        raise ValueError(
            "Input checksum does not match the original run; reproduction stopped."
        )

    plan = manifest["plan"]
    runner = create_runner(plan["runner"])
    if plan.get("executor") == "local_queue":
        resources = plan["requested_resources"]
        runner = LocalQueueRunner(
            runner,
            ResourceRequest(
                cpus=resources["cpus"],
                memory_mb=resources["memory_mb"],
                wall_time_seconds=resources["wall_time_seconds"],
            ),
        )
    explanation_provider = create_explanation_provider(
        manifest.get("software", {}).get("explanation_provider", "none")
    )
    return run_workflow(
        input_file,
        auto_approve=False,
        runner=runner,
        explanation_provider=explanation_provider,
        quality_threshold=plan["quality_threshold"],
        invocation=invocation or [sys.executable, *sys.argv],
        provenance_context={
            "reproduced_from_run_id": manifest["run"]["run_id"],
            "source_manifest_sha256": sha256_file(manifest_path),
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct a run from its manifest and ask for approval again."
    )
    parser.add_argument("run", help="Original run ID or path to manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        record = reproduce_from_manifest(
            resolve_manifest(args.run),
            invocation=[sys.executable, *sys.argv],
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"\nFinal status: {record.status}")
    print(f"Run folder: {record.run_directory}")


if __name__ == "__main__":
    main()
