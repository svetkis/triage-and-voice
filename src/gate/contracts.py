"""Core protocols for Gate framework extension points."""

from typing import Protocol

from src.gate.decision import GateDecision
from src.models import TriageResult


class GateAction(Protocol):
    """Atomic post-triage operation. Writes into the decision accumulator."""

    def apply(
        self,
        triage: TriageResult,
        decision: GateDecision,
        params: dict,
    ) -> None: ...


class DataSource(Protocol):
    """Named data source referenced by inject_data actions."""

    def fetch(self, params: dict) -> str | None: ...
