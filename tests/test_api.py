"""Tests for the API-layer gate that strips internal observability fields
(trace, classification) from responses when expose_trace is off."""

from unittest.mock import patch

from src.api import _gate_internal_fields
from src.models import BotResponse, TriageClassification


def _settings(expose_trace: bool):
    """Minimal stand-in for src.config.Settings with only the flag we care about."""

    class _S:
        pass

    s = _S()
    s.expose_trace = expose_trace
    return s


def _response_with_internals() -> BotResponse:
    return BotResponse(
        text="Hi there.",
        trace=["triage: intent=product_question, ..."],
        classification=TriageClassification(intent="product_question", urgency="low"),
    )


def test_gate_strips_trace_and_classification_when_expose_trace_off():
    with patch("src.api.get_settings", return_value=_settings(expose_trace=False)):
        gated = _gate_internal_fields(_response_with_internals())

    assert gated.trace == []
    assert gated.classification is None
    assert gated.text == "Hi there."  # user-visible fields untouched


def test_gate_preserves_trace_and_classification_when_expose_trace_on():
    response = _response_with_internals()

    with patch("src.api.get_settings", return_value=_settings(expose_trace=True)):
        gated = _gate_internal_fields(response)

    assert gated.trace == ["triage: intent=product_question, ..."]
    assert gated.classification is not None
    assert gated.classification.intent == "product_question"
