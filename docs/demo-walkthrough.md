# Visual Demonstration Walkthrough

## Start

```bash
cd "/path/to/bioinformatics-pipeline-agent"
source .venv/bin/activate
python -m bioagent.dashboard_server
```

## Five-minute walkthrough

1. Open **12 phases** and explain how one controlled capability was added at a time.
2. Return to **Run lab** and choose a verified public dataset.
3. Select Python or Nextflow and direct or local-queue execution.
4. Prepare the plan and show that execution pauses for human approval.
5. Approve only after reading the plan; watch the live trace and job state.
6. Open the human report and compare its measurements with the recommendation.
7. Accept or reject the report. Explain that rejection means review is still needed, not that execution failed.
8. Open **Run history** and show the saved status.
9. Show the run folder's `audit.jsonl`, `report.md`, and `manifest.json` when deeper evidence is needed.

## Honest labels

- `accepted_by_human`: a person approved and accepted an interactive run.
- `needs_human_review`: execution finished but the person did not accept the report.
- `accepted_for_demo`: automated test/demo approval; never present this as human acceptance.
- The local queue is a governance simulation, not an HPC scheduler.
- The explanation layer is offline and deterministic, not an external production LLM.
- The project performs research-data QC, not clinical interpretation.
