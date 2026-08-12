# Bioinformatics Pipeline Agent

A small learning project that shows a human-in-the-loop bioinformatics workflow.

The agent:

1. validates a FASTQ file;
2. proposes a quality-control plan;
3. waits for human approval;
4. runs the approved analysis;
5. records each job-state change and explains failures;
6. offers at most one unchanged retry, which requires approval;
7. optionally explains the approved plan and saved measurements in plain language;
8. waits for a human to review the report;
9. saves the plan, attempts, result and audit history; and
10. writes a reproducibility manifest with input and code fingerprints.

The core Python application uses only the standard library. It also has an optional, pinned Nextflow 26.04.6 execution backend and an optional local MCP 2.0.0 adapter. It does **not** make clinical interpretations.

The quality-control report includes:

- read count and total bases;
- GC and unknown (`N`) base percentages;
- minimum, maximum, mean, and median read length;
- a warning when the read-length range exceeds 10% of the median length;
- mean Phred quality by base position; and
- deterministic guidance for reviewing a low-quality tail for trimming.

The trimming guidance is advisory. The agent never changes the input FASTQ file.

## Run it

From this folder:

```bash
python3 run.py data/sample.fastq
```

On a successful run, you will see two approval gates:

- approval before the analysis runs;
- confirmation after you review the result.

If execution fails, a third gate asks whether the same approved analysis may be
retried once. The agent does not silently retry or change inputs, parameters, or
resources.

For automated tests only, approvals can be supplied with `--yes`:

```bash
python3 run.py data/sample.fastq --yes
```

## Use the visual dashboard

Phase 12 adds a local browser workspace over the same controlled workflow. It
shows the 12-phase roadmap, verified datasets, runner choices, live output,
approval buttons, reports, and recent run history.

First-time setup:

```bash
cd "/path/to/bioinformatics-pipeline-agent/dashboard"
npm install
```

Start the complete local dashboard:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m bioagent.dashboard_server
```

On macOS, this version explicitly waits for the dashboard and opens it in the
default browser:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m bioagent.dashboard_server &
DASHBOARD_PID=$!
until curl -fsS http://localhost:3000/ >/dev/null; do sleep 1; done
open http://localhost:3000/
wait "$DASHBOARD_PID"
```

The browser opens at `http://localhost:3000/`. The dashboard can select only
the approved local dataset catalog and the Python/Nextflow runners. It starts
the existing CLI as a child process and enables a decision button only after
the real workflow prints an approval prompt. It has no automatic-approval
control. Stop the local dashboard with `Ctrl+C` in its terminal.

Choose the Nextflow backend explicitly:

```bash
python3 run.py data/sample.fastq --runner nextflow
```

