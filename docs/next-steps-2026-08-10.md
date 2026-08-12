# Next Steps and Independent-Agent Handoff

**Date:** 10 August 2026  
**Project:** Bioinformatics Pipeline Agent  
**Project path:** local clone of `bioinformatics-pipeline-agent`

## Objective

Develop a small, understandable bioinformatics agent that can validate genomic data, propose an analysis, wait for human approval, run an approved pipeline, monitor it, explain the result, and wait for final human review.

The finished project is intended to demonstrate the following capabilities for a Forward Deployed AI Engineer application:

- modular Python engineering;
- bioinformatics and research-computing workflows;
- Nextflow pipeline execution;
- agent tool use through MCP;
- careful LLM integration;
- human-in-the-loop control;
- monitoring, evaluation, governance, and reproducibility; and
- user-centred deployment and adoption.

The code must remain simple enough for the project owner to read and explain personally.

## Current working baseline

The core Python application uses only the standard library. Its optional MCP adapter uses a pinned local dependency. The project now provides:

- FASTQ structure validation;
- read count, read-length distribution, GC content, unknown-base percentage, and Phred quality measurements;
- mean quality by base position and deterministic trimming guidance;
- a warning when the read-length range exceeds 10% of the median length;
- a deterministic quality recommendation;
- explicit Python and Nextflow runner selection;
- a minimal Nextflow FASTQ-to-QC-JSON pipeline using the current v2 parser;
- captured runner command, version, standard output, standard error, exit code, duration, and output path;
- timestamped `queued`, `running`, `completed`, `failed`, and `awaiting_retry_approval` job states;
- deterministic failure explanations and one unchanged, approval-controlled retry;
- five typed MCP tools for validation, planning, pending requests, status, and result summaries;
- project-data path restrictions and an MCP boundary that cannot execute or approve work;
- a provider-neutral, optional explanation layer for approved plans and saved QC measurements;
- deterministic grounding checks that reject invented numbers, workflow-control instructions, sensitive-data requests, and clinical claims;
- a repeatable evaluation runner with versioned FASTQ, adversarial explanation, and MCP contract cases;
- a dated evaluation report that separates deterministic results from subjective explanation quality and states known limitations;
- four checksum-verified public ENA microbial datasets with versioned provenance, including one independently checked demonstration;
- a local queue wrapper with governed CPU, memory, wall-time, job-state, and cost fields;
- separate approval for resource increases and audited rejection above conservative local ceilings;
- a machine-readable run manifest with input, source-tree, and pipeline SHA-256 fingerprints;
- recorded invocation, parameters, software versions, timestamps, execution evidence, and approval events;
- approval-preserving reproduction that rejects a changed or missing original input;
- approval before the analysis runs;
- human review after the report is produced;
- saved `state.json`, `audit.jsonl`, and `report.md` files;
- explicit distinction between human approval and `--yes` automatic demonstration mode; and
- seventy-two passing tests covering validation, measurements, runners, monitoring, approval, controlled retry, MCP safety, grounded explanations, prompt-injection resistance, evaluation behaviour, public-data integrity, local queue governance, provenance, reproduction, and dashboard boundaries.

As of 11 August 2026, the local environment contained:

- Python 3.14.5;
- Homebrew OpenJDK 17.0.16, detected by the runner without changing the system path;
- a project-local, ignored Nextflow 26.04.6 executable with an isolated user cache;
- a project-local `.venv` with the official MCP Python SDK 2.0.0; and
- no external LLM provider, API key, or network-dependent explanation test; and
- no third-party test framework.

An independent agent must recheck the environment rather than assume it is unchanged.

## Existing project map

