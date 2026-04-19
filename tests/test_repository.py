from src.repository import get_order, get_policy, get_escalation_contact


def test_get_order_existing_returns_dict_with_status():
    result = get_order("ORD-001")
    assert isinstance(result, dict)
    assert "status" in result


def test_get_order_missing_returns_none():
    result = get_order("ORD-999")
    assert result is None


def test_get_policy_refund_contains_14():
    result = get_policy("refund_policy")
    assert isinstance(result, str)
    assert "14" in result


def test_get_policy_missing_returns_none():
    result = get_policy("nonexistent_policy")
    assert result is None


def test_get_escalation_contact_safety_hotline_has_email():
    result = get_escalation_contact("safety_hotline")
    assert isinstance(result, dict)
    assert "email" in result


def test_get_escalation_contact_missing_returns_none():
    result = get_escalation_contact("nonexistent_contact")
    assert result is None
