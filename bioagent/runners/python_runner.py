"""Reference backend that runs the existing Python QC function directly."""

import platform
from pathlib import Path
from time import perf_counter

from bioagent.runners.base import RunnerOutcome
from bioagent.tools.qc import analyse_fastq


class PythonRunner:
    name = "python"

    def run(
        self,
        input_file: Path,
        quality_threshold: float,
        run_directory: Path,
    ) -> RunnerOutcome:
        del run_directory
        command = [
            "python",
            "bioagent.tools.qc.analyse_fastq",
            str(input_file),
            str(quality_threshold),
        ]
        started = perf_counter()

        try:
            result = analyse_fastq(input_file, quality_threshold)
        except Exception as error:
            return RunnerOutcome(
                runner=self.name,
                command=command,
                exit_code=1,
                duration_seconds=round(perf_counter() - started, 6),
                version=f"Python {platform.python_version()}",
                stderr=str(error),
            )

        return RunnerOutcome(
            runner=self.name,
            command=command,
            exit_code=0,
            duration_seconds=round(perf_counter() - started, 6),
            version=f"Python {platform.python_version()}",
            result=result,
        )
