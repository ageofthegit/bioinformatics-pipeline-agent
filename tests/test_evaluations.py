import unittest
from datetime import datetime, timezone

from evaluations.run_evaluations import (
    CASES_DIRECTORY,
    EvaluationResult,
    evaluate_fastq_cases,
    evaluation_exit_code,
    load_json,
    render_report,
)


class EvaluationRunnerTests(unittest.TestCase):
    def test_versioned_fastq_cases_all_pass(self) -> None:
        cases = load_json(CASES_DIRECTORY / "fastq_cases.json")

        results = evaluate_fastq_cases(cases)

        self.assertEqual(len(results), 15)
        self.assertTrue(all(result.passed for result in results))

    def test_exit_code_is_nonzero_when_any_check_fails(self) -> None:
        passing = EvaluationResult("Example", "pass", True, "Expected")
        failing = EvaluationResult("Example", "fail", False, "Mismatch")

        self.assertEqual(evaluation_exit_code([passing]), 0)
        self.assertEqual(evaluation_exit_code([passing, failing]), 1)

    def test_report_displays_failures_and_limitations(self) -> None:
        results = [
            EvaluationResult("Example", "known_failure", False, "Visible failure")
        ]

        report = render_report(
            results,
            datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
        )

        self.assertIn("**Overall result:** FAIL", report)
        self.assertIn("0 passed, 1 failed", report)
        self.assertIn("| Example | known_failure | FAIL | Visible failure |", report)
        self.assertIn("## Subjective explanation quality", report)
        self.assertIn("## Known limitations", report)


if __name__ == "__main__":
    unittest.main()
