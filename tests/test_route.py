from datetime import date, timedelta

from core.models import Verdict
from core.route import route


def make_verdict(**overrides) -> Verdict:
    values = {
        "document_type": "bill",
        "action_required": True,
        "two_line_verdict": "Take action.",
        "confidence": 0.9,
    }
    values.update(overrides)
    return Verdict(**values)


def test_eob_without_action_is_silent() -> None:
    assert route(
        make_verdict(document_type="eob", action_required=False),
        [],
    ) == "SILENT"


def test_low_confidence_is_unsure() -> None:
    assert route(make_verdict(confidence=0.5), []) == "UNSURE"


def test_matching_prior_amount_is_duplicate() -> None:
    assert route(make_verdict(amount_due=25.00), [("bill", 25.009)]) == "DUPLICATE"


def test_actionable_without_deadline_is_weekly() -> None:
    assert route(make_verdict(), []) == "WEEKLY"


def test_legal_letter_due_in_three_days_is_urgent() -> None:
    deadline = (date.today() + timedelta(days=3)).isoformat()
    assert route(make_verdict(document_type="legal", deadline=deadline), []) == "URGENT"


def test_bill_due_in_thirty_days_is_soon() -> None:
    deadline = (date.today() + timedelta(days=30)).isoformat()
    assert route(make_verdict(deadline=deadline), []) == "SOON"
