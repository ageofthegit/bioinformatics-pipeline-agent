"""Local browser bridge for the existing interactive workflow.

The browser starts the normal CLI and may only answer an approval prompt that
the CLI has actually printed. It never receives an automatic-approval option.
"""

import argparse
import json
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.download_public_dataset import (
    available_accessions,
    load_manifest,
    manifest_path_for,
)


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DASHBOARD_DIRECTORY = PROJECT_DIRECTORY / "dashboard"
RUN_DIRECTORY_PATTERN = re.compile(r"Run folder: (.+run-[0-9-]+)")
REPORT_PATTERN = re.compile(r"Report: (.+/report\.md)")
PROMPTS = {
    "Approve this increase above the local queue defaults? [y/N]: ": "resources",
    "Approve this analysis plan? [y/N]: ": "plan",
    "Approve this one unchanged retry? [y/N]: ": "retry",
    "Have you reviewed and accepted this report? [y/N]: ": "report",
}
PHASES = [
    (1, "Basic agent", "Plan, approve, analyse, report"),
    (2, "Data checks", "Measure read quality and flag problems"),
    (3, "Nextflow", "Run a repeatable scientific pipeline"),
    (4, "Recovery", "Track failures and ask before retrying"),
    (5, "MCP", "Expose small, controlled AI tools"),
    (6, "Explanations", "Explain facts without controlling decisions"),
    (7, "Evaluation", "Test accuracy and safety repeatedly"),
    (8, "Public data", "Use verified, non-human ENA samples"),
    (9, "Compute queue", "Govern resources for larger jobs"),
    (10, "Provenance", "Record data, code, settings and approvals"),
    (11, "Owner review", "Test three datasets and record confusion"),
    (12, "Portfolio", "Visual interface, documentation and sharing"),
]


def dataset_catalog() -> list[dict[str, Any]]:
    sample_path = PROJECT_DIRECTORY / "data" / "sample.fastq"
    datasets: list[dict[str, Any]] = [
        {
            "accession": "sample",
            "name": "Synthetic learning sample",
            "organism": "Synthetic DNA",
            "reads": 4,
            "size_bytes": sample_path.stat().st_size,
            "path": "data/sample.fastq",
            "kind": "synthetic",
            "ready": True,
        }
    ]
    for accession in available_accessions():
        manifest = load_manifest(manifest_path_for(accession))
        fastq = PROJECT_DIRECTORY / manifest["local_fastq"]
        datasets.append(
            {
                "accession": accession,
                "name": manifest["sample_title"],
                "organism": manifest["scientific_name"],
                "reads": manifest["expected_read_count"],
                "size_bytes": fastq.stat().st_size if fastq.exists() else None,
                "path": manifest["local_fastq"],
                "kind": manifest["data_classification"],
                "ready": fastq.is_file(),
            }
        )
    return datasets


def recent_runs(limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for state_path in sorted(
        (PROJECT_DIRECTORY / "runs").glob("run-*/state.json"), reverse=True
    ):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "run_id": state.get("run_id"),
                "status": state.get("status"),
                "input": Path(
                    state.get("plan", {}).get("input_file", "unknown")
                ).name,
                "runner": state.get("plan", {}).get("runner", "unknown"),
            }
        )
        if len(rows) >= limit:
            break
    return rows


@dataclass
class DashboardRun:
    process: subprocess.Popen[str]
    command: list[str]
    output: str = ""
    awaiting: str | None = None
    run_directory: str = ""
    report_path: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)
    reader_thread: threading.Thread | None = None

    def start_reader(self) -> None:
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

    def _read_output(self) -> None:
        assert self.process.stdout is not None
        while True:
            character = self.process.stdout.read(1)
            if not character:
                break
            with self.lock:
                self.output += character
                for prompt, gate in PROMPTS.items():
                    if self.output.endswith(prompt):
                        self.awaiting = gate
                run_match = RUN_DIRECTORY_PATTERN.search(self.output)
                if run_match:
                    self.run_directory = run_match.group(1).strip()
                report_match = REPORT_PATTERN.search(self.output)
                if report_match:
                    self.report_path = report_match.group(1).strip()

    def decide(self, approve: bool) -> None:
        with self.lock:
            if not self.awaiting:
                raise ValueError(
                    "The workflow is not waiting for an approval decision"
                )
            self.awaiting = None
            input_stream = self.process.stdin
        if input_stream is None:
            raise ValueError("The workflow input stream is unavailable")
        input_stream.write("y\n" if approve else "n\n")
        input_stream.flush()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            output = self.output
            awaiting = self.awaiting
            run_directory = self.run_directory
            report_path = self.report_path
        exit_code = self.process.poll()
        report = ""
        if report_path:
            path = Path(report_path)
            runs_root = (PROJECT_DIRECTORY / "runs").resolve()
            try:
                if path.resolve().is_relative_to(runs_root) and path.is_file():
                    report = path.read_text(encoding="utf-8")
            except OSError:
                pass
        return {
            "output": output,
            "awaiting": awaiting,
            "running": exit_code is None,
            "exit_code": exit_code,
            "run_directory": run_directory,
            "report": report,
        }


