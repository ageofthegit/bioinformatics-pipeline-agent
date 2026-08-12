"""Deterministic offline provider used for learning and tests."""

from typing import Mapping

from bioagent.llm.base import ExplanationDraft, FactValue
from bioagent.llm.safety import PLAN_EVIDENCE_KEYS, RESULT_EVIDENCE_KEYS


class OfflineDemoProvider:
    """Mimic structured LLM output without a network call or API key."""

    name = "offline-demo"

    def explain_plan(self, facts: Mapping[str, FactValue]) -> ExplanationDraft:
        summary = (
            f"The plan uses the {facts['runner']} runner to check "
            f"{facts['read_count']} reads with a Phred threshold of "
            f"{facts['quality_threshold']} in {facts['step_count']} fixed steps. "
            "A person remains responsible for the decision."
        )
        return ExplanationDraft(
            kind="plan",
            summary=summary,
            evidence_keys=PLAN_EVIDENCE_KEYS,
        )

    def explain_result(self, facts: Mapping[str, FactValue]) -> ExplanationDraft:
        summary = (
            f"The analysis measured {facts['read_count']} reads with mean base "
            f"quality {facts['mean_base_quality']}. {facts['low_quality_reads']} "
            f"reads were below Phred {facts['quality_threshold']}, representing "
            f"{facts['low_quality_percent']}%. GC content was {facts['gc_percent']}% "
            f"and there were {facts['n_bases']} unknown bases "
            f"({facts['n_percent']}%). Read lengths ranged from "
            f"{facts['shortest_read']} to {facts['longest_read']}, with variation "
            f"of {facts['read_length_variation_percent']}%. Human review remains "
            "responsible for the final decision."
        )
        return ExplanationDraft(
            kind="result",
            summary=summary,
            evidence_keys=RESULT_EVIDENCE_KEYS,
        )
