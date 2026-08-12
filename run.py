"""Command-line entry point for the learning project."""

import argparse
import sys
from pathlib import Path

from bioagent.llm import create_explanation_provider
from bioagent.runners import LocalQueueRunner, ResourceRequest, create_runner
from bioagent.runners.local_queue_runner import (
    DEFAULT_CPUS,
    DEFAULT_MEMORY_MB,
    DEFAULT_WALL_TIME_SECONDS,
)
from bioagent.workflow import run_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a human-approved FASTQ quality-control workflow."
    )
    parser.add_argument("fastq", type=Path, help="Path to a FASTQ file")
    parser.add_argument(
        "--runner",
        choices=("python", "nextflow"),
        default="python",
        help="Execution backend. The default is the reference Python runner.",
    )
    parser.add_argument(
        "--executor",
        choices=("direct", "local-queue"),
        default="direct",
        help="Run directly or through the governed local queue simulation.",
    )
    parser.add_argument("--cpus", type=int, default=DEFAULT_CPUS)
    parser.add_argument("--memory-mb", type=int, default=DEFAULT_MEMORY_MB)
    parser.add_argument(
        "--wall-time-seconds",
        type=int,
        default=DEFAULT_WALL_TIME_SECONDS,
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Automatically approve gates. Use only for tests or demonstrations.",
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=20.0,
        help="Mean-read Phred threshold used by the quality checks.",
    )
    parser.add_argument(
        "--explain-with",
        choices=("none", "offline-demo"),
        default="none",
        help=(
            "Optional explanation layer. offline-demo uses no network or API key."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = create_runner(args.runner)
    resource_request = ResourceRequest(
        cpus=args.cpus,
        memory_mb=args.memory_mb,
        wall_time_seconds=args.wall_time_seconds,
    )
    if args.executor == "local-queue":
        runner = LocalQueueRunner(runner, resource_request)
    elif resource_request != ResourceRequest():
        raise SystemExit("Resource options require --executor local-queue")
    explanation_provider = create_explanation_provider(args.explain_with)
    record = run_workflow(
        args.fastq,
        auto_approve=args.yes,
        runner=runner,
        explanation_provider=explanation_provider,
        quality_threshold=args.quality_threshold,
        invocation=[sys.executable, *sys.argv],
    )
    print(f"\nFinal status: {record.status}")
    print(f"Run folder: {record.run_directory}")


if __name__ == "__main__":
    main()
