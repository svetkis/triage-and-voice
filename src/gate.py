"""Deterministic gate: routes triage results to voice personas with data injection."""

import json

from src.models import GateDecision, TriageResult
from src import repository


def apply_gate(triage: TriageResult) -> GateDecision:
    """Apply priority-ordered gate rules to a triage result.

    Returns a GateDecision with voice persona, injected data, handoff flag,
    and a reasoning trace for debugging.
    """
    decision = GateDecision()

    # ── Priority rule 1: safety_issue (returns immediately) ──────────────
    if triage.category == "safety_issue":
        decision.voice_persona = "empathetic_escalation"
        decision.human_handoff = True
        contact = repository.get_escalation_contact("safety_hotline")
        if contact:
            decision.injected_data["safety_hotline"] = json.dumps(contact)
        decision.reasoning_trace.append(
            "Category safety_issue → empathetic_escalation, human_handoff, safety contact injected. Returning immediately."
        )
        return decision

    # ── Priority rule 2: legal_threat ────────────────────────────────────
    if triage.category == "legal_threat":
        decision.voice_persona = "formal"
        decision.human_handoff = True
        contact = repository.get_escalation_contact("legal_department_email")
        if contact:
            decision.injected_data["legal_department_email"] = json.dumps(contact)
        decision.reasoning_trace.append(
            "Category legal_threat → formal, human_handoff, legal contact injected."
        )

    # ── Priority rule 3: out_of_scope ────────────────────────────────────
    elif triage.category == "out_of_scope":
        decision.voice_persona = "polite_refusal"
        decision.reasoning_trace.append(
            "Category out_of_scope → polite_refusal, no data injection."
        )

    # ── Default ──────────────────────────────────────────────────────────
    else:
        decision.voice_persona = "default_friendly"
        decision.reasoning_trace.append(
            f"Category {triage.category} → default_friendly."
        )

    # ── Data injection (applied for all except safety_issue) ─────────────
    if "refund_policy" in triage.requested_data:
        policy = repository.get_policy("refund_policy")
        if policy:
            decision.injected_data["refund_policy"] = policy
            decision.reasoning_trace.append("Injected refund_policy from repository.")

    if "order_status" in triage.requested_data:
        order_id = triage.extracted_entities.order_id
        if order_id:
            order = repository.get_order(order_id)
            if order:
                decision.injected_data["order_status"] = json.dumps(order)
                decision.reasoning_trace.append(
                    f"Injected order_status for {order_id}."
                )
            else:
                decision.injected_data["order_status"] = (
                    f"Order {order_id} not found in our system."
                )
                decision.reasoning_trace.append(
                    f"Order {order_id} not found, injected not-found message."
                )

    # ── Urgency override ─────────────────────────────────────────────────
    if triage.urgency == "critical" and not decision.human_handoff:
        decision.human_handoff = True
        decision.reasoning_trace.append(
            "Urgency critical → forced human_handoff."
        )

    return decision