```text
README.md                 Project explanation and basic commands
run.py                    Command-line entry point
bioagent/models.py        PipelinePlan and RunRecord data structures
bioagent/state.py         State persistence and audit events
bioagent/approvals.py     Human approval prompts
bioagent/workflow.py      End-to-end workflow coordinator
bioagent/monitoring.py    Job states, failure summaries, and retry limit
bioagent/tools/fastq.py   FASTQ reading and validation
bioagent/tools/qc.py      QC calculations and recommendations
bioagent/mcp_tools.py     Safe MCP functions and approval-request persistence
bioagent/mcp_server.py    Five typed MCP tools over local stdio
bioagent/run_request.py   Human-operated approval bridge
bioagent/provenance.py    SHA-256 fingerprints and machine-readable run manifest
bioagent/reproduce.py     Approval-preserving plan reconstruction
bioagent/llm/base.py      Provider-neutral structured explanation contract
bioagent/llm/fake.py      Offline deterministic demo provider
bioagent/llm/safety.py    Fact selection and explanation safety checks
bioagent/runners/local_queue_runner.py  Local queue and resource limits
evaluations/cases/        Versioned inputs and expected outcomes
evaluations/run_evaluations.py  Repeatable evaluation command
evaluations/reports/      Dated evidence reports
data/sample.fastq         Small synthetic FASTQ example
data/public/DRR002057.manifest.json  Versioned public-data provenance
data/public/*.manifest.json         Four approved ENA dataset records
scripts/download_public_dataset.py  Verified ENA download and extraction
scripts/check_public_dataset.py     Public and independent result checks
tests/test_fastq.py       FASTQ and QC tests
tests/test_workflow.py    Approval and workflow tests
tests/test_monitoring.py  Failure explanation and retry-policy tests
tests/test_mcp_tools.py   MCP path, request, status, and result safety tests
tests/test_mcp_server.py  In-memory MCP protocol and schema tests
tests/test_llm.py         Grounding, injection, sensitive-data, and clinical tests
tests/test_evaluations.py Evaluation runner and failure-reporting tests
tests/test_public_dataset.py  Provenance and integrity tests
tests/test_local_queue.py Queue, resource approval, and limit tests
tests/test_provenance.py  Manifest, checksum, and safe-reproduction tests
docs/                     Project handoff and learning documents
approval_requests/        Generated MCP requests; ignored by Git
runs/                     Generated output; ignored by Git
```

## Baseline commands

Run these from the project root before making changes:

```bash
python3 -m unittest discover -s tests -v
python3 run.py data/sample.fastq
```

The second command is interactive. It must stop at both approval gates. Use the following only for automated verification:

```bash
python3 run.py data/sample.fastq --yes
```

An automatically accepted demonstration must use the status `accepted_for_demo`. It must never be recorded as human approval.

## Non-negotiable design rules

1. Keep the code human-readable and modular. Prefer small functions and descriptive names.
2. `bioagent/workflow.py` coordinates work. Tool modules perform specific operations and must not approve their own actions.
3. Deterministic Python owns validation, calculations, safety rules, and approval enforcement.
4. An LLM may propose or explain. It may not invent measurements, execute unapproved work, or approve its own output.
5. Every material action must be recorded in the audit history.
6. Human approval is required before pipeline execution, retrying with changed parameters, increasing resources, or accepting a final report.
7. Use only synthetic or clearly public, openly usable data. Never add patient-identifiable, clinical, confidential, or restricted data.
8. Do not make clinical interpretations or medical recommendations.
9. Never commit credentials, tokens, downloaded executables, large datasets, generated run folders, or secrets.
10. Add dependencies only when a stage genuinely requires them. Pin and document every added dependency.
11. Tests must not require network access, paid services, credentials, or human input.
12. Do not claim that a prototype, simulation, or automatic demonstration is a production deployment.
13. Complete and verify one stage before starting the next stage.
14. Preserve the working command-line experience unless a change is clearly documented.

## Independent-agent operating procedure

For every stage:

