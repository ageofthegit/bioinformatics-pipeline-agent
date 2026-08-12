"""Execution backends for the bioinformatics workflow."""

from bioagent.runners.base import Runner
from bioagent.runners.local_queue_runner import LocalQueueRunner, ResourceRequest
from bioagent.runners.nextflow_runner import NextflowRunner
from bioagent.runners.python_runner import PythonRunner


def create_runner(name: str) -> Runner:
    if name == "python":
        return PythonRunner()
    if name == "nextflow":
        return NextflowRunner()
    raise ValueError(f"Unknown runner: {name}")


__all__ = [
    "LocalQueueRunner",
    "NextflowRunner",
    "PythonRunner",
    "ResourceRequest",
    "Runner",
    "create_runner",
]
