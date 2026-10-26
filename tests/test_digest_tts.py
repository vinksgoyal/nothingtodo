from datetime import date, timedelta

from core.digest import render_digest
from core.models import Verdict
from core.tts import verdict_to_script


def make_verdict(**overrides) -> Verdict:
    values = {
        "document_type": "bill",
        "action_required": True,
        "two_line_verdict": "Review this document.",
        "confidence": 0.9,
    }
    values.update(overrides)
    return Verdict(**values)


def test_silent_only_digest_is_empty():
    content = render_digest(
        [{"tier": "SILENT", "verdict": make_verdict(action_required=False), "snoozes": 0}]
    )
    assert "Nothing needed you." in content


def test_digest_orders_urgent_before_unsure():
    content = render_digest(
        [
            {"tier": "UNSURE", "verdict": make_verdict(confidence=0.5), "snoozes": 0},
            {"tier": "URGENT", "verdict": make_verdict(), "snoozes": 0},
        ]
    )
    assert content.index("## Urgent") < content.index("## Couldn't read")


def test_verdict_script_spells_small_amount():
    script = verdict_to_script(make_verdict(amount_due=47.0))
    assert "forty seven" in script
    assert "47" not in script


def test_verdict_script_says_soon_for_near_deadline():
    script = verdict_to_script(
        make_verdict(deadline=(date.today() + timedelta(days=3)).isoformat())
    )
    assert "soon" in script
