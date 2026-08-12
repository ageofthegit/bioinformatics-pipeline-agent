# Expected Learning

This document records the learning activities selected to strengthen the Bioinformatics Pipeline Agent and the Garvan Forward Deployed AI Engineer application.

## 10 August 2026 — Competitions and courses for the Garvan application

### Role status

Garvan's live Workday record was checked on 10 August 2026. At the time of checking, requisition `PRF8200` returned:

- `posted: true`
- `canApply: true`
- Posted more than 30 days ago

Links:

- [Live Workday record](https://garvan.wd3.myworkdayjobs.com/wday/cxs/garvan/garvan_institute/job/Sydney/Forward-Deployed-AI-Engineer_PRF8200)
- [Direct application](https://garvan.wd3.myworkdayjobs.com/garvan_institute/login?redirect=%2Fgarvan_institute%2Fjob%2Fsydney%2Fforward-deployed-ai-engineer_prf8200%2Fapply%2FapplyManually)

The application should be submitted soon because Garvan reviews applications as they are received. Completing another competition should not delay applying.

### Recommended competitions

| Priority | Competition | Status when checked | Expected learning |
|---:|---|---|---|
| 1 | [AI Agent Security — Multi-Step Tool Attacks](https://www.kaggle.com/competitions/ai-agent-security-multi-step-tool-attacks/discussion/726520) | Open; Kaggle listed 1 September 2026 deadline | Tool-using agent security, prompt injection, data exfiltration, reproducible failures, mitigations, and regression testing |
| 2 | [Biohub — Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/overview/evaluation) | Open; Kaggle listed 29 September 2026 deadline | Biomedical research data, computer vision, reproducible scientific execution, evaluation, and compute management |
| 3 | [Open Problems — Single-Cell Perturbations](https://www.kaggle.com/competitions/open-problems-single-cell-perturbations/discussion/452515) | Ended; late submissions available | Single-cell biology, gene expression, compound perturbations, validation, and bioinformatics workflows |
| 4 | [Stanford RNA 3D Folding Part 2](https://www.kaggle.com/competitions/stanford-rna-3d-folding-2/discussion/680551) | Ended; late submissions available | RNA biology, difficult scientific modelling, research pipelines, and reproducibility |

#### Highest-priority competition

The strongest direct match is **AI Agent Security — Multi-Step Tool Attacks** because the Garvan role explicitly mentions:

- prompt injection;
- data exfiltration;
- tool and function calling;
- agentic workflows;
- MCP integrations;
- AI governance; and
- evaluation and maintenance.

This competition would extend the existing GPT-OSS red-team experience from prompt-level attacks to multi-step failures involving tools. Any work must remain inside the competition's authorised environment and be presented defensively:

1. describe the vulnerability;
2. reproduce it safely;
3. explain the impact;
4. implement a mitigation; and
5. add a regression test.

#### How to use biomedical competitions

The Biohub competition is useful for biomedical research and scientific-compute experience, although it is computer vision rather than genomics.

The single-cell competition is more directly relevant to gene expression and bioinformatics. A manageable subset should be used rather than allowing its large dataset to overwhelm the main project. The strongest portfolio outcome would be to execute its preparation, training, and evaluation through the human-approved Nextflow workflow.

### Recommended courses

#### 1. Hello Nextflow and Nextflow for Genomics

Links:

- [Official Nextflow training](https://training.nextflow.io/)
- [Nextflow for Genomics](https://training.nextflow.io/2.1.4/nf4_science/genomics/)

Expected learning:

- Nextflow processes, channels, inputs, and outputs;
- reproducible scientific pipelines;
- variant-calling workflows;
- multi-sample execution;
- resource configuration; and
- pipeline testing.

Evidence to add to this project:

- a Nextflow quality-control pipeline;
- a runner interface supporting Python and Nextflow;
- captured commands, versions, logs, outputs, and exit codes; and
- tests comparing both runners' core results.

Implementation completed on 10 August 2026: the project now includes the Nextflow QC pipeline, Python and Nextflow runners, captured execution metadata, failure-path tests, and a real integration check with identical backend results.

#### 2. MCP: Build Rich-Context AI Apps with Anthropic

Link: [DeepLearning.AI MCP course](https://www.deeplearning.ai/courses/mcp-build-rich-context-ai-apps-with-anthropic)

Expected learning:

- MCP client-server architecture;
- tools, resources, and prompts;
- typed tool inputs and outputs;
- connecting agents to external capabilities; and
- controlling what an agent is allowed to do.

Evidence to add to this project:

- `validate_fastq` MCP tool;
- `propose_qc_plan` MCP tool;
- `request_pipeline_run` MCP tool;
- `get_run_status` MCP tool;
- `summarise_qc_result` MCP tool; and
- tests proving MCP calls cannot bypass human approval.

Implementation completed on 11 August 2026: the project now exposes all five
tools with typed input/output schemas through the official MCP Python SDK 2.0.0.
Project-data path restrictions, pending approval requests, audit records, and
protocol tests prevent MCP calls from executing or approving a pipeline.

#### 3. Evaluating AI Agents

Link: [DeepLearning.AI Evaluating AI Agents](https://www.deeplearning.ai/courses/evaluating-ai-agents)

Expected learning:

- agent tracing and observability;
- component-level evaluation;
- tool-selection and routing evaluation;
- trajectory evaluation;
- structured experiments; and
- production monitoring.

Evidence to add to this project:

- agent execution traces;
- known good and bad FASTQ cases;
- approval-bypass tests;
- tool-selection tests;
- prompt-injection tests; and
- a dated, versioned evaluation report.

Implementation completed on 11 August 2026: the project now has versioned
synthetic FASTQ, prompt-injection, and MCP contract cases; one repeatable runner;
and a dated report showing 26 deterministic checks passed. Subjective explanation
quality is kept separate for human review, and known limitations are stated.

#### Optional: Data Carpentry Genomics

Link: [Data Carpentry lessons](https://datacarpentry.org/lessons/)

This is an optional foundation if FASTQ, sequence quality, variant calling, command-line genomics, or cloud-computing concepts remain unclear.

Expected learning:

- organisation of bioinformatics projects;
- genomic file handling;
- command-line tools;
- sequence quality analysis;
- variant calling; and
- introductory cloud computing for genomics.

### Recommended sequence

1. Apply for the Garvan role without waiting for another competition result.
2. Complete **Hello Nextflow** and integrate Nextflow into this project.
3. Complete the **MCP course** and expose the existing controlled tools.
4. Complete **Evaluating AI Agents** and add a repeatable evaluation suite.
5. Enter **AI Agent Security** if it can be done without delaying the application or main project.
6. Later use a small single-cell competition subset to deepen the bioinformatics example.

### Expected overall outcome

Phase 6 implementation completed on 11 August 2026: a provider-neutral offline
explanation layer now demonstrates grounded plan/result explanations, structured
evidence, prompt-injection rejection, and strict separation from measurements,
execution, and approval. No external provider or API key has been enabled.

Phase 8 implementation completed on 11 August 2026: the agent downloaded a
checksum-verified public *E. coli* FASTQ from ENA, handled 128,518 real reads
without sample-specific code, issued a strong low-quality warning, matched ENA's
read count, matched an independent base count, and produced identical Python and
Nextflow results. The differing ENA run-level base count is documented rather
than hidden.

Phase 9 local implementation completed on 11 August 2026: Python or Nextflow can
run through a simulated local queue with recorded CPU, memory, wall-time, job ID,
status, and `not_applicable` cost. Conservative defaults need no extra gate,
increases require separate approval, and requests above the local ceiling are
audited and rejected before execution. No external infrastructure was created.

Phase 10 implementation completed on 11 August 2026: every terminal run now has
a machine-readable manifest containing data, code, pipeline, software, settings,
execution, timing, and approval evidence. SHA-256 fingerprints detect changed
inputs. A reproduction command reconstructs the recorded plan but deliberately
requires fresh plan and report approvals.

Three more public ENA datasets were prepared on 11 August 2026 for sequential
practice: yeast reduced-representation reads, environmental *Pseudomonas* reads,
and laboratory *E. coli* WGS. Their official sizes, MD5 checksums, metadata, and
read counts were verified before analysis; no result was assumed in advance.

Certificates by themselves provide limited evidence. The intended outcome is to convert each course or competition into working, reviewable additions to this repository:

- a reproducible Nextflow pipeline;
- controlled MCP tools;
- a grounded optional LLM layer;
- human approval that cannot be bypassed;
- agent traces and evaluation results;
- safe use of biomedical research data; and
- honest application evidence that the project owner can explain end to end.
