# Architecture and Human-Control Boundaries

```text
Browser dashboard
    │
    ├── choose approved local data, runner and executor
    │
    └── local dashboard bridge
            │ starts the existing interactive command
            ▼
        workflow coordinator
            │
            ├── deterministic FASTQ validation and QC
            ├── Python or Nextflow runner
            ├── direct or governed local-queue executor
            ├── state.json + audit.jsonl
            ├── report.md + manifest.json
            │
            ├── PLAN PROMPT ───────► human approve/reject
            ├── optional RETRY ────► human approve/reject
            └── REPORT PROMPT ─────► human accept/reject

Optional AI application
    └── MCP read/proposal/status tools
            └── cannot execute or approve a workflow

Optional explanation provider
    └── receives selected facts only
            └── cannot calculate, execute or approve
```

The dashboard does not duplicate analysis logic. It streams the existing CLI
and can answer only a prompt that the workflow has already emitted. It exposes
no `--yes` control and accepts no arbitrary filesystem path or shell command.

The current dashboard is local-only. This matters because the genomic files,
run records, and Python/Nextflow processes stay on the project owner's machine.
