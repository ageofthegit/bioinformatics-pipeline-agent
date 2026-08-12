"""Run both local backends and require exactly equivalent QC measurements."""

import argparse
import tempfile
from pathlib import Path

from bioagent.runners.nextflow_runner import NextflowRunner
from bioagent.runners.python_runner import PythonRunner


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Python and Nextflow QC results for one FASTQ file."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        default=SAMPLE_FASTQ,
        help="FASTQ input; defaults to data/sample.fastq.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = args.input_file.resolve()
    with tempfile.TemporaryDirectory() as temporary_directory:
        run_directory = Path(temporary_directory)
        python_outcome = PythonRunner().run(input_file, 20, run_directory)
        nextflow_outcome = NextflowRunner().run(input_file, 20, run_directory)

    if not python_outcome.succeeded:
        raise SystemExit(f"Python reference run failed: {python_outcome.stderr}")
    if not nextflow_outcome.succeeded:
        failure_detail = nextflow_outcome.stderr or nextflow_outcome.stdout
        raise SystemExit(f"Nextflow run failed: {failure_detail}")
    if python_outcome.result != nextflow_outcome.result:
        raise SystemExit("Python and Nextflow QC measurements differ")

    print(f"Nextflow integration passed ({nextflow_outcome.version})")
    print(f"Python and Nextflow produced identical QC measurements for {input_file}.")


if __name__ == "__main__":
    main()