1. Read `README.md`, this file, and the modules relevant to the stage.
2. Run the baseline tests before editing.
3. Inspect the working tree and preserve unrelated user changes.
4. Implement the smallest version that satisfies the stage.
5. Add or update tests for both success and failure paths.
6. Run the complete test suite.
7. Run one local demonstration when safe and non-interactive verification is sufficient.
8. Update `README.md` when commands, dependencies, architecture, or user behaviour changes.
9. Update the progress table in this document.
10. Report exactly what was implemented, what was verified, and what remains incomplete.

Stop and ask the user before:

- downloading or installing software that requires permission;
- using a paid API;
- creating or using cloud resources;
- incurring costs;
- accessing accounts or credentials;
- downloading a dataset whose licence, sensitivity, or size is unclear;
- contacting pilot users; or
- publishing the repository or application materials.

## Progress tracker

| Stage | Status | Completion evidence |
|---|---|---|
| Working Python baseline | Complete | Seventy-two tests pass; interactive workflow exists |
| 1. Learn and exercise baseline | Pending user exercise | Manual run and inspection by project owner |
| 2. Stronger FASTQ QC | Complete | Eleven tests pass; sample demonstration produced the expanded report |
| 3. Nextflow | Complete | Nextflow 26.04.6 real run passed; Python and Nextflow results are identical |
| 4. Monitoring and recovery | Complete | 21 tests pass; real Nextflow run recorded timestamped transitions |
| 5. MCP | Complete | Five typed tools; 34 tests; rejected request started no analysis |
| 6. LLM integration | Complete | Offline provider; grounded output; 44 tests pass |
| 7. Evaluation | Complete | 26 deterministic checks pass; dated report records limitations |
| 8. Public dataset | Complete | DRR002057 verified; real-data run and independent checks pass |
| 9. Cloud/HPC-style execution | Local phase complete | Governed local queue; no external executor created |
| 10. Provenance | Complete | Reproducible manifest and checksum verification |
| 11. User pilot | In progress | First owner review recorded; two approved datasets remain |
| 12. Application evidence | Initial release complete | Dashboard, docs, clean-clone check, and public GitHub repository |

## Stage 1: Understand the current workflow

### Tasks

- Run `python3 run.py data/sample.fastq` manually.
- Approve the proposed plan and review the final report.
- Inspect the new run folder containing `state.json`, `audit.jsonl`, and `report.md`.
- Read `run_workflow()` in `bioagent/workflow.py` from top to bottom.
- Follow each call into `approvals.py`, `fastq.py`, `qc.py`, and `state.py`.
- Change the quality threshold and observe the recommendation.
- Create a temporary low-quality FASTQ example and observe the warning.

### Acceptance criteria

- The project owner can explain the FASTQ four-line record format.
- The project owner can identify both human approval gates.
- The project owner can explain why `--yes` is demonstration mode rather than human approval.
- No code change is necessary unless the exercise reveals a defect or unclear wording.

### Learning goal

Understand FASTQ data, tool calls, saved state, approval gates, and audit history.

## Stage 2: Add stronger FASTQ quality control

**Status:** Complete on 10 August 2026. The implementation uses median read length as the typical length, warns when the read-length range exceeds 10% of that median, and recommends review of a trailing low-quality region without modifying the input.

### Tasks

- Extend `bioagent/tools/qc.py` to calculate:
  - quality by base position;
  - percentage of `N` bases;
  - minimum, maximum, and typical read length; and
  - a clear warning for unusual read-length variation.
- Add a deterministic trimming recommendation without automatically modifying data.
- Extend `report.md` generation to present the new measurements simply.
- Add small fixture files or generate temporary test files for:
  - valid high-quality data;
  - valid low-quality data;
  - incomplete FASTQ records;
  - sequence/quality length mismatch;
  - unexpected bases; and
  - variable read lengths.

### Suggested files

- Modify `bioagent/tools/qc.py`.
- Modify `bioagent/workflow.py` only if report formatting requires it.
- Expand `tests/test_fastq.py` or add `tests/test_qc.py`.

### Acceptance criteria

