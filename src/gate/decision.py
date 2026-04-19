from pydantic import BaseModel


class VoiceCallSpec(BaseModel):
    persona: str
    inject_data_keys: list[str] = []


class GateDecision(BaseModel):
    handoff: bool = False
    handoff_reason: str | None = None
    payload: dict[str, str] = {}
    voice_call: VoiceCallSpec | None = None
    reasoning_trace: list[str] = []
