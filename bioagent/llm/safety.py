"""Build trusted fact maps and validate optional explanation output."""

import re
from types import MappingProxyType
from typing import Any, Mapping

from bioagent.llm.base import (
    ExplanationDraft,
    ExplanationKind,
    ExplanationProvider,
    FactValue,
    GroundedExplanation,
)


PLAN_EVIDENCE_KEYS = (
    "runner",
    "read_count",
    "quality_threshold",
    "step_count",
)
RESULT_EVIDENCE_KEYS = (
    "read_count",
    "mean_base_quality",
    "quality_threshold",
    "low_quality_reads",
    "low_quality_percent",
    "gc_percent",
    "n_bases",
    "n_percent",
    "shortest_read",
    "longest_read",
    "read_length_variation_percent",
)

NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
CONTROL_PATTERN = re.compile(
    r"\b(?:approve|approval|execute|execution|retry|rerun|bypass|"
    r"change parameters?|increase resources?|ignore (?:all )?previous|"
    r"secret|credentials?|api key)\b",
    re.IGNORECASE,
)
CLINICAL_PATTERN = re.compile(
    r"\b(?:clinical decision|diagnos\w*|disease|medical advice|patient|"
    r"prescrib\w*|treat(?:ment|ing)?)\b",
    re.IGNORECASE,
)


class ExplanationSafetyError(ValueError):
    """Raised when provider output is ungrounded or exceeds its role."""


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ExplanationSafetyError(f"Invalid deterministic fact: {name}")
    return value


def _number(value: Any, name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExplanationSafetyError(f"Invalid deterministic fact: {name}")
    return value


def build_plan_facts(
    plan: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, FactValue]:
    """Select trusted plan facts and deliberately omit filenames and metadata."""
    runner = plan.get("runner")
    if runner not in {"python", "nextflow"}:
        raise ExplanationSafetyError("Invalid deterministic fact: runner")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ExplanationSafetyError("Invalid deterministic fact: steps")
    if validation.get("status") != "valid":
        raise ExplanationSafetyError("Only a validated plan may be explained")

    return {
        "runner": runner,
        "read_count": _integer(validation.get("read_count"), "read_count", 1),
        "quality_threshold": _number(
            plan.get("quality_threshold"), "quality_threshold"
        ),
        "step_count": len(steps),
    }


def build_result_facts(result: Mapping[str, Any]) -> dict[str, FactValue]:
    """Select only deterministic QC measurements for result explanation."""
    return {
        "read_count": _integer(result.get("read_count"), "read_count", 1),
        "mean_base_quality": _number(
            result.get("mean_base_quality"), "mean_base_quality"
        ),
        "quality_threshold": _number(
            result.get("quality_threshold"), "quality_threshold"
        ),
        "low_quality_reads": _integer(
            result.get("low_quality_reads"), "low_quality_reads"
        ),
        "low_quality_percent": _number(
            result.get("low_quality_percent"), "low_quality_percent"
        ),
        "gc_percent": _number(result.get("gc_percent"), "gc_percent"),
        "n_bases": _integer(result.get("n_bases"), "n_bases"),
        "n_percent": _number(result.get("n_percent"), "n_percent"),
        "shortest_read": _integer(result.get("shortest_read"), "shortest_read", 1),
        "longest_read": _integer(result.get("longest_read"), "longest_read", 1),
        "read_length_variation_percent": _number(
            result.get("read_length_variation_percent"),
            "read_length_variation_percent",
        ),
    }


def _validate_summary(summary: str, facts: Mapping[str, FactValue]) -> str:
    cleaned = summary.strip()
    if not cleaned or len(cleaned) > 1000:
        raise ExplanationSafetyError("Explanation summary is empty or too long")
    if CONTROL_PATTERN.search(cleaned):
        raise ExplanationSafetyError("Explanation attempted to control the workflow")
    if CLINICAL_PATTERN.search(cleaned):
        raise ExplanationSafetyError("Clinical interpretation is not supported")

    allowed_numbers = [
        float(value)
        for value in facts.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    for token in NUMBER_PATTERN.findall(cleaned):
        number = float(token)
        if not any(abs(number - allowed) < 1e-9 for allowed in allowed_numbers):
            raise ExplanationSafetyError(
                f"Explanation introduced an unsupported number: {token}"
            )
    return cleaned


def _validate_draft(
    provider: ExplanationProvider,
    draft: ExplanationDraft,
    expected_kind: ExplanationKind,
    facts: Mapping[str, FactValue],
    required_keys: tuple[str, ...],
) -> GroundedExplanation:
    if draft.kind != expected_kind:
        raise ExplanationSafetyError("Explanation returned the wrong kind")
    if tuple(draft.evidence_keys) != required_keys:
        raise ExplanationSafetyError(
            "Explanation did not cite the required deterministic facts"
        )
    summary = _validate_summary(draft.summary, facts)
    evidence = {key: facts[key] for key in required_keys}
    label = (
        "Offline demo explanation — not a measurement or approval"
        if provider.name == "offline-demo"
        else "AI-generated explanation — not a measurement or approval"
    )
    return GroundedExplanation(
        label=label,
        provider=provider.name,
        kind=expected_kind,
        summary=summary,
        evidence=evidence,
    )


def explain_plan_safely(
    provider: ExplanationProvider,
    plan: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> GroundedExplanation:
    facts = build_plan_facts(plan, validation)
    draft = provider.explain_plan(MappingProxyType(facts))
    return _validate_draft(provider, draft, "plan", facts, PLAN_EVIDENCE_KEYS)


def explain_result_safely(
    provider: ExplanationProvider,
    result: Mapping[str, Any],
) -> GroundedExplanation:
    facts = build_result_facts(result)
    draft = provider.explain_result(MappingProxyType(facts))
    return _validate_draft(provider, draft, "result", facts, RESULT_EVIDENCE_KEYS)
