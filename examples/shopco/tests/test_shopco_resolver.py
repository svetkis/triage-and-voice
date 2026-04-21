"""Unit tests for the ShopCo resolver — the fusion rule between triage and gate.

These tests cover the pure function that maps (intent, harm_state) pairs to
gate categories. The safety-net behaviour — "if active harm is signalled,
route to crisis regardless of what the user says they want" — is enforced
here as deterministic code so it can be exhaustively tested and cannot be
broken by LLM sycophancy under emotional pressure.

The three demo fixtures (B/A/Clarify) represent the same scenario family —
child ingested a piece of a ShopCo toy — under three different harm-state
classifications, producing three different routes.
"""

import pytest

from examples.shopco.resolver import resolve_category
from src.models import TriageClassification


def _classify(
    intent: str,
    harm_state: str = "none",
    emotional_state: str = "neutral",
    urgency: str = "medium",
) -> TriageClassification:
    return TriageClassification(
        intent=intent,
        urgency=urgency,
        user_emotional_state=emotional_state,
        harm_state=harm_state,
    )


# -- B: acute harm → crisis_handoff ---------------------------------------

def test_fixture_b_acute_plus_distressed_routes_to_crisis_handoff():
    """B-fixture: parent in panic, child just ingested a piece, live incident."""
    assert (
        resolve_category(_classify(
            intent="safety_issue",
            harm_state="acute",
            emotional_state="distressed",
            urgency="critical",
        ))
        == "crisis_handoff"
    )


@pytest.mark.parametrize("intent", [
    "safety_issue", "refund_request", "order_status", "complaint", "product_question",
])
def test_acute_harm_overrides_any_intent(intent):
    """Safe-default: acute harm routes to crisis regardless of commercial intent.

    If a user in acute distress happens to frame the message around a refund
    ("my kid just ate the toy and I want my money back"), the resolver must
    NOT honour the refund intent. Crisis routing is non-negotiable once
    triage has flagged active harm.
    """
    assert resolve_category(_classify(intent=intent, harm_state="acute")) == "crisis_handoff"


# -- A: past harm + safety_issue → priority_complaint ---------------------

def test_fixture_a_past_plus_frustrated_routes_to_priority_complaint():
    """A-fixture: same incident, days later, child is fine, parent wants followup."""
    assert (
        resolve_category(_classify(
            intent="safety_issue",
            harm_state="past",
            emotional_state="frustrated",
            urgency="high",
        ))
        == "priority_complaint"
    )


def test_past_harm_with_non_safety_intent_passes_through():
    """Past harm mentioned incidentally with an unrelated intent does not hijack routing.

    Example: user asking about an unrelated order status who happens to mention
    a resolved past injury should still be routed by the order_status intent.
    """
    assert (
        resolve_category(_classify(intent="order_status", harm_state="past"))
        == "order_status"
    )


# -- Clarify: unclear harm → ask_harm_clarification -----------------------

def test_fixture_clarify_unclear_routes_to_ask_harm_clarification():
    """Clarify-fixture: ambiguous harm signal — resolver refuses to guess."""
    assert (
        resolve_category(_classify(
            intent="safety_issue",
            harm_state="unclear",
            emotional_state="frustrated",
            urgency="critical",
        ))
        == "ask_harm_clarification"
    )


@pytest.mark.parametrize("intent", [
    "safety_issue", "refund_request", "order_status", "complaint", "product_question",
])
def test_unclear_harm_overrides_any_intent(intent):
    """Safe-default: unclear harm always triggers a clarification question, not a guess.

    Mirrors real support-script logic: when the operator cannot confirm whether
    anyone is hurt, they ask — they do not route the case to a commercial lane
    on the assumption that everything is fine.
    """
    assert (
        resolve_category(_classify(intent=intent, harm_state="unclear"))
        == "ask_harm_clarification"
    )


# -- harm_state=none: identity pass-through (existing ShopCo behaviour) ---

@pytest.mark.parametrize("intent", [
    "order_status", "refund_request", "product_question", "complaint",
    "legal_threat", "safety_issue", "out_of_scope",
])
def test_harm_state_none_passes_intent_through(intent):
    """Without a harm signal, the resolver falls back to identity behaviour."""
    assert resolve_category(_classify(intent=intent, harm_state="none")) == intent


def test_unknown_intent_with_no_harm_passes_through_to_gate_default():
    """Preserves identity-resolver behaviour for unseen intents."""
    assert resolve_category(_classify(intent="something_unseen", harm_state="none")) == "something_unseen"