- All old tests still pass.
- New measurements are calculated deterministically.
- A low-quality sample produces a warning but is never modified automatically.
- Invalid FASTQ data fails before the first execution approval.
- Reports remain understandable without bioinformatics expertise.

### Learning goal

Understand how bioinformatics quality measurements become operational decisions.

## Stage 3: Add Nextflow

**Status:** Complete on 10 August 2026. The project has a pinned Nextflow 26.04.6 pipeline, explicit `--runner` selection, recorded execution metadata, offline failure tests, and a separately verified real integration run. `python3 -m scripts.check_nextflow_integration` confirmed that both backends produce exactly identical measurements for `data/sample.fastq`.

### Preconditions

- Recheck Java and Nextflow availability.
- If Nextflow is absent, use its current official installation documentation.
- Request permission before downloading or installing it when the environment requires approval.
- Do not commit the Nextflow executable.

### Tasks

- Create a minimal Nextflow pipeline under `pipelines/`.
- Give the pipeline one input FASTQ and one output QC JSON file.
- Keep the existing Python QC implementation as a working reference backend.
- Add a small runner interface, for example:
  - `bioagent/runners/base.py` for the runner contract;
  - `bioagent/runners/python_runner.py`; and
  - `bioagent/runners/nextflow_runner.py`.
- Let the workflow select a runner through an explicit command-line option.
- Execute subprocesses without a shell when practical.
- Capture command arguments, output, error text, exit code, duration, and Nextflow version.
- Require approval before any Nextflow execution.

### Acceptance criteria

- `python3 run.py data/sample.fastq` continues to work.
- A documented option runs the Nextflow backend.
- Python and Nextflow produce equivalent core measurements for the sample data.
- A failed Nextflow command is recorded as failed rather than accepted.
- Tests use a fake runner where possible and do not require Nextflow.
- At least one separately documented local integration check uses real Nextflow.

### Learning goal

Understand processes, channels, inputs, outputs, and reproducible scientific execution.

## Stage 4: Add job monitoring and human-approved recovery

**Status:** Complete on 11 August 2026. Every execution attempt now records
timestamped job transitions and subprocess evidence. Known failures receive a
deterministic plain-language summary. The agent may propose one unchanged retry,
but it runs only after a separately audited approval and never retries more than
once.

### Tasks

- Add explicit job states such as `queued`, `running`, `completed`, `failed`, and `awaiting_retry_approval`.
- Record timestamps for each transition.
- Capture standard output, standard error, exit code, and duration.
- Add a plain-language deterministic failure summary for known cases.
- Allow the agent to propose one retry action.
- Require human approval before a retry, changed parameter, or resource increase.
- Set a small maximum retry count, initially one.

### Suggested files

- Extend `bioagent/models.py` and `bioagent/state.py`.
- Add `bioagent/monitoring.py` or keep monitoring inside the runner if it remains small.
- Update `bioagent/workflow.py` for retry approval.

### Acceptance criteria

- Tests cover success, failure, rejected retry, and approved retry.
- No retry occurs silently.
- Every state transition and approval appears in `audit.jsonl`.
- A failed run cannot produce an accepted report.

### Learning goal

Understand production ownership, state transitions, failures, and controlled recovery.

## Stage 5: Expose tools through MCP

**Status:** Complete on 11 August 2026. The project uses the official MCP Python
SDK 2.0.0 over local `stdio`. Five typed tools reuse the deterministic project
logic. MCP can create an audited pending request, but a separate person-operated
command must still show the plan and obtain approval before the existing workflow
can run. A real rejection demonstration confirmed that no analysis started.

### Preconditions

- Use the current official Model Context Protocol Python SDK documentation.
- Create a local virtual environment if a third-party package is required.
- Pin the selected SDK version in the project dependency file.
- Keep tests independent of a running desktop client.

### Tasks

