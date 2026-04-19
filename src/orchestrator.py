"""Orchestrator — chains triage → gate → voice into a complete pipeline.

A `Pipeline` is the composition root for one vertical: it owns the (frozen) Gate
instance and the triage system prompt. Entry points (`api.py`, `run_eval.py`) or
tests build a Pipeline via the vertical's `build_pipeline()` factory and then call
`pipeline.process_message(...)` for each incoming request.
"""

import logging

from src.gate.engine import Gate
from src.models import BotResponse, ChatMessage
from src.triage import TriageFailure, run_triage
from src.voice import VoiceFailure, generate_response

logger = logging.getLogger(__name__)

_FALLBACK_TEXT = (
    "I'm sorry, I'm having trouble processing your request. "
    "Let me connect you with a human agent."
)


class Pipeline:
    def __init__(self, gate: Gate, triage_prompt: str):
        self._gate = gate
        self._triage_prompt = triage_prompt

    async def process_message(self, user_message: str, history: list[ChatMessage]) -> BotResponse:
        """Process a user message through the triage → gate → voice pipeline."""
        trace: list[str] = []

        try:
            # 1. Triage
            triage_result = await run_triage(user_message, history, self._triage_prompt)
            trace.append(f"triage: category={triage_result.category}, urgency={triage_result.urgency}")

            # 2. Gate
            decision = self._gate.decide(triage_result)
            trace.extend(decision.reasoning_trace)

            # 3. Voice (optional — only if voice_response action fired)
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
        )