class DashboardService:
    def __init__(self) -> None:
        self.runs: dict[str, DashboardRun] = {}
        self.lock = threading.Lock()

    def bootstrap(self) -> dict[str, Any]:
        return {
            "datasets": dataset_catalog(),
            "phases": [
                {"number": number, "title": title, "summary": summary}
                for number, title, summary in PHASES
            ],
            "recent_runs": recent_runs(),
        }

    def start_run(self, request: dict[str, Any]) -> str:
        catalog = {item["accession"]: item for item in dataset_catalog()}
        accession = str(request.get("accession", ""))
        if accession not in catalog or not catalog[accession].get("ready", True):
            raise ValueError(
                "Choose a downloaded dataset from the approved catalog"
            )
        runner = str(request.get("runner", "python"))
        executor = str(request.get("executor", "direct"))
        explanation = str(request.get("explanation", "offline-demo"))
        if runner not in {"python", "nextflow"}:
            raise ValueError("Unsupported runner")
        if executor not in {"direct", "local-queue"}:
            raise ValueError("Unsupported executor")
        if explanation not in {"none", "offline-demo"}:
            raise ValueError("Unsupported explanation provider")

        command = [
            sys.executable,
            "-u",
            "run.py",
            catalog[accession]["path"],
            "--runner",
            runner,
            "--executor",
            executor,
            "--explain-with",
            explanation,
        ]
        process = subprocess.Popen(
            command,
            cwd=PROJECT_DIRECTORY,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,
        )
        session = DashboardRun(process=process, command=command)
        session_id = uuid.uuid4().hex
        with self.lock:
            self.runs[session_id] = session
        session.start_reader()
        return session_id

    def get_run(self, session_id: str) -> DashboardRun:
        with self.lock:
            session = self.runs.get(session_id)
        if session is None:
            raise ValueError("Unknown dashboard run")
        return session


SERVICE = DashboardService()


class DashboardHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/bootstrap":
                self._send(200, SERVICE.bootstrap())
                return
            match = re.fullmatch(r"/api/runs/([a-f0-9]{32})", path)
            if match:
                self._send(200, SERVICE.get_run(match.group(1)).snapshot())
                return
            self._send(404, {"error": "Not found"})
        except ValueError as error:
            self._send(400, {"error": str(error)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 10_000:
                raise ValueError("Request is too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/runs":
                session_id = SERVICE.start_run(payload)
                self._send(201, {"session_id": session_id})
                return
            match = re.fullmatch(
                r"/api/runs/([a-f0-9]{32})/decision", path
            )
            if match:
                approve = payload.get("approve")
                if not isinstance(approve, bool):
                    raise ValueError("Approval decision must be true or false")
                SERVICE.get_run(match.group(1)).decide(approve)
                self._send(200, {"recorded": True})
                return
            self._send(404, {"error": "Not found"})
        except (ValueError, json.JSONDecodeError) as error:
            self._send(400, {"error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def wait_for_frontend(
    process: subprocess.Popen[str], timeout: float = 30
) -> None:
    import socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Dashboard interface stopped during startup")
        try:
            with socket.create_connection(("localhost", 3000), timeout=0.2):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("Dashboard interface did not start within 30 seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local visual dashboard.")
    parser.add_argument("--api-only", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frontend: subprocess.Popen[str] | None = None
    server = ThreadingHTTPServer(("127.0.0.1", 8766), DashboardHandler)
    server_thread: threading.Thread | None = None
    try:
        print("Bioinformatics dashboard: http://localhost:3000/")
        print("Press Ctrl+C to stop it.")
        if args.api_only:
            server.serve_forever()
        else:
            if not (DASHBOARD_DIRECTORY / "node_modules").is_dir():
                raise SystemExit(
                    "Dashboard dependencies are missing; run npm install in dashboard/"
                )
            server_thread = threading.Thread(
                target=server.serve_forever, daemon=True
            )
            server_thread.start()
            frontend = subprocess.Popen(
                ["npm", "run", "dev"], cwd=DASHBOARD_DIRECTORY
            )
            wait_for_frontend(frontend)
            webbrowser.open("http://localhost:3000/")
            while frontend.poll() is None:
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        if server_thread is not None:
            server_thread.join(timeout=2)
        if frontend is not None:
            frontend.terminate()
            try:
                frontend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend.kill()


if __name__ == "__main__":
    main()
