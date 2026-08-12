"""Write the existing Python QC measurements to JSON for pipeline runners."""

import argparse
import json
from pathlib import Path

from bioagent.tools.fastq import validate_fastq
from bioagent.tools.qc import analyse_fastq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write FASTQ QC measurements as JSON.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quality-threshold", required=True, type=float)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_fastq(args.input)
    result = analyse_fastq(args.input, args.quality_threshold)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