- Add an MCP server as a thin adapter over existing Python functions.
- Do not duplicate QC logic inside the MCP layer.
- Expose small tools with typed schemas:
  - `validate_fastq`;
  - `propose_qc_plan`;
  - `request_pipeline_run`;
  - `get_run_status`; and
  - `summarise_qc_result`.
- Design `request_pipeline_run` so it creates or returns an approval request rather than bypassing approval.
- Reject missing paths, unsupported formats, unsafe paths, unknown run IDs, and execution without approval.
- Document how to start and inspect the server locally.

### Acceptance criteria

- Each MCP tool has a concise description and clear input/output schema.
- MCP calls use the same validation, workflow, state, and audit modules as the CLI.
- Tests prove that MCP access cannot bypass the human approval gate.
- No credentials are required for the local MCP demonstration.

### Learning goal

Understand MCP, tool schemas, agent integrations, and controlled capability exposure.

## Stage 6: Add an LLM carefully

**Status:** Complete offline on 11 August 2026. A provider-neutral interface and
deterministic demo provider explain only an approved plan and saved QC facts. The
provider receives no filenames, metadata, logs, credentials, approval state, or
execution tools. Structured output is labelled and rejected if it invents a
number, attempts workflow control, requests sensitive data, or makes a clinical
claim. No external LLM, API key, paid call, or network-dependent test was added.

### Preconditions and decisions

- Do not assume an LLM provider. Ask the user before enabling paid external calls.
- Put provider-specific code behind a small interface.
- Provide a fake or deterministic provider for tests and offline learning.
- Read the selected provider's current official documentation before implementation.
- Load credentials from environment variables only.

### Tasks

- Use the LLM for two narrow functions:
  - explain an approved plan in plain language; and
  - explain deterministic QC results using only supplied measurements.
- Keep plan validation, QC calculations, resource limits, and approvals outside the LLM.
- Require structured output where supported.
- Include the measurement values used to support every recommendation.
- Treat filenames, metadata, logs, paper text, and retrieved text as untrusted.
- Add prompt-injection cases that try to bypass approval, invent results, or request sensitive data.
- Reject unsupported clinical interpretation.

### Suggested files

- Add `bioagent/llm/base.py`.
- Add `bioagent/llm/fake.py` for tests.
- Add one provider adapter only after user approval.

### Acceptance criteria

- The full workflow still works without an API key.
- Unit tests never call the network.
- The LLM cannot change measured values or approval state.
- LLM output is labelled as explanation rather than measurement.
- Prompt-injection tests cannot trigger execution or approval.

### Learning goal

Understand the division of responsibility between an LLM, deterministic tools, and humans.

## Stage 7: Add a repeatable evaluation suite

**Status:** Complete on 11 August 2026. Versioned cases cover valid and malformed
FASTQ data, QC measurements, recommendations, saved-report consistency, rejected
approval, adversarial explanation output, and the five-tool MCP contract. The
dated report records 26 passed deterministic checks, separates subjective
explanation quality for human review, and states known limitations.

### Tasks

- Create `evaluations/cases/` with small synthetic examples and expected outcomes.
- Add an evaluation runner that measures:
  - FASTQ validation accuracy;
  - QC calculation correctness;
  - recommendation correctness;
  - report consistency with tool output;
  - approval-gate enforcement;
  - MCP schema/tool behaviour; and
  - prompt-injection resistance after Stage 6.
- Save a dated Markdown or JSON evaluation report.
- Separate deterministic pass/fail checks from subjective explanation-quality ratings.

### Acceptance criteria

- Evaluation runs with one documented command.
- Expected results are versioned and reviewable.
- Failed cases cause a non-zero exit code.
- The report includes known limitations and does not hide failures.

### Learning goal

Demonstrate reliability with evidence rather than relying on a successful demo.

## Stage 8: Add one real public dataset

