"""Orchestrator — chains triage → resolve → gate → voice into a complete pipeline.

A `Pipeline` is the composition root for one vertical: it owns the (frozen) Gate
instance, the triage system prompt, and a domain-specific resolver that fuses
the two triage axes (intent + emotional_state) into a gate category. Entry
points (`api.py`, `run_eval.py`) or tests build a Pipeline via the vertical's
`build_pipeline()` factory and then call `pipeline.process_message(...)` for
each incoming request.
"""

import logging
from typing import Callable

from src.gate.engine import Gate
from src.models import BotResponse, ChatMessage, TriageClassification, TriageResult
from src.triage import TriageFailure, run_triage
from src.voice import VoiceFailure, generate_response

logger = logging.getLogger(__name__)

_FALLBACK_TEXT = (
    "I'm sorry, I'm having trouble processing your request. "
    "Let me connect you with a human agent."
)

Resolver = Callable[[TriageClassification], str]


def _identity_resolver(classification: TriageClassification) -> str:
    """Default resolver: intent is used as-is as the gate category.

    Appropriate for verticals where emotional_state does not alter routing
    (e.g. ShopCo). Verticals where emotion is a second routing axis supply
    their own resolver (e.g. SkyCarrier).
    """
    return classification.intent


class Pipeline:
    def __init__(
        self,
        gate: Gate,
        triage_prompt: str,
        resolver: Resolver = _identity_resolver,
    ):
        self._gate = gate
        self._triage_prompt = triage_prompt
        self._resolver = resolver

    async def process_message(self, user_message: str, history: list[ChatMessage]) -> BotResponse:
        """Process a user message through the triage → resolve → gate → voice pipeline."""
        trace: list[str] = []
        classification: TriageClassification | None = None

        try:
            # 1. Triage — two independent axes
            classification = await run_triage(user_message, history, self._triage_prompt)
            trace.append(
                f"triage: intent={classification.intent}, "
                f"emotional_state={classification.user_emotional_state}, "
                f"harm_state={classification.harm_state}, "
                f"urgency={classification.urgency}"
            )

            # 2. Resolve — fuse (intent, emotional_state) → category
            category = self._resolver(classification)
            trace.append(f"resolve: category={category}")
            triage_result = TriageResult(
                category=category,
                urgency=classification.urgency,
                requested_data=classification.requested_data,
                extracted_entities=classification.extracted_entities,
                user_emotional_state=classification.user_emotional_state,
            )

            # 3. Gate
            decision = self._gate.decide(triage_result)
            trace.extend(decision.reasoning_trace)

            # 4. Voice (optional — only if voice_response action fired)
            if decision.voice_call is not None:
                persona = decision.voice_call.persona
                persona_path = self._gate.persona_template_path(persona)
                response_text = await generate_response(
                    decision.voice_call,
                    decision.payload,
                    persona_template_path=persona_path,
                    user_message=user_message,
                    history=history,
                )
                trace.append(f"voice: persona={persona}")
            else:
                # No voice_response action — assemble reply from payload only.
                response_text = "\n".join(decision.payload.values())

            return BotResponse(
                text=response_text,
                human_handoff=decision.handoff,
                trace=trace,
                classification=classification,
            )

        except TriageFailure as exc:
            logger.warning("triage failed: %s", exc)
            trace.append(f"triage failed: {exc}")

        except VoiceFailure as exc:
            logger.warning("voice failed: %s", exc)
            trace.append(f"voice failed: {exc}")

        except Exception as exc:
            logger.exception("unexpected pipeline failure")
            trace.append(f"pipeline error: {type(exc).__name__}: {exc}")

        return BotResponse(
            text=_FALLBACK_TEXT,
            human_handoff=True,
            trace=trace,
            classification=classification,
        )
