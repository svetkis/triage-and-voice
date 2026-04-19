import json
import re
from pathlib import Path


_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_ORDER_ID_PATTERN = re.compile(r"ORD-\d+")


def _load_json(name: str) -> dict:
    return json.loads((_DATA_DIR / name).read_text(encoding="utf-8"))


class OrderSource:
    def __init__(self) -> None:
        self._orders = _load_json("orders.json")

    def fetch(self, params: dict) -> str | None:
        order_id = params.get("order_id")
        if not order_id or not _ORDER_ID_PATTERN.fullmatch(order_id):
            return "Order not found in our system." if order_id else None
        order = self._orders.get(order_id)
        if not order:
            return f"Order {order_id} not found in our system."
        tracking = f", tracking: {order['tracking']}" if order.get("tracking") else ""
        return f"Order {order_id}: {order['status']}{tracking}"


class PolicySource:
    def __init__(self) -> None:
        self._policies = _load_json("policies.json")

    def fetch(self, params: dict) -> str | None:
        return self._policies.get(params["policy_name"])


class ContactsSource:
    def __init__(self) -> None:
        self._contacts = _load_json("escalation_contacts.json")

    def fetch(self, params: dict) -> str | None:
        contact = self._contacts.get(params["contact_key"])
        if not contact:
            return None
        field = params.get("field")
        if field:
            return contact.get(field)
        parts = []
        if "phone" in contact:
            parts.append(f"Phone: {contact['phone']}")
        if "email" in contact:
            parts.append(f"Email: {contact['email']}")
        return ", ".join(parts)
