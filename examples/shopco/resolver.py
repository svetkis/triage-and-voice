"""ShopCo resolver — fuses (intent, harm_state) into a gate category.

The triage LLM classifies three independent axes: `intent`, `user_emotional_state`,
and `harm_state`. This module is the deterministic code that maps the pair
(intent, harm_state) to the gate category used by `config/shopco.yaml`.

Why fusion lives here, not in the triage prompt:
- The rule is testable as a pure function (no LLM needed).
- The safe-default ("if active harm is signalled, route to crisis regardless
  of what the user says they want") is enforced by code, not by prompt
  discipline that the LLM can break under sycophancy or completion bias.
- The triage prompt stays narrow — classify each axis from a closed list —
  which keeps each classification task small and independently auditable.

Mirrors the ASPCA / Poison Control / CPSC triage pattern: the first question
operators ask is "is anyone hurt right now?", and that answer, not the
commercial intent, decides the lane.
"""

from src.models import TriageClassification


def resolve_category(classification: TriageClassification) -> str:
    """Map (intent, harm_state) → gate category for ShopCo.

    Harm-state routing takes priority over intent — an acute or unclear harm
    signal sends the case to a safety lane regardless of what the user
    explicitly requested (refund, order status, etc). This is the code-enforced
    safe-default: the resolver will not let commercial intent override a live
    safety signal that triage has already captured.
    """
    if classification.harm_state == "acute":
        return "crisis_handoff"
    if classification.harm_state == "unclear":
        return "ask_harm_clarification"
    if classification.harm_state == "past" and classification.intent == "safety_issue":
        return "priority_complaint"
    return classification.intent
