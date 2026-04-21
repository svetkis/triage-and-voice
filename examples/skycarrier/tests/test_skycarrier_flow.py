"""Acceptance tests for SkyCarrier: demonstrates the framework's core thesis —
(intent, emotional_state) is the real routing key. The resolver fuses the two
axes into a gate category; the gate then dispatches deterministically. The fare
terms payload is identical in both branches. No LLM is invoked; we assert on
the Gate decision only."""

import pytest

from examples.skycarrier.main import build_gate
from examples.skycarrier.resolver import resolve_category
from src.models import ExtractedEntities, TriageClassification, TriageResult


@pytest.fixture(scope="module")
def gate():
    return build_gate()


def _triage(**overrides) -> TriageResult:
    """Build a TriageResult directly — bypasses the resolver, used when we want
    to test gate behaviour on an already-fused category."""
    defaults = {
        "category": "bereavement_fare_neutral",
        "urgency": "low",
        "requested_data": [],
        "extracted_entities": ExtractedEntities(),
        "user_emotional_state": "neutral",
    }
    defaults.update(overrides)
    return TriageResult(**defaults)


def _classify_and_resolve(**overrides) -> TriageResult:
    """Build a TriageClassification, run it through the resolver, return a
    TriageResult as the Pipeline would. Use this when the test is about the
    (intent, emotional_state) → persona linkage, not just gate dispatch."""
    defaults = {
        "intent": "bereavement_fare",
        "urgency": "low",
        "requested_data": [],
        "extracted_entities": ExtractedEntities(),
        "user_emotional_state": "neutral",
    }
    defaults.update(overrides)
    classification = TriageClassification(**defaults)
    return TriageResult(
        category=resolve_category(classification),
        urgency=classification.urgency,
        requested_data=classification.requested_data,
        extracted_entities=classification.extracted_entities,
        user_emotional_state=classification.user_emotional_state,
    )


# -- 1. distressed passenger routes to the supportive persona ---------------

def test_bereavement_under_distress_uses_bereavement_support_persona(gate):
    decision = gate.decide(_triage(
        category="bereavement_fare_under_distress",
        urgency="high",
        user_emotional_state="distressed",
    ))
    assert decision.voice_call.persona == "bereavement_support"
    assert "bereavement_fare" in decision.payload


# -- 2. neutral inquiry routes to the factual persona ----------------------

def test_bereavement_neutral_uses_factual_persona(gate):
    decision = gate.decide(_triage(category="bereavement_fare_neutral"))
    assert decision.voice_call.persona == "factual_fare_terms"
    assert "bereavement_fare" in decision.payload


# -- 3. fare terms payload is identical across both branches ---------------

def test_same_fare_terms_payload_regardless_of_distress(gate):
    distressed = gate.decide(_triage(
        category="bereavement_fare_under_distress",
        user_emotional_state="distressed",
    ))
    neutral = gate.decide(_triage(category="bereavement_fare_neutral"))
    assert distressed.payload["bereavement_fare"] == neutral.payload["bereavement_fare"]


# -- 4. fare terms explicitly forbid retroactive claims (anti-sycophancy) --

def test_fare_terms_contain_explicit_timing_constraint(gate):
    decision = gate.decide(_triage(
        category="bereavement_fare_under_distress",
        user_emotional_state="distressed",
    ))
    terms = decision.payload["bereavement_fare"].lower()
    assert "before" in terms and "departure" in terms
    assert "retroactive" in terms


# -- 5. critical urgency still forces handoff (override path) --------------

def test_critical_urgency_forces_handoff(gate):
    decision = gate.decide(_triage(
        category="bereavement_fare_under_distress",
        urgency="critical",
        user_emotional_state="distressed",
    ))
    assert decision.handoff is True


# -- 6. flight_status — verified channel redirect, never invented status ---

def test_flight_status_uses_factual_general_persona(gate):
    decision = gate.decide(_triage(category="flight_status"))
    assert decision.voice_call.persona == "factual_general_info"
    assert "flight_status_info" in decision.payload


def test_flight_status_info_redirects_to_live_channel(gate):
    decision = gate.decide(_triage(category="flight_status"))
    info = decision.payload["flight_status_info"].lower()
    assert "app" in info or "website" in info


# -- 7. baggage_issue — policy from data, no invented compensation numbers -

def test_baggage_issue_uses_factual_general_persona(gate):
    decision = gate.decide(_triage(category="baggage_issue"))
    assert decision.voice_call.persona == "factual_general_info"
    assert "baggage_policy" in decision.payload


def test_baggage_policy_points_to_services_desk(gate):
    decision = gate.decide(_triage(category="baggage_issue"))
    policy = decision.payload["baggage_policy"].lower()
    assert "baggage services" in policy


# -- 8. unknown category falls through to default --------------------------

def test_unknown_category_falls_back_to_factual_persona(gate):
    decision = gate.decide(_triage(category="something_not_configured"))
    assert decision.voice_call.persona == "factual_fare_terms"


# -- 9. two-axes linkage (the article's core thesis) -----------------------
# Same intent, different emotional_state → different persona. This linkage
# is what the paper calls "emotional state as a second routing axis". It is
# mediated by the resolver, not hard-coded into category names passed to the
# gate. These tests go through classify_and_resolve() so the linkage is real,
# not simulated by the test fixture.

def test_same_intent_distressed_routes_to_support_persona(gate):
    decision = gate.decide(
        _classify_and_resolve(intent="bereavement_fare", user_emotional_state="distressed")
    )
    assert decision.voice_call.persona == "bereavement_support"


def test_same_intent_neutral_routes_to_factual_persona(gate):
    decision = gate.decide(
        _classify_and_resolve(intent="bereavement_fare", user_emotional_state="neutral")
    )
    assert decision.voice_call.persona == "factual_fare_terms"


@pytest.mark.parametrize("state", ["distressed", "frustrated", "angry"])
def test_same_intent_any_non_neutral_emotion_triggers_safe_default(gate, state):
    """If triage detects ANY distress signal, the resolver forces the supportive
    persona. This is the safe-default that used to live as prose in the triage
    prompt and is now enforced by code."""
    decision = gate.decide(
        _classify_and_resolve(intent="bereavement_fare", user_emotional_state=state)
    )
    assert decision.voice_call.persona == "bereavement_support"
