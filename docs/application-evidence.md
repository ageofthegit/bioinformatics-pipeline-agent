# Application Evidence Draft

## Résumé entry

**Bioinformatics Pipeline Agent — Applied AI Engineering Project**

- Built a human-controlled FASTQ quality workflow with deterministic QC, Python and Nextflow runners, monitored retries, MCP tools, grounded explanations, and reproducible manifests.
- Added a local browser dashboard that operates the real approval-gated workflow, plus verified public ENA datasets and 72 automated tests covering correctness, safety, provenance, and interface boundaries.
- Designed explicit controls preventing an LLM, MCP client, or dashboard from silently executing, retrying, increasing resources, or accepting its own result.

## Cover-letter paragraph

I built a small bioinformatics pipeline agent to practise the combination of
software engineering, scientific workflows, AI tool integration, and user
enablement required in a forward-deployed role. The project validates and
analyses FASTQ data through Python or Nextflow, exposes narrowly controlled MCP
tools, records provenance, and keeps execution and report acceptance behind
human approval gates. I then added a local visual workspace so a user can move
through the same governed workflow without relying on terminal commands. Its
limitations—including simulated queueing, offline explanations, and non-clinical
scope—are documented alongside repeatable tests and public-data evidence.

## Follow-up evidence after initial publication

- Complete project-owner reviews of `SRR29651967` and `SRR12966849` in the dashboard.
- Record confusion, decisions, and any resulting interface changes.
- Choose a reuse licence before inviting reuse or outside contributions.

The initial public release followed a tracked-file review and a fresh GitHub
clone check covering 72 Python tests, the synthetic sample workflow, dependency
installation, and the dashboard build/render test.
