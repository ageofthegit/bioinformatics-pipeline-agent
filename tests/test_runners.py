import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bioagent.runners.nextflow_runner import NextflowRunner
from bioagent.runners.python_runner import PythonRunner
from bioagent.tools.qc import analyse_fastq


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


class RunnerTests(unittest.TestCase):
    def test_python_runner_matches_reference_qc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            outcome = PythonRunner().run(
                SAMPLE_FASTQ,
                quality_threshold=20,
                run_directory=Path(temporary_directory),
            )

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.exit_code, 0)
        self.assertEqual(outcome.result, analyse_fastq(SAMPLE_FASTQ, 20))
        self.assertEqual(outcome.runner, "python")

    def test_qc_json_command_uses_existing_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "qc.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bioagent.qc_command",
                    "--input",
                    str(SAMPLE_FASTQ),
                    "--output",
                    str(output_path),
                    "--quality-threshold",
                    "20",
                ],
                cwd=PROJECT_DIRECTORY,
                capture_output=True,
                text=True,
                check=False,
            )

            result = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(result, analyse_fastq(SAMPLE_FASTQ, 20))

    def test_missing_nextflow_executable_is_a_failed_outcome(self) -> None:
        runner = NextflowRunner(executable="/missing/nextflow")
        with tempfile.TemporaryDirectory() as temporary_directory:
            outcome = runner.run(
                SAMPLE_FASTQ,
                quality_threshold=20,
                run_directory=Path(temporary_directory),
            )

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.exit_code, 127)
        self.assertEqual(outcome.version, "unavailable")
        self.assertIn("No such file", outcome.stderr)


if __name__ == "__main__":
    unittest.main()
