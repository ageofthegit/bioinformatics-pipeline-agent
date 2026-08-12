import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bioagent.runners.base import RunnerOutcome
from bioagent.runners.local_queue_runner import LocalQueueRunner, ResourceRequest
from bioagent.tools.qc import analyse_fastq
from bioagent.workflow import run_workflow


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SAMPLE_FASTQ = PROJECT_DIRECTORY / "data" / "sample.fastq"


class RecordingRunner:
    name = "python"

    def __init__(self, duration_seconds: float = 0.1) -> None:
        self.call_count = 0
        self.duration_seconds = duration_seconds

    def run(
        self,
        input_file: Path,
        quality_threshold: float,
        run_directory: Path,
    ) -> RunnerOutcome:
        del run_directory
        self.call_count += 1
        return RunnerOutcome(
            runner=self.name,
            command=["python", "qc"],
            exit_code=0,
            duration_seconds=self.duration_seconds,
            version="Python test",
            result=analyse_fastq(input_file, quality_threshold),
        )


def audit_events(run_directory: Path) -> list[str]:
    return [
        json.loads(line)["event"]
        for line in (run_directory / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]


class ResourceRequestTests(unittest.TestCase):
    def test_defaults_are_conservative_and_need_no_extra_approval(self) -> None:
        request = ResourceRequest()

        self.assertEqual(
            request.to_dict(),
            {"cpus": 1, "memory_mb": 1024, "wall_time_seconds": 600},
        )
        self.assertFalse(request.exceeds_defaults())
        self.assertEqual(request.hard_limit_violations(), [])

    def test_increase_and_hard_limit_are_distinct(self) -> None:
        approved_range = ResourceRequest(cpus=2, memory_mb=2048, wall_time_seconds=900)
        above_limit = ResourceRequest(cpus=5, memory_mb=8192, wall_time_seconds=7200)

        self.assertTrue(approved_range.exceeds_defaults())
        self.assertEqual(approved_range.hard_limit_violations(), [])
        self.assertEqual(len(above_limit.hard_limit_violations()), 3)


class LocalQueueRunnerTests(unittest.TestCase):
    def test_wrapper_records_executor_resources_cost_and_job_id(self) -> None:
        backend = RecordingRunner()
        runner = LocalQueueRunner(backend)
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_directory = Path(temporary_directory) / "run-test"
            run_directory.mkdir()

            outcome = runner.run(SAMPLE_FASTQ, 20, run_directory)

        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.executor, "local_queue")
        self.assertEqual(outcome.requested_resources["cpus"], 1)
        self.assertEqual(outcome.cost, "not_applicable")
        self.assertEqual(outcome.queue_job_id, "local-run-test")

    def test_wall_time_overrun_invalidates_the_result(self) -> None:
        runner = LocalQueueRunner(
            RecordingRunner(duration_seconds=2),
            ResourceRequest(wall_time_seconds=1),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            outcome = runner.run(SAMPLE_FASTQ, 20, Path(temporary_directory))

        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.exit_code, 124)
        self.assertIn("wall-time limit", outcome.stderr)


class LocalQueueWorkflowTests(unittest.TestCase):
    def test_default_queue_run_is_audited(self) -> None:
        backend = RecordingRunner()
        runner = LocalQueueRunner(backend)
        with patch("bioagent.workflow.create_run_directory") as create_directory:
            with tempfile.TemporaryDirectory() as temporary_directory:
                run_directory = Path(temporary_directory) / "run-test"
                run_directory.mkdir()
                create_directory.return_value = ("run-test", run_directory)

                record = run_workflow(
                    SAMPLE_FASTQ,
                    auto_approve=True,
                    runner=runner,
                )

                events = audit_events(run_directory)
                report = (run_directory / "report.md").read_text(encoding="utf-8")

        self.assertEqual(record.status, "accepted_for_demo")
        self.assertEqual(record.plan["executor"], "local_queue")
        self.assertEqual(record.execution["queue_job_id"], "local-run-test")
        self.assertIn("resource_request_recorded", events)
        self.assertNotIn("resource_increase_requested", events)
        self.assertIn("**Cost:** not_applicable", report)

    def test_increased_resources_can_be_rejected_before_execution(self) -> None:
        backend = RecordingRunner()
        runner = LocalQueueRunner(backend, ResourceRequest(cpus=2))
        with patch("bioagent.workflow.create_run_directory") as create_directory:
            with tempfile.TemporaryDirectory() as temporary_directory:
                run_directory = Path(temporary_directory) / "run-test"
                run_directory.mkdir()
                create_directory.return_value = ("run-test", run_directory)
                with patch(
                    "bioagent.workflow.ask_for_approval", return_value=False
                ) as approval:
                    record = run_workflow(SAMPLE_FASTQ, runner=runner)

                events = audit_events(run_directory)

        self.assertEqual(record.status, "resource_increase_rejected")
        self.assertEqual(backend.call_count, 0)
        self.assertEqual(approval.call_count, 1)
        self.assertIn("resource_increase_requested", events)
        self.assertIn("resource_increase_rejected", events)

    def test_approved_resource_increase_still_needs_plan_approval(self) -> None:
        backend = RecordingRunner()
        runner = LocalQueueRunner(backend, ResourceRequest(memory_mb=2048))
        with patch("bioagent.workflow.create_run_directory") as create_directory:
            with tempfile.TemporaryDirectory() as temporary_directory:
                run_directory = Path(temporary_directory) / "run-test"
                run_directory.mkdir()
                create_directory.return_value = ("run-test", run_directory)
                with patch(
                    "bioagent.workflow.ask_for_approval",
                    side_effect=[True, False],
                ) as approval:
                    record = run_workflow(SAMPLE_FASTQ, runner=runner)

                events = audit_events(run_directory)

        self.assertEqual(record.status, "run_rejected")
        self.assertEqual(backend.call_count, 0)
        self.assertEqual(approval.call_count, 2)
        self.assertIn("resource_increase_approved", events)
        self.assertIn("run_rejected", events)

    def test_request_above_hard_limit_is_rejected_without_a_prompt(self) -> None:
        backend = RecordingRunner()
        runner = LocalQueueRunner(backend, ResourceRequest(cpus=5))
        with patch("bioagent.workflow.create_run_directory") as create_directory:
            with tempfile.TemporaryDirectory() as temporary_directory:
                run_directory = Path(temporary_directory) / "run-test"
                run_directory.mkdir()
                create_directory.return_value = ("run-test", run_directory)
                with patch("bioagent.workflow.ask_for_approval") as approval:
                    record = run_workflow(SAMPLE_FASTQ, runner=runner)

                events = audit_events(run_directory)

        self.assertEqual(record.status, "resource_request_rejected")
        self.assertEqual(backend.call_count, 0)
        approval.assert_not_called()
        self.assertIn("resource_request_rejected", events)


if __name__ == "__main__":
    unittest.main()
