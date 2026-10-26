import json

from core.classify import classify


def ollama_response(**values) -> dict:
    return {"message": {"content": json.dumps(values)}}


def test_bill_with_high_confidence_uses_triage(monkeypatch) -> None:
    def chat(**kwargs):
        return ollama_response(
            document_type="bill",
            action_required=True,
            two_line_verdict="Pay this bill.",
            confidence=0.9,
        )

    monkeypatch.setattr("ollama.chat", chat)

    verdict, tier = classify("This is a sufficiently long document for testing.")

    assert verdict.document_type == "bill"
    assert tier == "triage"


def test_low_confidence_triage_escalates(monkeypatch) -> None:
    responses = iter(
        [
            ollama_response(
                document_type="bill",
                action_required=True,
                two_line_verdict="Review this bill.",
                confidence=0.5,
            ),
            ollama_response(
                document_type="bill",
                action_required=True,
                two_line_verdict="Pay this bill.",
                confidence=0.9,
            ),
        ]
    )

    monkeypatch.setattr("ollama.chat", lambda **kwargs: next(responses))

    verdict, tier = classify("This is a sufficiently long document for testing.")

    assert verdict.confidence == 0.9
    assert tier == "escalate"


def test_empty_text_is_ocr_rejected(monkeypatch) -> None:
    def fail_if_called(**kwargs):
        raise AssertionError("ollama.chat should not be called")

    monkeypatch.setattr("ollama.chat", fail_if_called)

    verdict, tier = classify("")

    assert verdict.confidence == 0.0
    assert tier == "ocr_rejected"
