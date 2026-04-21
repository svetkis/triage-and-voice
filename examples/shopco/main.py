from pathlib import Path

from examples.shopco.resolver import resolve_category
from examples.shopco.sources import ContactsSource, OrderSource, PolicySource
from src.gate.engine import Gate
from src.orchestrator import Pipeline

_CONFIG_PATH = Path(__file__).parent / "config" / "shopco.yaml"
_TRIAGE_PROMPT_PATH = Path(__file__).parent / "prompts" / "triage.md"


def build_gate() -> Gate:
    gate = Gate.from_yaml(_CONFIG_PATH)
    gate.register_source("orders", OrderSource())
    gate.register_source("policies", PolicySource())
    gate.register_source("escalation_contacts", ContactsSource())
    gate.freeze()
    return gate


def build_pipeline() -> Pipeline:
    return Pipeline(
        gate=build_gate(),
        triage_prompt=_TRIAGE_PROMPT_PATH.read_text(encoding="utf-8"),
        resolver=resolve_category,
    )
