import pytest
from pydantic import ValidationError

from core.models import Verdict


def valid_verdict(**overrides) -> Verdict:
    values = {
        "document_type": "bill",
        "action_required": True,
        "two_line_verdict": "Pay this bill.",
        "confidence": 0.9,
    }
    values.update(overrides)
    return Verdict(**values)


def test_valid_verdict_parses() -> None:
    assert valid_verdict().document_type == "bill"


def test_invalid_deadline_raises() -> None:
    with pytest.raises(ValidationError):
        valid_verdict(deadline="Nov 3")


def test_empty_deadline_becomes_none() -> None:
    assert valid_verdict(deadline="").deadline is None


def test_two_line_verdict_collapses_newlines() -> None:
    assert valid_verdict(two_line_verdict="First\n\nSecond").two_line_verdict == (
        "First Second"
    )


def test_confidence_above_one_raises() -> None:
    with pytest.raises(ValidationError):
        valid_verdict(confidence=1.5)
