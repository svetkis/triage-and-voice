from src.gate.decision import GateDecision, VoiceCallSpec
from src.models import TriageResult


class VoiceResponseAction:
    def apply(self, triage: TriageResult, decision: GateDecision, params: dict) -> None:
        decision.voice_call = VoiceCallSpec(
            persona=params["persona"],
            inject_data_keys=params.get("inject_data", []),
        )
        decision.reasoning_trace.append(
            f"voice_response: persona={decision.voice_call.persona!r}"
        )