**Status:** Implemented on 11 August 2026 using public, non-human *Escherichia
coli* run `DRR002057` from ENA. The 14,215,821-byte compressed FASTQ matched its
published MD5, extracted to 128,518 valid reads, and ran without sample-specific
code. ENA's read count, an independent local base count, and Python/Nextflow
equivalence passed. The differing ENA run-level base count is documented rather
than hidden. The saved run is labelled `accepted_for_demo`; a project owner can
rerun the documented interactive command for personal acceptance.

### Preconditions

- Research an openly usable, non-identifiable genomic dataset from an authoritative source.
- Record source, licence or usage terms, accession, checksum, expected format, and approximate size.
- Prefer a dataset no larger than 25 MB for the first example.
- Ask the user before downloading it.

### Tasks

- Add a small download script or documented manual command.
- Keep downloaded data out of Git.
- Verify its checksum before use.
- Run it through the same human-approved workflow.
- Compare core measurements with another trusted tool or published information where possible.
- Save only small, non-sensitive derived demonstration results.

### Acceptance criteria

- Dataset provenance and usage permission are documented.
- No sensitive or restricted data enters the repository.
- The workflow handles the data without code changes specific to that sample.
- Results are independently checked where practical.

### Learning goal

Move from synthetic input to realistic, reproducible research data.

## Stage 9: Add cloud or HPC-style execution

**Status:** Local phase complete on 11 August 2026. Either Python or Nextflow can
run through a simulated local queue. Requests record CPU, memory, wall time,
executor, queue job ID, status, and `not_applicable` local cost. Defaults are 1
CPU, 1,024 MB, and 600 seconds. Increases need separate approval; requests above
4 CPUs, 4,096 MB, or 3,600 seconds are audited and rejected before execution.
Sixty tests, queued Python/Nextflow demonstrations, and a rejected over-limit
demonstration passed. This is not an
OS scheduler, cloud service, or HPC deployment, and no external infrastructure
or credentials were created.

### Local phase

- First create a local queued-job abstraction.
- Record requested CPUs, memory, wall time, and execution status.
- Enforce conservative default limits.
- Require approval before increasing resources.
- Add cost as `not_applicable` for local execution rather than inventing a value.

### External phase

- Do not create cloud or HPC resources without explicit user authority.
- Ask which approved environment and credentials should be used.
- Keep executor-specific code behind the runner interface.
- Record data location, access controls, requested resources, and actual use.
- Add a cost estimate and approval gate before paid cloud execution.

### Acceptance criteria

- Queue behaviour is testable locally without cloud access.
- Resource requests and changes are auditable.
- External execution is optional; the local workflow continues to work.
- No credentials or infrastructure identifiers are committed.

### Learning goal

Understand research-computing queues, resources, limits, and governed execution.

## Stage 10: Add provenance and reproducibility

**Status:** Complete on 11 August 2026. Every terminal workflow path now writes
`manifest.json` with input, source-tree, and pipeline SHA-256 fingerprints;
Python, runner, explanation-provider, and dependency versions; invocation and
reproduction arguments; plan parameters; runner/executor evidence; timestamps;
results; and approval events. Reproduction verifies the original input and has
no automatic-approval option. Six provenance tests cover changed data, complete
and rejected-run manifests, checksum refusal, fresh approvals, and equivalent
sample results. The current full suite has 72 passing tests; the 26-check evaluation,
MCP integration, and Python/Nextflow equivalence also pass.

### Tasks

- Calculate SHA-256 checksums for every input.
- Record:
  - code version or source-tree identifier;
  - pipeline and Nextflow versions;
  - Python version;
  - command arguments;
  - parameters;
  - runner and executor;
  - timestamps;
  - dependency versions; and
  - approval events.
- Produce a machine-readable `manifest.json` for every run.
- Add a `reproduce` command that reconstructs the plan but still requires approval before execution.

### Acceptance criteria

- Changing an input changes its checksum.
- A manifest contains enough information to repeat the run.
- Reproduction never bypasses approval.
- A sample run can be reproduced with equivalent core results.

### Learning goal

