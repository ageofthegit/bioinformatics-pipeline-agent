"""Provider-neutral data structures for grounded explanation output."""

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Protocol, TypeAlias


FactValue: TypeAlias = str | int | float | bool
ExplanationKind: TypeAlias = Literal["plan", "result"]


@dataclass(frozen=True)
class ExplanationDraft:
    """Structured provider response before deterministic safety checks."""

    kind: ExplanationKind
    summary: str
    evidence_keys: tuple[str, ...]


@dataclass(frozen=True)
class GroundedExplanation:
    """Validated explanation with evidence copied from deterministic facts."""

    label: str
    provider: str
    kind: ExplanationKind
    summary: str
    evidence: dict[str, FactValue]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExplanationProvider(Protocol):
    """Narrow interface implemented by offline or future external providers."""

    name: str

    def explain_plan(self, facts: Mapping[str, FactValue]) -> ExplanationDraft: ...

    def explain_result(self, facts: Mapping[str, FactValue]) -> ExplanationDraft: ...
