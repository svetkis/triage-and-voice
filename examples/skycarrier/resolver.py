"""SkyCarrier resolver — fuses (intent, emotional_state) into a gate category.

The triage LLM is asked to classify two independent axes: `intent` and
`user_emotional_state`. This module is the deterministic code that maps that
pair to the gate category used by `config/skycarrier.yaml`.

Why fusion lives here, not in the triage prompt:
- The rule is testable as a pure function (no LLM needed).
- The safe-default ("when in doubt prefer the supportive persona") is enforced
  by code, not by prompt discipline that the LLM can break under pressure.
- The triage prompt stays narrow — classify each axis from a closed list —
  which keeps each classification task small and less susceptible to
  sycophancy or completion bias.
"""

from src.models import TriageClassification

_NON_NEUTRAL_STATES = {"distressed", "frustrated", "angry"}


def resolve_category(classification: TriageClassification) -> str:
    """Map (intent, emotional_state) → gate category for SkyCarrier.

    For `bereavement_fare`, any non-neutral emotional state routes to the
    supportive persona — this is the safe default when distress signals are
    present but classification is uncertain. Other intents pass through
    unchanged (emotion is not a routing axis for them).
    """
    intent = classification.intent
    state = classification.user_emotional_state

    if intent == "bereavement_fare":
        if state in _NON_NEUTRAL_STATES:
            return "bereavement_fare_under_distress"
        return "bereavement_fare_neutral"

    return intent
