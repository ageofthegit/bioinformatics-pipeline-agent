import time
import unittest

from bioagent.dashboard_server import DashboardService, dataset_catalog


class DashboardTests(unittest.TestCase):
    def test_catalog_contains_only_known_local_inputs(self) -> None:
        catalog = {item["accession"]: item for item in dataset_catalog()}

        self.assertIn("sample", catalog)
        self.assertIn("ERR1229325", catalog)
        self.assertTrue(all(item["path"].startswith("data/") for item in catalog.values()))

    def test_dashboard_rejects_arbitrary_input_and_runner(self) -> None:
        service = DashboardService()

        with self.assertRaisesRegex(ValueError, "approved catalog"):
            service.start_run({"accession": "../../private"})
        with self.assertRaisesRegex(ValueError, "Unsupported runner"):
            service.start_run({"accession": "sample", "runner": "shell"})

    def test_dashboard_cannot_execute_after_plan_rejection(self) -> None:
        service = DashboardService()
        session_id = service.start_run(
            {
                "accession": "sample",
                "runner": "python",
                "executor": "direct",
                "explanation": "none",
            }
        )
        session = service.get_run(session_id)
        deadline = time.monotonic() + 5
        while session.snapshot()["awaiting"] != "plan":
            if time.monotonic() > deadline:
                self.fail("Dashboard workflow did not reach plan approval")
            time.sleep(0.01)

        session.decide(False)
        session.process.wait(timeout=5)
        if session.reader_thread is not None:
            session.reader_thread.join(timeout=2)
        snapshot = session.snapshot()
        if session.process.stdin is not None:
            session.process.stdin.close()
        if session.process.stdout is not None:
            session.process.stdout.close()

        self.assertEqual(snapshot["exit_code"], 0)
        self.assertIn("Final status: run_rejected", snapshot["output"])
        self.assertNotIn("Analysis complete", snapshot["output"])


if __name__ == "__main__":
    unittest.main()
