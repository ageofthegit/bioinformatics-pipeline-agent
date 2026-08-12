import unittest

from bioagent.monitoring import explain_failure, propose_retry
from bioagent.runners.base import RunnerOutcome


class MonitoringTests(unittest.TestCase):
    def test_missing_runner_has_plain_language_summary(self) -> None:
        outcome = RunnerOutcome(
            runner="nextflow",
            command=["nextflow"],
            exit_code=127,
            duration_seconds=0.01,
            version="unavailable",
            stderr="No such file or directory",
        )

        summary = explain_failure(outcome)

        self.assertIn("could not start", summary)
        self.assertIn("Java runtime", summary)

    def test_missing_qc_output_has_plain_language_summary(self) -> None:
        outcome = RunnerOutcome(
            runner="nextflow",
            command=["nextflow"],
            exit_code=1,
            duration_seconds=0.01,
            version="nextflow 1.0",
            stderr="Nextflow completed without publishing qc.json",
        )

        self.assertIn("did not produce a readable qc.json", explain_failure(outcome))

    def test_retry_proposal_preserves_the_approved_plan(self) -> None:
        proposal = propose_retry()

        self.assertIn("once", proposal)
        self.assertIn("unchanged input", proposal)
        self.assertIn("resources", proposal)

    def test_wall_time_failure_requires_review_before_an_increase(self) -> None:
        outcome = RunnerOutcome(
            runner="python",
            command=["python"],
            exit_code=124,
            duration_seconds=601,
            version="Python test",
            stderr="Local queue wall-time limit was exceeded",
        )

        summary = explain_failure(outcome)

        self.assertIn("approved wall-time limit", summary)
        self.assertIn("requesting any increase", summary)


if __name__ == "__main__":
    unittest.main()
