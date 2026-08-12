"""Local Nextflow execution backend."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

from bioagent.runners.base import RunnerOutcome


PROJECT_DIRECTORY = Path(__file__).resolve().parents[2]
PIPELINE_PATH = PROJECT_DIRECTORY / "pipelines" / "main.nf"
LOCAL_NEXTFLOW = PROJECT_DIRECTORY / ".tools" / "nextflow"
LOCAL_NEXTFLOW_HOME = Path.home() / ".nextflow-bioinformatics-agent"
HOMEBREW_JAVA_HOME = Path(
    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
)


class NextflowRunner:
    name = "nextflow"

    def __init__(self, executable: str | Path | None = None) -> None:
        if executable is not None:
            self.executable = str(executable)
        elif LOCAL_NEXTFLOW.exists():
            self.executable = str(LOCAL_NEXTFLOW)
        else:
            self.executable = shutil.which("nextflow") or "nextflow"

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        java_home = environment.get("JAVA_HOME")
        if not java_home and HOMEBREW_JAVA_HOME.exists():
            java_home = str(HOMEBREW_JAVA_HOME)

        if java_home:
            environment["JAVA_HOME"] = java_home
            java_bin = str(Path(java_home) / "bin")
            environment["PATH"] = f"{java_bin}:{environment.get('PATH', '')}"

        environment["NXF_HOME"] = str(LOCAL_NEXTFLOW_HOME)
        environment["NXF_OFFLINE"] = "true"
        environment["NXF_SYNTAX_PARSER"] = "v2"
        return environment

    def _version(self, environment: dict[str, str]) -> str:
        try:
            completed = subprocess.run(
                [self.executable, "-version"],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )
        except OSError:
            return "unavailable"

        output = (completed.stdout or completed.stderr).strip()
        for line in output.splitlines():
            if "version" in line.lower():
                return " ".join(line.split())
        return " ".join(output.split()) or "unavailable"

    def run(
        self,
        input_file: Path,
        quality_threshold: float,
        run_directory: Path,
    ) -> RunnerOutcome:
        output_directory = run_directory / "nextflow-output"
        work_directory = run_directory / "nextflow-work"
        log_path = run_directory / "nextflow.log"
        result_path = output_directory / "qc.json"
        command = [
            self.executable,
            "-log",
            str(log_path),
            "run",
            str(PIPELINE_PATH),
            "--input",
            str(input_file),
            "--quality_threshold",
            str(quality_threshold),
            "-output-dir",
            str(output_directory),
            "-work-dir",
            str(work_directory),
            "-ansi-log",
            "false",
        ]
        environment = self._environment()
        version = self._version(environment)
        started = perf_counter()

        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_DIRECTORY,
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )
        except OSError as error:
            return RunnerOutcome(
                runner=self.name,
                command=command,
                exit_code=127,
                duration_seconds=round(perf_counter() - started, 6),
                version=version,
                stderr=str(error),
            )

        duration = round(perf_counter() - started, 6)
        if completed.returncode != 0:
            return RunnerOutcome(
                runner=self.name,
                command=command,
                exit_code=completed.returncode,
                duration_seconds=duration,
                version=version,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        if not result_path.exists():
            return RunnerOutcome(
                runner=self.name,
                command=command,
                exit_code=1,
                duration_seconds=duration,
                version=version,
                stdout=completed.stdout,
                stderr="Nextflow completed without publishing qc.json",
            )

        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            return RunnerOutcome(
                runner=self.name,
                command=command,
                exit_code=1,
                duration_seconds=duration,
                version=version,
                stdout=completed.stdout,
                stderr=f"Could not read Nextflow QC output: {error}",
                output_file=str(result_path),
            )

        return RunnerOutcome(
            runner=self.name,
            command=command,
            exit_code=0,
            duration_seconds=duration,
            version=version,
            stdout=completed.stdout,
            stderr=completed.stderr,
            output_file=str(result_path),
            result=result,
        )
