from src.gate.contracts import DataSource
from src.gate.decision import GateDecision
from src.models import TriageResult


class InjectDataAction:
    def __init__(self, sources: dict[str, DataSource]):
        self._sources = sources

    def apply(self, triage: TriageResult, decision: GateDecision, params: dict) -> None:
        locus = params.get("_locus", "<unknown>")
        source_name = params["source"]
        key = params["key"]
        if source_name not in self._sources:
            raise KeyError(f"unknown data source {source_name!r} at {locus}")

        value = self._sources[source_name].fetch(
            {k: v for k, v in params.items() if k not in ("source", "key", "_locus")}
        )
        if value is not None:
            decision.payload[key] = value
            decision.reasoning_trace.append(
                f"inject_data: {source_name}→{key}"
            )
        else:
            decision.reasoning_trace.append(
                f"inject_data: {source_name}→{key} returned None, skipped"
            )
