from src.gate.decision import GateDecision
from src.models import TriageResult


class HandoffAction:
    def apply(self, triage: TriageResult, decision: GateDecision, params: dict) -> None:
        decision.handoff = True
        decision.handoff_reason = params.get("reason")
        decision.reasoning_trace.append(
            f"handoff: reason={decision.handoff_reason!r}"
        )
