"""Repository for static reference data (orders, policies, escalation contacts)."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


_orders: dict = _load_json("orders.json")
_policies: dict = _load_json("policies.json")
_escalation_contacts: dict = _load_json("escalation_contacts.json")


def get_order(order_id: str) -> dict | None:
    """Return order dict by ID, or None if not found."""
    return _orders.get(order_id)


def get_policy(policy_name: str) -> str | None:
    """Return policy text by name, or None if not found."""
    return _policies.get(policy_name)


def get_escalation_contact(contact_type: str) -> dict | None:
    """Return escalation contact dict by type, or None if not found."""
    return _escalation_contacts.get(contact_type)
