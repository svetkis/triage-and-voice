from pathlib import Path

from src.gate.actions.handoff import HandoffAction
from src.gate.actions.inject_data import InjectDataAction
from src.gate.actions.voice_response import VoiceResponseAction
from src.gate.config import GateConfig, load_config
from src.gate.contracts import DataSource, GateAction
from src.gate.decision import GateDecision
from src.models import TriageResult


class Gate:
    def __init__(self, config: GateConfig):
        self._config = config
        self._sources: dict[str, DataSource] = {}
        self._actions: dict[str, GateAction] = {}
        self._register_builtins()

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Gate":
        return cls(load_config(path))

    def _register_builtins(self) -> None:
        self._actions["handoff"] = HandoffAction()
        self._actions["voice_response"] = VoiceResponseAction()
        self._actions["inject_data"] = InjectDataAction(self._sources)

    def register_source(self, name: str, source: DataSource) -> None:
        self._sources[name] = source

    def register_action(self, name: str, action: GateAction) -> None:
        self._actions[name] = action

    def decide(self, triage: TriageResult) -> GateDecision:
        decision = GateDecision()
        rule = self._config.categories.get(triage.category) or self._config.default
        for action_spec in rule.actions:
            self._run_action(action_spec, triage, decision)
        self._apply_overrides(triage, decision)
        return decision

    def _run_action(self, spec, triage, decision):
        action = self._actions.get(spec.type)
        if action is None:
            raise KeyError(f"unknown action type: {spec.type!r}")
        action.apply(triage, decision, spec.params)

    def _apply_overrides(self, triage: TriageResult, decision: GateDecision) -> None:
        forced = self._config.overrides.force_handoff_on_urgency
        if triage.urgency in forced and not decision.handoff:
            decision.handoff = True
            decision.handoff_reason = f"override:urgency={triage.urgency}"
            decision.reasoning_trace.append(
                f"override: forcing handoff due to urgency={triage.urgency!r}"
            )
