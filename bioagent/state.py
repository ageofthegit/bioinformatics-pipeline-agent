"""Save workflow state and an append-only audit history."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bioagent.models import RunRecord


def save_record(record: RunRecord) -> None:
    path = Path(record.run_directory) / "state.json"
    path.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")


def add_audit_event(run_directory: Path, event: str, details: dict[str, Any]) -> None:
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": details,
    }
    path = run_directory / "audit.jsonl"
    with path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(entry) + "\n")

