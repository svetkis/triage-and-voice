from pathlib import Path

from examples.shopco.sources import ContactsSource, OrderSource, PolicySource
from src.gate.engine import Gate

_CONFIG_PATH = Path(__file__).parent / "config" / "shopco.yaml"


def build_gate() -> Gate:
    gate = Gate.from_yaml(_CONFIG_PATH)
    gate.register_source("orders", OrderSource())
    gate.register_source("policies", PolicySource())
    gate.register_source("escalation_contacts", ContactsSource())
    gate.freeze()
    return gate
