"""Unit tests for the SkyCarrier resolver — the fusion rule between triage and gate.

These tests cover the pure function that maps (intent, emotional_state) pairs
to gate categories. The rule that used to live inside the triage LLM prompt
("prefer bereavement_fare_under_distress if unsure") is now deterministic code
that can be exhaustively tested here.
"""

import pytest

from examples.skycarrier.resolver import resolve_category
from src.models import TriageClassification


def _classify(intent: str, state: str = "neutral") -> TriageClassification:
    return TriageClassification(
        intent=intent,
        urgency="low",
        user_emotional_state=state,
    )


# -- bereavement_fare: emotion is a second routing axis --------------------

def test_bereavement_neutral_routes_to_factual_branch():
    assert resolve_category(_classify("bereavement_fare", "neutral")) == "bereavement_fare_neutral"


def test_bereavement_distressed_routes_to_support_branch():
    assert (
        resolve_category(_classify("bereavement_fare", "distressed"))
        == "bereavement_fare_under_distress"
    )


@pytest.mark.parametrize("state", ["distressed", "frustrated", "angry"])
def test_bereavement_any_non_neutral_state_is_safe_defaulted_to_support(state):
    """Safe default: if distress signals are present, route to the supportive persona.

    This rule used to live as prose in the triage prompt; now it is enforced
    by deterministic code so the LLM cannot drop it under pressure.
    """
    assert (
        resolve_category(_classify("bereavement_fare", state))
        == "bereavement_fare_under_distress"
    )


# -- other intents: emotion is NOT a routing axis --------------------------

@pytest.mark.parametrize("state", ["neutral", "distressed", "frustrated", "angry"])
def test_flight_status_ignores_emotional_state(state):
    assert resolve_category(_classify("flight_status", state)) == "flight_status"


@pytest.mark.parametrize("state", ["neutral", "distressed", "frustrated", "angry"])
def test_baggage_issue_ignores_emotional_state(state):
    assert resolve_category(_classify("baggage_issue", state)) == "baggage_issue"


def test_out_of_scope_passes_through():
    assert resolve_category(_classify("out_of_scope", "angry")) == "out_of_scope"


# -- unknown intent: passes through (gate falls back to default) -----------

def test_unknown_intent_passes_through_to_gate_default():
    assert resolve_category(_classify("something_unseen")) == "something_unseen"
