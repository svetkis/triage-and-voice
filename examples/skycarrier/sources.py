import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _load_json(name: str) -> dict:
    return json.loads((_DATA_DIR / name).read_text(encoding="utf-8"))


class FareTermsSource:
    """Returns fare terms for a given fare type as a plain-text block."""

    def __init__(self) -> None:
        self._fares = _load_json("bereavement_fare.json")

    def fetch(self, params: dict) -> str | None:
        fare_type = params.get("fare_type")
        if not fare_type:
            return None
        return self._fares.get(fare_type)


class FlightStatusInfoSource:
    """Returns generic flight-status information (how to check, where to go).

    Deliberately does NOT return per-flight status — real-time status lives in
    a live system the user can access directly. The pattern here is to redirect
    rather than to fabricate specific statuses.
    """

    def __init__(self) -> None:
        self._info = _load_json("flight_status_info.json")

    def fetch(self, params: dict) -> str | None:
        info_type = params.get("info_type")
        if not info_type:
            return None
        return self._info.get(info_type)


class BaggagePolicySource:
    """Returns the baggage-issue policy text for a given policy key."""

    def __init__(self) -> None:
        self._policies = _load_json("baggage_policy.json")

    def fetch(self, params: dict) -> str | None:
        policy_key = params.get("policy_key")
        if not policy_key:
            return None
        return self._policies.get(policy_key)
