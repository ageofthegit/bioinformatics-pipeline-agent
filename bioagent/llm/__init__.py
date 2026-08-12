"""Optional explanation providers for the learning workflow."""

from bioagent.llm.base import ExplanationProvider
from bioagent.llm.fake import OfflineDemoProvider


def create_explanation_provider(name: str) -> ExplanationProvider | None:
    if name == "none":
        return None
    if name == "offline-demo":
        return OfflineDemoProvider()
    raise ValueError(f"Unknown explanation provider: {name}")


__all__ = ["ExplanationProvider", "create_explanation_provider"]