Understand traceability and reproducibility in biomedical research.

## Stage 11: Conduct a small user pilot

**Status:** Reframed as a project-owner usability review because no additional
participants are available. The owner completed the first of three public-data
sessions with yeast `ERR1229325` and correctly withheld report acceptance after
spotting contradictory unknown-base wording. That finding produced a regression
test and clearer count-aware wording. The two remaining datasets will be tested
through the visual dashboard before this stage is complete.

### Agent boundary

The independent agent may prepare pilot materials but must not contact people or distribute the project without user direction.

### Tasks

- Prepare a one-page user guide and a short observation checklist.
- Ask the project owner to select two or three suitable technical users.
- Collect only non-sensitive feedback about:
  - ease of setup;
  - clarity of the plan;
  - clarity of approval questions;
  - usefulness of the report;
  - confusing errors; and
  - time to complete the workflow.
- Record feedback anonymously unless participants consent otherwise.
- Prioritise improvements using evidence.

### Acceptance criteria

- The user owns all external contact and consent.
- No participant data or genomic data is collected unnecessarily.
- Feedback, changes, and unresolved issues are documented.
- At least one interface improvement is tied to observed evidence.

### Learning goal

Demonstrate forward-deployed engineering, enablement, adoption support, and user-centred iteration.

## Stage 12: Prepare application evidence

**Status:** In progress on 12 August 2026. A local visual dashboard now shows the
approved dataset catalog, runner/executor choices, live workflow trace, actual
approval prompts, reports, 12-phase roadmap, and recent run history. Its bridge
can answer only prompts emitted by the existing CLI and exposes no automatic
approval or arbitrary path/command. Architecture, demonstration, and application
evidence drafts are present. A local Git repository is initialized and ignored
files have been audited. Public GitHub publication waits for the two remaining
owner reviews and a final licence/file-list decision.

### Tasks

- Ensure generated runs, downloaded data, credentials, and executables are excluded from Git.
- Create a small architecture diagram showing tools, approvals, runner, MCP, and optional LLM.
- Add one reproducible demonstration using public or synthetic data.
- Include the evaluation report and known limitations.
- Prepare a short walkthrough that shows both human gates.
- Clearly label what is implemented, simulated, locally tested, externally tested, or not deployed.
- Draft an honest résumé entry under **Applied AI Engineering Projects**.
- Draft a concise cover-letter paragraph connecting the project to Garvan's requirements.

### Acceptance criteria

- A reviewer can run the local demonstration from the README.
- The repository contains no sensitive data or secrets.
- Tests and evaluation pass with documented commands.
- The architecture and human-control boundaries are clear.
- No application claim exceeds the available evidence.

### Learning goal

Turn the project into credible and reviewable evidence for the Garvan application.

## Whole-project definition of done

The project is complete when a reviewer can:

1. provide a synthetic or approved public FASTQ file;
2. receive a valid, understandable analysis plan;
3. approve or reject execution;
4. run the approved analysis through Nextflow;
5. observe job status and controlled recovery;
6. access the same controlled tools through MCP;
7. optionally use an LLM for grounded explanations;
8. review measurements, provenance, limitations, and audit history;
9. accept or reject the final report; and
10. reproduce the run from its manifest without bypassing approval.

The project must also have passing tests, a versioned evaluation report, no sensitive data, and documentation the project owner can explain without relying on an external agent.

## Required implementation order

1. Exercise the current workflow.
2. Improve deterministic QC.
3. Add Nextflow.
4. Add monitoring and recovery.
5. Add MCP.
6. Add the optional LLM layer.
7. Build the evaluation suite.
8. Add one approved public dataset.
9. Add local HPC-style execution before considering external compute.
10. Complete provenance and reproduction.
11. Prepare and conduct the user-owned pilot.
12. Package the evidence for the application.

Do not combine stages merely to move faster. A stage is complete only when its acceptance criteria pass and its behaviour is documented.
