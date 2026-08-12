import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bioagent.mcp_tools import McpToolService
from bioagent.tools.qc import analyse_fastq, make_recommendation


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


class McpToolServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.project_directory = Path(self.temporary_directory.name)
        self.data_directory = self.project_directory / "data"
        self.data_directory.mkdir()
        self.sample = self.data_directory / "sample.fastq"
        shutil.copy(SAMPLE_FASTQ, self.sample)
        self.service = McpToolService(self.project_directory)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_validate_fastq_reuses_existing_validation(self) -> None:
        result = self.service.validate_fastq("data/sample.fastq")

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["read_count"], 4)
        self.assertFalse(result["execution_started"])

    def test_mcp_rejects_paths_outside_the_project_data_folder(self) -> None:
        outside = self.project_directory / "outside.fastq"
        shutil.copy(SAMPLE_FASTQ, outside)

        with self.assertRaisesRegex(ValueError, "project data folder"):
            self.service.validate_fastq(str(outside))

    def test_mcp_rejects_unsupported_file_types(self) -> None:
        unsupported = self.data_directory / "sample.txt"
        shutil.copy(SAMPLE_FASTQ, unsupported)

        with self.assertRaisesRegex(ValueError, "Only .fastq and .fq"):
            self.service.validate_fastq(str(unsupported))

    def test_mcp_rejects_missing_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.service.validate_fastq("data/missing.fastq")

    def test_proposal_is_validated_but_not_executed(self) -> None:
        proposal = self.service.propose_qc_plan("data/sample.fastq", "nextflow")

        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["plan"]["runner"], "nextflow")
        self.assertTrue(proposal["approval_required"])
        self.assertFalse(proposal["execution_started"])
        self.assertFalse((self.project_directory / "runs").exists())

    def test_pipeline_request_cannot_bypass_human_approval(self) -> None:
        request = self.service.request_pipeline_run("data/sample.fastq")

        self.assertEqual(request["status"], "awaiting_human_approval")
        self.assertTrue(request["approval_required"])
        self.assertFalse(request["execution_started"])
        self.assertFalse((self.project_directory / "runs").exists())
        request_file = (
            self.project_directory
            / "approval_requests"
            / f"{request['request_id']}.json"
        )
        self.assertTrue(request_file.is_file())
        audit = (
            self.project_directory / "approval_requests" / "audit.jsonl"
        ).read_text(encoding="utf-8")
        self.assertIn("pipeline_run_requested", audit)

    def test_get_status_rejects_unknown_and_unsafe_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown run ID"):
            self.service.get_run_status("run-missing")
        with self.assertRaisesRegex(ValueError, "Invalid"):
            self.service.get_run_status("../../state.json")

    def test_get_status_reads_a_pending_request(self) -> None:
        request = self.service.request_pipeline_run("data/sample.fastq")

        status = self.service.get_run_status(request["request_id"])

        self.assertEqual(status["kind"], "approval_request")
        self.assertEqual(status["status"], "awaiting_human_approval")
        self.assertFalse(status["execution_started"])

    def test_summary_uses_only_saved_qc_measurements(self) -> None:
        result = analyse_fastq(self.sample, 20)
        run_id = "run-test"
        state_directory = self.project_directory / "runs" / run_id
        state_directory.mkdir(parents=True)
        state = {
            "run_id": run_id,
            "status": "awaiting_human_review",
            "job_status": "completed",
            "result": result,
            "recommendation": make_recommendation(result),
        }
        (state_directory / "state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

        summary = self.service.summarise_qc_result(run_id)

        self.assertEqual(summary["read_count"], result["read_count"])
        self.assertEqual(summary["mean_base_quality"], result["mean_base_quality"])
        self.assertTrue(summary["human_review_required"])

    def test_summary_rejects_a_run_without_results(self) -> None:
        run_id = "run-empty"
        state_directory = self.project_directory / "runs" / run_id
        state_directory.mkdir(parents=True)
        (state_directory / "state.json").write_text(
            json.dumps({"run_id": run_id, "status": "analysis_failed"}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "no completed QC result"):
            self.service.summarise_qc_result(run_id)


if __name__ == "__main__":
    unittest.main()
