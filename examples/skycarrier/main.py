from pathlib import Path

from examples.skycarrier.resolver import resolve_category
from examples.skycarrier.sources import (
    BaggagePolicySource,
    FareTermsSource,
    FlightStatusInfoSource,
)
from src.gate.engine import Gate
from src.orchestrator import Pipeline

_CONFIG_PATH = Path(__file__).parent / "config" / "skycarrier.yaml"
_TRIAGE_PROMPT_PATH = Path(__file__).parent / "prompts" / "triage.md"


def build_gate() -> Gate:
    gate = Gate.from_yaml(_CONFIG_PATH)
    gate.register_source("fare_terms", FareTermsSource())
    gate.register_source("flight_status_info", FlightStatusInfoSource())
    gate.register_source("baggage_policy", BaggagePolicySource())
    gate.freeze()
    return gate


def build_pipeline() -> Pipeline:
    return Pipeline(
        gate=build_gate(),
        triage_prompt=_TRIAGE_PROMPT_PATH.read_text(encoding="utf-8"),
        resolver=resolve_category,
    )