The Nextflow backend requires Java 17 or later and Nextflow 26.04.6. The runner checks for a project-local `.tools/nextflow` executable first and then checks the normal command path. Follow the [official Nextflow installation instructions](https://docs.seqera.io/nextflow/install); do not commit the downloaded executable.

Run the separately documented real-backend equivalence check:

```bash
python3 -m scripts.check_nextflow_integration
```

This command requires a local Nextflow installation. It verifies that Python and Nextflow produce exactly the same QC measurements for the synthetic sample.

## Use the local MCP tools

MCP lets an AI application discover and call a small set of typed tools. Install
the pinned official SDK in a project-only environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-mcp.txt
```

Start the local `stdio` server:

```bash
.venv/bin/python -m bioagent.mcp_server
```

The process waits for an MCP host to communicate over standard input and output.
A host should launch it with the project folder as its working directory. No port,
account, API key, or credential is needed.

Inspect the five real tools without a desktop client:

```bash
.venv/bin/python -m scripts.check_mcp_integration
```

The tools validate a FASTQ, propose a QC plan, create an approval request, read
request/run status, and summarise a saved result. MCP may only read `.fastq` or
`.fq` files inside `data/`. It cannot execute or approve a pipeline.

When `request_pipeline_run` returns a request ID, a person can review it with:

```bash
.venv/bin/python -m bioagent.run_request request-...
```

That separate command shows the plan and asks the person for approval. Rejecting
the prompt starts no analysis, and both the request and rejection are audited.

## Use the offline explanation layer

Run the normal interactive workflow with the provider-neutral explanation layer:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python run.py data/sample.fastq --explain-with offline-demo
```

`offline-demo` mimics structured LLM output without a network call, API key, or
paid service. It receives only selected facts such as read count and measured
quality—not filenames, metadata, logs, credentials, or approval controls.

Every explanation is labelled separately from measurements and checked before it
is shown. Output is rejected if it introduces unsupported numbers, tries to
control execution or approval, requests sensitive data, or makes a clinical claim.
Rejected explanation text cannot stop, start, approve, or change the deterministic
workflow.

## Run the repeatable evaluation

Phase 7 checks the agent against versioned good, bad, and adversarial examples:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m evaluations.run_evaluations
```

The command writes a dated report under `evaluations/reports/` and returns a
non-zero exit code if any check fails. It scores objective behaviour such as QC
maths and approval enforcement. Explanation helpfulness remains a human review
question and is not presented as an automatic score.

## Use the approved public dataset

Phase 8 first used public, non-human *Escherichia coli* whole-genome run
[DRR002057](https://www.ebi.ac.uk/ena/browser/view/DRR002057) from the European
Nucleotide Archive. Its compressed FASTQ is 14.2 MB and expands to about 82.6 MB.
The data files are ignored by Git; the accession, source, usage policy, size, MD5,
and expected record count are kept in a small versioned manifest.

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m scripts.download_public_dataset
python run.py data/public/DRR002057.fastq --explain-with offline-demo
```

The downloader verifies the published size and MD5 before extracting and
validating the FASTQ. The analysis command uses the normal two human gates. The
demonstration found substantial low quality, so the agent warned against
continuing without human review. See
`docs/public-dataset-DRR002057.md` for provenance, results, and the openly recorded
ENA base-count discrepancy.

Three additional approved ENA runs are available for one-at-a-time testing:

| Accession | Sample | Compressed size | Reads |
|---|---|---:|---:|
| `ERR1229325` | Yeast reduced-representation sequencing | 3.0 MB | 122,511 |
| `SRR29651967` | Rhizosphere *Pseudomonas* sequencing | 4.4 MB | 53,841 |
| `SRR12966849` | Laboratory *E. coli* WGS | 23.6 MB | 629,082 |

Download one accession, or verify an existing download, with:

```bash
python -m scripts.download_public_dataset ERR1229325
```

Use `all` to prepare every approved accession. Their official metadata and
checksums are versioned in separate manifest files under `data/public/`; the
downloaded FASTQ files remain ignored by Git. See `docs/public-datasets.md` for
the recommended testing order and commands.

## Use the local compute queue

Phase 9 can submit either runner through a governed local queue simulation:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python run.py data/sample.fastq --executor local-queue
```

The defaults are 1 CPU, 1,024 MB memory, and 600 seconds wall time. A larger
request adds a separate approval gate:

```bash
python run.py data/sample.fastq --executor local-queue \
  --cpus 2 --memory-mb 2048 --wall-time-seconds 900
```

Local requests above 4 CPUs, 4,096 MB, or 3,600 seconds are rejected before
execution. The plan, approval decision, queued/running/completed states, queue job
ID, and requested resources are audited. Local cost is `not_applicable`.

This is a learning simulation, not a real scheduler or operating-system resource
container. It governs requested limits and flags a wall-time overrun, but it does
not reserve CPUs or memory. No cloud or HPC service is used.

## Reproduce a recorded run

Phase 10 writes `manifest.json` in every finished run folder. It records the
input SHA-256, source and pipeline fingerprints, software versions, arguments,
parameters, runner, executor, timestamps, execution details, and approval events.

Reconstruct a run from its ID:

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m bioagent.reproduce run-...
```

The command first verifies that the original input still has the recorded
checksum. It then rebuilds the same plan and asks for plan approval and final
report acceptance again. The reproduction command has no `--yes` option.

Run the tests:

```bash
python3 -m unittest discover -s tests
```

Run all MCP protocol tests with the optional environment:

```bash
.venv/bin/python -m unittest discover -s tests
```

## The main concepts

```text
FASTQ input
    ↓
validation tool
    ↓
agent creates a plan
    ↓
HUMAN APPROVAL
    ↓
runner selection
    ├── Python reference backend
    └── Nextflow pipeline
    ↓
executor selection
    ├── direct
    └── governed local queue
    ↓
record queued/running/completed or failed
    └── if failed: explain → HUMAN RETRY APPROVAL → retry once
    ↓
agent interprets the measurements
    ↓
optional explanation layer receives selected facts only
    ↓
HUMAN REVIEW
    ↓
saved report and audit trail
    ↓
manifest with data, code, settings, versions and approval history
    └── reproduce → verify input → HUMAN APPROVAL again

AI application
    ↓ MCP
typed read/proposal/status tools
    └── run request → PENDING HUMAN APPROVAL → existing workflow
```

The browser dashboard is an interface over this flow, not a separate analysis
engine. Validation, calculations, approval enforcement, state and provenance
remain in the existing Python modules.

This follows the same pattern as the proposed FPL project:

> Agent recommends → human approves → agent acts → human reviews.

## Best order for reading the code

1. `run.py` — where the program starts
2. `bioagent/workflow.py` — the end-to-end sequence
3. `bioagent/tools/fastq.py` — input validation
4. `bioagent/tools/qc.py` — the analysis and recommendation
5. `bioagent/runners/` — the Python and Nextflow execution backends
6. `bioagent/monitoring.py` — job states, failure explanations and retry limit
7. `pipelines/main.nf` — the Nextflow process, channel and workflow
8. `bioagent/approvals.py` — the human gates
9. `bioagent/state.py` — saved state and audit events
10. `bioagent/mcp_tools.py` — MCP safety and approval-request logic
11. `bioagent/mcp_server.py` — typed MCP adapter
12. `bioagent/run_request.py` — person-operated request approval bridge
13. `bioagent/llm/` — provider interface, offline demo and grounding checks
14. `evaluations/` — versioned cases, evaluation runner and dated reports
15. `bioagent/runners/local_queue_runner.py` — queue and resource limits
16. `bioagent/provenance.py` — checksums and run manifest
17. `bioagent/reproduce.py` — approval-preserving run reconstruction
18. `bioagent/dashboard_server.py` — local browser bridge to real approval prompts
19. `dashboard/` — visual workflow and 12-phase roadmap

The workflow file is the best place to start. Read it from the top of `run_workflow()` to the bottom and follow each function call into its small module.

## Folder guide

```text
run.py                  command-line entry point
bioagent/models.py      simple data structures
bioagent/state.py       saves state and audit events
bioagent/approvals.py   human approval gates
bioagent/workflow.py    coordinates the complete workflow
bioagent/monitoring.py  job transitions and controlled retry guidance
bioagent/tools/fastq.py reads and validates FASTQ data
bioagent/tools/qc.py    calculates quality measurements
bioagent/runners/       selects Python or Nextflow execution
bioagent/runners/local_queue_runner.py local queue and resource governance
bioagent/qc_command.py  writes QC JSON for the Nextflow process
bioagent/mcp_tools.py   safe functions and pending approval requests
bioagent/mcp_server.py  five typed MCP tools over local stdio
bioagent/run_request.py separate human-operated approval command
bioagent/provenance.py creates checksums and manifest.json receipts
bioagent/reproduce.py reconstructs a recorded plan with fresh approvals
bioagent/dashboard_server.py safely connects browser actions to CLI prompts
bioagent/llm/           optional grounded explanation layer
pipelines/main.nf       minimal FASTQ-to-QC-JSON workflow
nextflow.config         pins Nextflow and conservative local execution
requirements-mcp.txt    pinned optional MCP SDK dependency
scripts/                real Nextflow and MCP integration checks
data/sample.fastq       tiny synthetic learning dataset
data/public/            public-data manifests; downloaded reads are ignored
evaluations/            repeatable cases, runner and dated evidence report
dashboard/              local visual interface and web build tests
tests/                  small automated tests
approval_requests/      generated pending requests and audit history
runs/                   created at runtime; one folder per run
```

## What this version teaches

- FASTQ structure
- bioinformatics quality control
- modular Python
- tool-based workflows
- persistent state
- human approval gates
- audit trails
- simple evaluation and reporting
- Nextflow processes, channels, inputs and outputs
- equivalent execution through two runner backends
- subprocess metadata and failure handling
- timestamped job monitoring and human-approved recovery
- MCP tool schemas and controlled capability exposure
- provider-neutral explanations grounded in deterministic facts
- prompt-injection and clinical-claim rejection
- evidence-based evaluation with visible failures and known limitations
- verified public-data retrieval and realistic QC warnings
- local queue concepts, conservative resources and approval-controlled increases
- scientific provenance, SHA-256 fingerprints and approval-safe reproduction
- browser-based workflow operation without weakening human approval

## Deliberate limits

This version does not call an external LLM and does not use cloud computing or real patient data. The remaining features should be added one at a time in this order:

1. complete the remaining project-owner dataset reviews;
2. polish the application evidence; and
3. publish the reviewed repository.

See `docs/next-steps-2026-08-10.md` for the complete staged roadmap and acceptance criteria.
