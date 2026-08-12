"""Cross-check a Phase 8 run against ENA metadata and an independent count."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.download_public_dataset import (
    MANIFEST_PATH,
    PROJECT_DIRECTORY,
    load_manifest,
    manifest_path_for,
    verify_compressed_file,
)


def independently_count_fastq(path: Path) -> tuple[int, int]:
    """Count reads and bases without using the agent's FASTQ or QC functions."""
    line_count = 0
    read_count = 0
    base_count = 0
    with path.open(encoding="utf-8") as handle:
        for line_count, line in enumerate(handle, start=1):
            if line_count % 4 == 2:
                read_count += 1
                base_count += len(line.rstrip("\r\n"))
    if line_count % 4:
        raise ValueError("Independent count found an incomplete four-line record")
    return read_count, base_count


def check_public_run(
    run_directory: Path,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    compressed = manifest["compressed_file"]
    compressed_path = manifest_path.parent / compressed["name"]
    fastq_path = PROJECT_DIRECTORY / manifest["local_fastq"]
    verify_compressed_file(
        compressed_path,
        compressed["bytes"],
        compressed["md5"],
    )

    independent_reads, independent_bases = independently_count_fastq(fastq_path)
    state = json.loads((run_directory / "state.json").read_text(encoding="utf-8"))
    measured = state["result"]

    checks = {
        "ena_read_count_matches_file": (
            independent_reads == manifest["expected_read_count"]
        ),
        "agent_read_count_matches_independent_count": (
            measured["read_count"] == independent_reads
        ),
        "agent_base_count_matches_independent_count": (
            measured["total_bases"] == independent_bases
        ),
    }
    if not all(checks.values()):
        raise ValueError(f"Public dataset cross-check failed: {checks}")

    return {
        "checks": checks,
        "independent_read_count": independent_reads,
        "independent_base_count": independent_bases,
        "ena_portal_base_count": manifest["ena_portal_base_count"],
        "run_status": state["status"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check a saved Phase 8 run against public and independent evidence."
    )
    parser.add_argument("run_directory", type=Path)
    parser.add_argument(
        "--accession",
        default="DRR002057",
        help="Approved ENA accession used by the run. Default: DRR002057",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = check_public_run(
        args.run_directory.resolve(),
        manifest_path_for(args.accession),
    )
    print("Public dataset cross-check passed")
    print(f"Reads: {result['independent_read_count']} (matches ENA and agent)")
    print(f"Bases in generated FASTQ: {result['independent_base_count']} (matches agent)")
    if result["independent_base_count"] != result["ena_portal_base_count"]:
        print(
            "Note: ENA's run-level base_count is "
            f"{result['ena_portal_base_count']}; it does not match the archive-generated "
            "FASTQ and is not presented as a passing comparison."
        )


if __name__ == "__main__":
    main()
