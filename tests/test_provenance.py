import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bioagent.provenance import sha256_file
from bioagent.reproduce import reproduce_from_manifest
from bioagent.workflow import run_workflow


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


def read_manifest(run_directory: Path) -> dict:
    return json.loads(
        (run_directory / "manifest.json").read_text(encoding="utf-8")
    )


class ProvenanceTests(unittest.TestCase):
    def test_changed_input_changes_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.fastq"
            path.write_text("first", encoding="utf-8")
            first = sha256_file(path)
            path.write_text("second", encoding="utf-8")

            self.assertNotEqual(first, sha256_file(path))

    def test_successful_run_manifest_records_reproduction_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_directory = Path(temporary_directory) / "run-original"
            run_directory.mkdir()
            with patch(
                "bioagent.workflow.create_run_directory",
                return_value=("run-original", run_directory),
            ):
                run_workflow(
                    SAMPLE_FASTQ,
                    auto_approve=True,
                    quality_threshold=25.0,
                    invocation=["python", "run.py", "data/sample.fastq", "--yes"],
                )

            manifest = read_manifest(run_directory)

        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["input"]["sha256"], sha256_file(SAMPLE_FASTQ))
        self.assertEqual(manifest["plan"]["quality_threshold"], 25.0)
        self.assertEqual(manifest["execution"]["runner"], "python")
        self.assertTrue(manifest["code"]["source_tree_sha256"])
        self.assertTrue(manifest["code"]["pipeline"]["sha256"])
        self.assertTrue(manifest["software"]["python"])
        self.assertEqual(manifest["software"]["nextflow"], "not_used")
        self.assertIn("dependencies", manifest["software"])
        self.assertEqual(
            manifest["invocation"]["reproduction_arguments"],
            ["python", "-m", "bioagent.reproduce", "run-original"],
        )
        self.assertNotIn("--yes", manifest["invocation"]["reproduction_command"])
        self.assertEqual(
            [event["event"] for event in manifest["approval_events"]],
            ["run_approved", "report_accepted"],
        )

    def test_rejected_run_also_gets_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_directory = Path(temporary_directory) / "run-rejected"
            run_directory.mkdir()
            with patch(
                "bioagent.workflow.create_run_directory",
                return_value=("run-rejected", run_directory),
            ), patch("bioagent.workflow.ask_for_approval", return_value=False):
                record = run_workflow(SAMPLE_FASTQ)

            manifest = read_manifest(run_directory)

        self.assertEqual(record.status, "run_rejected")
        self.assertEqual(manifest["run"]["status"], "run_rejected")
        self.assertEqual(manifest["approval_events"][0]["event"], "run_rejected")

    def test_reproduction_stops_if_input_checksum_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_file = directory / "input.fastq"
            input_file.write_text("original", encoding="utf-8")
            manifest_path = directory / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "input": {
                            "path": str(input_file),
                            "sha256": sha256_file(input_file),
                        },
                    }
                ),
                encoding="utf-8",
            )
            input_file.write_text("changed", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "checksum does not match"):
                reproduce_from_manifest(manifest_path)

    def test_reproduction_asks_for_approval_and_records_its_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            original_directory = directory / "run-original"
            reproduced_directory = directory / "run-reproduced"
            original_directory.mkdir()
            reproduced_directory.mkdir()
            with patch(
                "bioagent.workflow.create_run_directory",
                return_value=("run-original", original_directory),
            ):
                original = run_workflow(SAMPLE_FASTQ, auto_approve=True)

            with patch(
                "bioagent.workflow.create_run_directory",
                return_value=("run-reproduced", reproduced_directory),
            ), patch(
                "bioagent.workflow.ask_for_approval", side_effect=[True, True]
            ) as approval:
                reproduced = reproduce_from_manifest(
                    original_directory / "manifest.json",
                    invocation=["python", "-m", "bioagent.reproduce", "run-original"],
                )

            manifest = read_manifest(reproduced_directory)

        self.assertEqual(approval.call_count, 2)
        self.assertEqual(reproduced.status, "accepted_by_human")
        self.assertEqual(reproduced.result, original.result)
        self.assertEqual(
            manifest["context"]["reproduced_from_run_id"], "run-original"
        )
        self.assertNotIn("--yes", manifest["invocation"]["reproduction_command"])

    def test_reproduction_cannot_execute_after_plan_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            original_directory = directory / "run-original"
            rejected_directory = directory / "run-reproduction-rejected"
            original_directory.mkdir()
            rejected_directory.mkdir()
            with patch(
                "bioagent.workflow.create_run_directory",
                return_value=("run-original", original_directory),
            ):
                run_workflow(SAMPLE_FASTQ, auto_approve=True)

            with patch(
                "bioagent.workflow.create_run_directory",
                return_value=("run-reproduction-rejected", rejected_directory),
            ), patch("bioagent.workflow.ask_for_approval", return_value=False) as approval:
                record = reproduce_from_manifest(
                    original_directory / "manifest.json"
                )

        approval.assert_called_once()
        self.assertEqual(record.status, "run_rejected")
        self.assertEqual(record.execution_attempts, [])


if __name__ == "__main__":
    unittest.main()
