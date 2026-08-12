"""Create a durable, machine-readable receipt for every completed run."""

import hashlib
import json
import platform
import shlex
from datetime import datetime, timezone
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Any

from bioagent.models import RunRecord
from bioagent.state import save_record


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
APPROVAL_EVENTS = {
    "resource_increase_approved",
    "resource_increase_rejected",
    "run_approved",
    "run_rejected",
    "retry_approved",
    "retry_rejected",
    "report_accepted",
    "report_not_accepted",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_files(project_directory: Path) -> list[Path]:
    candidates = [
        project_directory / "run.py",
        project_directory / "nextflow.config",
        *project_directory.glob("requirements*.txt"),
        *project_directory.glob("bioagent/**/*.py"),
        *project_directory.glob("pipelines/**/*"),
        *project_directory.glob("scripts/**/*.py"),
    ]
    return sorted(
        {path.resolve() for path in candidates if path.is_file()},
        key=lambda path: path.relative_to(project_directory.resolve()).as_posix(),
    )


@lru_cache(maxsize=4)
def source_tree_sha256(project_directory_text: str = str(PROJECT_DIRECTORY)) -> str:
    project_directory = Path(project_directory_text).resolve()
    digest = hashlib.sha256()
    for path in _source_files(project_directory):
        relative = path.relative_to(project_directory).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _package_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not_installed"


def _audit_entries(run_directory: Path) -> list[dict[str, Any]]:
    audit_path = run_directory / "audit.jsonl"
    if not audit_path.exists():
        return []
    entries = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _file_identity(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": None,
            "sha256": None,
        }
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_run_manifest(record: RunRecord, run_directory: Path) -> Path:
    """Write the final receipt after the last audit event for this workflow."""
    audit_entries = _audit_entries(run_directory)
    input_file = Path(record.plan.get("input_file", ""))
    pipeline_path = PROJECT_DIRECTORY / "pipelines" / "main.nf"
    now = datetime.now(timezone.utc).isoformat()
    reproduction_arguments = [
        "python",
        "-m",
        "bioagent.reproduce",
        record.run_id,
    ]
    timestamps = {
        "created_at": audit_entries[0]["time"] if audit_entries else now,
        "finished_at": audit_entries[-1]["time"] if audit_entries else now,
    }
    input_identity = _file_identity(input_file)
    runner_version = record.execution.get("version", "not_started")
    context = record.provenance.get("context", {})
    record.provenance = {
        "manifest_schema_version": 1,
        "input_sha256": input_identity["sha256"],
        "source_tree_sha256": source_tree_sha256(),
        "pipeline_sha256": sha256_file(pipeline_path) if pipeline_path.is_file() else None,
        "reproduction_command": shlex.join(reproduction_arguments),
        "context": context,
    }
    save_record(record)

    manifest = {
        "schema_version": 1,
        "run": {
            "run_id": record.run_id,
            "status": record.status,
            "run_directory": record.run_directory,
            "timestamps": timestamps,
        },
        "input": input_identity,
        "code": {
            "source_tree_sha256": record.provenance["source_tree_sha256"],
            "pipeline": {
                "path": str(pipeline_path),
                "sha256": record.provenance["pipeline_sha256"],
            },
        },
        "software": {
            "python": platform.python_version(),
            "runner": record.plan.get("runner", "unknown"),
            "runner_version": runner_version,
            "nextflow": (
                runner_version
                if record.plan.get("runner") == "nextflow"
                else "not_used"
            ),
            "explanation_provider": record.explanation_provider or "none",
            "dependencies": {"mcp": _package_version("mcp")},
        },
        "invocation": {
            "arguments": record.invocation,
            "reproduction_arguments": reproduction_arguments,
            "reproduction_command": record.provenance["reproduction_command"],
        },
        "plan": record.plan,
        "execution": record.execution,
        "execution_attempts": record.execution_attempts,
        "result": record.result,
        "recommendation": record.recommendation,
        "approval_events": [
            entry for entry in audit_entries if entry["event"] in APPROVAL_EVENTS
        ],
        "audit_file": str(run_directory / "audit.jsonl"),
        "context": context,
    }
    manifest_path = run_directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path
